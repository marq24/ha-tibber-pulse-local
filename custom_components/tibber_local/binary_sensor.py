import logging
from typing import Literal

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from . import TibberLocalDataUpdateCoordinator, TibberLocalEntity
from .const import (
    DOMAIN,
    BINARY_SENSOR_TYPES,
    OBIS_DATA_KEY,
    NODES_KEY,
    METRICS_KEY,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    obis_values = coordinator.data.get(OBIS_DATA_KEY, {}) if coordinator.data else {}
    nodes_values = coordinator.data.get(NODES_KEY, {}) if coordinator.data else {}
    metrics_values = coordinator.data.get(METRICS_KEY, {}) if coordinator.data else {}

    for description in BINARY_SENSOR_TYPES:
        if description.tag is None:
            _LOGGER.warning(f"no tag found for binary_sensor description key: {description.key} - please create a issue on github!")
            continue

        should_add = False
        if description.tag.section == NODES_KEY:
            should_add = bool(nodes_values)
        elif description.tag.section == METRICS_KEY:
            should_add = bool(metrics_values)

        if should_add:
            entities.append(TibberLocalBinarySensor(coordinator, description))

    async_add_entities(entities)


class TibberLocalBinarySensor(TibberLocalEntity, BinarySensorEntity):
    def __init__(
            self,
            coordinator: TibberLocalDataUpdateCoordinator,
            description: BinarySensorEntityDescription
    ):
        """Initialize a singular value sensor."""
        super().__init__(coordinator=coordinator, description=description)

        key = self.entity_description.key.lower()
        self.entity_id = f"{Platform.BINARY_SENSOR}.{slugify(self.coordinator._config_entry.title)}_{key}".lower()

        # we use the "key" also as our internal translation-key - and EXTREMELY important we have
        self._attr_translation_key = key

        self._attr_icon = self.entity_description.icon
        self._attr_icon_off = None
        if hasattr(self.entity_description, "icon_off"):
            self._attr_icon_off = self.entity_description.icon_off

    @property
    def is_on(self) -> bool:
        if self.coordinator.data is not None:
            a_val = self.coordinator.get_sensor_value(self.entity_description.tag)
            if a_val:
                if isinstance(a_val, bool):
                    return a_val

                str_val = str(a_val).lower()
                return str_val in ["true", "on", "t", "connected"]

        return None

    @property
    def state(self) -> Literal["on", "off"] | None:
        """Return the state."""
        if (is_on := self.is_on) is None:
            return None
        return STATE_ON if is_on else STATE_OFF

    @property
    def icon(self):
        """Return the icon of the sensor."""
        if self._attr_icon_off is not None and self.state == STATE_OFF:
            return self._attr_icon_off
        else:
            return self._attr_icon