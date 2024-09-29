"""Support for EnOcean sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from enocean.utils import combine_hex
from enocean4ha_bridge import EnOceanGateway, EO4HASensor, EO4HAHumiditySensor, EO4HAIlluminanceSensor, EO4HAOccupancySensor, EO4HAPowerSensor, EO4HATemperatureSensor, EO4HAWindowHandleSensor
import voluptuous as vol
from homeassistant.helpers import device_registry as dr

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

from .const import CONF_EEP, DATA_ENOCEAN, ENOCEAN_DONGLE, LOGGER, SENSOR_TYPES, SENSOR_TYPE_HUMIDITY, \
    SENSOR_TYPE_TEMPERATURE, SENSOR_TYPE_OCCUPANCY, SENSOR_TYPE_ILLUMINANCE, SENSOR_TYPE_WINDOWHANDLE, \
    SENSOR_TYPE_POWER, DOMAIN
from .enocean_entity import EnOceanEntity
from enocean.utils import to_hex_string
from . import EnOceanConfigEntry
from ...helpers.device_registry import DeviceInfo

CONF_MAX_TEMP = "max_temp"
CONF_MIN_TEMP = "min_temp"
CONF_RANGE_FROM = "range_from"
CONF_RANGE_TO = "range_to"

DEFAULT_NAME = "EnOcean sensor"

# SENSOR_TYPE_HUMIDITY = "humidity"
# SENSOR_TYPE_ILLUMINANCE = "illuminance"
# SENSOR_TYPE_OCCUPANCY = "occupancy"
# SENSOR_TYPE_POWER = "powersensor"
# SENSOR_TYPE_TEMPERATURE = "temperature"
# SENSOR_TYPE_WINDOWHANDLE = "windowhandle"



PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS, default=SENSOR_TYPE_POWER): cv.string,
    }
)

@dataclass(frozen=True, kw_only=True)
class EnOceanSensorEntityDescription(SensorEntityDescription):
    """Describes EnOcean sensor entity."""

    unique_id: Callable[[list[int]], str | None]


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

SENSOR_DESC_TEMPERATURE = EnOceanSensorEntityDescription(
    key=SENSOR_TYPE_TEMPERATURE,
    name="Temperature",
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    suggested_display_precision=2,
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
    unique_id=lambda dev_id: f"{combine_hex(dev_id)}-{SENSOR_TYPE_TEMPERATURE}",
)

SENSOR_DESC_WINDOWHANDLE = EnOceanSensorEntityDescription(
    key=SENSOR_TYPE_WINDOWHANDLE,
    name="WindowHandle",
    translation_key="window_handle",
    unique_id=lambda dev_id: f"{combine_hex(dev_id)}-{SENSOR_TYPE_WINDOWHANDLE}",
)

SENSORS: tuple[EnOceanSensorEntityDescription, ...] = [
    SENSOR_DESC_HUMIDITY,
    SENSOR_DESC_ILLUMINANCE,
    SENSOR_DESC_OCCUPANCY,
    SENSOR_DESC_POWER,
    SENSOR_DESC_TEMPERATURE,
    SENSOR_DESC_WINDOWHANDLE
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLED sensor based on a config entry."""
    LOGGER.info(f"sensor.async_setup_entry: {config_entry}")
    # coordinator = entry.runtime_data

    sensors = {
        SENSOR_TYPE_HUMIDITY: (EnOceanHumiditySensor, SENSOR_DESC_HUMIDITY),
        SENSOR_TYPE_ILLUMINANCE: (EnOceanIlluminanceSensor, SENSOR_DESC_ILLUMINANCE),
        SENSOR_TYPE_OCCUPANCY: (EnOceanOccupancySensor, SENSOR_DESC_OCCUPANCY),
        SENSOR_TYPE_POWER: (EnOceanPowerSensor, SENSOR_DESC_POWER),
        SENSOR_TYPE_TEMPERATURE: (EnOceanTemperatureSensor, SENSOR_DESC_TEMPERATURE),
        SENSOR_TYPE_WINDOWHANDLE: (EnOceanWindowHandle, SENSOR_DESC_WINDOWHANDLE),
    }

    if 'device_type' in config_entry.data:
        if config_entry.data['device_type'] in sensors:
            sensor = sensors[config_entry.data['device_type']][0]
            sensor_description = sensors[config_entry.data['device_type']][1]
            async_add_entities([sensor(config_entry, sensor_description)])


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up an EnOcean sensor device."""
    dev_id: list[int] = config[CONF_ID]
    dev_name: str = config[CONF_NAME]
    eep: list[int] = config[CONF_EEP]
    sensor_type: str = config[CONF_DEVICE_CLASS]

    entities: list[EnOceanSensor] = []
    if sensor_type == SENSOR_TYPE_HUMIDITY:
        entities = [EnOceanHumiditySensor(dev_id, eep, dev_name, SENSOR_DESC_HUMIDITY)]

    elif sensor_type == SENSOR_TYPE_ILLUMINANCE:
        entities = [EnOceanIlluminanceSensor(dev_id, eep, dev_name, SENSOR_DESC_ILLUMINANCE)]

    elif sensor_type == SENSOR_TYPE_OCCUPANCY:
        entities = [EnOceanOccupancySensor(dev_id, eep, dev_name, SENSOR_DESC_OCCUPANCY)]

    elif sensor_type == SENSOR_TYPE_POWER:
        entities = [EnOceanPowerSensor(dev_id, eep, dev_name, SENSOR_DESC_POWER)]

    elif sensor_type == SENSOR_TYPE_TEMPERATURE:
        entities = [EnOceanTemperatureSensor(dev_id, eep, dev_name, SENSOR_DESC_TEMPERATURE)]

    elif sensor_type == SENSOR_TYPE_WINDOWHANDLE:
        entities = [EnOceanWindowHandle(dev_id, eep, dev_name, SENSOR_DESC_WINDOWHANDLE)]

    async_add_entities(entities)


class EnOceanSensor(EnOceanEntity, RestoreSensor):
    """Representation of an EnOcean sensor device such as a power meter."""

    def __init__(
        self,
        config_entry: EnOceanConfigEntry,
        description: EnOceanSensorEntityDescription,
    ) -> None:
        """Initialize the EnOcean sensor device."""
        super().__init__(config_entry.data[CONF_ID], config_entry.options[CONF_EEP])
        dev_id_str = to_hex_string(config_entry.data[CONF_ID])
        self.entity_description = description
        self._attr_name = f"{description.name} {config_entry.title}"
        self._attr_unique_id = description.unique_id(config_entry.data[CONF_ID])
        self.eo_sensor = None
        # gateway: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        self._attr_device_info = DeviceInfo(
            # name="start/stop teach in",
            identifiers={(DOMAIN, dev_id_str)},
            model_id=f"Device ID: {dev_id_str}",
            # via_device=(DOMAIN, gateway.sender_id_str)
        )
    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await self.add_eo4ha_bridge()
        await super().async_added_to_hass()
        await self.bridge_added_to_sensor()

        # If not None, we got an initial value.
        if self._attr_native_value is not None:
            return
        if (sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = sensor_data.native_value

    async def add_eo4ha_bridge(self):
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("sensor: no gateway configured")
            return
        self.eo_sensor = EO4HASensor(
            gateway=dongle,
            dev_id=self.dev_id,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )

    async def bridge_added_to_sensor(self):
        if hasattr(self.eo_sensor, 'range_min'):
            if self.eo_sensor.range_min:
                extra_attributes: dict[str, Any] = self.extra_state_attributes
                if extra_attributes:
                    extra_attributes.update({
                        'range_min': self.eo_sensor.range_min,
                        'range_max': self.eo_sensor.range_max,
                        'scale_min': self.eo_sensor.scale_min,
                        'scale_max': self.eo_sensor.scale_max
                    })
                else:
                    extra_attributes = {
                        'range_min': self.eo_sensor.range_min,
                        'range_max': self.eo_sensor.range_max,
                        'scale_min': self.eo_sensor.scale_min,
                        'scale_max': self.eo_sensor.scale_max
                    }
                self._attr_extra_state_attributes = extra_attributes

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        raise NotImplemented


class EnOceanHumiditySensor(EnOceanSensor):
    """Representation of an EnOcean humidity sensor device."""

    async def add_eo4ha_bridge(self) -> None:
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("humidity_sensor: no gateway configured")
            return
        self.eo_sensor = EO4HAHumiditySensor(
            gateway=dongle,
            dev_id=self.dev_id,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_humidity_sensor(packet)
        except (ValueError, LookupError):
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()


class EnOceanIlluminanceSensor(EnOceanSensor):
    """Representation of an EnOcean illumination sensor."""

    async def add_eo4ha_bridge(self) -> None:
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("illuminance_sensor: no gateway configured")
            return
        self.eo_sensor = EO4HAIlluminanceSensor(
            gateway=dongle,
            dev_id=self.dev_id,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )

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

    async def add_eo4ha_bridge(self) -> None:
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("occupancy_sensor: no gateway configured")
            return
        self.eo_sensor = EO4HAOccupancySensor(
            gateway=dongle,
            dev_id=self.dev_id,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        # try:
        value, new_extra_attr = self.eo_sensor.parse_occupancy_sensor(packet)
        # except ValueError:
        #     return
        if value != self._attr_native_value:
            self._attr_native_value = value
            extra_attributes: dict[str, Any] = self.extra_state_attributes
            if extra_attributes:
                extra_attributes.update(new_extra_attr)
            else:
                extra_attributes = new_extra_attr
            self._attr_extra_state_attributes = extra_attributes
            self.schedule_update_ha_state()


class EnOceanPowerSensor(EnOceanSensor):
    """Representation of an EnOcean power sensor."""

    async def add_eo4ha_bridge(self) -> None:
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("power_sensor: no gateway configured")
            return
        self.eo_sensor = EO4HAPowerSensor(
            gateway=dongle,
            dev_id=self.dev_id,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )

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

    async def add_eo4ha_bridge(self) -> None:
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("temperature_sensor: no gateway configured")
            return
        self.eo_sensor = EO4HATemperatureSensor(
            gateway=dongle,
            dev_id=self.dev_id,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_temperature_sensor(packet)
        except (ValueError, LookupError):
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()


class EnOceanWindowHandle(EnOceanSensor):
    """Representation of an EnOcean window handle device."""

    async def add_eo4ha_bridge(self) -> None:
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("window_handle_sensor: no gateway configured")
            return
        self.eo_sensor = EO4HAWindowHandleSensor(
            gateway=dongle,
            dev_id=self.dev_id,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )

    def value_changed(self, packet):
        """Update the internal state of the sensor."""
        try:
            value = self.eo_sensor.parse_window_handle_sensor(packet)
        except LookupError:
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()
