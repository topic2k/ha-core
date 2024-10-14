""" Support for EnOcean sensors. """

from dataclasses import dataclass

import voluptuous as vol

from enocean import __version__ as enocean_version
from enocean.protocol.eep import EEPSoup
from enocean.utils import to_hex_string
from enocean4ha_bridge import (
    __version__ as enocean4ha_bridge_version,
    EnOceanGateway,
    EO4HAHumiditySensor,
    EO4HAIlluminanceSensor,
    EO4HAPowerSensor,
    EO4HASensor,
    EO4HAShortcutSensor,
    EO4HATemperatureSensor,
    EO4HAWindowHandleSensor,
)

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_ENTITIES,
    CONF_ENTITY_CATEGORY,
    CONF_ID,
    CONF_NAME,
    CONF_URL,
    EntityCategory,
    LIGHT_LUX,
    MATCH_ALL, PERCENTAGE,
    Platform,
    UnitOfPower,
    UnitOfTemperature
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.config_validation import ensure_list, string
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import EnOceanConfigEntry
from .const import (
    CONF_CMD_OR_DIR, CONF_EEP,
    CONF_GATEWAY,
    CONF_PROFILE_SHORTCUT,
    DEVICE_CLASS_PROFILE_SHORTCUT,
    DEVICE_CLASS_WINDOWHANDLE,
    DOMAIN,
    SENSOR_TYPE_HUMIDITY,
    SENSOR_TYPE_ILLUMINANCE,
    SENSOR_TYPE_POWER,
    SENSOR_TYPE_TEMPERATURE,
    SENSOR_TYPE_WINDOWHANDLE
)
from .enocean_entity import EnOceanEntity

DEFAULT_NAME = "EnOcean sensor"


PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): string,
        vol.Optional(CONF_DEVICE_CLASS, default=SENSOR_TYPE_POWER): string,
    }
)

