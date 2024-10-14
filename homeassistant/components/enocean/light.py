""" Support for EnOcean light sources. """

from dataclasses import dataclass

import voluptuous as vol

from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string
from enocean4ha_bridge import EO4HALight

from homeassistant.components.light import (
    LightEntity,
    LightEntityDescription,
    PLATFORM_SCHEMA as LIGHT_PLATFORM_SCHEMA
)
from homeassistant.const import CONF_BRIGHTNESS, CONF_ENTITIES, CONF_ID, CONF_NAME, CONF_STATE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import EnOceanConfigEntry
from .const import CONF_CHANNEL, CONF_CHANNEL_COUNT, CONF_COLOR_MODE, CONF_EEP, CONF_GATEWAY, DOMAIN
from .enocean_entity import EnOceanEntity

DEFAULT_NAME = "EnOcean Light"

PLATFORM_SCHEMA = LIGHT_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ID, default=[]): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHANNEL, default=0): cv.positive_int,
    }
)

@dataclass(frozen=True, kw_only=True)
class EnOceanLightEntityDescription(LightEntityDescription):
    """ Describes EnOcean light entity. """
    unique_id: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light based on a config entry."""

    if CONF_GATEWAY in config_entry.data:
        return

    if not config_entry.data[CONF_ENTITIES].get(Platform.LIGHT):
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

    for entity_options in entity_config[CONF_ENTITIES][Platform.LIGHT]:
        for channel in range(entity_config[CONF_CHANNEL_COUNT]):
            description = EnOceanLightEntityDescription(
                key=Platform.LIGHT,
                name=f"{entity_config[CONF_NAME]} {Platform.LIGHT} {CONF_CHANNEL} {channel}",
                unique_id=f"{dev_id_str}-{Platform.LIGHT}-channel_{channel}"
            )
            entity_options[CONF_CHANNEL] = channel
            entities.append(EnOceanLight(entity_config, description, entity_options))

    async_add_entities(entities)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the EnOcean light platform."""
    dev_name: str = config[CONF_NAME]
    dev_id: list[int] = config[CONF_ID]
    eep: list[int] = config[CONF_EEP]
    channel: int = config[CONF_CHANNEL]
    dimmable: bool = config[CONF_DIMMABLE]

    async_add_entities([EnOceanLight(dev_id, eep, dev_name, channel, dimmable)])


class EnOceanLight(EO4HALight, EnOceanEntity, LightEntity):
    """ Representation of an EnOcean light source. """

    def __init__(self, entity_config: dict, description: EnOceanLightEntityDescription, entity_options: dict) -> None:
        """ Initialize the EnOcean light source. """
        dev_id = entity_config[CONF_ID]
        dev_id_str = to_hex_string(dev_id)
        super().__init__(dev_id, entity_config[CONF_EEP])
        self._attr_unique_id = description.unique_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_id_str)},)
        self.entity_description = description
        self._attr_supported_color_modes = {entity_options[CONF_COLOR_MODE]}
        self._attr_color_mode = entity_options[CONF_COLOR_MODE]
        self.channel = entity_options.get(CONF_CHANNEL)

    def value_changed(self, packet: RadioPacket):
        """Update the internal state of this device."""
        result = self.parse_packet(packet)
        if not result:
            return
        if "status" in result:
            if result["status"][CONF_BRIGHTNESS] != self._attr_brightness or result["status"][CONF_STATE] != self._attr_is_on:
                self._attr_brightness = result["status"][CONF_BRIGHTNESS]
                self._attr_is_on = result["status"][CONF_STATE]
                self._attr_extra_state_attributes = result["extra_state_attr"]
                self.schedule_update_ha_state()
