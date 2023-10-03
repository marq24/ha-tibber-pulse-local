"""Platform for Senec sensors."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify
from homeassistant.const import CONF_TYPE

from . import TibberLocalDataUpdateCoordinator, TibberLocalEntity
from .const import (
    DOMAIN,
    SENSOR_TYPES
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities):
    """Initialize sensor platform from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in SENSOR_TYPES:
        entity = TibberLocalSensor(coordinator, description)
        entities.append(entity)

    async_add_entities(entities)


class TibberLocalSensor(TibberLocalEntity, SensorEntity):
    """Sensor for the single values (e.g. pv power, ac power)."""

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

        title = self.coordinator._config_entry.title
        key = self.entity_description.key.lower()
        name = self.entity_description.name
        self.entity_id = f"sensor.{slugify(title)}_{key}"
        self._attr_name = f"{name}"
        if hasattr(description, 'suggested_display_precision') and description.suggested_display_precision is not None:
            self._attr_suggested_display_precision = description.suggested_display_precision
        else:
            self._attr_suggested_display_precision = 2

    @property
    def state(self):
        """Return the current state."""
        value = getattr(self.coordinator.bridge, 'get'+self.entity_description.key)
        if type(value) != type(False):
            try:
                rounded_value = round(float(value), self._attr_suggested_display_precision)
                return rounded_value
            except (ValueError, TypeError):
                return value
        else:
            return value