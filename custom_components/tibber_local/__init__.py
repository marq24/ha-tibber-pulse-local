import asyncio
import logging
import voluptuous as vol

from datetime import timedelta
from smllib import SmlStreamReader

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, Event
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityDescription, Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    MANUFACTURE,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=10)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    global SCAN_INTERVAL

    SCAN_INTERVAL = timedelta(seconds=config_entry.options.get(CONF_SCAN_INTERVAL,
                                                               config_entry.data.get(CONF_SCAN_INTERVAL,
                                                                                     DEFAULT_SCAN_INTERVAL)))

    _LOGGER.info("Starting TibberLocal with interval: " + str(SCAN_INTERVAL))

    session = async_get_clientsession(hass)

    coordinator = TibberLocalDataUpdateCoordinator(hass, session, config_entry)

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    for platform in PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(config_entry, platform))

    config_entry.add_update_listener(async_reload_entry)
    return True


class TibberLocalDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, session, config_entry):
        self._host = config_entry.options.get(CONF_HOST, config_entry.data[CONF_HOST])
        the_pwd = config_entry.options.get(CONF_PASSWORD, config_entry.data[CONF_PASSWORD])
        self.bridge = TibberLocalBridge(host=self._host, pwd=the_pwd, websession=session, options=None)
        self.name = config_entry.title
        self._config_entry = config_entry
        self._statistics_available = False
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    # Callable[[Event], Any]
    # def __call__(self, evt: Event) -> bool:
    #    # just as testing the 'event.async_track_entity_registry_updated_event'
    #    _LOGGER.warning(str(evt))
    #    return True

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
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)


