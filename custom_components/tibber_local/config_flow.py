import asyncio
import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientResponseError
from requests.exceptions import HTTPError, Timeout

from custom_components.tibber_local import TibberLocalBridge
from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigFlowResult, SOURCE_RECONFIGURE
from homeassistant.const import CONF_ID, CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL, CONF_PASSWORD, CONF_MODE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import slugify
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
    DEFAULT_NODE_NUMBER,
    CONFIG_VERSION,
    CONFIG_MINOR_VERSION
)

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
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        self._errors = {}
        self._default_name = DEFAULT_NAME
        self._default_host = DEFAULT_HOST
        self._default_pwd = DEFAULT_PWD
        self._default_use_polling = DEFAULT_USE_POLLING
        self._default_scan_interval = DEFAULT_SCAN_INTERVAL
        self._default_node_number = DEFAULT_NODE_NUMBER
        self._default_ignore_errors = False


    async def _test_connection_tibber_local(self, host, pwd, node_num):
        self._errors = {}
        try:
            bridge = TibberLocalBridge(host=host, pwd=pwd, websession=async_get_clientsession(self.hass),
                                       node_num=node_num)
            try:
                await bridge.detect_com_mode()
                if bridge._com_mode in ENUM_IMPLEMENTATIONS:
                    self._con_mode = bridge._com_mode
                    return await self._test_data_available(bridge, host)
                else:
                    self._errors[CONF_HOST] = "unknown_mode"

            except ValueError as val_err:
                self._errors[CONF_HOST] = "unknown_mode"
                _LOGGER.warning(f"ValueError: {val_err}")

        except (OSError, HTTPError, Timeout, ClientResponseError) as exc:
            self._errors[CONF_HOST] = "cannot_connect"
            _LOGGER.warning(f"Could not connect to local Tibber Pulse Bridge at {host}, check host/ip address\n{type(exc)} -> {exc}")
        return False

    async def _test_data_available(self, bridge: TibberLocalBridge, host: str) -> bool:
        try:
            await bridge.update_and_log()
            _data_available = len(bridge._obis_values.keys()) > 0
            if _data_available:
                self._serial = bridge.serial
                _LOGGER.info(f"Successfully connect to local Tibber Pulse Bridge at {host}")
                return True
            else:
                await asyncio.sleep(2)
                await bridge.update_and_log()
                _data_available = len(bridge._obis_values.keys()) > 0
                if _data_available:
                    self._serial = bridge.serial
                    _LOGGER.info(f"Successfully connect to local Tibber Pulse Bridge at {host}")
                    return True
                else:
                    _LOGGER.warning(f"No data from Tibber Pulse Bridge at {host}")
                    self._errors[CONF_HOST] = "no_data"
                    return False

        except (OSError, HTTPError, Timeout, ClientResponseError) as exc:
            self._errors[CONF_HOST] = "cannot_connect"
            _LOGGER.warning(f"Could not read data from local Tibber Pulse Bridge at {host}, check host/ip address\n{type(exc)} -> {exc}")
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
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
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
                          CONF_ID: self._serial,
                          CONF_MODE: self._con_mode}

                self._abort_if_unique_id_configured()
                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_reload_and_abort(entry=self._get_reconfigure_entry(), data=a_data)
                else:
                    return self.async_create_entry(title=name, data=a_data)
            else:
                _LOGGER.error("Could not connect to Tibber Pulse Bridge at %s, check host ip address", host)
        else:
            user_input = {}
            user_input[CONF_NAME] = self._default_name
            user_input[CONF_HOST] = self._default_host
            user_input[CONF_PASSWORD] = self._default_pwd
            user_input[CONF_USE_POLLING] = self._default_use_polling
            user_input[CONF_SCAN_INTERVAL] = self._default_scan_interval
            user_input[CONF_NODE_NUMBER] = self._default_node_number
            user_input[CONF_IGNORE_READING_ERRORS] = self._default_ignore_errors

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                vol.Required(CONF_HOST, default=user_input[CONF_HOST]): str,
                vol.Required(CONF_PASSWORD, default=user_input[CONF_PASSWORD]): str,
                vol.Required(CONF_USE_POLLING, default=user_input[CONF_USE_POLLING]): bool,
                vol.Required(CONF_SCAN_INTERVAL, default=user_input[CONF_SCAN_INTERVAL]): int,
                vol.Required(CONF_NODE_NUMBER, default=user_input[CONF_NODE_NUMBER]): int,
                vol.Required(CONF_IGNORE_READING_ERRORS, default=user_input[CONF_IGNORE_READING_ERRORS]): bool
            }),
            last_step=True,
            errors=self._errors,
        )

    # @staticmethod
    # @callback
    # def async_get_options_flow(config_entry):
    #     return TibberLocalOptionsFlowHandler(config_entry)


