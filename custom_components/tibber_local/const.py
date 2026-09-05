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

DATA_KEY: Final = "data"
METRICS_KEY: Final = "metrics"

UNKNOWN_SERIAL: Final = "UNKNOWN_SERIAL"

DEFAULT_OBIS_CODES: Final = ["0100010800ff", "0100100700ff"]

OBIS_KEY_ALIASES: Final = {
    "0100100700ff": ["0100010700ff", "01000107ffff", "0100020700ff", "01000f0700ff"],
    "0100240700ff": ["0100150700ff", "01001507ffff", "0100160700ff", "0100230700ff"],
    "0100380700ff": ["0100290700ff", "01002907ffff", "01002a0700ff", "0100370700ff"],
    "01004c0700ff": ["01003d0700ff", "01003d07ffff", "01003e0700ff", "01004b0700ff"],
}

NODE_METRICS: Final = "node_status"
HUB_METRICS: Final = "hub_attachments"
NODE_METRIC_PREFIX: Final = "node_"
HUB_METRIC_PREFIX: Final = "hub_"

NODE_METRIC_MAP: Final = {
    "node_battery_voltage": ["battery_voltage", "node_battery_voltage"],
    "node_temperature": ["temperature", "node_temperature"],
    "node_avg_rssi": ["avg_rssi", "node_avg_rssi"],
    "node_avg_lqi": ["avg_lqi", "node_avg_lqi"],
    "node_radio_tx_power": ["radio_tx_power"],
    "node_uptime_ms": ["node_uptime_ms"],
    "node_meter_msg_count_sent": ["meter_msg_count_sent"],
    "node_meter_pkg_count_sent": ["meter_pkg_count_sent"],
    "node_time_in_em0_ms": ["time_in_em0_ms"],
    "node_time_in_em1_ms": ["time_in_em1_ms"],
    "node_time_in_em2_ms": ["time_in_em2_ms"],
    "node_acmp_rx_autolevel_9600": ["acmp_rx_autolevel_9600"],
    "node_invalid_meter_readings_count": ["invalid_meter_readings_count"],
}

@dataclass(frozen=True)
class SensorTag:
    key: str
    data_type: str
    divide_by_1000: bool = False
    aliases: list[str] | None = None


@dataclass(frozen=True)
class ExtSensorEntityDescription(SensorEntityDescription):
    tag: SensorTag | None = None

    @classmethod
    def from_tag(cls, tag: SensorTag, **kwargs):
        return cls(key=f"{tag.key}_in_k" if tag.divide_by_1000 else tag.key, tag=tag, **kwargs)
    

