import logging
from datetime import timedelta
from numbers import Number
from typing import Final, Any

import voluptuous as vol
from aiohttp import ClientConnectionError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ID,
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    CONF_PASSWORD,
    CONF_MODE,
    EVENT_HOMEASSISTANT_STARTED,
    Platform, EntityCategory
)
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry, device_registry as device_reg
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from homeassistant.helpers.typing import UNDEFINED
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from smllib.sml import ObisCode

from .const import (
    DOMAIN,
    MANUFACTURE,

    CONF_NODE_NUMBER,
    CONF_USE_POLLING,
    CONF_IGNORE_READING_ERRORS,

    DEFAULT_USE_POLLING,
    DEFAULT_SCAN_INTERVAL,
    MODE_3_SML_1_04,

    CONFIG_VERSION,
    CONFIG_MINOR_VERSION,

    DATA_KEY,
    METRICS_KEY,
    NODE_METRICS,
    NODE_METRIC_PREFIX,
    NODE_METRIC_MAP,
    HUB_METRICS,
    HUB_METRIC_PREFIX,
    SensorTag,
    UNKNOWN_SERIAL,
)
from .entity import CustomFriendlyNameEntity
from .tibber_client import TibberLocalBridge

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS: Final = [Platform.SENSOR]
WEBSOCKET_WATCHDOG_INTERVAL: Final = timedelta(seconds=64)
MASKED_KEYS: Final = ("host", "password")

def mask_map(d: dict) -> dict:
    # returns a copy - so we will never modify the data of the config_entry itself
    return {k: mask_map(v) if isinstance(v, dict) else ("<MASKED>" if k.lower() in MASKED_KEYS else v)
            for k, v in d.items()}

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    if config_entry.version < CONFIG_VERSION:
        if config_entry.data is not None and len(config_entry.data) > 0:
            _LOGGER.debug(f"async_migrate_entry(): Migrating configuration from version {config_entry.version}.{config_entry.minor_version}")
            if config_entry.options is not None and len(config_entry.options):
                new_data = {**config_entry.data, **config_entry.options}
            else:
                new_data = config_entry.data
            hass.config_entries.async_update_entry(config_entry, data=new_data, options={}, version=2, minor_version=0)
            _LOGGER.debug(f"async_migrate_entry(): Migration to configuration version {config_entry.version}.{config_entry.minor_version} successful")

    if config_entry.version == 2 and config_entry.minor_version == 0:
        # update from 2.0 to 2.1 [ensure that all unique_id's are lower case!]
        _LOGGER.info(f"async_migrate_entry(): Migration: from v{config_entry.version}.{config_entry.minor_version} to v{CONFIG_VERSION}.{CONFIG_MINOR_VERSION}")
        registry = entity_registry.async_get(hass)

        # 1'st run - ensure that all 'unique_id' are lower case...
        entities = entity_registry.async_entries_for_config_entry(registry, config_entry.entry_id)
        for entity in entities:
            if entity.unique_id != entity.unique_id.lower():
                new_unique_id = entity.unique_id.lower()
                _LOGGER.info(f"async_migrate_entry(): Entity ID: {entity.entity_id}, Unique ID: {entity.unique_id} updated!")
                for already_existing_entity in entities:
                    if already_existing_entity.unique_id == new_unique_id:
                        _LOGGER.info(f"async_migrate_entry(): Entity ID: {entity.entity_id}, Unique ID: {new_unique_id} already exists! - Will PURGE previous {already_existing_entity.entity_id}")
                        registry.async_remove(already_existing_entity.entity_id)

                registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

        # 2'nd run - add the DOMAIN...
        entities = entity_registry.async_entries_for_config_entry(registry, config_entry.entry_id)
        prefix = f"{DOMAIN.lower()}.".lower()
        for entity in entities:
            if not entity.unique_id.startswith(prefix):
                new_unique_id = f"{DOMAIN}.{entity.unique_id}".lower()
                _LOGGER.debug(f"async_migrate_entry(): Entity ID: {entity.entity_id}, Unique ID: {entity.unique_id} will be updated!")
                registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

        hass.config_entries.async_update_entry(config_entry, version=CONFIG_VERSION, minor_version=CONFIG_MINOR_VERSION)
        _LOGGER.info(f"async_migrate_entry(): Migration to configuration version {config_entry.version}.{config_entry.minor_version} successful")

    return True

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.info(f"async_setup_entry(): Starting TibberLocal - ConfigEntry: {mask_map(dict(config_entry.as_dict()))}")

    if DOMAIN not in hass.data:
        value = "UNKOWN"
        hass.data.setdefault(DOMAIN, {"manifest_version": value})

    # if polling is NOT enabled - we will use of the websocket implementation...
    use_websocket = not config_entry.data.get(CONF_USE_POLLING, DEFAULT_USE_POLLING)
    coordinator = TibberLocalDataUpdateCoordinator(hass, config_entry)
    init_succeeded = await coordinator.init_on_load(use_websocket)
    _LOGGER.info(f"async_setup_entry(): TibberLocal - init_succeeded: {init_succeeded}")

    if not init_succeeded: #or coordinator.data is None:
        raise ConfigEntryNotReady
    else:
        hass.data[DOMAIN][config_entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

        if use_websocket:
            # ws watchdog...
            if hass.state is CoreState.running:
                await coordinator.start_watchdog()
            else:
                hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, coordinator.start_watchdog)

        config_entry.async_on_unload(config_entry.add_update_listener(entry_update_listener))
        return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(f"async_unload_entry(): called for entry: {config_entry.entry_id}")
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][config_entry.entry_id]
            await coordinator.bridge.ws_close_and_prepare_to_terminate()
            coordinator.stop_watchdog()
            hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok

