import asyncio
import logging
import re
from datetime import timedelta

import voluptuous as vol
from smllib import SmlStreamReader
from smllib.const import UNITS
from smllib.errors import CrcError, SmlLibException
from smllib.sml import SmlListEntry, ObisCode

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_ID, CONF_HOST, CONF_SCAN_INTERVAL, CONF_PASSWORD, CONF_MODE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityDescription, Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import (
    DOMAIN,
    MANUFACTURE,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    CONF_NODE_NUMBER,
    CONF_IGNORE_READING_ERRORS,
    ENUM_MODES,
    MODE_UNKNOWN,
    MODE_0_AutoScanMode,
    MODE_3_SML_1_04,
    MODE_99_PLAINTEXT,
    MODE_1_IEC_62056_21,
    ENUM_IMPLEMENTATIONS,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=10)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]


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


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    global SCAN_INTERVAL
    SCAN_INTERVAL = timedelta(seconds=config_entry.options.get(CONF_SCAN_INTERVAL,
                                                               config_entry.data.get(CONF_SCAN_INTERVAL,
                                                                                     DEFAULT_SCAN_INTERVAL)))

    _LOGGER.info(
        f"Starting TibberLocal with interval: {SCAN_INTERVAL} - ConfigEntry: {mask_map(dict(config_entry.as_dict()))}")

    if DOMAIN not in hass.data:
        value = "UNKOWN"
        hass.data.setdefault(DOMAIN, {"manifest_version": value})

    coordinator = TibberLocalDataUpdateCoordinator(hass, config_entry)
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady
    else:
        await coordinator.init_on_load()

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if config_entry.state != ConfigEntryState.LOADED:
        config_entry.add_update_listener(async_reload_entry)

    return True


class TibberLocalDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry):
        self._host = config_entry.options.get(CONF_HOST, config_entry.data[CONF_HOST])
        the_pwd = config_entry.options.get(CONF_PASSWORD, config_entry.data[CONF_PASSWORD])

        # support for systems where node != 1
        node_num = int(config_entry.options.get(CONF_NODE_NUMBER, config_entry.data.get(CONF_NODE_NUMBER, 1)))

        # ignore parse errors is only in the OPTIONS (not part of the initial setup)
        ignore_parse_errors = bool(config_entry.options.get(CONF_IGNORE_READING_ERRORS, False))

        # the communication_mode is not "adjustable" via the options - it will be only set during the
        # initial configuration phase - so we read it from the config_entry.data ONLY!
        com_mode = int(config_entry.data.get(CONF_MODE, MODE_3_SML_1_04))

        self.bridge = TibberLocalBridge(host=self._host, pwd=the_pwd, websession=async_get_clientsession(hass),
                                        node_num=node_num,
                                        com_mode=com_mode, options={"ignore_parse_errors": ignore_parse_errors})
        self.name = config_entry.title
        self._config_entry = config_entry
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    # Callable[[Event], Any]
    # def __call__(self, evt: Event) -> bool:
    #    # just as testing the 'event.async_track_entity_registry_updated_event'
    #    _LOGGER.warning(str(evt))
    #    return True

    async def init_on_load(self):
        try:
            await self.bridge.update()
            _LOGGER.info(f"after init - found OBIS entries: '{self.bridge._obis_values}'")
        except Exception as exception:
            _LOGGER.warning(f"init caused {exception}")

    async def _async_update_data(self):
        try:
            await self.bridge.update()
            return self.bridge
        except UpdateFailed as exception:
            raise UpdateFailed() from exception

    # async def _async_switch_to_state(self, switch_key, state):
    #    try:
    #        await self.bridge.switch(switch_key, state)
    #        return self.bridge
    #    except UpdateFailed as exception:
    #        raise UpdateFailed() from exception


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    if await async_unload_entry(hass, config_entry):
        await asyncio.sleep(2)
        await async_setup_entry(hass, config_entry)


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
        # "hw_version": self.coordinator._config_entry.options.get(CONF_DEV_NAME, self.coordinator._config_entry.data.get(CONF_DEV_NAME)),
        return {
            "identifiers": {(DOMAIN, self.coordinator._host, self._stitle)},
            "name": "Tibber Pulse Bridge local polling",
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


class TibberLocalBridge:
    ONLY_DIGITS: re.Pattern = re.compile("^[0-9]+$")
    PLAIN_TEXT_LINE: re.Pattern = re.compile('(.*?)-(.*?):(.*?)\\.(.*?)\\.(.*?)(?:\\*(.*?)|)\\((.*?)\\)')

    # _communication_mode 'MODE_3_SML_1_04' is the initial implemented mode (reading binary sml data)...
    # 'all' other modes have to be implemented... also it could be, that the bridge does
    # not return a value for param_id=27
    def __init__(self, host, pwd, websession, node_num: int = 1, com_mode: int = MODE_3_SML_1_04, options: dict = None):
        if websession is not None:
            _LOGGER.info(
                f"restarting TibberLocalBridge integration... for host: '{host}' node: '{node_num}' com_mode: '{com_mode}' with options: {options}")
            self.websession = websession
            self.url_data = f"http://admin:{pwd}@{host}/data.json?node_id={node_num}"
            self.url_mode = f"http://admin:{pwd}@{host}/node_params.json?node_id={node_num}"
        self._com_mode = com_mode
        self.ignore_parse_errors = False
        if options is not None and "ignore_parse_errors" in options:
            self.ignore_parse_errors = options["ignore_parse_errors"]
        self._obis_values = {}
        self._obis_values_by_short = {}

        self._fallback_usage_counter = 0
        self._use_fallback_by_default = False

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

        # finally raise value error if not implemented yet!
        if self._com_mode not in ENUM_IMPLEMENTATIONS:
            raise ValueError(f"NOT IMPLEMENTED yet! - Mode: {self._com_mode}")

    async def _check_modes_internal(self, mode_1: int, mode_2: int):
        _LOGGER.debug(f"detect_com_mode is {self._com_mode}: will try to read {mode_1}")
        await self.read_tibber_local(mode_1, False, log_payload=True)
        if len(self._obis_values) > 0:
            self._com_mode = mode_1
            _LOGGER.debug(f"detect_com_mode 1 SUCCESS -> _com_mode: {self._com_mode}")
        else:
            _LOGGER.debug(f"detect_com_mode 1 is {self._com_mode}: {mode_1} failed - will try to read {mode_2}")
            await self.read_tibber_local(mode_2, False, log_payload=True)
            if len(self._obis_values) > 0:
                self._com_mode = mode_2
                _LOGGER.debug(f"detect_com_mode 2 SUCCESS -> _com_mode: {self._com_mode}")
            else:
                _LOGGER.debug(f"detect_com_mode 2 is {self._com_mode}: {mode_1} failed and {mode_2} failed")
                pass

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
                    _LOGGER.warning(f"access to bridge failed with exception: {exec}")
        except Exception as exec:
            _LOGGER.warning(f"access to bridge failed with exception: {exec}")

    async def update(self):
        await self.read_tibber_local(mode=self._com_mode, retry=True)

    async def read_tibber_local(self, mode: int, retry: bool, log_payload: bool = False):
        async with self.websession.get(self.url_data, ssl=False, timeout=10.0) as res:
            try:
                res.raise_for_status()
                if res.status == 200:
                    if mode == MODE_3_SML_1_04:
                        await self.read_sml(await res.read(), retry, log_payload)
                    elif mode == MODE_99_PLAINTEXT:
                        await self.read_plaintext(await res.text(), retry, log_payload)
                else:
                    if res is not None:
                        _LOGGER.warning(f"access to bridge failed with code {res.status} - res: {res}")
                    else:
                        _LOGGER.warning(f"access to bridge failed (UNKNOWN reason)")
            except Exception as exec:
                _LOGGER.warning(f"access to bridge failed with exception: {exec}")

    def check_first_six_parts_for_digits_or_last_is_none(self, parts: list[str]) -> bool:
        return (self.ONLY_DIGITS.match(parts[1]) is not None and
                self.ONLY_DIGITS.match(parts[2]) is not None and
                self.ONLY_DIGITS.match(parts[3]) is not None and
                self.ONLY_DIGITS.match(parts[4]) is not None and
                self.ONLY_DIGITS.match(parts[5]) is not None and
                (parts[6] is None or self.ONLY_DIGITS.match(parts[6]) is not None))

    async def read_plaintext(self, plaintext: str, retry: bool, log_payload: bool):
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

                    # looks like that in the format 'IEC-62056-21' there are the '1-0:' is missing ?! [this is really
                    # a very DUMP implementation]
                    if a_line[1] != '-' and a_line[3] != ':' and '*' in a_line and '(' in a_line and ')' in a_line:
                        a_line = '1-0:' + a_line
                        pass

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

                                unit = self.find_unit_int_from_string(val_with_unit[1])

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
            if retry:
                await asyncio.sleep(2.5)
                await self.read_tibber_local(mode=MODE_99_PLAINTEXT, retry=False)

    @staticmethod
    def find_unit_int_from_string(unit_str: str):
        for aUnit in UNITS.items():
            if aUnit[1] == unit_str:
                return aUnit[0]
        return None

    async def read_sml(self, payload: bytes, retry: bool, log_payload: bool):
        # for what ever reason the data that can be read from the TibberPulse Webserver is
        # not always valid! [I guess there is a issue with an internal buffer in the webserver
        # implementation] - in any case the bytes received contain sometimes invalid characters
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
                if retry:
                    await asyncio.sleep(2.5)
                    await self.read_tibber_local(mode=MODE_3_SML_1_04, retry=False)
            else:
                use_fallback_impl = self._use_fallback_by_default
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

                        # if we have multiple times the same exception - we switch to the fallback implementation
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

            if sml_list is not None and len(sml_list) > 0:
                    for entry in sml_list:
                        self._obis_values[entry.obis] = entry
                        self._obis_values_by_short[entry.obis.obis_short] = entry

        except CrcError as crc:
            if not self.ignore_parse_errors:
                _LOGGER.info(f"CRC while parse data - payload: {payload}")
            if retry:
                await asyncio.sleep(2.5)
                await self.read_tibber_local(mode=MODE_3_SML_1_04, retry=False)

        except Exception as exc:
            if not self.ignore_parse_errors:
                _LOGGER.warning(f"Exception {exc} while parse data - payload: {payload}")
            if retry:
                await asyncio.sleep(2.5)
                await self.read_tibber_local(mode=MODE_3_SML_1_04, retry=False)

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

    # obis: https://www.promotic.eu/en/pmdoc/Subsystems/Comm/PmDrivers/IEC62056_OBIS.htm
    # units: https://github.com/spacemanspiff2007/SmlLib/blob/master/src/smllib/const.py

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
            return f"{self.attr010060320101}-{self.attr0100605a0201}"
        elif self.attr0100600100ff is not None:
            return f"{self.attr0100600100ff}"

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
