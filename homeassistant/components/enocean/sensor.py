"""Support for EnOcean sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from enocean.utils import combine_hex
from enocean4ha_bridge import EnOceanDongle, EO4HASensor
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_ID,
    CONF_NAME,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_EEP, DATA_ENOCEAN, ENOCEAN_DONGLE
from .device import EnOceanEntity

CONF_MAX_TEMP = "max_temp"
CONF_MIN_TEMP = "min_temp"
CONF_RANGE_FROM = "range_from"
CONF_RANGE_TO = "range_to"

DEFAULT_NAME = "EnOcean sensor"

SENSOR_TYPE_HUMIDITY = "humidity"
SENSOR_TYPE_ILLUMINANCE = "illuminance"
SENSOR_TYPE_OCCUPANCY = "occupancy"
SENSOR_TYPE_POWER = "powersensor"
SENSOR_TYPE_TEMPERATURE = "temperature"
SENSOR_TYPE_WINDOWHANDLE = "windowhandle"

PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS, default=SENSOR_TYPE_POWER): cv.string,
        vol.Optional(CONF_MAX_TEMP, default=40): vol.Coerce(int),
        vol.Optional(CONF_MIN_TEMP, default=0): vol.Coerce(int),
        vol.Optional(CONF_RANGE_FROM, default=255): cv.positive_int,
        vol.Optional(CONF_RANGE_TO, default=0): cv.positive_int,
        vol.Optional(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
    }
)

@dataclass(frozen=True, kw_only=True)
class EnOceanSensorEntityDescription(SensorEntityDescription):
    """Describes EnOcean sensor entity."""

    unique_id: Callable[[list[int]], str | None]


SENSOR_DESC_TEMPERATURE = EnOceanSensorEntityDescription(
    key=SENSOR_TYPE_TEMPERATURE,
    name="Temperature",
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    suggested_display_precision=2,
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
    unique_id=lambda dev_id: f"{combine_hex(dev_id)}-{SENSOR_TYPE_TEMPERATURE}",
)

SENSOR_DESC_HUMIDITY = EnOceanSensorEntityDescription(
    key=SENSOR_TYPE_HUMIDITY,
    name="Humidity",
    native_unit_of_measurement=PERCENTAGE,
    suggested_display_precision=2,
    device_class=SensorDeviceClass.HUMIDITY,
    state_class=SensorStateClass.MEASUREMENT,
    unique_id=lambda dev_id: f"{combine_hex(dev_id)}-{SENSOR_TYPE_HUMIDITY}",
)

SENSOR_DESC_ILLUMINANCE = EnOceanSensorEntityDescription(
    key=SENSOR_TYPE_ILLUMINANCE,
    name="Illuminance",
    native_unit_of_measurement=LIGHT_LUX,
    suggested_display_precision=2,
    device_class=SensorDeviceClass.ILLUMINANCE,
    state_class=SensorStateClass.MEASUREMENT,
    unique_id=lambda dev_id: f"{combine_hex(dev_id)}-{SENSOR_TYPE_ILLUMINANCE}",
)

SENSOR_DESC_OCCUPANCY = EnOceanSensorEntityDescription(
    key=SENSOR_TYPE_OCCUPANCY,
    name="Occupancy",
    unique_id=lambda dev_id: f"{combine_hex(dev_id)}-{SENSOR_TYPE_OCCUPANCY}",
)

SENSOR_DESC_POWER = EnOceanSensorEntityDescription(
    key=SENSOR_TYPE_POWER,
    name="Power",
    native_unit_of_measurement=UnitOfPower.WATT,
    suggested_display_precision=2,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    unique_id=lambda dev_id: f"{combine_hex(dev_id)}-{SENSOR_TYPE_POWER}",
)

SENSOR_DESC_WINDOWHANDLE = EnOceanSensorEntityDescription(
    key=SENSOR_TYPE_WINDOWHANDLE,
    name="WindowHandle",
    translation_key="window_handle",
    unique_id=lambda dev_id: f"{combine_hex(dev_id)}-{SENSOR_TYPE_WINDOWHANDLE}",
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up an EnOcean sensor device."""
    dev_id: list[int] = config[CONF_ID]
    dev_name: str = config[CONF_NAME]
    sensor_type: str = config[CONF_DEVICE_CLASS]

    entities: list[EnOceanSensor] = []
    if sensor_type == SENSOR_TYPE_TEMPERATURE:
        temp_min: int = config[CONF_MIN_TEMP]
        temp_max: int = config[CONF_MAX_TEMP]
        range_from: int = config[CONF_RANGE_FROM]
        range_to: int = config[CONF_RANGE_TO]
        entities = [
            EnOceanTemperatureSensor(
                dev_id,
                dev_name,
                SENSOR_DESC_TEMPERATURE,
                scale_min=temp_min,
                scale_max=temp_max,
                range_from=range_from,
                range_to=range_to,
            )
        ]

    elif sensor_type == SENSOR_TYPE_HUMIDITY:
        entities = [EnOceanHumiditySensor(dev_id, dev_name, SENSOR_DESC_HUMIDITY)]

    elif sensor_type == SENSOR_TYPE_ILLUMINANCE:
        entities = [EnOceanIlluminanceSensor(dev_id, dev_name, SENSOR_DESC_ILLUMINANCE)]

    elif sensor_type == SENSOR_TYPE_OCCUPANCY:
        entities = [EnOceanOccupancySensor(dev_id, dev_name, SENSOR_DESC_OCCUPANCY)]

    elif sensor_type == SENSOR_TYPE_POWER:
        entities = [EnOceanPowerSensor(dev_id, dev_name, SENSOR_DESC_POWER)]

    elif sensor_type == SENSOR_TYPE_WINDOWHANDLE:
        entities = [EnOceanWindowHandle(dev_id, dev_name, SENSOR_DESC_WINDOWHANDLE)]

    async_add_entities(entities)


