import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify

from . import TibberLocalDataUpdateCoordinator, TibberLocalEntity
from .const import (
    DOMAIN,
    SENSOR_TYPES
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    available_sensors = None
    if hasattr(coordinator, 'bridge' ):
        if hasattr(coordinator.bridge, '_obis_values'):
            if len(coordinator.bridge._obis_values) > 0:
                available_sensors = coordinator.bridge._obis_values.keys()
                _LOGGER.info(f"available sensors found: {available_sensors}")

    for description in SENSOR_TYPES:
        if available_sensors is None or description.key in available_sensors:
            entity = TibberLocalSensor(coordinator, description)
            entities.append(entity)

    async_add_entities(entities)


class TibberLocalSensor(TibberLocalEntity, SensorEntity):
    def __init__(
            self,
            coordinator: TibberLocalDataUpdateCoordinator,
            description: SensorEntityDescription
    ):
        """Initialize a singular value sensor."""
        super().__init__(coordinator=coordinator, description=description)
        if (hasattr(self.entity_description, 'entity_registry_enabled_default')):
            self._attr_entity_registry_enabled_default = self.entity_description.entity_registry_enabled_default
        else:
            self._attr_entity_registry_enabled_default = True

        key = self.entity_description.key.lower()
        self.entity_id = f"sensor.{slugify(self.coordinator._config_entry.title)}_{key}"

        # we use the "key" also as our internal translation-key - and EXTREMELY important we have
        # to set the '_attr_has_entity_name' to trigger the calls to the localization framework!
        self._attr_translation_key = key
        self._attr_has_entity_name = True

        if hasattr(description, 'suggested_display_precision') and description.suggested_display_precision is not None:
            self._attr_suggested_display_precision = description.suggested_display_precision
        else:
            self._attr_suggested_display_precision = 2

    @property
    def state(self):
        """Return the current state."""
        value = getattr(self.coordinator.bridge, 'get' + self.entity_description.key)
        if type(value) != type(False):
            try:
                rounded_value = round(float(value), self._attr_suggested_display_precision)
                return rounded_value
            except (ValueError, TypeError):
                return value
        else:
            return value
