import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from homeassistant.util import slugify
from . import TibberLocalDataUpdateCoordinator, TibberLocalEntity
from .const import (
    DOMAIN,
    SENSOR_TYPES
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    available_sensors = None
    if hasattr(coordinator, 'bridge' ):
        if hasattr(coordinator.bridge, '_obis_values'):
            if len(coordinator.bridge._obis_values) > 0:
                available_sensors = coordinator.bridge._obis_values.keys()
                _LOGGER.info(f"available sensors found: {available_sensors}")
            else:
                _LOGGER.warning(f"no sensors found @ bridge")

    if available_sensors is None or len(available_sensors) == 0:
        _LOGGER.warning(f"could not detect available sensors (obis-codes) using just 'import total' and 'power current' as default!")
        # ok looks like, that we do not have any information about available sensors - so we just use two simple
        # obis codes 'import total' and 'power current'
        available_sensors = ["0100010800ff", "0100100700ff"]

    for description in SENSOR_TYPES:
        key = description.key
        if key.endswith("_in_k"):
           key = key[:-5]

        if key in available_sensors:
            entity = TibberLocalSensor(coordinator, description)
            entities.append(entity)
        elif hasattr(description, "aliases"):
            if description.aliases is not None and len(description.aliases) > 0:
                for alias in description.aliases:
                    if alias in available_sensors:
                        entity = TibberLocalSensor(coordinator, description)
                        entities.append(entity)
                        break

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
    def native_value(self) -> StateType:
        return getattr(self.coordinator.bridge, 'attr' + self.entity_description.key)

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