class TibberLocalEntity(Entity):
    _attr_should_poll = False

    def __init__(
            self, coordinator: TibberLocalDataUpdateCoordinator, description: EntityDescription
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._name = coordinator._config_entry.title
        self._state = None

    @property
    def device_info(self) -> dict:
        # "hw_version": self.coordinator._config_entry.options.get(CONF_DEV_NAME, self.coordinator._config_entry.data.get(CONF_DEV_NAME)),
        return {
            "identifiers": {(DOMAIN, self.coordinator._host, self._name)},
            "name": "Tibber Pulse local polling Bridge",
            "model": "Tibber Pulse+Bridge",
            "sw_version": "001",
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
        return f"{self._name}_{sensor}"

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

class TibberLocalBridge:

    def __init__(self, host, pwd, websession, options: dict = None):
        _LOGGER.info(f"restarting TibberLocalBridge integration... for host: '{host}' with options: {options}")
        self.websession = websession
        self.url = f"http://admin:{pwd}@{host}/data.json?node_id=1"
        self._obis_values = {}

    async def update(self):
        await self.read_tibber_local()

    async def read_tibber_local(self):
        self._obis_values = {}
        async with self.websession.get(self.url, ssl=False) as res:
            res.raise_for_status()
            if res.status == 200:
                stream = SmlStreamReader()
                stream.add(await res.content.read())
                sml_frame = stream.get_frame()
                if sml_frame is None:
                    _LOGGER.warning("Bytes missing")
                else:
                    # Shortcut to extract all values without parsing the whole frame
                    for entry in sml_frame.get_obis():
                        self._obis_values[entry.obis] = entry
            else:
                _LOGGER.warning(f"access to bridge failed with code {res.status}")

    def _get_value_internal(self, key):
        if key in self._obis_values:
            a_obis = self._obis_values.get(key)
            if hasattr(a_obis, 'scaler'):
                return a_obis.value * 10 ** int(a_obis.scaler)
            else:
                return a_obis.value

    def _get_str_internal(self, key):
        if key in self._obis_values:
            return self._obis_values.get(key).value

    # obis: https://www.promotic.eu/en/pmdoc/Subsystems/Comm/PmDrivers/IEC62056_OBIS.htm
    # units: https://github.com/spacemanspiff2007/SmlLib/blob/master/src/smllib/const.py

    #<obis: 010060320101, value: XYZ>
    #<obis: 0100600100ff, value: 0a123b4c567890d12e34>
    #<obis: 0100010800ff, status: 1861892, unit: 30, scaler: -1, value: 36061128>
    #<obis: 0100020800ff, unit: 30, scaler: -1, value: 86194714>
    #<obis: 0100100700ff, unit: 27, scaler: 0, value: -49>
    #<obis: 0100240700ff, unit: 27, scaler: 0, value: 511>
    #<obis: 0100380700ff, unit: 27, scaler: 0, value: -415>
    #<obis: 01004c0700ff, unit: 27, scaler: 0, value: -146>
    #<obis: 0100200700ff, unit: 35, scaler: -1, value: 2390>
    #<obis: 0100340700ff, unit: 35, scaler: -1, value: 2394>
    #<obis: 0100480700ff, unit: 35, scaler: -1, value: 2397>
    #<obis: 01001f0700ff, unit: 33, scaler: -2, value: 215>
    #<obis: 0100330700ff, unit: 33, scaler: -2, value: 170>
    #<obis: 0100470700ff, unit: 33, scaler: -2, value: 67>
    #<obis: 0100510701ff, unit: 8, scaler: -1, value: 2390>
    #<obis: 0100510702ff, unit: 8, scaler: -1, value: 1204>
    #<obis: 0100510704ff, unit: 8, scaler: -1, value: 8>
    #<obis: 010051070fff, unit: 8, scaler: -1, value: 1779>
    #<obis: 010051071aff, unit: 8, scaler: -1, value: 1856>
    #<obis: 01000e0700ff, unit: 44, scaler: -1, value: 500>
    #<obis: 010000020000, value: 01>
    #<obis: 0100605a0201, value: 123a4567>

    @property
    def get010060320101(self) -> str: # XYZ
        return self._get_str_internal('010060320101')
    @property
    def get0100600100ff(self) -> str: # 0a123b4c567890d12e34
        return self._get_str_internal('0100600100ff')
    @property
    def get0100010800ff(self) -> float:
        return self._get_value_internal('0100010800ff')
    @property
    def get0100010800ff_status(self) -> float:
        if '0100010800ff' in self._obis_values and hasattr(self._obis_values.get('0100010800ff'), 'status'):
            return self._obis_values.get('0100010800ff').status
    @property
    def get0100020800ff(self) -> float:
        return self._get_value_internal('0100020800ff')
    @property
    def get0100100700ff(self) -> float:
        return self._get_value_internal('0100100700ff')
    @property
    def get0100240700ff(self) -> float:
        return self._get_value_internal('0100240700ff')
    @property
    def get0100380700ff(self) -> float:
        return self._get_value_internal('0100380700ff')
    @property
    def get01004c0700ff(self) -> float:
        return self._get_value_internal('01004c0700ff')
    @property
    def get0100200700ff(self) -> float:
        return self._get_value_internal('0100200700ff')
    @property
    def get0100340700ff(self) -> float:
        return self._get_value_internal('0100340700ff')
    @property
    def get0100480700ff(self) -> float:
        return self._get_value_internal('0100480700ff')
    @property
    def get01001f0700ff(self) -> float:
        return self._get_value_internal('01001f0700ff')
    @property
    def get0100330700ff(self) -> float:
        return self._get_value_internal('0100330700ff')
    @property
    def get0100470700ff(self) -> float:
        return self._get_value_internal('0100470700ff')
    @property
    def get0100510701ff(self) -> float:
        return self._get_value_internal('0100510701ff')
    @property
    def get0100510702ff(self) -> float:
        return self._get_value_internal('0100510702ff')
    @property
    def get0100510704ff(self) -> float:
        return self._get_value_internal('0100510704ff')
    @property
    def get010051070fff(self) -> float:
        return self._get_value_internal('010051070fff')
    @property
    def get010051071aff(self) -> float:
        return self._get_value_internal('010051071aff')
    @property
    def get01000e0700ff(self) -> float:
        return self._get_value_internal('01000e0700ff')
    @property
    def get010000020000(self) -> str: # 01
        return self._get_str_internal('010000020000')
    @property
    def get0100605a0201(self) -> str: # 123a4567
        return self._get_str_internal('0100605a0201')