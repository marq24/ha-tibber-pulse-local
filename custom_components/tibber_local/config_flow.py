import asyncio
import logging
from typing import Any

import probatio


from aiohttp import ClientError
from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigFlowResult, SOURCE_RECONFIGURE
from homeassistant.const import (
    CONF_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_PASSWORD,
    CONF_MODE,
    CONF_DEVICE_ID
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
from homeassistant.util import slugify

from . import TibberLocalDataUpdateCoordinator
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_HOST,
    DEFAULT_PWD,
    DEFAULT_USE_POLLING,
    DEFAULT_SCAN_INTERVAL,
    ENUM_IMPLEMENTATIONS,
    CONF_NODE_NUMBER,
    CONF_IGNORE_READING_ERRORS,
    CONF_USE_POLLING,
    CONF_OBIS_CODES,
    DEFAULT_NODE_NUMBER,
    CONFIG_VERSION,
    CONFIG_MINOR_VERSION,
    OBIS_DATA_KEY,
    UNKNOWN_SERIAL
)
from .tibber_client import TibberLocalBridge

_LOGGER = logging.getLogger(__name__)


@staticmethod
def tibber_local_entries(hass: HomeAssistant):
    conf_hosts = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        a_host = entry.data[CONF_HOST]
        a_node = entry.data[CONF_NODE_NUMBER]

        if hasattr(entry, 'options'):
            if CONF_HOST in entry.options:
                a_host = entry.options[CONF_HOST]
            if CONF_NODE_NUMBER in entry.options:
                a_node = entry.options[CONF_NODE_NUMBER]

        conf_hosts.append(f"{a_node}@@{a_host}")
    return conf_hosts


@staticmethod
def _host_in_configuration_exists(a_host: str, a_node, hass: HomeAssistant) -> bool:
    if f"{a_node}@@{a_host}" in tibber_local_entries(hass):
        return True
    return False

def _config_title_exists(a_title: str, hass: HomeAssistant) -> bool:
    return slugify(a_title) in [slugify(a_entry.title) for a_entry in hass.config_entries.async_entries(DOMAIN)]

class TibberLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION

    def __init__(self):
        self._errors = {}
        self._default_name = DEFAULT_NAME
        self._default_host = DEFAULT_HOST
        self._default_pwd = DEFAULT_PWD
        self._default_use_polling = DEFAULT_USE_POLLING
        self._default_scan_interval = DEFAULT_SCAN_INTERVAL
        self._default_node_number = DEFAULT_NODE_NUMBER
        self._default_ignore_errors = False
        self._default_obis_codes = None
        self._node_device_id = None

    async def _test_connection_tibber_local(self, host, pwd, node_num):
        self._errors = {}
        self._node_device_id = None
        try:
            bridge = TibberLocalBridge(host=host, pwd=pwd, websession=async_get_clientsession(self.hass), node_num=node_num)
            try:
                # we MUST init the device_id
                await bridge.get_eui_for_node()
                if bridge.node_device_id is not None:
                    _LOGGER.debug(f"_test_connection_tibber_local(): Found device_id: {bridge.node_device_id} for node: {node_num}")
                    self._node_device_id = bridge.node_device_id
                    await bridge.detect_com_mode()
                    if bridge._com_mode in ENUM_IMPLEMENTATIONS:
                        self._con_mode = bridge._com_mode
                        return await self._test_data_available(bridge, host)
                    else:
                        self._errors[CONF_HOST] = "unknown_mode"
                else:
                    self._errors[CONF_HOST] = "unknown_device"

            except ValueError as val_err:
                self._errors[CONF_HOST] = "unknown_mode"
                _LOGGER.warning(f"_test_connection_tibber_local(): ValueError: {val_err}")

        except (OSError, ClientError, asyncio.TimeoutError) as exc:
            self._errors[CONF_HOST] = "cannot_connect"
            _LOGGER.warning(f"_test_connection_tibber_local(): Could not connect to local Tibber Pulse Bridge at {host}, check host/ip address\n{type(exc).__name__} -> {exc}")
        return False

    async def _test_data_available(self, bridge: TibberLocalBridge, host: str) -> bool:
        try:
            await bridge.update_and_log()

            # unfortunately, there is no other parser than the TibberLocalDataUpdateCoordinator,
            # so we must create a dummy one here, to be able to parse the serial data/number
            # from the found smart-meter
            coordinator = TibberLocalDataUpdateCoordinator(self.hass, None)

            if len(bridge._obis_values.keys()) > 0:
                coordinator.data = {OBIS_DATA_KEY: bridge._obis_values}
                self._serial = coordinator.serial if coordinator.serial != UNKNOWN_SERIAL else self._node_device_id
                _LOGGER.info(f"_test_data_available(): Successfully connect to local Tibber Pulse Bridge at {host} - found serial: {self._serial}")
                if self._default_obis_codes is None:
                    self._default_obis_codes = list(bridge._obis_values.keys())
                return True
            else:
                await asyncio.sleep(2)
                await bridge.update_and_log()
                if len(bridge._obis_values.keys()) > 0:
                    coordinator.data = {OBIS_DATA_KEY: bridge._obis_values}
                    self._serial = coordinator.serial if coordinator.serial != UNKNOWN_SERIAL else self._node_device_id
                    _LOGGER.info(f"_test_data_available(): Successfully connect to local Tibber Pulse Bridge at {host} - found serial: {self._serial}")
                    if self._default_obis_codes is None:
                        self._default_obis_codes = list(bridge._obis_values.keys())
                    return True
                else:
                    _LOGGER.warning(f"_test_data_available(): No data from Tibber Pulse Bridge at {host}")
                    self._errors[CONF_HOST] = "no_data"
                    return False

        except (OSError, ClientError, asyncio.TimeoutError) as exc:
            self._errors[CONF_HOST] = "cannot_connect"
            _LOGGER.warning(f"_test_data_available(): Could not read data from local Tibber Pulse Bridge at {host}, check host/ip address\n{type(exc).__name__} -> {exc}")
        return False

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry_data = self._get_reconfigure_entry().data
        self._default_name = entry_data.get(CONF_NAME, DEFAULT_NAME)
        self._default_host = entry_data.get(CONF_HOST, DEFAULT_HOST)
        self._default_pwd = entry_data.get(CONF_PASSWORD, DEFAULT_PWD)
        self._default_use_polling = entry_data.get(CONF_USE_POLLING, DEFAULT_USE_POLLING)
        self._default_scan_interval = entry_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._default_node_number = entry_data.get(CONF_NODE_NUMBER, DEFAULT_NODE_NUMBER)
        self._default_ignore_errors = entry_data.get(CONF_IGNORE_READING_ERRORS, False)
        self._default_obis_codes = entry_data.get(CONF_OBIS_CODES, None)
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        self._errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST].lower()
            # make sure we just handle host/ip's - removing http/https
            if host.startswith("http://"):
                host = host.replace("http://", "")
            if host.startswith('https://'):
                host = host.replace("https://", "")

            name = user_input[CONF_NAME]
            pwd = user_input[CONF_PASSWORD]
            use_polling = user_input[CONF_USE_POLLING]
            scan = user_input[CONF_SCAN_INTERVAL]
            node_num = user_input[CONF_NODE_NUMBER]
            ignore_errors = user_input[CONF_IGNORE_READING_ERRORS]

            if self.source != SOURCE_RECONFIGURE:
                if _config_title_exists(name, self.hass):
                    self._errors[CONF_NAME] = "already_configured"
                    raise data_entry_flow.AbortFlow("already_configured")
                elif _host_in_configuration_exists(host, node_num, self.hass):
                    self._errors[CONF_HOST] = "already_configured"
                    self._errors[CONF_NODE_NUMBER] = "already_configured"
                    raise data_entry_flow.AbortFlow("already_configured")

            if await self._test_connection_tibber_local(host, pwd, node_num):
                a_data = {CONF_NAME: name,
                          CONF_HOST: host,
                          CONF_PASSWORD: pwd,
                          CONF_USE_POLLING: use_polling,
                          CONF_SCAN_INTERVAL: scan,
                          CONF_NODE_NUMBER: node_num,
                          CONF_IGNORE_READING_ERRORS: ignore_errors,
                          CONF_ID: self._serial,
                          CONF_DEVICE_ID: self._node_device_id,
                          CONF_MODE: self._con_mode}

                # just store again the obis codes (that have been previously available in the config_entry)
                if self._default_obis_codes is not None:
                    a_data[CONF_OBIS_CODES] = self._default_obis_codes

                self._abort_if_unique_id_configured()
                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_reload_and_abort(entry=self._get_reconfigure_entry(), data=a_data)
                else:
                    return self.async_create_entry(title=name, data=a_data)
            else:
                if self._node_device_id is not None:
                    _LOGGER.error(f"async_step_user(): Could not successfully read data from your Tibber Pulse Bridge at '{host}'. The specified host is fine - but the Integration could not detect the protocol - please enable the debug log to receive more details.")
                else:
                    _LOGGER.error(f"async_step_user(): Could not connect to Tibber Pulse Bridge at '{host}', check host ip address")
        else:
            user_input = {CONF_NAME: self._default_name,
                          CONF_HOST: self._default_host,
                          CONF_PASSWORD: self._default_pwd,
                          CONF_USE_POLLING: self._default_use_polling,
                          CONF_SCAN_INTERVAL: self._default_scan_interval,
                          CONF_NODE_NUMBER: self._default_node_number,
                          CONF_IGNORE_READING_ERRORS: self._default_ignore_errors}

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                probatio.Schema({
                    probatio.Required(CONF_NAME): selector.TextSelector(),
                    probatio.Required(CONF_HOST): selector.TextSelector(),
                    probatio.Required(CONF_PASSWORD):
                        selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
                    probatio.Required(CONF_USE_POLLING): selector.BooleanSelector(),
                    probatio.Required(CONF_SCAN_INTERVAL):
                        selector.NumberSelector(selector.NumberSelectorConfig(
                            step=1,
                            mode=selector.NumberSelectorMode.BOX)),
                    probatio.Required(CONF_NODE_NUMBER):
                        selector.NumberSelector(selector.NumberSelectorConfig(
                            step=1,
                            mode=selector.NumberSelectorMode.BOX)),
                    probatio.Required(CONF_IGNORE_READING_ERRORS): selector.BooleanSelector(),
                }),
                user_input,
            ),
            description_placeholders={"repo": "https://github.com/marq24/ha-tibber-pulse-local"},
            last_step=True,
            errors=self._errors,
        )