async def entry_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    _LOGGER.debug(f"entry_update_listener(): called for entry: {config_entry.entry_id}")
    await hass.config_entries.async_reload(config_entry.entry_id)


class TibberLocalDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, config_entry):
        if config_entry is None:
            _LOGGER.info(f"TibberLocalDataUpdateCoordinator(): created - just to parse the serial number...")
            super().__init__(hass, _LOGGER, name=DOMAIN)
        else:
            self._host = config_entry.data[CONF_HOST]
            the_pwd = config_entry.data[CONF_PASSWORD]

            # support for systems where node != 1
            self.node_num = int(config_entry.data.get(CONF_NODE_NUMBER, 1))

            # ignore parse errors is only in the OPTIONS (not part of the initial setup)
            ignore_parse_errors = bool(config_entry.data.get(CONF_IGNORE_READING_ERRORS, False))

            # the communication_mode is not "adjustable" via the options - it will be only set during the
            # initial configuration phase - so we read it from the config_entry.data ONLY!
            com_mode = int(config_entry.data.get(CONF_MODE, MODE_3_SML_1_04))

            self.bridge = TibberLocalBridge(host=self._host, pwd=the_pwd, websession=async_get_clientsession(hass),
                                            node_num=self.node_num, com_mode=com_mode,
                                            options={"ignore_parse_errors": ignore_parse_errors},
                                            coordinator=self)

            self.name = config_entry.title
            self._config_entry = config_entry

            self._watchdog = None
            self._a_task = None

            self._use_websocket_in_config = not config_entry.data.get(CONF_USE_POLLING, DEFAULT_USE_POLLING)
            self._device_info = None
            self._device_info_model_raw = None
            self._update_device_registry_is_running = False

            super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)))

    async def call_later_update_device_registry(self, now:Any):
        if not self._update_device_registry_is_running:
            self._update_device_registry_is_running = True
            try:
                _LOGGER.debug(f"call_later_update_device_registry(): called with '{now}'")
                if self._use_websocket_in_config:
                    if self.hass is not None:
                        a_device_reg = device_reg.async_get(self.hass)
                        if a_device_reg is not None:
                            if hasattr(a_device_reg, "async_get_device_by_identifier"):
                                device = a_device_reg.async_get_device_by_identifier(identifier=next(iter(self._device_info["identifiers"])), config_entry_id=self.config_entry.entry_id)
                            else:
                                device = a_device_reg.async_get_device(identifiers=self._device_info["identifiers"])
                            if device:
                                _LOGGER.info(f"call_later_update_device_registry(): device registry update triggered for device {device.name}")
                                if self.bridge.ws_connected and self.bridge.ws_check_last_update():
                                    f_model = f"{self._device_info_model_raw} ✅"
                                else:
                                    f_model = f"{self._device_info_model_raw} ⛔"

                                a_device_reg.async_update_device(
                                    device.id,
                                    model=f_model
                                )
            except BaseException as ex:
                _LOGGER.warning(f"call_later_update_device_registry(): failed: {type(ex).__name__} - {ex}")

            self._update_device_registry_is_running = False

    # Callable[[Event], Any]
    # def __call__(self, evt: Event) -> bool:
    #    # just as testing the 'event.async_track_entity_registry_updated_event'
    #    _LOGGER.warning(str(evt))
    #    return True

    def get_device_info(self):
        if self._device_info is None:
            if self._use_websocket_in_config:
                used_protocol = "WebSocket"
                a_name = "Tibber Pulse+Bridge [local push]"
            else:
                used_protocol = "HTTP REST"
                a_name = "Tibber Pulse+Bridge [local poll]"

            self._device_info_model_raw = f"Tibber Pulse+Bridge {used_protocol}"
            self._device_info =  {
                "identifiers": {(DOMAIN, self._host, self._config_entry.title)},
                "name": a_name,
                "model": f"{self._device_info_model_raw}",
                "sw_version": f"{self._config_entry.data.get(CONF_ID, '-unknown-')}",
                "manufacturer": MANUFACTURE,
            }
        return self._device_info

    async def start_watchdog(self, event=None):
        """Start websocket watchdog."""
        await self._async_watchdog_check()
        self._watchdog = async_track_time_interval(self.hass, self._async_watchdog_check, WEBSOCKET_WATCHDOG_INTERVAL)

    def stop_watchdog(self):
        if hasattr(self, "_watchdog") and self._watchdog is not None:
            self._watchdog()
            self._watchdog = None
            async_call_later(self.hass, 5, self.call_later_update_device_registry)

    def _check_for_ws_task_and_cancel_if_running(self):
        if self._a_task is not None and not self._a_task.done():
            _LOGGER.debug(f"_check_for_ws_task_and_cancel_if_running(): Watchdog: websocket connect task is still running - canceling it...")
            try:
                canceled = self._a_task.cancel()
                _LOGGER.debug(f"_check_for_ws_task_and_cancel_if_running(): Watchdog: websocket connect task was CANCELED? {canceled}")
            except BaseException as ex:
                _LOGGER.info(f"_check_for_ws_task_and_cancel_if_running(): Watchdog: websocket connect task cancel failed: {type(ex).__name__} - {ex}")

            self._a_task = None

    async def _async_watchdog_check(self, *_):
        """Reconnect the websocket if it fails."""
        if not self.bridge.ws_supported:
            _LOGGER.info(f"_async_watchdog_check(): Watchdog: terminated, cause bridge reported 'ws_supported' = false")
            self.stop_watchdog()
        else:
            if not self.bridge.ws_connected:
                self._check_for_ws_task_and_cancel_if_running()
                _LOGGER.info(f"_async_watchdog_check(): Watchdog: websocket connect required")
                self._a_task = self._config_entry.async_create_background_task(self.hass, self.bridge.ws_connect(), "ws_connection")
                if self._a_task is not None:
                    _LOGGER.debug(f"_async_watchdog_check(): Watchdog: task created {self._a_task.get_coro()}")
                    async_call_later(self.hass, 10, self.call_later_update_device_registry)
            else:
                _LOGGER.debug(f"_async_watchdog_check(): Watchdog: websocket is connected")
                if not self.bridge.ws_check_last_update():
                    self._check_for_ws_task_and_cancel_if_running()
                    async_call_later(self.hass, 5, self.call_later_update_device_registry)

    async def init_on_load(self, use_websocket: bool = False):
        if use_websocket:
            try:
                await self.bridge.get_eui_for_node()
                _LOGGER.debug(f"init_on_load(): using device_id: {self.bridge.node_device_id} for node: {self.node_num}")
            except BaseException as exception:
                _LOGGER.warning(f"init_on_load(): (self.bridge.get_eui_for_node) caused {exception}")

        bridge_data = self.bridge._obis_values
        if bridge_data is None or len(bridge_data) == 0:
            _LOGGER.info(f"init_on_load(): fetch initial data...")
            try:
                await self.bridge.update()
                bridge_data = self.bridge._obis_values
            except BaseException as exception:
                _LOGGER.warning(f"init_on_load(): caused {type(exception).__name__} - {exception}")

        if _LOGGER.isEnabledFor(logging.INFO):
            _LOGGER.info(f"init_on_load(): after init - found OBIS entries: '{tibber_client.gen_log_list(bridge_data)}'")

        # was the init successful ?!
        if use_websocket:
            return self.bridge.node_device_id is not None
        else:
            return len(bridge_data.keys()) > 0

    async def _async_update_data(self):
        try:
            if self.bridge.ws_connected:
                _LOGGER.debug("_async_update_data(): called (but websocket is active - no data will be requested!)")
            else:
                should_call_update = True
                # we do not have an active websocket connection... but if the use of websocket is configured...
                if self._use_websocket_in_config:
                    # then check, if there has been at least ONE opdate of the websocket...
                    if self.bridge._ws_LAST_UPDATE == 0:
                        if self.bridge.ws_supported:
                            # and if we have somehow already some data...
                            if len(self.bridge._obis_values) > 0:
                                should_call_update = False
                                _LOGGER.info(f"_async_update_data(): skipping cause the use of websocket is configured, but we have not read yet a message from the socket yet (we are probably still in init)")

                if should_call_update:
                    _LOGGER.debug(f"_async_update_data(): called")
                    await self.bridge.update()

            # we always return a DICT of the current data in the bridge objects...
            return {
                DATA_KEY: self.bridge._obis_values,
                METRICS_KEY: self.bridge._metrics_data,
            }

        except UpdateFailed as exception:
            _LOGGER.warning(f"_async_update_data(): UpdateFailed: {type(exception).__name__} - {exception}")
            raise UpdateFailed() from exception
        except ClientConnectionError as exception:
            _LOGGER.warning(f"_async_update_data(): UpdateFailed cause of ClientConnectionError: {type(exception).__name__} - {exception}")
            raise UpdateFailed() from exception
        except Exception as other:
            _LOGGER.warning(f"_async_update_data(): UpdateFailed unexpected: {type(other).__name__} - {other}")
            raise UpdateFailed() from other

    # obis: https://www.promotic.eu/en/pmdoc/Subsystems/Comm/PmDrivers/PmIEC62056/IEC62056_OBIS.htm
    # units: https://github.com/spacemanspiff2007/SmlLib/blob/master/src/smllib/const.py
    # https://onemeter.com/docs/device/obis/

    # <obis: 010060320101, value: XYZ>
    # <obis: 0100600100ff, value: 0a123b4c567890d12e34>
    # <obis: 0100010800ff, status: 1861892, unit: 30, scaler: -1, value: 36061128>
    # <obis: 0100020800ff, unit: 30, scaler: -1, value: 86194714>
    # <obis: 0100100700ff, unit: 27, scaler: 0, value: -49>
    # <obis: 0100240700ff, unit: 27, scaler: 0, value: 511>
    # <obis: 0100380700ff, unit: 27, scaler: 0, value: -415>
    # <obis: 01004c0700ff, unit: 27, scaler: 0, value: -146>
    # <obis: 0100200700ff, unit: 35, scaler: -1, value: 2390>
    # <obis: 0100340700ff, unit: 35, scaler: -1, value: 2394>
    # <obis: 0100480700ff, unit: 35, scaler: -1, value: 2397>
    # <obis: 01001f0700ff, unit: 33, scaler: -2, value: 215>
    # <obis: 0100330700ff, unit: 33, scaler: -2, value: 170>
    # <obis: 0100470700ff, unit: 33, scaler: -2, value: 67>
    # <obis: 0100510701ff, unit: 8, scaler: -1, value: 2390>
    # <obis: 0100510702ff, unit: 8, scaler: -1, value: 1204>
    # <obis: 0100510704ff, unit: 8, scaler: -1, value: 8>
    # <obis: 010051070fff, unit: 8, scaler: -1, value: 1779>
    # <obis: 010051071aff, unit: 8, scaler: -1, value: 1856>
    # <obis: 01000e0700ff, unit: 44, scaler: -1, value: 500>
    # <obis: 010000020000, value: 01>
    # <obis: 0100605a0201, value: 123a4567>

    @property
    def serial(self) -> str:  # XYZ-123a4567
        meter_name = self._get_string_internal("010060320101")
        meter_id_new = self._get_string_internal("0100605a0201")
        meter_id_old = self._get_string_internal("0100600100ff")

        if meter_name is not None:
            if meter_id_new is not None:
                return f"{meter_name}-{meter_id_new}"
            elif meter_id_old is not None:
                return f"{meter_name}-{meter_id_old}"
            else:
                return f"{meter_name}"

        elif meter_id_old is not None:
            return f"{meter_id_old}"
        elif meter_id_new is not None:
            return f"{meter_id_new}"
        else:
            return UNKNOWN_SERIAL

    def _get_metric_value_internal(self, sensor_key):
        if self.data is None:
            return None

        node_status = self.data.get(METRICS_KEY, {}).get(NODE_METRICS, {})
        hub_attachments = self.data.get(METRICS_KEY, {}).get(HUB_METRICS, {})

        if sensor_key in NODE_METRIC_MAP:
            for mapped_metric_key in NODE_METRIC_MAP.get(sensor_key, []):
                if mapped_metric_key in node_status:
                    return node_status.get(mapped_metric_key)

        if sensor_key in hub_attachments:
            return hub_attachments.get(sensor_key)

        return None

    def _get_numeric_value_internal(self, key, divisor: int = 1) -> float | int | None:
        if isinstance(key, list):
            val = None
            for a_key in key:
                if val is None:
                    val = self._get_numeric_value_internal(a_key, divisor)
            return val

        if self.data is not None:
            obis_values = self.data.get(DATA_KEY, {})
            if key in obis_values:
                a_obis_obj = obis_values.get(key)
                if isinstance(a_obis_obj.value, Number):
                    if hasattr(a_obis_obj, 'scaler'):
                        try:
                            return a_obis_obj.value * 10 ** int(a_obis_obj.scaler) / divisor
                        except (TypeError, ValueError):
                            _LOGGER.info(f"_get_numeric_value_internal(): could not convert scaler to int for key {key} - {a_obis_obj}")
                            return None
                    else:
                        return a_obis_obj.value / divisor

        return None

    def _get_string_internal(self, sensor_key) -> str | None:
        if self.data is not None:
            obis_values = self.data.get(DATA_KEY, {})
            if sensor_key in obis_values:
                return obis_values.get(sensor_key).value

        return None

    def get_sensor_value(self, tag:SensorTag):
        if tag is None:
            return None

        if tag.data_type == METRICS_KEY:
            return self._get_metric_value_internal(tag.key)

        if tag.data_type == DATA_KEY:
            obis_candidates = [tag.key]
            if tag.aliases is not None and len(tag.aliases) > 0:
                obis_candidates.extend(tag.aliases)

            divisor = 1000 if tag.divide_by_1000 else 1
            numeric_value = self._get_numeric_value_internal(obis_candidates, divisor=divisor)
            if numeric_value is not None:
                return numeric_value

            return self._get_string_internal(obis_candidates)

        return None


