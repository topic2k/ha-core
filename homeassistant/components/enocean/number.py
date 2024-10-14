"""Support for EnOcean number sources."""
import sys
from dataclasses import dataclass

import voluptuous as vol

from enocean.protocol.eep import EEPSoup
from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string
from enocean4ha_bridge import EO4HANumber

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
    PLATFORM_SCHEMA as NUMBER_PLATFORM_SCHEMA
)
from homeassistant.const import (
    CONF_ENTITIES,
    CONF_ENTITY_CATEGORY,
    CONF_ID,
    CONF_MAXIMUM, CONF_MINIMUM, CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT, EntityCategory,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import EnOceanConfigEntry
from .const import CONF_CHANNEL, CONF_CHANNEL_COUNT, CONF_CMD_OR_DIR, CONF_EEP, CONF_GATEWAY, CONF_PROFILE_SHORTCUT, \
    DOMAIN
from .enocean_entity import EnOceanEntity
from ..input_number import CONF_STEP

DEFAULT_NAME = "EnOcean Number"

PLATFORM_SCHEMA = NUMBER_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ID, default=[]): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

@dataclass(frozen=True, kw_only=True)
class EnOceanNumberEntityDescription(NumberEntityDescription):
    """ Describes EnOcean number entity. """
    unique_id: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """ Set up number based on a config entry. """

    if CONF_GATEWAY in config_entry.data:
        return

    if not config_entry.data[CONF_ENTITIES].get(Platform.NUMBER):
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

    for entity_options in entity_config[CONF_ENTITIES][Platform.NUMBER]:
        for channel in range(entity_config[CONF_CHANNEL_COUNT]):
            profile = EEPSoup.find_profile(*entity_config[CONF_EEP], **entity_options[CONF_CMD_OR_DIR])
            entity_options[CONF_CHANNEL] = channel
            category = entity_options.get(CONF_ENTITY_CATEGORY, None)
            name = profile.findChild(shortcut=entity_options[CONF_PROFILE_SHORTCUT])["description"]
            description = EnOceanNumberEntityDescription(
                key=f"{dev_id_str}-shortcut-{entity_options[CONF_PROFILE_SHORTCUT]}",
                entity_category=EntityCategory(category) if category else None,
                mode=NumberMode.AUTO,
                name=f"{entity_config[CONF_NAME]} {name}",
                native_max_value=entity_options.get(CONF_MAXIMUM, float(sys.maxsize)),
                native_min_value=entity_options.get(CONF_MINIMUM, -1 * float(sys.maxsize)),
                native_step=entity_options.get(CONF_STEP, 0.1),
                native_unit_of_measurement=entity_options.get(CONF_UNIT_OF_MEASUREMENT, None),
                unique_id=f"{dev_id_str}-{Platform.NUMBER}-{channel}-shortcut_{entity_options[CONF_PROFILE_SHORTCUT]}",
            )
            entities.append(EnOceanNumber(entity_config, description, entity_options))

    async_add_entities(entities)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """ Set up the EnOcean number platform. """
    dev_name: str = config[CONF_NAME]
    dev_id: list[int] = config[CONF_ID]
    eep: list[int] = config[CONF_EEP]

    async_add_entities([EnOceanNumber(dev_id, eep, dev_name, channel, dimmable)])


class EnOceanNumber(EO4HANumber, EnOceanEntity, NumberEntity):
    """ Representation of an EnOcean number source. """

    def __init__(self, entity_config: dict, description: EnOceanNumberEntityDescription, options: dict) -> None:
        """ Initialize the EnOcean number source. """
        super().__init__(entity_config[CONF_ID], entity_config[CONF_EEP])
        dev_id_str = to_hex_string(self.dev_id)
        self.channel = options[CONF_CHANNEL]
        self.shortcut = options[CONF_PROFILE_SHORTCUT]
        self._attr_unique_id = description.unique_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_id_str)},)
        self.entity_description = description
        self._attr_native_value = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self.async_query_actuator_status()
        await self.async_query_actuator_external_interface_settings()

    def value_changed(self, packet: RadioPacket):
        """ Update the internal state of this device. """
        result = self.parse_packet(packet)
        if not result:
            return
        if "status" in result:
            if result["status"] != self._attr_native_value:
                self._attr_native_value = result["status"] / 10
                self._attr_extra_state_attributes = result.get('extra_state_attr', {})
                self.schedule_update_ha_state()