# class TibberLocalOptionsFlowHandler(config_entries.OptionsFlow):
#
#     def __init__(self, config_entry):
#         """Initialize HACS options flow."""
#         self.data = dict(config_entry.data);
#         if len(dict(config_entry.options)) == 0:
#             self.options = {}
#         else:
#             self.options = dict(config_entry.options)
#
#     async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
#         """Manage the options."""
#         return await self.async_step_user()
#
#     async def async_step_user(self, user_input=None):
#         """Handle a flow initialized by the user."""
#         self._errors = {}
#         if user_input is not None:
#
#             # verify the entered host...
#             host_entry = user_input.get(CONF_HOST, DEFAULT_HOST).lower()
#             # make sure we just handle host/ip's - removing http/https
#             if host_entry.startswith("http://"):
#                 host_entry = host_entry.replace("http://", "")
#             if host_entry.startswith('https://'):
#                 host_entry = host_entry.replace("https://", "")
#             user_input[CONF_HOST] = host_entry
#
#             node_num = user_input[CONF_NODE_NUMBER]
#             self.options.update(user_input)
#             if self.data.get(CONF_HOST) != self.options.get(CONF_HOST) or self.data.get(CONF_NODE_NUMBER) != self.options.get(CONF_NODE_NUMBER):
#                 # ok looks like the host has been changed... we need to do some things...
#                 if _host_in_configuration_exists(host_entry, node_num, self.hass):
#                     self._errors[CONF_HOST] = "already_configured"
#                     self._errors[CONF_NODE_NUMBER] = "already_configured"
#                 else:
#                     return self._update_options()
#             else:
#                 # host/node-number did not change...
#                 return self._update_options()
#
#         return self.async_show_form(
#             step_id="user",
#             data_schema=vol.Schema({
#                 vol.Required(CONF_NAME,
#                              default=self.options.get(CONF_NAME, self.data.get(CONF_NAME, DEFAULT_NAME))): str,
#                 vol.Required(CONF_HOST,
#                              default=self.options.get(CONF_HOST, self.data.get(CONF_HOST, DEFAULT_HOST))): str,
#                 vol.Required(CONF_PASSWORD,
#                              default=self.options.get(CONF_PASSWORD, self.data.get(CONF_PASSWORD, DEFAULT_PWD))): str,
#                 vol.Required(CONF_SCAN_INTERVAL, default=self.options.get(CONF_SCAN_INTERVAL,
#                                                                           self.data.get(CONF_SCAN_INTERVAL,
#                                                                                         DEFAULT_SCAN_INTERVAL))): int,
#                 vol.Required(CONF_NODE_NUMBER, default=self.options.get(CONF_NODE_NUMBER,
#                                                                         self.data.get(CONF_NODE_NUMBER,
#                                                                                       DEFAULT_NODE_NUMBER))): int,
#                 vol.Required(CONF_IGNORE_READING_ERRORS, default=self.options.get(CONF_IGNORE_READING_ERRORS,
#                                                                                   self.data.get(
#                                                                                       CONF_IGNORE_READING_ERRORS,
#                                                                                       False))): bool
#             }),
#         )
#
#     def _update_options(self):
#         """Update config entry options."""
#         return self.async_create_entry(data=self.options)
