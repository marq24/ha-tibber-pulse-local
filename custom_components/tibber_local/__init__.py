import asyncio
import base64
import json
import logging
import random
import re
import time
from asyncio import CancelledError
from datetime import timedelta
from typing import Final

import aiohttp
import voluptuous as vol
from aiohttp import ClientConnectionError, ClientResponseError
from smllib import SmlStreamReader
from smllib.const import UNITS, OBIS_NAMES
from smllib.errors import CrcError, SmlLibException
from smllib.sml import SmlListEntry, ObisCode

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
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import EntityDescription, Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import (
    DOMAIN,
    MANUFACTURE,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_POLLING,
    CONF_USE_POLLING,
    CONF_NODE_NUMBER,
    CONF_IGNORE_READING_ERRORS,
    ENUM_MODES,
    MODE_UNKNOWN,
    MODE_0_AutoScanMode,
    MODE_3_SML_1_04,
    MODE_10_ImpressionsAmbient,
    MODE_99_PLAINTEXT,
    MODE_1_IEC_62056_21,
    ENUM_IMPLEMENTATIONS,
    CONFIG_VERSION, CONFIG_MINOR_VERSION
)

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
        if use_websocket:
            # ws watchdog...
            if hass.state is CoreState.running:
                await coordinator.start_watchdog()
            else:
                hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, coordinator.start_watchdog)

        hass.data[DOMAIN][config_entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
        config_entry.async_on_unload(config_entry.add_update_listener(entry_update_listener))

        return True


class TibberLocalDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, config_entry):
        self._host = config_entry.data[CONF_HOST]
        the_pwd = config_entry.data[CONF_PASSWORD]

        # the polling interval
        interval = timedelta(seconds=config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

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

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=interval)

    # Callable[[Event], Any]
    # def __call__(self, evt: Event) -> bool:
    #    # just as testing the 'event.async_track_entity_registry_updated_event'
    #    _LOGGER.warning(str(evt))
    #    return True

    async def start_watchdog(self, event=None):
        """Start websocket watchdog."""
        await self._async_watchdog_check()
        self._watchdog = async_track_time_interval(self.hass, self._async_watchdog_check, WEBSOCKET_WATCHDOG_INTERVAL)


    def stop_watchdog(self):
        if hasattr(self, "_watchdog") and self._watchdog is not None:
            self._watchdog()


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
            else:
                _LOGGER.debug(f"Watchdog: websocket is connected")
                if not self.bridge.ws_check_last_update():
                    self._check_for_ws_task_and_cancel_if_running()


    async def init_on_load(self, use_websocket: bool = False):
        if use_websocket:
            try:
                await self.bridge.get_eui_for_node()
                _LOGGER.debug(f"init_on_load(): using device_id: {self.bridge.node_device_id} for node: {self.node_num}")
            except BaseException as exception:
                _LOGGER.warning(f"init_on_load(): (self.bridge.get_eui_for_node) caused {exception}")

        if self.bridge._obis_values is None or len(self.bridge._obis_values) == 0:
            _LOGGER.info(f"init_on_load(): fetch initial data...")
            try:
                await self.bridge.update()
            except Exception as exception:
                _LOGGER.warning(f"init_on_load(): caused {exception}")

        if _LOGGER.isEnabledFor(logging.INFO):
            _LOGGER.info(f"init_on_load(): after init - found OBIS entries: '{gen_log_list(self.bridge._obis_values)}'")

        # was the init successful ?!
        if use_websocket:
            return self.bridge.node_device_id is not None
        else:
            return len(self.bridge._obis_values) > 0


    async def _async_update_data(self):
        try:
            if self.bridge.ws_connected:
                _LOGGER.debug("_async_update_data called (but websocket is active - no data will be requested!)")
                return self.bridge
            else:
                _LOGGER.debug(f"_async_update_data called")
                await self.bridge.update()
                return self.bridge

        except UpdateFailed as exception:
            _LOGGER.warning(f"UpdateFailed: {exception}")
            raise UpdateFailed() from exception
        except ClientConnectionError as exception:
            _LOGGER.warning(f"UpdateFailed cause of ClientConnectionError: {exception}")
            raise UpdateFailed() from exception
        except Exception as other:
            _LOGGER.warning(f"UpdateFailed unexpected: {type(other)} - {other}")
            raise UpdateFailed() from other


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


class TibberLocalEntity(Entity):
    _attr_should_poll = False

    def __init__(
            self, coordinator: TibberLocalDataUpdateCoordinator, description: EntityDescription
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._stitle = coordinator._config_entry.title
        self._state = None

    @property
    def device_info(self) -> dict:
        # "hw_version": self.coordinator._config_entry.data.get(CONF_DEV_NAME, self.coordinator._config_entry.data.get(CONF_DEV_NAME)),
        return {
            "identifiers": {(DOMAIN, self.coordinator._host, self._stitle)},
            "name": "Tibber Pulse Bridge local push",
            "model": "Tibber Pulse+Bridge",
            "sw_version": self.coordinator._config_entry.data.get(CONF_ID, "-unknown-"),
            "manufacturer": MANUFACTURE,
        }

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        sensor = self.entity_description.key
        return f"{self._stitle}_{sensor}"

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

    async def async_update(self):
        """Update entity."""
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self) -> bool:
        """Entities do not individually poll."""
        return False