SENSOR_TYPES = [

    # Zählerstand Total
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010800ff", data_type=DATA_KEY),
        name="Import total",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Zählerstand Tarif 1
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010801ff", data_type=DATA_KEY),
        name="Import tariff 1",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Zählerstand Tarif 2
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010802ff", data_type=DATA_KEY),
        name="Import tariff 2",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Zählerstand Tarif 3
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010803ff", data_type=DATA_KEY),
        name="Import tariff 3",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Zählerstand Tarif 4
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010804ff", data_type=DATA_KEY),
        name="Import tariff 4",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Wirkenergie Total
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020800ff", data_type=DATA_KEY),
        name="Export total",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020801ff", data_type=DATA_KEY),
        name="Export tariff 1",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020802ff", data_type=DATA_KEY),
        name="Export tariff 2",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020803ff", data_type=DATA_KEY),
        name="Export tariff 3",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020804ff", data_type=DATA_KEY),
        name="Export tariff 4",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010800ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Import total (kWh)",
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010801ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Import tariff 1 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010802ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Import tariff 2 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010803ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Import tariff 3 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100010804ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Import tariff 4 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-import-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020800ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Export total (kWh)",
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020801ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Export tariff 1 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020802ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Export tariff 2 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020803ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Export tariff 3 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100020804ff", data_type=DATA_KEY, divide_by_1000=True),
        name="Export tariff 4 (kWh)",
        entity_registry_enabled_default=False,
        suggested_display_precision=5,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-export-outline",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # aktuelle Wirkleistung
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(
            key="0100100700ff",
            data_type=DATA_KEY,
            aliases=OBIS_KEY_ALIASES.get("0100100700ff"),
        ),
        name="Power (actual)",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Wirkleistung L1
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(
            key="0100240700ff",
            data_type=DATA_KEY,
            aliases=OBIS_KEY_ALIASES.get("0100240700ff"),
        ),
        name="Power L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Wirkleistung L2
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(
            key="0100380700ff",
            data_type=DATA_KEY,
            aliases=OBIS_KEY_ALIASES.get("0100380700ff"),
        ),
        name="Power L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Wirkleistung L3
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(
            key="01004c0700ff",
            data_type=DATA_KEY,
            aliases=OBIS_KEY_ALIASES.get("01004c0700ff"),
        ),
        name="Power L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Spannung L1
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100200700ff", data_type=DATA_KEY),
        name="Potential L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:lightning-bolt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Spannung L2
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100340700ff", data_type=DATA_KEY),
        name="Potential L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:lightning-bolt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Spannung L3
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100480700ff", data_type=DATA_KEY),
        name="Potential L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:lightning-bolt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Strom L1
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="01001f0700ff", data_type=DATA_KEY),
        name="Current L1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Strom L2
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100330700ff", data_type=DATA_KEY),
        name="Current L2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Strom L3
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100470700ff", data_type=DATA_KEY),
        name="Current L3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Netz Frequenz
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="01000e0700ff", data_type=DATA_KEY),
        name="Net frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Phasenabweichung Spannungen L1/L2
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100510701ff", data_type=DATA_KEY),
        name="Potential Phase deviation L1/L2",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Phasenabweichung Spannungen L1/L3
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100510702ff", data_type=DATA_KEY),
        name="Potential Phase deviation L1/L3",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Phasenabweichung Strom/Spannung L1
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="0100510704ff", data_type=DATA_KEY),
        name="Current/Potential L1 Phase deviation",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Phasenabweichung Strom/Spannung L2
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="010051070fff", data_type=DATA_KEY),
        name="Current/Potential L2 Phase deviation",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Phasenabweichung Strom/Spannung L3
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="010051071aff", data_type=DATA_KEY),
        name="Current/Potential L3 Phase deviation",
        suggested_display_precision=1,
        native_unit_of_measurement=DEGREE,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),


    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_battery_voltage", data_type=METRICS_KEY),
        name="node_battery_voltage",
        suggested_display_precision=3,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        icon="mdi:battery",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_temperature", data_type=METRICS_KEY),
        name="node_temperature",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_avg_rssi", data_type=METRICS_KEY),
        name="node_avg_rssi",
        suggested_display_precision=3,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        icon="mdi:wifi-strength-4",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_avg_lqi", data_type=METRICS_KEY),
        name="node_avg_lqi",
        suggested_display_precision=3,
        icon="mdi:signal-variant",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_radio_tx_power", data_type=METRICS_KEY),
        name="node_radio_tx_power",
        suggested_display_precision=3,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        icon="mdi:lightning-bolt-circle",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_uptime_ms", data_type=METRICS_KEY),
        name="node_uptime_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_meter_msg_count_sent", data_type=METRICS_KEY),
        name="node_meter_msg_count_sent",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_meter_pkg_count_sent", data_type=METRICS_KEY),
        name="node_meter_pkg_count_sent",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_time_in_em0_ms", data_type=METRICS_KEY),
        name="node_time_in_em0_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_time_in_em1_ms", data_type=METRICS_KEY),
        name="node_time_in_em1_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_time_in_em2_ms", data_type=METRICS_KEY),
        name="node_time_in_em2_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_acmp_rx_autolevel_9600", data_type=METRICS_KEY),
        name="node_acmp_rx_autolevel_9600",
        suggested_display_precision=3,
        icon="mdi:sine-wave",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="node_invalid_meter_readings_count", data_type=METRICS_KEY),
        name="node_invalid_meter_readings_count",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="meter_pkg_count_recv", data_type=METRICS_KEY),
        name="hub_meter_pkg_count_recv",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="meter_reading_count_recv", data_type=METRICS_KEY),
        name="hub_meter_reading_count_recv",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="meter_corrupt_reading_count_recv", data_type=METRICS_KEY),
        name="hub_meter_corrupt_reading_count_recv",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
    ExtSensorEntityDescription.from_tag(
        tag=SensorTag(key="compression_error_readings_count", data_type=METRICS_KEY),
        name="hub_compression_error_readings_count",
        suggested_display_precision=0,
        icon="mdi:counter",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
]
