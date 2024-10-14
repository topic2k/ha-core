""" Support for EnOcean binary sensors. """

from dataclasses import dataclass

import voluptuous as vol

from enocean.utils import to_hex_string
from enocean4ha_bridge import EO4HABinarySensor

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA as BINARY_SENSOR_PLATFORM_SCHEMA
)
from homeassistant.const import CONF_DEVICE_CLASS, CONF_ENABLED, CONF_ENTITIES, CONF_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import EnOceanConfigEntry
from .const import (
    CONF_BUTTON,
    CONF_CHANNEL,
    CONF_CHANNEL_COUNT,
    CONF_EEP,
    CONF_GATEWAY,
    CONF_PROFILE_SHORTCUT,
    DOMAIN
)
from .enocean_entity import EnOceanEntity

DEFAULT_NAME = "EnOcean binary sensor"
DEPENDENCIES = ["enocean"]
EVENT_BUTTON_PRESSED = "button_pressed"

PLATFORM_SCHEMA = BINARY_SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Required(CONF_BUTTON): vol.In([None, "AO", "AI", "BO", "BI"])
    }
)


@dataclass(frozen=True, kw_only=True)
class EnOceanBinarySensorEntityDescription(BinarySensorEntityDescription):
    """ Describes EnOcean sensor entity. """
    unique_id: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """ Add binary sensors for passed config_entry in HA. """

    if CONF_GATEWAY in config_entry.data:
        return

    if not config_entry.data[CONF_ENTITIES].get(Platform.BINARY_SENSOR):
        return

    entities = []
    entity_config = dict(config_entry.data)
    dev_id_str = to_hex_string(entity_config[CONF_ID])

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, dev_id_str)},
        name=config_entry.title,
        model=f"Base ID: {dev_id_str}",
        model_id=f"EEP: {to_hex_string(entity_config[CONF_EEP], sep='-')}",
    )
    for entity_options in entity_config[CONF_ENTITIES][Platform.BINARY_SENSOR]:
        if CONF_CHANNEL_COUNT in entity_config:
            for channel in range(entity_config[CONF_CHANNEL_COUNT]):
                name = get_name(
                    entry_name=entity_options[CONF_NAME],
                    button=entity_options[CONF_BUTTON],
                    device_class=entity_options.get(CONF_DEVICE_CLASS),
                    chnnl=channel,
                )
                uid = get_unique_id(
                    dev_id_str=dev_id_str,
                    button=entity_options[CONF_BUTTON],
                    device_class=entity_options.get(CONF_DEVICE_CLASS),
                    chnnl=channel,
                )
                description = EnOceanBinarySensorEntityDescription(
                    key=Platform.BINARY_SENSOR,
                    name=name,
                    translation_key="binary_sensor",
                    unique_id=uid
                )
                entity_options[CONF_CHANNEL] = channel
                entities.append(EnOceanBinarySensor(entity_config, description, entity_options))
        else:
            name = get_name(
                entry_name=entity_options[CONF_NAME],
                button=entity_options[CONF_BUTTON],
                device_class=entity_options.get(CONF_DEVICE_CLASS),
                chnnl=None,
            )
            uid = get_unique_id(
                dev_id_str=dev_id_str,
                button=entity_options[CONF_BUTTON],
                device_class=entity_options.get(CONF_DEVICE_CLASS),
                chnnl=None,
            )
            description = EnOceanBinarySensorEntityDescription(
                key=Platform.BINARY_SENSOR,
                name=name,
                translation_key="binary_sensor",
                unique_id=uid
            )
            entities.append(EnOceanBinarySensor(entity_config, description, entity_options))

    async_add_entities(entities)

def setup_platform(
    hass: HomeAssistant,
    config_entry: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """ Set up the Binary Sensor platform for EnOcean. """
    dev_id: list[int] = config_entry[CONF_ID]
    dev_name: str = config_entry[CONF_NAME]
    device_class: BinarySensorDeviceClass | None = config_entry.get(CONF_DEVICE_CLASS)
    eep: list[int] = config_entry[CONF_EEP]
    button: str | None = config_entry.get(CONF_BUTTON)

    add_entities([EnOceanBinarySensor(config_entry, BinarySensorEntityDescription)])


def get_unique_id(dev_id_str, button, device_class, chnnl) -> str:
    uid = f"{dev_id_str}"
    if button:
        uid += f"-button_{button}"
    elif device_class:
        uid += f"-{device_class}"
    else :
        uid += f"-{Platform.BINARY_SENSOR}"
    if chnnl is not None:
        uid += f"-channel_{chnnl}"
    return uid

def get_name(entry_name, button, device_class, chnnl) -> str:
    name = f"{entry_name}"
    if button:
        name += f" Button {button}"
    elif device_class:
        name += f" {device_class}"
    else:
        name += f" {Platform.BINARY_SENSOR}"
    if chnnl is not None:
        name += f" {CONF_CHANNEL} {chnnl}"
    return name


class EnOceanBinarySensor(EO4HABinarySensor, EnOceanEntity, BinarySensorEntity):
    """ Representation of EnOcean binary sensors such as wall switches. """

    def __init__(
        self,
        config: dict,
        description: EnOceanBinarySensorEntityDescription,
        options,
    ) -> None:
        """ Initialize the EnOcean binary sensor. """
        dev_id = config[CONF_ID]
        dev_id_str = to_hex_string(dev_id)
        super().__init__(dev_id, config[CONF_EEP])
        self.button = options.get(CONF_BUTTON)
        self.shortcut = options.get(CONF_PROFILE_SHORTCUT)
        self.channel = options.get(CONF_CHANNEL)
        self.eo_sensor = None
        self.onoff = -1
        self.which = -1

        self._attr_unique_id = description.unique_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_id_str)})
        self.entity_description = description
        self._attr_entity_registry_enabled_default = options.get(CONF_ENABLED, True)

    def value_changed(self, packet):
        """ Fire an event with the data that have changed. """
        result = self.parse_packet(
            packet=packet,
            actual_which=self.which,
            actual_onoff=self.onoff,
            shortcut=self.shortcut,
        )
        if not result:
            return

        if "legacy" in result:
            pushed, self.which, self.onoff = result["legacy"]
            if pushed != self._attr_state:
                self._attr_state = pushed
                self.schedule_update_ha_state()

            self.hass.bus.fire(
                EVENT_BUTTON_PRESSED,
                {
                    "id": self.dev_id,
                    "pushed": pushed,
                    "which": self.which,
                    "onoff": self.onoff,
                },
            )
        elif "status" in result:
            if result["status"] != self._attr_is_on:
                self._attr_is_on = result["status"]
                self._attr_extra_state_attributes = result.get('extra_state_attr', {})
                self.schedule_update_ha_state()