class IntBasedObisCode:
    # This is for sure a VERY STUPID Python class - but I am a NOOB - would be cool, if someone could teach me
    # how I could fast convert my number array to the required format...
    def __init__(self, obis_src: list, do_log_output: bool):
        try:
            _a = int(obis_src[1])
            _b = int(obis_src[2])
            _c = int(obis_src[3])
            _d = int(obis_src[4])
            _e = int(obis_src[5])
            if obis_src[6] is not None and len(obis_src[6]) > 0:
                _f = int(obis_src[6])
            else:
                _f = 255

            # self.obis_code = f'{_a}-{_b}:{_c}.{_d}.{_e}*{_f}'
            # self.obis_short = f'{_c}.{_d}.{_e}'
            self.obis_hex = f'{self.get_as_two_digit_hex(_a)}{self.get_as_two_digit_hex(_b)}{self.get_as_two_digit_hex(_c)}{self.get_as_two_digit_hex(_d)}{self.get_as_two_digit_hex(_e)}{self.get_as_two_digit_hex(_f)}'
        except Exception as e:
            if do_log_output:
                _LOGGER.warning(
                    f"could not parse a value as int from list {obis_src} - Please check the position of your Tibber Pulse reading head (you might need to rotate it few degrees anti clock wise) - Exception: {e}")

    @staticmethod
    def get_as_two_digit_hex(input: int) -> str:
        out = f'{input:x}'
        if len(out) == 1:
            return '0' + out
        else:
            return out

@staticmethod
def gen_log_list(obis_values:dict)-> list:
    a_list = []
    try:
        for a_obis in obis_values.values():
            a_list.append(format_entry_short(a_obis))
    except BaseException:
        pass
    return a_list

@staticmethod
def format_entry(entry: SmlListEntry):
    try:
        r = f'{entry.obis.obis_code} ({entry.obis})'
        summary = ''
        if entry.unit:
            val = entry.get_value()
            u = UNITS.get(entry.unit)
            if u is None:
                u = f' ?:{entry.unit}'
            summary += f'{val}{u}'

        desc = OBIS_NAMES.get(entry.obis)
        if desc is not None:
            summary += f'{" " if summary else ""}({desc})'
        if summary:
            r += f': {summary:s}'
        else:
            r += f': {entry.get_value():s}'
        return r
    except BaseException:
        return 'A_ERROR_OBIS_LONG'

@staticmethod
def format_entry_short(entry: SmlListEntry):
    try:
        r = f'{entry.obis.obis_short} ({entry.obis})'
        summary = ''
        if entry.unit:
            val = entry.get_value()
            u = UNITS.get(entry.unit)
            if u is None:
                u = f' ?:{entry.unit}'
            summary += f'{val}{u}'

        if summary:
            r += f': {summary:s}'
        else:
            r += f': {entry.get_value():s}'
        return r
    except BaseException:
        return 'A_ERROR_OBIS_SHORT'

@staticmethod
def ws_parse_header_string(payload_head):
    # Parse device and topic
    device = None
    topic = None
    try:
        header_str = payload_head.strip('<>')
        parts = header_str.split()

        for part in parts:
            if part.startswith('device:'):
                device = part.split(':', 1)[1]
            elif part.startswith('topic:'):
                topic = part.split(':', 1)[1]

        topic = topic.strip('"')
        device = device.lower()
        #_LOGGER.debug(f"ws_parse_header(): device: {device}, topic: {topic}")

    except (UnicodeDecodeError, ValueError) as e:
        _LOGGER.info(f"ws_parse_header_string(): Failed to parse string header: {e}")

    return (topic, device)

@staticmethod
def ws_parse_header_bytes(sml_head: bytes):
    try:
        return ws_parse_header_string(sml_head.decode('ascii', errors='ignore'))
    except (UnicodeDecodeError, ValueError) as e:
        _LOGGER.info(f"ws_parse_header_bytes(): Failed to parse bytes header: {e}")
    return None

@staticmethod
def find_unit_int_from_string(unit_str: str):
    for aUnit in UNITS.items():
        if aUnit[1] == unit_str:
            return aUnit[0]
    return None