@dataclass(frozen=True, kw_only=True)
class EnOceanSensorEntityDescription(SensorEntityDescription):
    """ Describes EnOcean sensor entity. """
    unique_id: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """ Set up sensor based on a config entry. """
    if CONF_GATEWAY in config_entry.data:
        description_eo = EnOceanSensorEntityDescription(
            device_class=None,
            entity_category=EntityCategory(EntityCategory.DIAGNOSTIC),
            key=f"{config_entry.unique_id}-lib-enocean-version",
            name=f"{config_entry.title} enocean lib version",
            unique_id=f"{config_entry.unique_id}-lib-enocean-version",
        )
        description_eo4ha = EnOceanSensorEntityDescription(
            device_class=None,
            entity_category=EntityCategory(EntityCategory.DIAGNOSTIC),
            key=f"{config_entry.unique_id}-lib-enocean4ha_bridge-version",
            name=f"{config_entry.title} enocean4ha_bridge lib version",
            unique_id=f"{config_entry.unique_id}-lib-enocean4ha_bridge-version",
        )
        entities = [
            EnOceanDiagnoseEnOceanVersion(config_entry, description_eo),
            EnOceanDiagnoseEnOcean4haBridgeVersion(config_entry, description_eo4ha)
        ]
        async_add_entities(entities)
        return

    if not config_entry.data[CONF_ENTITIES].get(Platform.SENSOR):
        return

    entities = []
    dev_id_str = to_hex_string(config_entry.data[CONF_ID])
    entity_config = dict(config_entry.data)
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, dev_id_str)},
        name=config_entry.title,
        model=f"Base ID: {dev_id_str}",
        model_id=f"EEP: {to_hex_string(entity_config[CONF_EEP], sep='-')}",
    )

    for entity_options in entity_config[CONF_ENTITIES][Platform.SENSOR]:
        match entity_options[CONF_DEVICE_CLASS]:
            case SensorDeviceClass.HUMIDITY:
                description = EnOceanSensorEntityDescription(
                    device_class=SensorDeviceClass.HUMIDITY,
                    key=f"{dev_id_str}-{SENSOR_TYPE_HUMIDITY}",
                    name=f"{entity_config[CONF_NAME]} Humidity",
                    native_unit_of_measurement=PERCENTAGE,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=2,
                    unique_id=f"{dev_id_str}-{SENSOR_TYPE_HUMIDITY}",
                )
                entities.append(EnOceanHumiditySensor(entity_config, description))
            case SensorDeviceClass.ILLUMINANCE:
                description = EnOceanSensorEntityDescription(
                    device_class=SensorDeviceClass.ILLUMINANCE,
                    key=SensorDeviceClass.ILLUMINANCE,
                    name=f"{entity_config[CONF_NAME]} Illuminance",
                    native_unit_of_measurement=LIGHT_LUX,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=2,
                    unique_id=f"{dev_id_str}-{SENSOR_TYPE_ILLUMINANCE}",
                )
                entities.append(EnOceanIlluminanceSensor(entity_config, description))
            case SensorDeviceClass.POWER:
                description = EnOceanSensorEntityDescription(
                    device_class=SensorDeviceClass.POWER,
                    key=f"{dev_id_str}-{SENSOR_TYPE_POWER}",
                    name=f"{entity_config[CONF_NAME]} Power",
                    native_unit_of_measurement=UnitOfPower.WATT,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=2,
                    unique_id=f"{dev_id_str}-{SENSOR_TYPE_POWER}",
                )
                entities.append(EnOceanPowerSensor(entity_config, description))
            case SensorDeviceClass.TEMPERATURE:
                description = EnOceanSensorEntityDescription(
                    device_class=SensorDeviceClass.TEMPERATURE,
                    key=f"{dev_id_str}-{SENSOR_TYPE_TEMPERATURE}",
                    name=f"{entity_config[CONF_NAME]} Temperature",
                    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=1,
                    unique_id=f"{dev_id_str}-{SENSOR_TYPE_TEMPERATURE}",
                )
                entities.append(EnOceanTemperatureSensor(entity_config, description))
            case dev_cls if dev_cls == DEVICE_CLASS_WINDOWHANDLE:
                description = EnOceanSensorEntityDescription(
                    device_class=DEVICE_CLASS_WINDOWHANDLE,
                    key=f"{dev_id_str}-{SENSOR_TYPE_WINDOWHANDLE}",
                    name="WindowHandle",
                    translation_key="window_handle",
                    unique_id=f"{dev_id_str}-{SENSOR_TYPE_WINDOWHANDLE}",
                )
                entities.append(EnOceanWindowHandleSensor(entity_config, description))
            case dev_cls if dev_cls == DEVICE_CLASS_PROFILE_SHORTCUT:
                profile = EEPSoup.find_profile(*entity_config[CONF_EEP], **entity_options[CONF_CMD_OR_DIR])
                name = profile.findChild(shortcut=entity_options[CONF_PROFILE_SHORTCUT])["description"]
                category = entity_options.get(CONF_ENTITY_CATEGORY)
                description = EnOceanSensorEntityDescription(
                    device_class=DEVICE_CLASS_PROFILE_SHORTCUT,
                    entity_category=EntityCategory(category) if category else None,
                    key=f"{dev_id_str}-profile_shortcut-{entity_options[CONF_PROFILE_SHORTCUT]}",
                    name=f"{entity_config[CONF_NAME]} {name}",
                    unique_id=f"{dev_id_str}-profile_shortcut-{entity_options[CONF_PROFILE_SHORTCUT]}",
                )
                entities.append(EnOceanShortcutSensor(entity_config, description, entity_options))

    async_add_entities(entities)


