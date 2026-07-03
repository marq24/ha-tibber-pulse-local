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
    Platform
)
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry, device_registry as device_reg
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from homeassistant.helpers.typing import UNDEFINED
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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

    UNKNOWN_SERIAL
)
from .entity import CustomFriendlyNameEntity
from .tibber_client import TibberLocalBridge

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS: Final = [Platform.SENSOR]
WEBSOCKET_WATCHDOG_INTERVAL: Final = timedelta(seconds=64)

def mask_map(d):
    for k, v in d.copy().items():
        if isinstance(v, dict):
            d.pop(k)
            d[k] = v
            mask_map(v)
        else:
            lk = k.lower()
            if lk == "host" or lk == "password":
                v = "<MASKED>"
            d.pop(k)
            d[k] = v
    return d


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    if config_entry.version < CONFIG_VERSION:
        if config_entry.data is not None and len(config_entry.data) > 0:
            _LOGGER.debug(f"Migrating configuration from version {config_entry.version}.{config_entry.minor_version}")
            if config_entry.options is not None and len(config_entry.options):
                new_data = {**config_entry.data, **config_entry.options}
            else:
                new_data = config_entry.data
            hass.config_entries.async_update_entry(config_entry, data=new_data, options={}, version=CONFIG_VERSION, minor_version=CONFIG_MINOR_VERSION)
            _LOGGER.debug(f"Migration to configuration version {config_entry.version}.{config_entry.minor_version} successful")

    if config_entry.version == 2 and config_entry.minor_version == 0:
        # update from 1.x to 1.2 [ensure that all unique_id's are lower case!]
        _LOGGER.info(f"async_migrate_entry(): Migration: from v{config_entry.version}.{config_entry.minor_version} to v{CONFIG_VERSION}.{CONFIG_MINOR_VERSION}")
        registry = entity_registry.async_get(hass)

        # 1'st run - ensure that all 'unique_id' are lower case...
        entities = entity_registry.async_entries_for_config_entry(registry, config_entry.entry_id)
        for entity in entities:
            if entity.unique_id != entity.unique_id.lower():
                new_unique_id = entity.unique_id.lower()
                _LOGGER.info(f"Entity ID: {entity.entity_id}, Unique ID: {entity.unique_id} updated!")
                for already_existing_entity in entities:
                    if already_existing_entity.unique_id == new_unique_id:
                        _LOGGER.info(f"Entity ID: {entity.entity_id}, Unique ID: {new_unique_id} already exists! - Will PURGE previous {already_existing_entity.entity_id}")
                        registry.async_remove(already_existing_entity.entity_id)

                registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

        # 2'nd run - add the DOMAIN...
        entities = entity_registry.async_entries_for_config_entry(registry, config_entry.entry_id)
        prefix = f"{DOMAIN.lower()}.".lower()
        for entity in entities:
            if not entity.unique_id.startswith(prefix):
                new_unique_id = f"{DOMAIN}.{entity.unique_id}".lower()
                _LOGGER.debug(f"Entity ID: {entity.entity_id}, Unique ID: {entity.unique_id} will be updated!")
                registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)

        hass.config_entries.async_update_entry(config_entry, version=CONFIG_VERSION, minor_version=CONFIG_MINOR_VERSION)
        _LOGGER.info(f"async_migrate_entry(): Migration to configuration version {config_entry.version}.{config_entry.minor_version} successful")

    return True

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.info(f"Starting TibberLocal - ConfigEntry: {mask_map(dict(config_entry.as_dict()))}")

    if DOMAIN not in hass.data:
        value = "UNKOWN"
        hass.data.setdefault(DOMAIN, {"manifest_version": value})

    # if polling is NOT enabled - we will use of the websocket implementation...
    use_websocket = not config_entry.data.get(CONF_USE_POLLING, DEFAULT_USE_POLLING)
    coordinator = TibberLocalDataUpdateCoordinator(hass, config_entry)
    init_succeeded = await coordinator.init_on_load(use_websocket)
    _LOGGER.info(f"TibberLocal - init_succeeded: {init_succeeded}")

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
    _LOGGER.debug(f"async_unload_entry() called for entry: {config_entry.entry_id}")
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][config_entry.entry_id]
            await coordinator.bridge.ws_close_and_prepare_to_terminate()
            coordinator.stop_watchdog()
            hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok

async def entry_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    _LOGGER.debug(f"entry_update_listener() called for entry: {config_entry.entry_id}")
    await hass.config_entries.async_reload(config_entry.entry_id)


class TibberLocalDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, config_entry):
        if config_entry is None:
            _LOGGER.info(f"TibberLocalDataUpdateCoordinator() created - just to parse the serial number...")
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

            self.bridge = TibberLocalBridge(host=self._host, pwd=the_pwd, websession=async_create_clientsession(hass),
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
            async_call_later(self.hass, 5, self.call_later_update_device_registry)

    def _check_for_ws_task_and_cancel_if_running(self):
        if self._a_task is not None and not self._a_task.done():
            _LOGGER.debug(f"Watchdog: websocket connect task is still running - canceling it...")
            try:
                canceled = self._a_task.cancel()
                _LOGGER.debug(f"Watchdog: websocket connect task was CANCELED? {canceled}")
            except BaseException as ex:
                _LOGGER.info(f"Watchdog: websocket connect task cancel failed: {type(ex).__name__} - {ex}")

            self._a_task = None

    async def _async_watchdog_check(self, *_):
        """Reconnect the websocket if it fails."""
        if not self.bridge.ws_supported:
            _LOGGER.info(f"Watchdog: terminated, cause bridge reported 'ws_supported' = false")
            self._watchdog()
        else:
            if not self.bridge.ws_connected:
                self._check_for_ws_task_and_cancel_if_running()
                _LOGGER.info(f"Watchdog: websocket connect required")
                self._a_task = self._config_entry.async_create_background_task(self.hass, self.bridge.ws_connect(), "ws_connection")
                if self._a_task is not None:
                    _LOGGER.debug(f"Watchdog: task created {self._a_task.get_coro()}")
                    async_call_later(self.hass, 10, self.call_later_update_device_registry)
            else:
                _LOGGER.debug(f"Watchdog: websocket is connected")
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
            except Exception as exception:
                _LOGGER.warning(f"init_on_load(): caused {exception}")

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
                _LOGGER.debug("_async_update_data called (but websocket is active - no data will be requested!)")
            else:
                _LOGGER.debug(f"_async_update_data called")
                await self.bridge.update()

            # we always return a DICT of the current data in the bridge objects...
            return {
                DATA_KEY: self.bridge._obis_values,
                METRICS_KEY: self.bridge._metrics_data,
            }

        except UpdateFailed as exception:
            _LOGGER.warning(f"UpdateFailed: {exception}")
            raise UpdateFailed() from exception
        except ClientConnectionError as exception:
            _LOGGER.warning(f"UpdateFailed cause of ClientConnectionError: {exception}")
            raise UpdateFailed() from exception
        except Exception as other:
            _LOGGER.warning(f"UpdateFailed unexpected: {type(other)} - {other}")
            raise UpdateFailed() from other

    def _get_numeric_value_internal(self, key, divisor: int = 1) -> float|int:
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

    def _get_string_internal(self, key) -> str:
        if self.data is not None:
            obis_values = self.data.get(DATA_KEY, {})
            if key in obis_values:
                return obis_values.get(key).value

        return None

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
        if self.attr010060320101 is not None:
            if self.attr0100605a0201 is not None:
                return f"{self.attr010060320101}-{self.attr0100605a0201}"
            elif self.attr0100600100ff is not None:
                return f"{self.attr010060320101}-{self.attr0100600100ff}"
            else:
                return f"{self.attr010060320101}"

        elif self.attr0100600100ff is not None:
            return f"{self.attr0100600100ff}"
        elif self.attr0100605a0201 is not None:
            return f"{self.attr0100605a0201}"
        else:
            return UNKNOWN_SERIAL

    @property
    def attrnode_battery_voltage(self):
        if self.data is not None:
            obj = self.data.get(METRICS_KEY, {}).get("node_status", {})
            if len(obj) > 0:
                return obj.get("battery_voltage",  obj.get("node_battery_voltage", None))

    @property
    def attrnode_temperature(self):
        if self.data is not None:
            obj = self.data.get(METRICS_KEY, {}).get("node_status", {})
            if len(obj) > 0:
                return obj.get("temperature",  obj.get("node_temperature", None))

    @property
    def attrnode_avg_rssi(self):
        if self.data is not None:
            obj = self.data.get(METRICS_KEY, {}).get("node_status", {})
            if len(obj) > 0:
                return obj.get("avg_rssi",  obj.get("node_avg_rssi", None))

    @property
    def attrnode_avg_lqi(self):
        if self.data is not None:
            obj = self.data.get(METRICS_KEY, {}).get("node_status", {})
            if len(obj) > 0:
                return obj.get("avg_lqi", obj.get("node_avg_lqi", None))

    @property
    def attrnode_radio_tx_power(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("radio_tx_power", None)

    @property
    def attrnode_uptime_ms(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("node_uptime_ms", None)

    @property
    def attrnode_meter_msg_count_sent(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("meter_msg_count_sent", None)

    @property
    def attrnode_meter_pkg_count_sent(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("meter_pkg_count_sent", None)

    @property
    def attrnode_time_in_em0_ms(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("time_in_em0_ms", None)

    @property
    def attrnode_time_in_em1_ms(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("time_in_em1_ms", None)

    @property
    def attrnode_time_in_em2_ms(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("time_in_em2_ms", None)

    @property
    def attrnode_acmp_rx_autolevel_9600(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("acmp_rx_autolevel_9600", None)

    @property
    def attrnode_invalid_meter_readings_count(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("node_status", {}).get("invalid_meter_readings_count", None)

    @property
    def attrhub_meter_pkg_count_recv(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("hub_attachments", {}).get("meter_pkg_count_recv", None)

    @property
    def attrhub_meter_reading_count_recv(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("hub_attachments", {}).get("meter_reading_count_recv", None)

    @property
    def attrhub_meter_corrupt_reading_count_recv(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("hub_attachments", {}).get("meter_corrupt_reading_count_recv", None)

    @property
    def attrhub_compression_error_readings_count(self):
        if self.data is not None:
            return self.data.get(METRICS_KEY, {}).get("hub_attachments", {}).get("compression_error_readings_count", None)

    @property
    def attr010060320101(self) -> str:  # XYZ
        return self._get_string_internal('010060320101')

    @property
    def attr0100600100ff(self) -> str:  # 0a123b4c567890d12e34
        return self._get_string_internal('0100600100ff')

    @property
    def attr0100010800ff(self) -> float|int:
        return self._get_numeric_value_internal('0100010800ff')

    @property
    def attr0100010800ff_in_k(self) -> float|int:
        return self._get_numeric_value_internal('0100010800ff', divisor=1000)

    @property
    def attr0100010800ff_status(self):
        if self.data is not None:
            obis_values = self.data.get(DATA_KEY, {})
            if '0100010800ff' in obis_values and hasattr(obis_values.get('0100010800ff'), 'status'):
                return obis_values.get('0100010800ff').status

    @property
    def attr0100010801ff(self) -> float|int:
        return self._get_numeric_value_internal('0100010801ff')

    @property
    def attr0100010801ff_in_k(self) -> float|int:
        return self._get_numeric_value_internal('0100010801ff', divisor=1000)

    @property
    def attr0100010802ff(self) -> float|int:
        return self._get_numeric_value_internal('0100010802ff')

    @property
    def attr0100010802ff_in_k(self) -> float|int:
        return self._get_numeric_value_internal('0100010802ff', divisor=1000)

    @property
    def attr0100010803ff(self) -> float|int:
        return self._get_numeric_value_internal('0100010803ff')

    @property
    def attr0100010803ff_in_k(self) -> float|int:
        return self._get_numeric_value_internal('0100010803ff', divisor=1000)

    @property
    def attr0100010804ff(self) -> float|int:
        return self._get_numeric_value_internal('0100010804ff')

    @property
    def attr0100010804ff_in_k(self) -> float|int:
        return self._get_numeric_value_internal('0100010804ff', divisor=1000)

    @property
    def attr0100020800ff(self) -> float|int:
        return self._get_numeric_value_internal('0100020800ff')

    @property
    def attr0100020800ff_in_k(self) -> float|int:
        return self._get_numeric_value_internal(key='0100020800ff', divisor=1000)

    @property
    def attr0100100700ff(self) -> float|int:
        # search for SUM (0), POS (0), POS (255), NEG (0), ABS (0)
        return self._get_numeric_value_internal(['0100100700ff', '0100010700ff', '01000107ffff', '0100020700ff', '01000f0700ff'])

    @property
    def attr0100240700ff(self) -> float|int:
        # search for SUM (0), POS (0), POS (255), NEG (0), ABS (0)
        return self._get_numeric_value_internal(['0100240700ff', '0100150700ff', '01001507ffff', '0100160700ff', '0100230700ff'])

    @property
    def attr0100380700ff(self) -> float|int:
        # search for SUM (0), POS (0), POS (255), NEG (0), ABS (0)
        return self._get_numeric_value_internal(['0100380700ff', '0100290700ff', '01002907ffff', '01002a0700ff', '0100370700ff'])

    @property
    def attr01004c0700ff(self) -> float|int:
        # search for SUM (0), POS (0), POS (255), NEG (0), ABS (0)
        return self._get_numeric_value_internal(['01004c0700ff', '01003d0700ff', '01003d07ffff', '01003e0700ff', '01004b0700ff'])

    @property
    def attr0100200700ff(self) -> float|int:
        return self._get_numeric_value_internal('0100200700ff')

    @property
    def attr0100340700ff(self) -> float|int:
        return self._get_numeric_value_internal('0100340700ff')

    @property
    def attr0100480700ff(self) -> float|int:
        return self._get_numeric_value_internal('0100480700ff')

    @property
    def attr01001f0700ff(self) -> float|int:
        return self._get_numeric_value_internal('01001f0700ff')

    @property
    def attr0100330700ff(self) -> float|int:
        return self._get_numeric_value_internal('0100330700ff')

    @property
    def attr0100470700ff(self) -> float|int:
        return self._get_numeric_value_internal('0100470700ff')

    @property
    def attr0100510701ff(self) -> float|int:
        return self._get_numeric_value_internal('0100510701ff')

    @property
    def attr0100510702ff(self) -> float|int:
        return self._get_numeric_value_internal('0100510702ff')

    @property
    def attr0100510704ff(self) -> float|int:
        return self._get_numeric_value_internal('0100510704ff')

    @property
    def attr010051070fff(self) -> float|int:
        return self._get_numeric_value_internal('010051070fff')

    @property
    def attr010051071aff(self) -> float|int:
        return self._get_numeric_value_internal('010051071aff')

    @property
    def attr01000e0700ff(self) -> float|int:
        return self._get_numeric_value_internal('01000e0700ff')

    @property
    def attr010000020000(self) -> str:  # 01
        return self._get_string_internal('010000020000')

    @property
    def attr0100605a0201(self) -> str:  # 123a4567
        return self._get_string_internal('0100605a0201')


class TibberLocalEntity(CustomFriendlyNameEntity):
    _attr_has_entity_name = True

    def __init__(
            self, coordinator: TibberLocalDataUpdateCoordinator, description: EntityDescription
    ) -> None:
        super().__init__(coordinator, description)
        self.coordinator = coordinator
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
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        sensor = self.entity_description.key
        return f"{DOMAIN}.{self._stitle}_{sensor}".lower()

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
        await super().async_added_to_hass()

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

        # we overwrite the default impl here and just return our 'name'
        # return f"{device_name} {name}" if device_name else name
        if device_entry.name_by_user is not None:
            return f"{device_entry.name_by_user} {name}" if device_name else name
        else:
            return name