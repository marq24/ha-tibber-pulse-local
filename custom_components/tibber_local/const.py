from dataclasses import dataclass
from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfFrequency,
    UnitOfEnergy,
    UnitOfPower,
    DEGREE,
)

DOMAIN: Final = "tibber_local"
MANUFACTURE: Final = "Tibber"
DEFAULT_NAME = "ltibber"
DEFAULT_HOST = "tibber-bridge"
DEFAULT_PWD = ""
DEFAULT_SCAN_INTERVAL = 10

CONF_NODE_NUMBER = "node_num"
CONF_IGNORE_READING_ERRORS = "ignore_errors"
DEFAULT_NODE_NUMBER = 1

MODE_UNKNOWN = -1
MODE_0_AutoScanMode = 0
MODE_1_IEC_62056_21 = 1
MODE_2_Logarex = 2
MODE_3_SML_1_04 = 3
MODE_10_ImpressionsAmbient = 10
MODE_11_ImpressionsIR = 11
MODE_99_PLAINTEXT = 99
ENUM_MODES = [MODE_0_AutoScanMode, MODE_1_IEC_62056_21, MODE_2_Logarex, MODE_3_SML_1_04, MODE_10_ImpressionsAmbient,
              MODE_11_ImpressionsIR]

ENUM_IMPLEMENTATIONS = [MODE_3_SML_1_04, MODE_99_PLAINTEXT]

@dataclass
class ExtSensorEntityDescription(SensorEntityDescription):
    aliases: list[str] | None = None

SENSOR_TYPES = [

    # Zählerstand Total
    SensorEntityDescription(
        key="0100010800ff",
        name="Import total",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Wirkenergie Total
    SensorEntityDescription(
        key="0100020800ff",
        name="Export total",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="0100010800ff_in_k",
        name="Import total (kWh)",
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="0100020800ff_in_k",
        name="Export total (kWh)",
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),

    # aktuelle Wirkleistung
    ExtSensorEntityDescription(
        key="0100100700ff",
        aliases=["0100010700ff",  "01000107ffff",  "0100020700ff", "01000f0700ff"],
        name="Power (actual)",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Wirkleistung L1
    ExtSensorEntityDescription(
        key="0100240700ff",
        aliases=["0100150700ff", "01001507ffff", "0100160700ff", "0100230700ff"],
        name="Power L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Wirkleistung L2
    ExtSensorEntityDescription(
        key="0100380700ff",
        aliases=["0100290700ff", "01002907ffff", "01002a0700ff", "0100370700ff"],
        name="Power L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Wirkleistung L3
    ExtSensorEntityDescription(
        key="01004c0700ff",
        aliases=["01003d0700ff", "01003d07ffff", "01003e0700ff", "01004b0700ff"],
        name="Power L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Spannung L1
    SensorEntityDescription(
        key="0100200700ff",
        name="Potential L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:lightning-bolt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Spannung L2
    SensorEntityDescription(
        key="0100340700ff",
        name="Potential L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:lightning-bolt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Spannung L3
    SensorEntityDescription(
        key="0100480700ff",
        name="Potential L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:lightning-bolt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Strom L1
    SensorEntityDescription(
        key="01001f0700ff",
        name="Current L1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Strom L2
    SensorEntityDescription(
        key="0100330700ff",
        name="Current L2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Strom L3
    SensorEntityDescription(
        key="0100470700ff",
        name="Current L3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Netz Frequenz
    SensorEntityDescription(
        key="01000e0700ff",
        name="Net frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Phasenabweichung Spannungen L1/L2
    SensorEntityDescription(
        key="0100510701ff",
        name="Potential Phase deviation L1/L2",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Phasenabweichung Spannungen L1/L3
    SensorEntityDescription(
        key="0100510702ff",
        name="Potential Phase deviation L1/L3",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Phasenabweichung Strom/Spannung L1
    SensorEntityDescription(
        key="0100510704ff",
        name="Current/Potential L1 Phase deviation",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Phasenabweichung Strom/Spannung L2
    SensorEntityDescription(
        key="010051070fff",
        name="Current/Potential L2 Phase deviation",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Phasenabweichung Strom/Spannung L3
    SensorEntityDescription(
        key="010051071aff",
        name="Current/Potential L3 Phase deviation",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]
