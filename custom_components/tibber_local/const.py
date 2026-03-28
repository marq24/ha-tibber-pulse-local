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
    EntityCategory,
    UnitOfTemperature,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTime,
)

DOMAIN: Final = "tibber_local"
MANUFACTURE: Final = "Tibber"
DEFAULT_NAME: Final = "ltibber"
DEFAULT_HOST: Final = "tibber-bridge"
DEFAULT_PWD: Final = ""
DEFAULT_USE_POLLING: Final = False
DEFAULT_SCAN_INTERVAL: Final = 10

CONFIG_VERSION: Final = 2
CONFIG_MINOR_VERSION: Final = 1

CONF_NODE_NUMBER: Final = "node_num"
CONF_USE_POLLING: Final = "use_polling"
CONF_OBIS_CODES: Final = "obis_codes"
CONF_IGNORE_READING_ERRORS: Final = "ignore_errors"
DEFAULT_NODE_NUMBER: Final = 1

MODE_UNKNOWN: Final = -1
MODE_0_AutoScanMode: Final = 0
MODE_1_IEC_62056_21: Final = 1
MODE_2_Logarex: Final = 2
MODE_3_SML_1_04: Final = 3
MODE_10_ImpressionsAmbient : Final= 10
MODE_11_ImpressionsIR: Final = 11
MODE_99_PLAINTEXT: Final = 99
ENUM_MODES: Final = [
    MODE_0_AutoScanMode,
    MODE_1_IEC_62056_21,
    MODE_2_Logarex,
    MODE_3_SML_1_04,
    MODE_10_ImpressionsAmbient,
    MODE_11_ImpressionsIR
]

ENUM_IMPLEMENTATIONS: Final = [MODE_3_SML_1_04, MODE_10_ImpressionsAmbient, MODE_99_PLAINTEXT]

@dataclass(frozen=True)
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
    # Zählerstand Tarif 1
    SensorEntityDescription(
        key="0100010801ff",
        name="Import tariff 1",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Zählerstand Tarif 2
    SensorEntityDescription(
        key="0100010802ff",
        name="Import tariff 2",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Zählerstand Tarif 3
    SensorEntityDescription(
        key="0100010803ff",
        name="Import tariff 3",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Zählerstand Tarif 4
    SensorEntityDescription(
        key="0100010804ff",
        name="Import tariff 4",
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
        key="0100010801ff_in_k",
        name="Import tariff 1 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="0100010802ff_in_k",
        name="Import tariff 2 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="0100010803ff_in_k",
        name="Import tariff 3 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="0100010804ff_in_k",
        name="Import tariff 4 (kWh)",
        entity_registry_enabled_default=False,
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


    SensorEntityDescription(
        key="node_battery_voltage",
        name="node_battery_voltage",
        suggested_display_precision=3,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:battery",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="node_temperature",
        name="node_temperature",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="node_avg_rssi",
        name="node_avg_rssi",
        suggested_display_precision=3,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        icon="mdi:wifi-strength-4",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="node_avg_lqi",
        name="node_avg_lqi",
        suggested_display_precision=3,
        icon="mdi:signal-variant",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="node_radio_tx_power",
        name="node_radio_tx_power",
        suggested_display_precision=3,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        icon="mdi:lightning-bolt-circle",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="node_uptime_ms",
        name="node_uptime_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="node_meter_msg_count_sent",
        name="node_meter_msg_count_sent",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="node_meter_pkg_count_sent",
        name="node_meter_pkg_count_sent",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="node_time_in_em0_ms",
        name="node_time_in_em0_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="node_time_in_em1_ms",
        name="node_time_in_em1_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="node_time_in_em2_ms",
        name="node_time_in_em2_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="node_acmp_rx_autolevel_9600",
        name="node_acmp_rx_autolevel_9600",
        suggested_display_precision=3,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="node_invalid_meter_readings_count",
        name="node_invalid_meter_readings_count",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="hub_meter_pkg_count_recv",
        name="hub_meter_pkg_count_recv",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="hub_meter_reading_count_recv",
        name="hub_meter_reading_count_recv",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="hub_meter_corrupt_reading_count_recv",
        name="hub_meter_corrupt_reading_count_recv",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="hub_compression_error_readings_count",
        name="hub_compression_error_readings_count",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
]