class TibberLocalEntity(CustomFriendlyNameEntity):
    _attr_has_entity_name = True

    def __init__(
            self, coordinator: TibberLocalDataUpdateCoordinator, description: EntityDescription
    ) -> None:
        super().__init__(coordinator)
        if description.entity_category != EntityCategory.DIAGNOSTIC:
            self.obis = ObisCode(description.key)
        self.entity_description = description
        self._stitle = coordinator._config_entry.title
        self._state = None

    @property
    def device_info(self) -> dict:
        # "hw_version": self.coordinator._config_entry.data.get(CONF_DEV_NAME, self.coordinator._config_entry.data.get(CONF_DEV_NAME)),
        return self.coordinator.get_device_info()

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success and len(self.coordinator.data) > 0

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        sensor = self.entity_description.key
        return f"{DOMAIN}.{self._stitle}_{sensor}".lower()

    def _friendly_name_internal(self) -> str | None:
        """Return the friendly name.

        If has_entity_name is False, this returns self.name
        If has_entity_name is True, this returns device.name + self.name
        """
        name = self.name
        if name is UNDEFINED:
            name = None

        if not self.has_entity_name or not (device_entry := self.device_entry):
            return name

        device_name = device_entry.name_by_user or device_entry.name
        if name is None and self.use_device_name:
            return device_name

        # check if there is a user specified entity name (overwritten)
        if registry_entry := self.registry_entry:
            if registry_entry.has_entity_name and registry_entry.name is not None:
                name = registry_entry.name

        if hasattr(self, "obis"):
            #name = f"{name} [{self.obis.obis_code}]"
            name = f"{name} [{self.obis.obis_short}]"

        return name