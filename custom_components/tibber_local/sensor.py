import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from homeassistant.util import slugify

from . import TibberLocalDataUpdateCoordinator, TibberLocalEntity
from .const import (
    DOMAIN,
    CONF_OBIS_CODES,
    SENSOR_TYPES,
    DEFAULT_OBIS_CODES,
    OBIS_DATA_KEY,
    METRICS_KEY,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    obis_values = coordinator.data.get(OBIS_DATA_KEY, {}) if coordinator.data else {}

    available_sensors = list(obis_values.keys()) if obis_values else None

    if available_sensors:
        _LOGGER.info(f"available obis codes found: {available_sensors}")
    else:
        available_sensors = config_entry.data.get(CONF_OBIS_CODES, [])
        _LOGGER.warning(f"no sensors found @ bridge [we check, if we have stored obis codes in our config_entry: {available_sensors}]")

    if available_sensors is None or len(available_sensors) == 0:
        _LOGGER.warning(f"could not detect available obis codes using just 'import total' and 'power current' as default!")
        # ok looks like, that we do not have any information about available sensors - so we just use two simple
        # obis codes 'import total' and 'power current'
        available_sensors = DEFAULT_OBIS_CODES


    if coordinator.device_id is None:
        _LOGGER.warning(f"no device id found in coordinator - please create a issue on github!")
        return

    if coordinator.eui_list is None:
        _LOGGER.warning(f"no eui id found in coordinator - please create a issue on github!")
        return

    for a_eui in coordinator.eui_list:
        for description in SENSOR_TYPES:
            if description.tag is None:
                _LOGGER.warning(f"no tag found for sensor description key: {description.key} - please create a issue on github!")
                continue

            should_add = False
            if description.tag.section == METRICS_KEY:
                should_add = bool(metrics_values)
            elif description.tag.section == OBIS_DATA_KEY:
                keys_to_check = [description.tag.key]
                if description.tag.aliases:
                    keys_to_check.extend(description.tag.aliases)
                should_add = any(sensor_key in available_sensors[a_eui] for sensor_key in keys_to_check)

            if should_add:
                entities.append(TibberLocalSensor(a_eui, coordinator, description))

    async_add_entities(entities)


class TibberLocalSensor(TibberLocalEntity, SensorEntity):
    def __init__(
            self,
            eui_id: str,
            coordinator: TibberLocalDataUpdateCoordinator,
            description: SensorEntityDescription
    ):
        """Initialize a singular value sensor."""
        super().__init__(eui_id=eui_id, coordinator=coordinator, description=description)

        key = self.entity_description.key.lower()
        if self.coordinator.use_classic_ids or (self.coordinator.device_id == self.eui_id):
            self.entity_id = f"{Platform.SENSOR}.{slugify(self.coordinator._config_entry.title)}_{key}".lower()
        else:
            # for compatibility reasons, we keep the old format for the eui_id, that match
            # the coordinator device_id (sinc that was the node, that was used to initialize
            # the integration)...
            self.entity_id = f"{Platform.SENSOR}.{self.eui_id}_{key}".lower()

        # we use the "key" also as our internal translation-key - and EXTREMELY important we have
        self._attr_translation_key = key

        if hasattr(description, 'suggested_display_precision') and description.suggested_display_precision is not None:
            self._attr_suggested_display_precision = description.suggested_display_precision
        else:
            self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data is not None:
            return self.coordinator.get_sensor_value(self.eui_id, self.entity_description.tag)
        return None

    @property
    def available(self):
        super_val = super().available
        if super_val:
            if self.entity_description.tag.section == OBIS_DATA_KEY and len(self.coordinator.data.get(OBIS_DATA_KEY), {}) == 0:
                return False

            if self.entity_description.tag.section == METRICS_KEY and len(self.coordinator.data.get(METRICS_KEY), {}) == 0:
                return False

        return super_val