class TibberLocalBridge:
    ONLY_DIGITS: re.Pattern = re.compile("^[0-9]+$")
    PLAIN_TEXT_LINE: re.Pattern = re.compile(r'(.*?)-(.*?):(.*?)\.(.*?)\.(.*?)(?:\*(.*?)|)\((.*?)\)')
    TWO_DIGIT_CODE_PATTERN = re.compile(r'^([^.]*\.[^.]*)(\(.*$)')

    def _get_value_internal(self, key, divisor: int = 1):
        if isinstance(key, list):
            val = None
            for a_key in key:
                if val is None:
                    val = self._get_value_internal(a_key, divisor)
            return val

        if key in self._obis_values:
            a_obis = self._obis_values.get(key)
            if hasattr(a_obis, 'scaler'):
                return a_obis.value * 10 ** int(a_obis.scaler) / divisor
            else:
                return a_obis.value / divisor

    def _get_str_internal(self, key):
        if key in self._obis_values:
            return self._obis_values.get(key).value

    def check_first_six_parts_for_digits_or_last_is_none(self, parts: list[str]) -> bool:
        return (self.ONLY_DIGITS.match(parts[1]) is not None and
                self.ONLY_DIGITS.match(parts[2]) is not None and
                self.ONLY_DIGITS.match(parts[3]) is not None and
                self.ONLY_DIGITS.match(parts[4]) is not None and
                self.ONLY_DIGITS.match(parts[5]) is not None and
                (parts[6] is None or self.ONLY_DIGITS.match(parts[6]) is not None))

    # _communication_mode 'MODE_3_SML_1_04' is the initial implemented mode (reading binary sml data)...
    # 'all' other modes have to be implemented... also it could be, that the bridge does
    # not return a value for param_id=27
    def __init__(self, host, pwd, websession, node_num: int = 1, com_mode: int = MODE_3_SML_1_04, options: dict = None, coordinator: DataUpdateCoordinator = None):
        if websession is not None:
            _LOGGER.info(f"restarting TibberLocalBridge integration... for host: '{host}' node: '{node_num}' com_mode: '{com_mode}' with options: {options}")
            self.websession = websession
            self.url_data = f"http://admin:{pwd}@{host}/data.json?node_id={node_num}"
            self.url_data_logging  = f"http://admin:<MASKED>@{host}/data.json?node_id={node_num}"
            self.url_mode = f"http://admin:{pwd}@{host}/node_params.json?node_id={node_num}"

            # we must fetch the bridge nodes configuration (from all nodes) and get the one,
            # that match the 'node_num' - since we need the 'eui'
            self.url_metadata = f"http://admin:{pwd}@{host}/nodes.json"
            self.node_number = node_num

            # websocket stuff...
            self.url_ws = f"http://{host}/ws"
            int_auth_info = f"admin:{pwd}"
            self.REQ_HEADERS_WS = {
                "Accept-Language": "en",
                "Authorization": f"Basic {base64.b64encode(int_auth_info.encode('utf-8')).decode('utf-8')}",
            }
            # The 'self.ws_device_id' will be needed, if multiple pulse are connected to the
            # bridge - and the websocket does not include the node_id (node nummer), instead
            # there is a '<device ...' header that must be used to identify the actual node.
            # The value will be init by calling 'get_eui_for_node()'
            self.node_device_id = None

        self.ws_connected = False
        self.ws_supported = True
        self.ws_obj = None
        self._ws_LAST_UPDATE = 0
        self._ws_debounced_update_task: asyncio.Task | None = None

        self._com_mode = com_mode
        self.ignore_parse_errors = False
        if options is not None and "ignore_parse_errors" in options:
            self.ignore_parse_errors = options["ignore_parse_errors"]
        self._obis_values = {}
        self._obis_values_by_short = {}

        self._fallback_usage_counter = 0
        self._use_fallback_by_default = False
        if com_mode == MODE_3_SML_1_04:
            self.MAX_READ_RETRIES = 5
        else:
            self.MAX_READ_RETRIES = 1

        self._coordinator = coordinator

    async def get_eui_for_node(self):
        # this must be called when we need a device_id... (when we receive data via websocket)
        try:
            async with self.websession.get(self.url_metadata, ssl=False, timeout=10.0) as res:
                try:
                    res.raise_for_status()
                    if res.status == 200:
                        json_resp = await res.json()
                        for a_node_obj in json_resp:
                            if int(a_node_obj.get("node_id", -1)) == self.node_number:
                                self.node_device_id = a_node_obj.get("eui").lower()
                                break
                except Exception as exec:
                    _LOGGER.warning(f"get_eui_for_node(): access to bridge failed with INNER exception: {exec}")
        except Exception as exec:
            _LOGGER.warning(f"get_eui_for_node(): access to bridge failed with OUTER exception: {exec}")

    async def detect_com_mode(self):
        await self.detect_com_mode_from_node_param27()
        _LOGGER.debug(f"detect_com_mode: after detect_com_mode_from_node_param27 mode is: {self._com_mode}")
        # if we can't read the mode from the properties (or the mode is not in the ENUM_MODES)
        # we want to check, if we can read plaintext?!
        if self._com_mode == MODE_UNKNOWN:
            await self._check_modes_internal(MODE_99_PLAINTEXT, MODE_3_SML_1_04)
        elif self._com_mode == MODE_0_AutoScanMode:
            await self._check_modes_internal(MODE_3_SML_1_04, MODE_99_PLAINTEXT)
        elif self._com_mode == MODE_1_IEC_62056_21:
            # https://github.com/marq24/ha-tibber-pulse-local/issues/29
            # looks like we can parse 'IEC_62056_21' as plaintext?!
            await self._check_modes_internal(MODE_99_PLAINTEXT, MODE_3_SML_1_04)

        # finally, raise value error if not implemented yet!
        if self._com_mode not in ENUM_IMPLEMENTATIONS:
            raise ValueError(f"NOT IMPLEMENTED yet! - Mode: {self._com_mode}")

    async def _check_modes_internal(self, mode_1: int, mode_2: int):
        _LOGGER.debug(f"detect_com_mode is {self._com_mode}: will try to read {mode_1}")
        await self.read_tibber_local(mode_1, retry_count=0, log_payload=True)
        if len(self._obis_values) > 0:
            self._com_mode = mode_1
            _LOGGER.debug(f"detect_com_mode 1 SUCCESS -> _com_mode: {self._com_mode}")
        else:
            if (mode_2 != -1):
                _LOGGER.debug(f"detect_com_mode 1 is {self._com_mode}: {mode_1} failed - will try to read {mode_2}")
                await self.read_tibber_local(mode_2, retry_count=0, log_payload=True)
                if len(self._obis_values) > 0:
                    self._com_mode = mode_2
                    _LOGGER.debug(f"detect_com_mode 2 SUCCESS -> _com_mode: {self._com_mode}")
                else:
                    _LOGGER.debug(f"detect_com_mode 2 is {self._com_mode}: {mode_1} failed and {mode_2} failed")
                    pass
            else:
                _LOGGER.debug(f"detect_com_mode 1 is {self._com_mode}: {mode_1} failed")

    async def detect_com_mode_from_node_param27(self):
        try:
            # {'param_id': 27, 'name': 'meter_mode', 'size': 1, 'type': 'uint8', 'help': '0:IEC 62056-21, 1:Count impressions', 'value': [3]}
            self._com_mode = MODE_UNKNOWN
            async with self.websession.get(self.url_mode, ssl=False, timeout=10.0) as res:
                try:
                    res.raise_for_status()
                    if res.status == 200:
                        json_resp = await res.json()
                        for a_parm_obj in json_resp:
                            if 'param_id' in a_parm_obj and a_parm_obj['param_id'] == 27 or \
                                    'name' in a_parm_obj and a_parm_obj['name'] == 'meter_mode':
                                if 'value' in a_parm_obj:
                                    self._com_mode = a_parm_obj['value'][0]
                                    # check for known modes in the UI (http://YOUR-IP-HERE/nodes/1/config)
                                    if self._com_mode not in ENUM_MODES:
                                        self._com_mode = MODE_UNKNOWN
                                    break
                except Exception as exec:
                    _LOGGER.warning(f"access to bridge failed with INNER exception: {exec}")
        except Exception as exec:
            _LOGGER.warning(f"access to bridge failed with OUTER exception: {exec}")

    async def update(self):
        await self.read_tibber_local(mode=self._com_mode, retry_count=0)

    async def update_and_log(self):
        await self.read_tibber_local(mode=self._com_mode, retry_count=0, log_payload=True)

    async def read_tibber_local(self, mode: int, retry_count: int, log_payload: bool = False):
        _LOGGER.debug(f"read_tibber_local: start[{retry_count}] - mode: {mode} request: {self.url_data_logging}")
        async with self.websession.get(self.url_data, ssl=False, timeout=10.0) as res:
            try:
                res.raise_for_status()
                if res.status == 200:
                    if mode == MODE_3_SML_1_04:
                        await self.mode_03_read_sml(await res.read(), retry_count, log_payload)

                    elif mode == MODE_10_ImpressionsAmbient:
                        await self.mode_10_read_json_impressions_ambient(await res.json(), retry_count, log_payload)

                    elif mode == MODE_99_PLAINTEXT:
                        await self.mode_99_read_plaintext(await res.text(), retry_count, log_payload)

                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        _LOGGER.debug(f"read_tibber_local: after[{retry_count}] read - found OBIS entries: '{gen_log_list(self._obis_values)}'")
                else:
                    if res is not None:
                        _LOGGER.warning(f"access to bridge failed with code {res.status} - res: {res}")
                    else:
                        _LOGGER.warning(f"access to bridge failed (UNKNOWN reason - 'res' is None)")

            except BaseException as exc:
                _LOGGER.warning(f"access to bridge failed with exception: {type(exc)} - {exc}")

    async def mode_99_read_plaintext(self, plaintext: str, retry_count: int, log_payload: bool):
        try:
            temp_obis_values = []
            if log_payload:
                _LOGGER.debug(f"plaintext payload: {plaintext}")

            if '\r' not in plaintext:
                plaintext = plaintext.replace(' ', '\r')

            for a_line in plaintext.splitlines():
                try:
                    # a patch for invalid reading?!
                    # a_line = a_line.replace('."55*', '.255*')

                    # if there are not at least 2 dot's before the opening '(', we must insert a '.0' before
                    # the opening '(' [see issue #73]
                    if self.TWO_DIGIT_CODE_PATTERN.match(a_line):
                        a_line = re.sub(self.TWO_DIGIT_CODE_PATTERN, r'\1.0\2', a_line)

                    # it looks like that in the format 'IEC-62056-21' there are the '1-0:' is missing ?! [this is really
                    # a very DUMP implementation] - but we check, if the line has at least
                    # 1. '(' [value start]
                    # 2. ')' [value end]
                    # 3. '*' [the unit delimiter]
                    if len(a_line) >= 4 and a_line[1] != '-' and a_line[3] != ':' and '*' in a_line and '(' in a_line and ')' in a_line:
                        a_line = '1-0:' + a_line

                    # obis pattern is 'a-b:c.d.e*f'
                    parts = re.split(self.PLAIN_TEXT_LINE, a_line)
                    if len(parts) == 9:
                        if self.check_first_six_parts_for_digits_or_last_is_none(parts):
                            int_obc = IntBasedObisCode(parts, not self.ignore_parse_errors)
                            value = parts[7]
                            unit = None
                            if '*' in value:
                                val_with_unit = value.split("*")
                                if '.' in val_with_unit[0]:
                                    value = float(val_with_unit[0])
                                else:
                                    value = int(val_with_unit[0])

                                # converting any "kilo" unit to base unit...
                                # so kWh will be converted to Wh - or kV will be V
                                if val_with_unit[1].lower()[0] == 'k':
                                    value = value * 1000
                                    val_with_unit[1] = val_with_unit[1][1:]

                                unit = find_unit_int_from_string(val_with_unit[1])

                            # creating finally the "right" object from the parsed information
                            if hasattr(int_obc, "obis_hex"):
                                entry = SmlListEntry()
                                entry.obis = ObisCode(int_obc.obis_hex)
                                entry.value = value
                                entry.unit = unit
                                temp_obis_values.append(entry)
                        else:
                            if not self.ignore_parse_errors:
                                _LOGGER.debug(f"ignore none digits-only code: {a_line}")
                    else:
                        if parts[0] == '!':
                            break
                        elif len(parts[0]) > 0 and parts[0][0] != '/':
                            if not self.ignore_parse_errors:
                                _LOGGER.debug(f"unknown entry: {parts[0]} (line: '{a_line}')")
                        # else:
                        #    print('ignore '+ parts[0])

                except Exception as e:
                    if not self.ignore_parse_errors:
                        _LOGGER.info(f"{e}")

            if len(temp_obis_values) > 0:
                self._obis_values = {}
                self._obis_values_by_short = {}
                for entry in temp_obis_values:
                    self._obis_values[entry.obis] = entry
                    self._obis_values_by_short[entry.obis.obis_short] = entry

        except Exception as exc:
            if not self.ignore_parse_errors:
                _LOGGER.warning(f"Exception {exc} while process data - plaintext: {plaintext}")
            if retry_count < self.MAX_READ_RETRIES:
                retry_count = retry_count + 1
                await asyncio.sleep(random.uniform(0.2, 1.2))
                await self.read_tibber_local(mode=MODE_99_PLAINTEXT, retry_count=retry_count)

    async def mode_10_read_json_impressions_ambient(self, data: dict, retry_count: int, log_payload: bool):
        # {"$type": "imp_data", "timestamp_ms": 2122625,"delta_ms": 9879,"kw":0.364409, "kwh": 0.0040}
        temp_obis_values = []

        if log_payload:
            _LOGGER.debug(f"mode 10 payload: {data}")

        if "$type" in data and data["$type"] == "imp_data":
            if "kw" in data:
                kw = data.get("kw")
                if kw is not None:
                    # this is hardcoded '0100100700ff' (Wirkleistung) - but the value in kW... and the sensor
                    # is in W - so we have to multiply it with 1000
                    entry = SmlListEntry()
                    entry.obis = ObisCode('0100100700ff')
                    entry.unit = 27 # 27 is the unit: Watt
                    entry.scaler = 0
                    entry.value = kw * 1000
                    temp_obis_values.append(entry)

            if "kwh" in data:
                # to do/implement...
                kwh = data.get("kwh")
                if kwh is not None:
                    entry = SmlListEntry()
                    entry.obis = ObisCode('0100010800ff')
                    entry.unit = 30 # 30 is the unit: Wh
                    entry.scaler = 0
                    entry.value = kwh * 1000
                    temp_obis_values.append(entry)

        if len(temp_obis_values) > 0:
            self._obis_values = {}
            self._obis_values_by_short = {}
            for entry in temp_obis_values:
                self._obis_values[entry.obis] = entry
                self._obis_values_by_short[entry.obis.obis_short] = entry

    async def mode_03_read_sml(self, payload: bytes, retry_count: int, log_payload: bool):
        # for whatever reason, the data that can be read from the TibberPulse Webserver is
        # not always valid! [I guess there is an issue with an internal buffer in the webserver
        # implementation] - in any case, the bytes received contain sometimes invalid characters,
        # so the 'stream.get_frame()' method will not be able to parse the data...
        if log_payload:
            _LOGGER.debug(f"sml payload: {payload}")

        stream = SmlStreamReader()
        stream.add(payload)
        try:
            sml_frame = stream.get_frame()
            if sml_frame is None:
                if not self.ignore_parse_errors:
                    _LOGGER.info(f"Bytes missing - payload: {payload}")
                if retry_count < self.MAX_READ_RETRIES:
                    retry_count = retry_count + 1
                    await asyncio.sleep(random.uniform(0.2, 1.2))
                    await self.read_tibber_local(mode=MODE_3_SML_1_04, retry_count=retry_count)
            else:
                use_fallback_impl = self._use_fallback_by_default
                sml_list = None
                a_source_exc = None

                self._obis_values = {}
                self._obis_values_by_short = {}

                if not use_fallback_impl:
                    try:
                        # Shortcut to extract all values without parsing the whole frame
                        sml_list = sml_frame.get_obis()

                    except SmlLibException as source_exc:
                        use_fallback_impl = True
                        a_source_exc = source_exc

                        # if we have multiple times the same exception, we switch to the fallback implementation
                        self._fallback_usage_counter = self._fallback_usage_counter + 1
                        if self._fallback_usage_counter > 20:
                            self._use_fallback_by_default = True

                if use_fallback_impl:
                    # see issue https://github.com/marq24/ha-tibber-pulse-local/issues/64
                    # there exist some devices that can't be parsed via 'get_obis()'
                    # see also my issue @ https://github.com/spacemanspiff2007/SmlLib/issues/28
                    sml_list = []
                    for msg in sml_frame.parse_frame():
                        # we simply get through all message bodies and check if we can find the 'val_list' - if so
                        # we just add them to our result.
                        for val in getattr(msg.message_body, 'val_list', []):
                            sml_list.append(val)

                    if a_source_exc is not None and len(sml_list) == 0 and not self.ignore_parse_errors:
                        _LOGGER.debug(f"Exception {a_source_exc} while 'sml_frame.get_obis()' (frame parsing did not work either) - payload: {payload}")

                # if we have a list of SML entries, we can process them
                if sml_list is not None and len(sml_list) > 0:
                    for entry in sml_list:
                        self._obis_values[entry.obis] = entry
                        self._obis_values_by_short[entry.obis.obis_short] = entry

        except (CrcError, BaseException) as exc:
            if not self.ignore_parse_errors:
                if isinstance(exc, CrcError):
                    _LOGGER.info(f"CRC while parse data - payload: {payload}")
                else:
                    _LOGGER.warning(f"Exception {type(exc)} - {exc} while parse data - payload: {payload}")

            if retry_count < self.MAX_READ_RETRIES:
                retry_count = retry_count + 1
                await asyncio.sleep(random.uniform(0.2, 1.2))
                await self.read_tibber_local(mode=MODE_3_SML_1_04, retry_count=retry_count)


    # websocket implementation from here...
    async def ws_connect(self):
        try:
            async with self.websession.ws_connect(self.url_ws, headers=self.REQ_HEADERS_WS) as ws:
                self.ws_connected = True
                self.ws_obj = ws
                _LOGGER.info(f"ws_connect(): connected to websocket: {self.url_ws} - in COM MODE: {self._com_mode}")
                async for msg in ws:
                    self._ws_LAST_UPDATE = time.time()
                    new_data_arrived = False

                    # self._com_mode == MODE_3_SML_1_04
                    # self._com_mode == MODE_10_ImpressionsAmbient
                    # self._com_mode == MODE_99_PLAINTEXT

                    if msg.type == aiohttp.WSMsgType.BINARY:
                        try:
                            binary_data = msg.data
                            # Find the position of '>' and extract everything after it
                            separator_pos = binary_data.index(b'>')
                            if separator_pos > 0:
                                binary_head = binary_data[:separator_pos + 1]
                                _LOGGER.debug(f"ws_connect(): WSMsgType.BINARY head: {binary_head}")
                                topic, device_id = ws_parse_header_bytes(binary_head)

                                if self.node_device_id is None or self.node_device_id == device_id:
                                    if topic is not None and "sml" in topic.lower() and self._com_mode == MODE_3_SML_1_04:
                                        binary_body = binary_data[separator_pos + 1:]
                                        _LOGGER.debug(f"ws_connect(): WSMsgType.BINARY body '{topic}' [len:{len(binary_body)}]: {binary_body if len(binary_body) <= 15 else binary_body[:15]}...")
                                        try:
                                            await self.mode_03_read_sml(binary_body, retry_count=self.MAX_READ_RETRIES, log_payload=False)
                                            new_data_arrived = True
                                        except Exception as e:
                                            _LOGGER.warning(f"ws_connect(): WSMsgType.BINARY 'mode_03_read_sml' caused {type(e).__name__} [{binary_body}] {e}")

                                    elif topic is not None and self._com_mode == MODE_99_PLAINTEXT:
                                        text_body = binary_data[separator_pos + 1:].decode('ascii', errors='ignore')
                                        _LOGGER.debug(f"ws_connect(): WSMsgType.BINARY body (as TEXT) '{topic}' [len:{len(text_body)}]: {text_body if len(text_body) <= 15 else text_body[:15]}...")
                                        try:
                                            await self.mode_99_read_plaintext(text_body, retry_count=self.MAX_READ_RETRIES, log_payload=False)
                                            new_data_arrived = True
                                        except Exception as e:
                                            _LOGGER.warning(f"ws_connect(): WSMsgType.BINARY 'mode_99_read_plaintext' caused {type(e).__name__} [{text_body}] {e}")

                                    elif topic is not None and self._com_mode == MODE_10_ImpressionsAmbient:
                                        json_body = binary_data[separator_pos + 1:].decode('ascii', errors='ignore')
                                        _LOGGER.debug(f"ws_connect(): WSMsgType.BINARY body (as JSON) '{topic}' [len:{len(json_body)}]: {json_body if len(json_body) <= 15 else json_body[:15]}...")
                                        try:
                                            await self.mode_10_read_json_impressions_ambient(json.loads(json_body), retry_count=self.MAX_READ_RETRIES, log_payload=False)
                                            new_data_arrived = True
                                        except Exception as e:
                                            _LOGGER.warning(f"ws_connect(): WSMsgType.BINARY 'mode_10_read_json_impressions_ambient' caused {type(e).__name__} [{json_body}] {e}")

                                    else:
                                        _LOGGER.warning(f"ws_connect(): WSMsgType.BINARY topic '{topic}'/mode_'{self._com_mode}' in: {binary_data}")
                                else:
                                    _LOGGER.debug(f"ws_connect(): WSMsgType.BINARY device of node_num '{self.node_device_id}' not matching the device in the message {device_id}")
                            else:
                                _LOGGER.debug(f"ws_connect(): WSMsgType.BINARY invalid data (NO '>' FOUND) in: {binary_data}")

                        except Exception as e:
                            _LOGGER.debug(f"ws_connect(): Could not read WSMsgType.BINARY from: {msg} - caused {type(e).__name__} {e}")

                    elif msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            text_data = msg.data.decode('ascii', errors='ignore')
                            separator_pos = text_data.index('>')
                            if separator_pos > 0:
                                text_head = text_data[:separator_pos + 1]

                                _LOGGER.debug(f"ws_connect(): WSMsgType.TEXT head: {text_head}")
                                topic, device_id = ws_parse_header_string(text_head)

                                if self.node_device_id is None or self.node_device_id == device_id:
                                    if topic is not None and self._com_mode == MODE_99_PLAINTEXT:
                                        text_body = text_data[separator_pos + 1:]
                                        _LOGGER.debug(f"ws_connect(): WSMsgType.TEXT body '{topic}' [len:{len(text_body)}]: {text_body}")
                                        try:
                                            await self.mode_99_read_plaintext(text_body, retry_count=self.MAX_READ_RETRIES, log_payload=False)
                                            new_data_arrived = True
                                        except Exception as e:
                                            _LOGGER.warning(f"ws_connect(): WSMsgType.TEXT 'mode_99_read_plaintext' caused {type(e).__name__} [{text_data}] {e}")
                                    else:
                                        _LOGGER.warning(f"ws_connect(): WSMsgType.TEXT 'UNHANDLED' topic '{topic}'/mode_'{self._com_mode}' in: {text_data}")
                                else:
                                    _LOGGER.debug(f"ws_connect(): WSMsgType.TEXT device of node_num '{self.node_device_id}' not matching the device in the message {device_id}")
                            else:
                                _LOGGER.debug(f"ws_connect(): WSMsgType.TEXT invalid data (NO '>' FOUND) in: {text_data}")

                        except Exception as e:
                            _LOGGER.debug(f"ws_connect(): Could not read WSMsgType.TEXT from: {msg} - caused {type(e).__name__} {e}")

                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        _LOGGER.debug(f"ws_connect(): received: {msg}")
                        break

                    # do we need to push new data event to the coordinator?
                    if new_data_arrived:
                        self._ws_notify_for_new_data()

        except ClientResponseError as cre:
            if hasattr(cre, "status") and cre.status == 404:
                _LOGGER.info(f"ws_connect(): Could not connect to websocket at {self.url_ws} - [HTTP:404] - looks like bridge firmware update '1428-6debbaf6/795-379a5e21' not installed")
                self.ws_supported = False
            else:
                _LOGGER.error(f"ws_connect(): Could not connect to websocket: {type(cre).__name__} - {cre}")
        except ClientConnectionError as err:
            _LOGGER.error(f"ws_connect(): Could not connect to websocket: {type(err).__name__} - {err}")
        except asyncio.TimeoutError as time_exc:
            _LOGGER.debug(f"ws_connect(): TimeoutError: No WebSocket message received within timeout period")
        except CancelledError as canceled:
            _LOGGER.debug(f"ws_connect(): Terminated? - {type(canceled).__name__} - {canceled}")
        except BaseException as x:
            _LOGGER.error(f"ws_connect(): !!! {type(x).__name__} - {x}")

        _LOGGER.debug(f"ws_connect(): -- END HAS REACHED --")
        try:
            await self.ws_close(ws)
        except UnboundLocalError as is_unbound:
            _LOGGER.debug(f"ws_connect(): skipping ws_close() (since ws is unbound)")
        except BaseException as e:
            _LOGGER.error(f"ws_connect(): Error while calling ws_close(): {type(e).__name__} - {e}")

        self.ws_connected = False
        self.ws_obj = None
        return None

    def _ws_notify_for_new_data(self):
        if self._ws_debounced_update_task is not None and not self._ws_debounced_update_task.done():
            self._ws_debounced_update_task.cancel()
        self._ws_debounced_update_task = asyncio.create_task(self._ws_debounce_coordinator_update())

    async def _ws_debounce_coordinator_update(self):
        if self._coordinator is not None:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"{self.url_ws} received: {gen_log_list(self._obis_values)}")
            self._coordinator.async_set_updated_data(self._obis_values)

    async def ws_close(self, ws):
        """Close the WebSocket connection cleanly."""
        _LOGGER.debug(f"ws_close(): called")
        self.ws_connected = False
        if ws is not None:
            try:
                await ws.close()
                _LOGGER.debug(f"ws_close(): connection closed successfully")
            except BaseException as e:
                _LOGGER.info(f"ws_close(): Error closing WebSocket connection: {type(e).__name__} - {e}")
            finally:
                ws = None
                self.ws_obj = None
        else:
            _LOGGER.debug(f"ws_close(): No active WebSocket connection to close (ws is None)")

    async def ws_close_and_prepare_to_terminate(self):
        try:
            if self.ws_obj is not None:
                await self.ws_close(self.ws_obj)
                await asyncio.sleep(4)
                if not self.ws_connected and self.ws_obj is None:
                    _LOGGER.debug(f"ws_close_and_prepare_to_terminate(): completed! -- ALL iS FINE --")
                else:
                    _LOGGER.debug(f"ws_close_and_prepare_to_terminate(): completed, but ws_connected: {self.ws_connected} | ws_obj: {self.ws_obj}")

                # funny this code can close the websession... but this will bring HA into trouble,,,
                #await self.websession.connector.close()
                #self.websession.detach()
                #_LOGGER.debug(f"ws_close_and_prepare_to_terminate(): websession is detached!")

        except UnboundLocalError as is_unbound:
            _LOGGER.debug(f"ws_close_and_prepare_to_terminate(): skipping (since ws is unbound) {type(is_unbound).__name__} - {is_unbound}")
        except BaseException as e:
            _LOGGER.error(f"ws_close_and_prepare_to_terminate(): Error: {type(e).__name__} - {e}")

    def ws_check_last_update(self) -> bool:
        if self._ws_LAST_UPDATE + 50 > time.time():
            _LOGGER.debug(f"ws_check_last_update(): all good! [last update: {int(time.time()-self._ws_LAST_UPDATE)} sec ago]")
            return True
        else:
            _LOGGER.info(f"ws_check_last_update(): force reconnect...")
            return False

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
            else:
                return f"{self.attr010060320101}"

        elif self.attr0100600100ff is not None:
            return f"{self.attr0100600100ff}"
        elif self.attr0100605a0201 is not None:
            return f"{self.attr0100605a0201}"
        else:
            return "UNKNOWN_SERIAL"

    @property
    def attr010060320101(self) -> str:  # XYZ
        return self._get_str_internal('010060320101')

    @property
    def attr0100600100ff(self) -> str:  # 0a123b4c567890d12e34
        return self._get_str_internal('0100600100ff')

    @property
    def attr0100010800ff(self) -> float:
        return self._get_value_internal('0100010800ff')

    @property
    def attr0100010800ff_in_k(self) -> float:
        return self._get_value_internal('0100010800ff', divisor=1000)

    @property
    def attr0100010800ff_status(self) -> float:
        if '0100010800ff' in self._obis_values and hasattr(self._obis_values.get('0100010800ff'), 'status'):
            return self._obis_values.get('0100010800ff').status

    @property
    def attr0100010801ff(self) -> float:
        return self._get_value_internal('0100010801ff')

    @property
    def attr0100010801ff_in_k(self) -> float:
        return self._get_value_internal('0100010801ff', divisor=1000)

    @property
    def attr0100010802ff(self) -> float:
        return self._get_value_internal('0100010802ff')

    @property
    def attr0100010802ff_in_k(self) -> float:
        return self._get_value_internal('0100010802ff', divisor=1000)

    @property
    def attr0100010803ff(self) -> float:
        return self._get_value_internal('0100010803ff')

    @property
    def attr0100010803ff_in_k(self) -> float:
        return self._get_value_internal('0100010803ff', divisor=1000)

    @property
    def attr0100010804ff(self) -> float:
        return self._get_value_internal('0100010804ff')

    @property
    def attr0100010804ff_in_k(self) -> float:
        return self._get_value_internal('0100010804ff', divisor=1000)

    @property
    def attr0100020800ff(self) -> float:
        return self._get_value_internal('0100020800ff')

    @property
    def attr0100020800ff_in_k(self) -> float:
        return self._get_value_internal(key='0100020800ff', divisor=1000)

    @property
    def attr0100100700ff(self) -> float:
        # search for SUM (0), POS (0), POS (255), NEG (0), ABS (0)
        return self._get_value_internal(
            ['0100100700ff', '0100010700ff', '01000107ffff', '0100020700ff', '01000f0700ff'])

    @property
    def attr0100240700ff(self) -> float:
        # search for SUM (0), POS (0), POS (255), NEG (0), ABS (0)
        return self._get_value_internal(
            ['0100240700ff', '0100150700ff', '01001507ffff', '0100160700ff', '0100230700ff'])

    @property
    def attr0100380700ff(self) -> float:
        # search for SUM (0), POS (0), POS (255), NEG (0), ABS (0)
        return self._get_value_internal(
            ['0100380700ff', '0100290700ff', '01002907ffff', '01002a0700ff', '0100370700ff'])

    @property
    def attr01004c0700ff(self) -> float:
        # search for SUM (0), POS (0), POS (255), NEG (0), ABS (0)
        return self._get_value_internal(
            ['01004c0700ff', '01003d0700ff', '01003d07ffff', '01003e0700ff', '01004b0700ff'])

    @property
    def attr0100200700ff(self) -> float:
        return self._get_value_internal('0100200700ff')

    @property
    def attr0100340700ff(self) -> float:
        return self._get_value_internal('0100340700ff')

    @property
    def attr0100480700ff(self) -> float:
        return self._get_value_internal('0100480700ff')

    @property
    def attr01001f0700ff(self) -> float:
        return self._get_value_internal('01001f0700ff')

    @property
    def attr0100330700ff(self) -> float:
        return self._get_value_internal('0100330700ff')

    @property
    def attr0100470700ff(self) -> float:
        return self._get_value_internal('0100470700ff')

    @property
    def attr0100510701ff(self) -> float:
        return self._get_value_internal('0100510701ff')

    @property
    def attr0100510702ff(self) -> float:
        return self._get_value_internal('0100510702ff')

    @property
    def attr0100510704ff(self) -> float:
        return self._get_value_internal('0100510704ff')

    @property
    def attr010051070fff(self) -> float:
        return self._get_value_internal('010051070fff')

    @property
    def attr010051071aff(self) -> float:
        return self._get_value_internal('010051071aff')

    @property
    def attr01000e0700ff(self) -> float:
        return self._get_value_internal('01000e0700ff')

    @property
    def attr010000020000(self) -> str:  # 01
        return self._get_str_internal('010000020000')

    @property
    def attr0100605a0201(self) -> str:  # 123a4567
        return self._get_str_internal('0100605a0201')