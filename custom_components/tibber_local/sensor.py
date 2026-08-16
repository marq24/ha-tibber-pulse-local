import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from homeassistant.util import slugify

from . import TibberLocalDataUpdateCoordinator, TibberLocalEntity
from .const import (
    DOMAIN,
    SENSOR_TYPES,
    CONF_OBIS_CODES
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    obis_values = getattr(coordinator.bridge, '_obis_values', {})
    if len(obis_values) > 0:
        available_sensors = list(obis_values.keys())
        _LOGGER.info(f"available obis codes found: {available_sensors}")

        # we store the available OBIS codes (so that we are able to use
        # them later - when startup fails for some reason)
        if len(config_entry.data.get(CONF_OBIS_CODES, [])) < len(available_sensors):
            new_data = dict(config_entry.data)
            new_data[CONF_OBIS_CODES] = available_sensors
            hass.config_entries.async_update_entry(config_entry, data=new_data)
            _LOGGER.info(f"Updated obis codes stored in config_entry: {new_data[CONF_OBIS_CODES]}")
        else:
            _LOGGER.debug(f"Stored obis codes in config_entry: {config_entry.data.get(CONF_OBIS_CODES, [])}")
    else:
        available_sensors = config_entry.data.get(CONF_OBIS_CODES, [])
        _LOGGER.warning(f"no sensors found @ bridge [we check, if we have stored obis codes in our config_entry: {available_sensors}]")

    if len(available_sensors) == 0:
        _LOGGER.warning(f"could not detect available obis codes using just 'import total' and 'power current' as default!")
        # ok looks like, that we do not have any information about available sensors - so we just use two simple
        # obis codes 'import total' and 'power current'
        available_sensors = ["0100010800ff", "0100100700ff"]

    for description in SENSOR_TYPES:
        # our metrics sensors are not OBIS based - so they will be added always
        if description.entity_category == EntityCategory.DIAGNOSTIC:
            entities.append(TibberLocalSensor(coordinator, description))
            continue

        key = description.key
        if key.endswith("_in_k"):
            key = key[:-len("_in_k")]

        if key in available_sensors or any(alias in available_sensors for alias in getattr(description, "aliases", None) or []):
            entities.append(TibberLocalSensor(coordinator, description))

    async_add_entities(entities)


class TibberLocalSensor(TibberLocalEntity, SensorEntity):
    def __init__(
            self,
            coordinator: TibberLocalDataUpdateCoordinator,
            description: SensorEntityDescription
    ):
        """Initialize a singular value sensor."""
        super().__init__(coordinator=coordinator, description=description)

        key = self.entity_description.key.lower()
        self.entity_id = f"{Platform.SENSOR}.{slugify(self.coordinator._config_entry.title)}_{key}".lower()

        # we use the "key" also as our internal translation-key - and EXTREMELY important we have
        self._attr_translation_key = key

        if description.suggested_display_precision is not None:
            self._attr_suggested_display_precision = description.suggested_display_precision
        else:
            self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data is not None:
            return getattr(self.coordinator, 'attr' + self.entity_description.key, None)
        return None

    # @property
    # def state(self):
    #     """Return the current state."""
    #     value = getattr(self.coordinator.bridge, 'attr' + self.entity_description.key)
    #     if type(value) != type(False):
    #         try:
    #             rounded_value = round(float(value), self._attr_suggested_display_precision)
    #             return rounded_value
    #         except (ValueError, TypeError):
    #             return value
    #     else:
    #         return value
