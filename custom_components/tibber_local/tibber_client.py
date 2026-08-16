import asyncio
import json
import logging
import random
import re
import time
from asyncio import CancelledError
from typing import Final
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientConnectionError, ClientResponseError, ClientTimeout
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from smllib import SmlStreamReader
from smllib.const import UNITS
from smllib.errors import CrcError, SmlLibException
from smllib.sml import SmlListEntry, ObisCode

from .const import (
    ENUM_MODES,
    MODE_UNKNOWN,
    MODE_0_AutoScanMode,
    MODE_3_SML_1_04,
    MODE_10_ImpressionsAmbient,
    MODE_99_PLAINTEXT,
    MODE_1_IEC_62056_21,
    ENUM_IMPLEMENTATIONS,
    DATA_KEY,
    METRICS_KEY,
)

_LOGGER = logging.getLogger(__name__)

MIN_RETRY_DELAY: Final = 2.5
MAX_RETRY_DELAY: Final = 10

# when HA is starting, plenty of requests are running - so we grant the bridge more time for the initial read
INITIAL_READ_TIMEOUT: Final = ClientTimeout(total=60)
REQUEST_TIMEOUT: Final = ClientTimeout(total=10)

# if we did not receive any websocket message for that many seconds, we force a reconnect
WS_MAX_SILENCE_IN_SEC: Final = 50

# the coordinator will be notified at most once per second (the bridge pushes data way more often)
WS_MIN_NOTIFY_DELAY_IN_SEC: Final = 1

# 'UNITS' maps the sml unit-code to its name - here we need the opposite direction [some names are used by
# multiple codes - like 'm³' - so we build it reversed: the first (lowest) code wins, as it did before]
UNIT_CODE_BY_NAME: Final = {a_name: a_code for a_code, a_name in reversed(UNITS.items())}

# a OBIS code consists of the six values 'a-b:c.d.e*f' - where 'f' is optional
OBIS_DEFAULT_F_VALUE: Final = 255


def obis_hex_from_parts(obis_parts: list, do_log_output: bool) -> str | None:
    # 'a-b:c.d.e*f' -> '0100010800ff' - each of the six OBIS values is just a single byte, so the hex
    # representation of these six bytes is already the code we are looking for
    try:
        values = [int(a_value) for a_value in obis_parts[:5]]
        values.append(int(obis_parts[5]) if obis_parts[5] else OBIS_DEFAULT_F_VALUE)
        # 'bytes()' will raise a ValueError, if a value does not fit into a single byte
        return bytes(values).hex()
    except (IndexError, TypeError, ValueError) as exc:
        if do_log_output:
            _LOGGER.warning(f"could not build a OBIS code from {obis_parts} - Please check the position of your "
                            f"Tibber Pulse reading head (you might need to rotate it few degrees anti clock wise) "
                            f"- Exception: {exc}")
    return None

def gen_log_list(obis_values: dict) -> list:
    if not obis_values:
        return []
    return [format_entry_short(a_obis) for a_obis in obis_values.values()]

def format_entry_short(entry: SmlListEntry) -> str:
    try:
        value = entry.get_value()
        if entry.unit:
            unit = UNITS.get(entry.unit, f' ?:{entry.unit}')
            return f'{entry.obis.obis_short} ({entry.obis}): {value}{unit}'
        return f'{entry.obis.obis_short} ({entry.obis}): {value}'
    except Exception:
        return 'A_ERROR_OBIS_SHORT'

def ws_parse_header_string(payload_head: str) -> tuple[str | None, str | None]:
    # a header looks like: '<device:0011223344556677 topic:"sml/xyz">'
    topic = None
    device = None
    for a_part in payload_head.strip('<>').split():
        if a_part.startswith('device:'):
            device = a_part.split(':', 1)[1].lower()
        elif a_part.startswith('topic:'):
            topic = a_part.split(':', 1)[1].strip('"')
    #_LOGGER.debug(f"ws_parse_header_string(): device: {device}, topic: {topic}")
    return topic, device

