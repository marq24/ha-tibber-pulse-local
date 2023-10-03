from typing import Final
from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.components.number import (
    NumberEntityDescription,
    NumberDeviceClass, NumberMode
)
from homeassistant.const import (
    ENERGY_KILO_WATT_HOUR,
    ENERGY_WATT_HOUR,
    PERCENTAGE,
    POWER_WATT,
    POWER_KILO_WATT,
    UnitOfElectricPotential,
    UnitOfElectricCurrent, UnitOfFrequency,
)
from homeassistant.helpers.entity import EntityCategory

DOMAIN: Final = "tibber_local"
MANUFACTURE: Final = "Tibber"
DEFAULT_HOST = "tibber-bridge"
DEFAULT_PWD = ""
DEFAULT_SCAN_INTERVAL = 10

SENSOR_TYPES = [
    SensorEntityDescription(
        key="0100010800ff",
        name="Home import",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="0100020800ff",
        name="Home export",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
]