async def async_setup_platform(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """ Set up an EnOcean sensor device. """
    dev_id: list[int] = config_entry[CONF_ID]
    dev_name: str = config_entry[CONF_NAME]
    eep: list[int] = config_entry[CONF_EEP]
    sensor_type: str = config_entry[CONF_DEVICE_CLASS]
    dev_id_str = to_hex_string(dev_id)

    entities: list[EnOceanSensor] = []
    if sensor_type == SENSOR_TYPE_HUMIDITY:
        entities = [EnOceanHumiditySensor(config_entry, SENSOR_DESC_HUMIDITY)]

    elif sensor_type == SENSOR_TYPE_ILLUMINANCE:
        entities = [EnOceanIlluminanceSensor(config_entry, SENSOR_DESC_ILLUMINANCE)]

    elif sensor_type == SENSOR_TYPE_POWER:
        entities = [EnOceanPowerSensor(config_entry, SENSOR_DESC_POWER)]

    elif sensor_type == SENSOR_TYPE_TEMPERATURE:
        entities = [EnOceanTemperatureSensor(config_entry, SENSOR_DESC_TEMPERATURE)]

    elif sensor_type == SENSOR_TYPE_WINDOWHANDLE:
        entities = [EnOceanWindowHandleSensor(config_entry, SENSOR_DESC_WINDOWHANDLE)]

    async_add_entities(entities)


class EnOceanSensor(EO4HASensor, EnOceanEntity, RestoreSensor):
    """ Representation of an EnOcean sensor device such as a power meter. """

    def __init__(
            self,
            entity_config: dict,
            description: EnOceanSensorEntityDescription,
    ) -> None:
        """ Initialize the EnOcean sensor device. """
        super().__init__(entity_config[CONF_ID], entity_config[CONF_EEP])
        dev_id_str = to_hex_string(self.dev_id)
        self._attr_unique_id = description.unique_id
        # self._attr_device_class = description.device_class
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_id_str)})
        # self._attr_name = f"{entity_config[CONF_NAME]} {description.name}"
        # self._attr_state_class = description.state_class
        self.entity_description = description
        self.gateway: EnOceanGateway|None = None
        self._logger.debug(f"Initialized {type(self).__name__}, ID {dev_id_str}, {repr(self.eep)}")

    async def async_added_to_hass(self) -> None:
        """ Call when entity about to be added to hass. """
        await super().async_added_to_hass()
        # If not None, we got an initial value.
        if self._attr_native_value is not None:
            return
        if (sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = sensor_data.native_value

    def value_changed(self, packet):
        """ Update the internal state of the sensor. """
        result: dict|None = self.parse_packet(packet)
        if not result:
            return
        if "status" in result:
            if result["status"] != self._attr_native_value:
                self._attr_native_value = result["status"]
                self._attr_extra_state_attributes = result.get('extra_state_attr', {})
                self.schedule_update_ha_state()


class EnOceanHumiditySensor(EO4HAHumiditySensor, EnOceanSensor):
    """ Representation of an EnOcean humidity sensor device. """


class EnOceanIlluminanceSensor(EO4HAIlluminanceSensor, EnOceanSensor):
    """ Representation of an EnOcean illumination sensor device. """


class EnOceanPowerSensor(EO4HAPowerSensor, EnOceanSensor):
    """ Representation of an EnOcean power sensor device. """

    def value_changed(self, packet):
        """ Update the internal state of the sensor. """
        try:
            value = self.parse_packet(packet)
        except (ValueError, LookupError):
            return
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.schedule_update_ha_state()


class EnOceanTemperatureSensor(EO4HATemperatureSensor, EnOceanSensor):
    """ Representation of an EnOcean temperature sensor device. """

    def __init__(self, entity_config: dict, description: EnOceanSensorEntityDescription) -> None:
        super().__init__(entity_config, description)
        if self.eep in ([0xA5, 0x04, 0x1], [0xA5, 0x04, 0x2], [0xA5, 0x10, 0x1F]):
            self._attr_entity_registry_enabled_default = False


class EnOceanWindowHandleSensor(EO4HAWindowHandleSensor, EnOceanSensor):
    """ Representation of an EnOcean window handle device. """


class EnOceanShortcutSensor(EO4HAShortcutSensor, EnOceanSensor):
    """ Representation of an EnOcean device for specific EEP shortcut data. """

    def __init__(self, entity_config: dict, description: EnOceanSensorEntityDescription, options: dict) -> None:
        super().__init__(entity_config, description)
        self.shortcut = options[CONF_PROFILE_SHORTCUT]


class EnOceanDiagnoseEntity(Entity):
    def __init__(
        self,
        config_entry: EnOceanConfigEntry,
        description: EnOceanSensorEntityDescription,
    ) -> None:
        """ Initialize the diagnose sensor. """
        super().__init__()
        gateway: EnOceanGateway = config_entry.runtime_data
        self.entity_description = description
        self._attr_unique_id = description.unique_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, gateway.sender_id_str)})
        self._unrecorded_attributes: frozenset[str] = MATCH_ALL


class EnOceanDiagnoseEnOceanVersion(EnOceanDiagnoseEntity):
    """ Show the version of the enocean python package. """

    # _attr_name = "enocean package version"
    _attr_state = enocean_version
    _attr_extra_state_attributes = {
        CONF_URL: r"https://github.com/topic2k/enocean4ha"
    }


class EnOceanDiagnoseEnOcean4haBridgeVersion(EnOceanDiagnoseEntity):
    """ Show the version of the enocean4ha_bridge python package. """

    # _attr_name = "enocean4ha_bridge package version"
    _attr_state = enocean4ha_bridge_version
    _attr_extra_state_attributes = {
        CONF_URL: r"https://github.com/topic2k/enocean4ha_bridge"
    }