def ws_parse_header_bytes(sml_head: bytes) -> tuple[str | None, str | None]:
    # 'errors=ignore' - so the decoding itself can't fail here
    return ws_parse_header_string(sml_head.decode('ascii', errors='ignore'))

def find_unit_int_from_string(unit_str: str) -> int | None:
    return UNIT_CODE_BY_NAME.get(unit_str)

def clean_host(host_input: str) -> str:
    # ensure it looks like a URL, so 'urlparse' can handle it
    as_url = host_input if "://" in host_input else "http://" + host_input
    try:
        parsed = urlparse(as_url)
        # .hostname returns just the IP/Domain (strips port and path)
        # .netloc returns IP/Domain + port (e.g., 192.168.1.50:8080)
        a_host = parsed.hostname
        a_port = parsed.port
    except ValueError as exc:
        # an invalid port will cause a ValueError when accessing 'parsed.port'
        _LOGGER.info(f"clean_host(): could not parse '{host_input}': {exc} - will use it as it is")
        return host_input

    if a_host is None:
        return host_input
    if a_port is not None and a_port != 80:
        return f"{a_host}:{a_port}"
    return a_host


class TibberLocalBridge:
    ONLY_DIGITS: re.Pattern = re.compile("^[0-9]+$")
    PLAIN_TEXT_LINE: re.Pattern = re.compile(r'(.*?)-(.*?):(.*?)\.(.*?)\.(.*?)(?:\*(.*?)|)\((.*?)\)')
    # matches OBIS codes with only one dot ('1-0:1.8(...)' or '1-0:1.8*255(...)') - the optional
    # '*f' part is kept in its own group, so the missing '.e' is inserted at the right position
    TWO_DIGIT_CODE_PATTERN: re.Pattern = re.compile(r'^([^.]*\.[^.]*?)(\*[^.(]*)?(\(.*$)')

    def check_obis_parts_are_digits(self, obis_parts: list[str]) -> bool:
        # the last part 'f' of 'a-b:c.d.e*f' is optional - so 'None' is allowed there
        return (all(a_part is not None and self.ONLY_DIGITS.match(a_part) is not None for a_part in obis_parts[:5]) and
                (obis_parts[5] is None or self.ONLY_DIGITS.match(obis_parts[5]) is not None))

    # _communication_mode 'MODE_3_SML_1_04' is the initially implemented mode (reading binary sml data)...
    # 'all' other modes have to be implemented... also it could be that the bridge does
    # not return a value for param_id=27
    def __init__(self, host, pwd, websession, node_num: int = 1, com_mode: int = MODE_3_SML_1_04, options: dict = None, coordinator: DataUpdateCoordinator = None):

        a_host = clean_host(host)
        _LOGGER.info(f"restarting TibberLocalBridge integration... for host: '{a_host}' node: '{node_num}' com_mode: '{com_mode}' with options: {options}")
        self.web_session = websession
        self.basic_auth = aiohttp.BasicAuth("admin", pwd)
        self.url_data = f"http://{a_host}/data.json?node_id={node_num}"
        self.url_metrics = f"http://{a_host}/metrics.json?node_id={node_num}"
        self.url_mode = f"http://{a_host}/node_params.json?node_id={node_num}"

        # we must fetch the bridge nodes configuration (from all nodes) and get the one,
        # that match the 'node_num' - since we need the 'eui'
        self.url_metadata = f"http://{a_host}/nodes.json"
        self.node_number = node_num

        # websocket stuff...
        self.url_ws = f"ws://{a_host}/ws"

        # The 'self.node_device_id' will be needed if multiple pulses are connected to the
        # bridge - and the websocket does not include the node_id (node nummer), instead
        # there is a '<device ...' header that must be used to identify the actual node.
        # The value will be init by calling 'get_eui_for_node()'
        self.node_device_id = None

        self.ws_connected = False
        self.ws_supported = True
        self.ws_obj = None
        self._ws_LAST_UPDATE = 0
        self._ws_debounced_update_task: asyncio.Task | None = None
        self._ws_LAST_UPDATE_NOTIFY = 0

        self._com_mode = com_mode
        self.ignore_parse_errors = bool(options.get("ignore_parse_errors", False)) if options else False
        self._metrics_update_is_running = False
        self._LAST_METRICS_UPDATE = 0
        self._metrics_data = {}
        self._obis_values = {}
        #self._obis_values_by_short = {}

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
            async with self.web_session.get(self.url_metadata, auth=self.basic_auth, ssl=False, timeout=REQUEST_TIMEOUT) as res:
                res.raise_for_status()
                for a_node_obj in await res.json():
                    if int(a_node_obj.get("node_id", -1)) == self.node_number:
                        a_eui = a_node_obj.get("eui")
                        if a_eui is not None:
                            self.node_device_id = a_eui.lower()
                        else:
                            _LOGGER.warning(f"get_eui_for_node(): bridge does not provide a 'eui' for node {self.node_number}: {a_node_obj}")
                        break
        except Exception as exc:
            _LOGGER.warning(f"get_eui_for_node(): access to bridge failed with exception: {type(exc).__name__} - {exc}")

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
            _LOGGER.debug(f"detect_com_mode 1 is {self._com_mode}: {mode_1} failed - will try to read {mode_2}")
            await self.read_tibber_local(mode_2, retry_count=0, log_payload=True)
            if len(self._obis_values) > 0:
                self._com_mode = mode_2
                _LOGGER.debug(f"detect_com_mode 2 SUCCESS -> _com_mode: {self._com_mode}")
            else:
                _LOGGER.debug(f"detect_com_mode 2 is {self._com_mode}: {mode_1} failed and {mode_2} failed")

    async def detect_com_mode_from_node_param27(self):
        # {'param_id': 27, 'name': 'meter_mode', 'size': 1, 'type': 'uint8', 'help': '0:IEC 62056-21, 1:Count impressions', 'value': [3]}
        self._com_mode = MODE_UNKNOWN
        try:
            async with self.web_session.get(self.url_mode, auth=self.basic_auth, ssl=False, timeout=REQUEST_TIMEOUT) as res:
                res.raise_for_status()
                for a_parm_obj in await res.json():
                    if (a_parm_obj.get('param_id') == 27 or a_parm_obj.get('name') == 'meter_mode') and 'value' in a_parm_obj:
                        self._com_mode = a_parm_obj['value'][0]
                        # check for known modes in the UI (http://YOUR-IP-HERE/nodes/1/config)
                        if self._com_mode not in ENUM_MODES:
                            self._com_mode = MODE_UNKNOWN
                        break
        except Exception as exc:
            _LOGGER.warning(f"detect_com_mode_from_node_param27(): access to bridge failed with exception: {type(exc).__name__} - {exc}")

    async def update(self):
        await self.read_tibber_local(mode=self._com_mode, retry_count=0)
        await self.updated_tibber_metrics_if_needed()

    async def update_and_log(self):
        await self.read_tibber_local(mode=self._com_mode, retry_count=0, log_payload=True)

    async def read_tibber_local(self, mode: int, retry_count: int, log_payload: bool = False):
        _LOGGER.debug(f"read_tibber_local(): start[{retry_count}] - mode: {mode} request: {self.url_data}")
        if mode not in ENUM_IMPLEMENTATIONS:
            _LOGGER.warning(f"read_tibber_local(): NOT IMPLEMENTED yet! - Mode: {mode}")
            return

        try:
            # on init we wait up to 60 seconds till we get a reply from the bridge (when HA is starting, plenty of
            # requests are running...
            a_timeout = INITIAL_READ_TIMEOUT if len(self._obis_values) == 0 else REQUEST_TIMEOUT
            async with self.web_session.get(self.url_data, auth=self.basic_auth, ssl=False, timeout=a_timeout) as res:
                res.raise_for_status()
                if mode == MODE_3_SML_1_04:
                    payload = await res.read()
                elif mode == MODE_10_ImpressionsAmbient:
                    payload = await res.json()
                else:
                    payload = await res.text()

        except Exception as exc:
            _LOGGER.warning(f"access to bridge failed with exception: {type(exc).__name__} - {exc}")
            return

        # the response is released at this point - so a possible retry (including its delay) will not
        # block the connection to the bridge any longer
        if mode == MODE_3_SML_1_04:
            await self.mode_03_read_sml(payload, retry_count, log_payload)
        elif mode == MODE_10_ImpressionsAmbient:
            await self.mode_10_read_json_impressions_ambient(payload, retry_count, log_payload)
        else:
            await self.mode_99_read_plaintext(payload, retry_count, log_payload)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"read_tibber_local: after[{retry_count}] read - found OBIS entries: '{gen_log_list(self._obis_values)}'")

    async def mode_99_read_plaintext(self, plaintext: str, retry_count: int, log_payload: bool):
        try:
            if log_payload:
                _LOGGER.debug(f"plaintext payload: {plaintext}")

            temp_obis_values = {}
            if '\r' not in plaintext:
                plaintext = plaintext.replace(' ', '\r')

            for a_line in plaintext.splitlines():
                try:
                    # a patch for invalid reading?!
                    # a_line = a_line.replace('."55*', '.255*')

                    # if there are not at least 2 dot's in the obis code, we must add the missing '.0'
                    # [see issue #73]
                    a_line = self.TWO_DIGIT_CODE_PATTERN.sub(r'\1.0\2\3', a_line, count=1)

                    # it looks like that in the format 'IEC-62056-21' there are the '1-0:' is missing ?! - so we
                    # check, if the line has at least
                    # 1. '(' [value start]
                    # 2. ')' [value end]
                    # 3. '*' [the unit delimiter]
                    if len(a_line) >= 4 and a_line[1] != '-' and a_line[3] != ':' and '*' in a_line and '(' in a_line and ')' in a_line:
                        a_line = '1-0:' + a_line

                    # obis pattern is 'a-b:c.d.e*f' - 'parts[0]' is the text before the match, 'parts[1:7]' are
                    # the six obis values and 'parts[7]' is the value (including its optional unit)
                    parts = self.PLAIN_TEXT_LINE.split(a_line)
                    if len(parts) != 9:
                        if parts[0] == '!':
                            break
                        if len(parts[0]) > 0 and parts[0][0] != '/' and not self.ignore_parse_errors:
                            _LOGGER.debug(f"unknown entry: {parts[0]} (line: '{a_line}')")
                        continue

                    if not self.check_obis_parts_are_digits(parts[1:7]):
                        if not self.ignore_parse_errors:
                            _LOGGER.debug(f"ignore none digits-only code: {a_line}")
                        continue

                    obis_hex = obis_hex_from_parts(parts[1:7], not self.ignore_parse_errors)
                    if obis_hex is None:
                        continue

                    value = parts[7]
                    unit = None
                    if '*' in value:
                        raw_value, _, raw_unit = value.partition('*')
                        value = float(raw_value) if '.' in raw_value else int(raw_value)

                        # converting any "kilo" unit to base unit...
                        # so kWh will be converted to Wh - or kV will be V
                        if raw_unit[:1].lower() == 'k':
                            value = value * 1000
                            raw_unit = raw_unit[1:]

                        unit = find_unit_int_from_string(raw_unit)

                    # creating finally the "right" object from the parsed information
                    entry = SmlListEntry()
                    entry.obis = ObisCode(obis_hex)
                    entry.value = value
                    entry.unit = unit
                    # our plaintext values are not scaled - but 'SmlListEntry.get_value()' requires the attribute
                    entry.scaler = 0
                    temp_obis_values[entry.obis] = entry

                except Exception as exc:
                    if not self.ignore_parse_errors:
                        _LOGGER.info(f"could not process line '{a_line}': {type(exc).__name__} - {exc}")

            # only replace the previous values, if we could read something
            if len(temp_obis_values) > 0:
                self._obis_values = temp_obis_values

        except Exception as exc:
            if not self.ignore_parse_errors:
                _LOGGER.warning(f"Exception {type(exc).__name__} - {exc} while process data - plaintext: {plaintext}")
            await self._retry_read(MODE_99_PLAINTEXT, retry_count)

    async def mode_10_read_json_impressions_ambient(self, data: dict, retry_count: int, log_payload: bool):
        # {"$type": "imp_data", "timestamp_ms": 2122625,"delta_ms": 9879,"kw":0.364409, "kwh": 0.0040}
        temp_obis_values = {}

        if log_payload:
            _LOGGER.debug(f"mode 10 payload: {data}")

        if isinstance(data, dict) and data.get("$type") == "imp_data":
            kw = data.get("kw")
            if kw is not None:
                # this is hardcoded '0100100700ff' (Wirkleistung) - but the value in kW... and the sensor
                # is in W - so we have to multiply it with 1000
                entry = SmlListEntry()
                entry.obis = ObisCode('0100100700ff')
                entry.unit = 27 # 27 is the unit: Watt
                entry.scaler = 0
                entry.value = kw * 1000
                temp_obis_values[entry.obis] = entry

            kwh = data.get("kwh")
            if kwh is not None:
                entry = SmlListEntry()
                entry.obis = ObisCode('0100010800ff')
                entry.unit = 30 # 30 is the unit: Wh
                entry.scaler = 0
                entry.value = kwh * 1000
                temp_obis_values[entry.obis] = entry
        else:
            _LOGGER.debug(f"mode_10_read_json_impressions_ambient(): unexpected payload: {data}")

        # only replace the previous values, if we could read something
        if len(temp_obis_values) > 0:
            self._obis_values = temp_obis_values

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
                await self._retry_read(MODE_3_SML_1_04, retry_count)
                return

            use_fallback_impl = self._use_fallback_by_default
            sml_list = None
            a_source_exc = None

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

            # if we have a list of SML entries, we can process them - only replacing the previous values, if we
            # could read something [a single invalid frame should not clear all our sensor states]
            if sml_list:
                self._obis_values = {entry.obis: entry for entry in sml_list}

        except CrcError:
            if not self.ignore_parse_errors:
                _LOGGER.info(f"CRC while parse data - payload: {payload}")
            await self._retry_read(MODE_3_SML_1_04, retry_count)

        except Exception as exc:
            if not self.ignore_parse_errors:
                _LOGGER.warning(f"Exception {type(exc).__name__} - {exc} while parse data - payload: {payload}")
            await self._retry_read(MODE_3_SML_1_04, retry_count)

    async def _retry_read(self, mode: int, retry_count: int):
        if retry_count < self.MAX_READ_RETRIES:
            await asyncio.sleep(random.uniform(MIN_RETRY_DELAY, MAX_RETRY_DELAY))
            await self.read_tibber_local(mode=mode, retry_count=retry_count + 1)

    async def updated_tibber_metrics_if_needed(self, log_payload: bool = False):
        if self._metrics_update_is_running:
            return

        # only request every 30 minutes (= 30 * 60sec) for new meta_data...
        to_wait_till = self._LAST_METRICS_UPDATE + 1800
        if to_wait_till > time.time():
            #_LOGGER.debug(f"updated_tibber_metrics_if_needed(): no update required [wait for: {round((to_wait_till - time.time())/60, 1)} min]")
            return

        self._metrics_update_is_running = True
        try:
            _LOGGER.debug(f"updated_tibber_metrics_if_needed(): request: {self.url_metrics}")
            async with self.web_session.get(self.url_metrics, auth=self.basic_auth, ssl=False, timeout=REQUEST_TIMEOUT) as res:
                res.raise_for_status()
                self._metrics_data = await res.json()
                if log_payload:
                    _LOGGER.debug(f"updated_tibber_metrics_if_needed(): metrics response: {self._metrics_data}")

        except Exception as exc:
            _LOGGER.warning(f"updated_tibber_metrics_if_needed(): access to bridge failed with exception: {type(exc).__name__} - {exc}")

        finally:
            # we also mark failed attempts - so a bridge that does not provide any metrics will not be
            # requested with every update cycle
            self._LAST_METRICS_UPDATE = time.time()
            self._metrics_update_is_running = False

    # websocket implementation from here...
    async def ws_connect(self):
        try:
            #async with self.websession.ws_connect(self.url_ws, headers=self.REQ_HEADERS_WS, compress=0) as ws:
            async with self.web_session.ws_connect(self.url_ws, auth=self.basic_auth, compress=0) as ws:
                self.ws_connected = True
                self.ws_obj = ws
                _LOGGER.info(f"ws_connect(): connected to websocket: {self.url_ws} - in COM MODE: {self._com_mode}")
                async for msg in ws:
                    self._ws_LAST_UPDATE = time.time()

                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        _LOGGER.debug(f"ws_connect(): received: {msg}")
                        break

                    # do we need to push new data event to the coordinator?
                    if await self._ws_handle_message(msg):
                        await self.updated_tibber_metrics_if_needed()
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
            _LOGGER.debug(f"ws_connect(): TimeoutError: No WebSocket message received within timeout period: {type(time_exc).__name__} - {time_exc}")
        except CancelledError as canceled:
            _LOGGER.debug(f"ws_connect(): Terminated? - {type(canceled).__name__} - {canceled}")
        except Exception as x:
            _LOGGER.error(f"ws_connect(): !!! {type(x).__name__} - {x}")

        finally:
            _LOGGER.debug(f"ws_connect(): -- END HAS REACHED --")
            # 'a_ws_obj' is None, if we could not connect at all (or if we have been closed already)
            a_ws_obj = self.ws_obj
            self.ws_connected = False
            self.ws_obj = None
            try:
                await self.ws_close(a_ws_obj)
            except Exception as e:
                _LOGGER.error(f"ws_connect(): Error while calling ws_close(): {type(e).__name__} - {e}")

    async def _ws_handle_message(self, msg) -> bool:
        # returns True, if the message contained data we could read
        if msg.type == aiohttp.WSMsgType.BINARY:
            payload = msg.data
            separator = b'>'
        elif msg.type == aiohttp.WSMsgType.TEXT:
            # for TEXT messages aiohttp provides a 'str' already
            payload = msg.data if isinstance(msg.data, str) else msg.data.decode('ascii', errors='ignore')
            separator = '>'
        else:
            _LOGGER.debug(f"ws_connect(): ignoring message of type {msg.type}: {msg}")
            return False

        try:
            # find the position of '>' - everything after it is the body
            separator_pos = payload.find(separator)
            if separator_pos <= 0:
                _LOGGER.debug(f"ws_connect(): {msg.type.name} invalid data (NO '>' FOUND) in: {payload}")
                return False

            head = payload[:separator_pos + 1]
            _LOGGER.debug(f"ws_connect(): {msg.type.name} head: {head}")
            topic, device_id = ws_parse_header_string(head) if isinstance(head, str) else ws_parse_header_bytes(head)

            # if multiple pulses are connected to the bridge, we must ignore the data of the other nodes
            if self.node_device_id is not None and self.node_device_id != device_id:
                _LOGGER.debug(f"ws_connect(): {msg.type.name} device of node_num '{self.node_device_id}' not matching the device in the message {device_id}")
                return False

            if topic is None:
                _LOGGER.warning(f"ws_connect(): {msg.type.name} without any topic (mode_'{self._com_mode}') in: {payload}")
                return False

            body = payload[separator_pos + 1:]
            _LOGGER.debug(f"ws_connect(): {msg.type.name} body '{topic}' [len:{len(body)}]: {body[:15]}{'...' if len(body) > 15 else ''}")

            if self._com_mode == MODE_3_SML_1_04 and isinstance(body, bytes) and "sml" in topic.lower():
                await self.mode_03_read_sml(body, retry_count=self.MAX_READ_RETRIES, log_payload=False)
                return True

            if self._com_mode == MODE_99_PLAINTEXT:
                await self.mode_99_read_plaintext(self._as_text(body), retry_count=self.MAX_READ_RETRIES, log_payload=False)
                return True

            if self._com_mode == MODE_10_ImpressionsAmbient:
                await self.mode_10_read_json_impressions_ambient(json.loads(self._as_text(body)), retry_count=self.MAX_READ_RETRIES, log_payload=False)
                return True

            _LOGGER.warning(f"ws_connect(): {msg.type.name} 'UNHANDLED' topic '{topic}'/mode_'{self._com_mode}' in: {payload}")

        except Exception as exc:
            _LOGGER.warning(f"ws_connect(): could not process {msg.type.name} message: {type(exc).__name__} - {exc} [{msg}]")

        return False

    @staticmethod
    def _as_text(body) -> str:
        return body if isinstance(body, str) else body.decode('ascii', errors='ignore')

    def _ws_notify_for_new_data(self):
        # the bridge is pushing data quite often - so we throttle the coordinator updates. an already
        # scheduled task will pick up the latest data by itself - so there is no need to cancel it
        if self._ws_debounced_update_task is not None and not self._ws_debounced_update_task.done():
            return
        self._ws_debounced_update_task = asyncio.create_task(self._ws_debounce_coordinator_update())

    async def _ws_debounce_coordinator_update(self):
        if self._coordinator is None:
            return

        elapsed = time.time() - self._ws_LAST_UPDATE_NOTIFY
        if elapsed < WS_MIN_NOTIFY_DELAY_IN_SEC:
            #_LOGGER.debug(f"_ws_debounce_coordinator_update(): sleeping before notifying for updated data")
            await asyncio.sleep(WS_MIN_NOTIFY_DELAY_IN_SEC - elapsed)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"{self.url_ws} received: {gen_log_list(self._obis_values)}")

        self._coordinator.async_set_updated_data({
            DATA_KEY: self._obis_values,
            METRICS_KEY: self._metrics_data
        })
        self._ws_LAST_UPDATE_NOTIFY = time.time()

    async def ws_close(self, ws):
        """Close the WebSocket connection cleanly."""
        _LOGGER.debug(f"ws_close(): called")
        self.ws_connected = False
        if ws is not None:
            try:
                await ws.close()
                _LOGGER.debug(f"ws_close(): connection closed successfully")
            except Exception as e:
                _LOGGER.info(f"ws_close(): Error closing WebSocket connection: {type(e).__name__} - {e}")
            finally:
                self.ws_obj = None
        else:
            _LOGGER.debug(f"ws_close(): No active WebSocket connection to close (ws is None)")

        # we want to trigger the "ws-connection-state" update...
        if self._coordinator is not None:
            async_call_later(self._coordinator.hass, 5, self._coordinator.call_later_update_device_registry)

    async def ws_close_and_prepare_to_terminate(self):
        try:
            # a possibly scheduled coordinator update is not required any longer
            if self._ws_debounced_update_task is not None and not self._ws_debounced_update_task.done():
                self._ws_debounced_update_task.cancel()
            self._ws_debounced_update_task = None

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

        except Exception as e:
            _LOGGER.error(f"ws_close_and_prepare_to_terminate(): Error: {type(e).__name__} - {e}")

    def ws_check_last_update(self) -> bool:
        if self._ws_LAST_UPDATE + WS_MAX_SILENCE_IN_SEC > time.time():
            _LOGGER.debug(f"ws_check_last_update(): all good! [last update: {int(time.time()-self._ws_LAST_UPDATE)} sec ago]")
            return True
        else:
            _LOGGER.info(f"ws_check_last_update(): force reconnect...")
            return False