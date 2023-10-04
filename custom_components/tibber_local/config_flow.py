import logging
import time

import voluptuous as vol

from custom_components.tibber_local import TibberLocalBridge
from requests.exceptions import HTTPError, Timeout
from aiohttp import ClientResponseError

from homeassistant import config_entries
from homeassistant.const import CONF_ID, CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_HOST,
    DEFAULT_PWD,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

@callback
def tibber_local_entries(hass: HomeAssistant):
    conf_hosts = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, 'options') and CONF_HOST in entry.options:
            conf_hosts.append(entry.options[CONF_HOST])
        else:
            conf_hosts.append(entry.data[CONF_HOST])
    return conf_hosts

class TibberLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        self._errors = {}
        self._data_available = False

    def _host_in_configuration_exists(self, host) -> bool:
        if host in tibber_local_entries(self.hass):
            return True
        return False

    async def _test_connection_tibber_local(self, host, pwd):
        self._errors = {}
        websession = self.hass.helpers.aiohttp_client.async_get_clientsession()
        try:
            bridge = TibberLocalBridge(host=host, pwd=pwd, websession=websession)
            await bridge.update()
            self._data_available = len(bridge._obis_values.keys()) > 0
            if self._data_available:
                self._serial = bridge.serial
                _LOGGER.info("Successfully connect to local Tibber Pulse Bridge at %s", host)
                return True
            else:
                # yes this will cause a WARNING in the LOG - but right now I have no clue how I
                # could implement a retry after a short while...
                time.sleep(2)
                await bridge.update()
                self._data_available = len(bridge._obis_values.keys()) > 0
                if self._data_available:
                    self._serial = bridge.serial
                    _LOGGER.info("Successfully connect to local Tibber Pulse Bridge at %s", host)
                    return True
                else:
                    _LOGGER.warning("No data from Tibber Pulse Bridge at %s", host)
                    self._errors[CONF_HOST] = "no_data"
                    return False

        except (OSError, HTTPError, Timeout, ClientResponseError):
            self._errors[CONF_HOST] = "cannot_connect"
            _LOGGER.warning("Could not connect to local Tibber Pulse Bridge at %s, check host/ip address", host)
        return False


    async def async_step_user(self, user_input=None):
        self._errors = {}
        if user_input is not None:
            host = user_input.get(CONF_HOST, DEFAULT_HOST).lower()
            # make sure we just handle host/ip's - removing http/https
            if host.startswith("http://"):
                host = host.replace("http://", "")
            if host.startswith('https://'):
                host = host.replace("https://", "")

            name = user_input.get(CONF_NAME, f"ltibber_{host}")
            pwd = user_input.get(CONF_PASSWORD, "")
            scan = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

            if self._host_in_configuration_exists(host):
                self._errors[CONF_HOST] = "already_configured"
            else:
                if await self._test_connection_tibber_local(host, pwd):

                    a_data = {CONF_NAME: name,
                              CONF_HOST: host,
                              CONF_PASSWORD: pwd,
                              CONF_SCAN_INTERVAL: scan,
                              CONF_ID: self._serial}

                    return self.async_create_entry(title=name, data=a_data)

                else:
                    _LOGGER.error("Could not connect to Tibber Pulse Bridge at %s, check host ip address", host)
        else:
            user_input = {}
            user_input[CONF_NAME] = DEFAULT_NAME
            user_input[CONF_HOST] = DEFAULT_HOST
            user_input[CONF_PASSWORD] = DEFAULT_PWD
            user_input[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME)
                    ): str,
                    vol.Required(
                        CONF_HOST, default=user_input.get(CONF_HOST, DEFAULT_HOST)
                    ): str,
                    vol.Required(
                        CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, DEFAULT_PWD)
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ): int,
                }
            ),
            last_step=True,
            errors=self._errors,
        )


    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TibberLocalOptionsFlowHandler(config_entry)

class TibberLocalOptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.data = dict(config_entry.data);
        if len(dict(config_entry.options)) == 0:
            self.options = {}
        else:
            self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}
        if user_input is not None:

            # verify the entered host...
            host_entry = user_input.get(CONF_HOST, DEFAULT_HOST).lower()
            # make sure we just handle host/ip's - removing http/https
            if host_entry.startswith("http://"):
                host_entry = host_entry.replace("http://", "")
            if host_entry.startswith('https://'):
                host_entry = host_entry.replace("https://", "")

            user_input[CONF_HOST] = host_entry

            self.options.update(user_input)
            if self.data.get(CONF_HOST) != self.options.get(CONF_HOST):
                # ok looks like the host has been changed... we need to do some things...
                if self._host_in_configuration_exists(host_entry):
                    self._errors[CONF_HOST] = "already_configured"
                else:
                    return self._update_options()
            else:
                # host did not change...
                return self._update_options()

        dataSchema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=self.options.get(CONF_NAME, self.data.get(CONF_NAME, DEFAULT_NAME)),
                ): str,  # pylint: disable=line-too-long
                vol.Required(
                    CONF_HOST, default=self.options.get(CONF_HOST, self.data.get(CONF_HOST, DEFAULT_HOST)),
                ): str,  # pylint: disable=line-too-long
                vol.Required(
                    CONF_PASSWORD, default=self.options.get(CONF_PASSWORD, self.data.get(CONF_PASSWORD, DEFAULT_PWD)),
                ): str,  # pylint: disable=line-too-long
                vol.Required(
                    CONF_SCAN_INTERVAL, default=self.options.get(CONF_SCAN_INTERVAL, self.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
                ): int,  # pylint: disable=line-too-long
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=dataSchema,
        )


    def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(data=self.options)