class EnOceanSensor(EnOceanEntity, RestoreSensor):
    """Representation of an EnOcean sensor device such as a power meter."""

    def __init__(
        self,
        dev_id: list[int],
        dev_name: str,
        description: EnOceanSensorEntityDescription,
    ) -> None:
        """Initialize the EnOcean sensor device."""
        super().__init__(dev_id)
        self.entity_description = description
        self._attr_name = f"{description.name} {dev_name}"
        self._attr_unique_id = description.unique_id(dev_id)
        self.eo_sensor = None

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        dongle: EnOceanDongle = self.hass.data[DATA_ENOCEAN][ENOCEAN_DONGLE]
        self.eo_sensor = EO4HASensor(controller=dongle, dev_id=self.dev_id)
        # If not None, we got an initial value.
        await super().async_added_to_hass()
        if self._attr_native_value is not None:
            return

        if (sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = sensor_data.native_value

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        raise NotImplemented


class EnOceanIlluminanceSensor(EnOceanSensor):
    """Representation of an EnOcean illumination sensor."""

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_illuminance_sensor(packet)
        except ValueError:
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()


class EnOceanOccupancySensor(EnOceanSensor):
    """Representation of an EnOcean occupancy sensor."""

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_occupancy_sensor(packet)
        except ValueError:
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()


class EnOceanPowerSensor(EnOceanSensor):
    """Representation of an EnOcean power sensor."""

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_power_sensor(packet)
        except (ValueError, LookupError):
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()


class EnOceanTemperatureSensor(EnOceanSensor):
    """Representation of an EnOcean temperature sensor device."""

    def __init__(
        self,
        dev_id: list[int],
        dev_name: str,
        description: EnOceanSensorEntityDescription,
        *,
        scale_min: int,
        scale_max: int,
        range_from: int,
        range_to: int,
    ) -> None:
        """Initialize the EnOcean temperature sensor device."""
        super().__init__(dev_id, dev_name, description)
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.range_from = range_from
        self.range_to = range_to

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.eo_sensor.scale_min = self.scale_min
        self.eo_sensor.scale_max = self.scale_max
        self.eo_sensor.range_from = self.range_from
        self.eo_sensor.range_to = self.range_to


    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_temperature_sensor(packet)
        except (ValueError, LookupError):
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()


class EnOceanHumiditySensor(EnOceanSensor):
    """Representation of an EnOcean humidity sensor device."""

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_humidity_sensor(packet)
        except (ValueError, LookupError):
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()


class EnOceanWindowHandle(EnOceanSensor):
    """Representation of an EnOcean window handle device."""

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_window_handle_sensor(packet)
        except LookupError:
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()
