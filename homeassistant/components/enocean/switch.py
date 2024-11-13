""" Support for EnOcean switches. """
from dataclasses import dataclass
from typing import Any

import voluptuous as vol

from enocean.protocol.packet import RadioPacket
from enocean.utils import combine_hex, to_hex_string
from enocean4ha_bridge import EnOceanGateway, EO4HASwitch
from homeassistant.components.switch import (
    PLATFORM_SCHEMA as SWITCH_PLATFORM_SCHEMA,
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription
)
from homeassistant.const import CONF_ENTITIES, CONF_ID, CONF_NAME, EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import EnOceanConfigEntry
from .const import CONF_CHANNEL, CONF_CHANNEL_COUNT, CONF_EEP, CONF_GATEWAY, CONF_MANUFACTURER, DOMAIN, LOGGER
from .enocean_entity import EnOceanEntity

DEFAULT_NAME = "EnOcean Switch"

PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHANNEL, default=0): cv.positive_int,
    }
)

@dataclass(frozen=True, kw_only=True)
class EnOceanSwitchEntityDescription(SwitchEntityDescription):
    """ Describes EnOcean seitch entity. """
    unique_id: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """ Set up the switch platform. """

    if CONF_GATEWAY in config_entry.data:
        async_add_entities([TeachModeSwitch(config_entry.runtime_data)])
        return

    if not config_entry.data[CONF_ENTITIES].get(Platform.SWITCH):
        return

    entities = []
    entity_config = dict(config_entry.data)
    dev_id_str = to_hex_string(config_entry.data[CONF_ID])

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, dev_id_str)},
        name=config_entry.title,
        manufacturer=entity_config.get(CONF_MANUFACTURER),
        model=f"Base ID: {dev_id_str}",
        model_id=f"EEP: {to_hex_string(entity_config[CONF_EEP], sep='-')}",
    )

    for entity_options in entity_config[CONF_ENTITIES][Platform.SWITCH]:
        for channel in range(entity_config[CONF_CHANNEL_COUNT]):
            description = EnOceanSwitchEntityDescription(
                key=Platform.SWITCH,
                device_class=SwitchDeviceClass.SWITCH,
                name=f"{entity_config[CONF_NAME]} {CONF_CHANNEL} {channel}",
                unique_id=generate_unique_id(config_entry.data[CONF_ID], channel),
            )
            _migrate_to_new_unique_id(hass, entity_config[CONF_ID], channel)
            entity_options[CONF_CHANNEL] = channel
            entities.append(EnOceanSwitch(entity_config, description, entity_options))

    async_add_entities(entities)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the EnOcean switch platform."""
    channel: int = config[CONF_CHANNEL]
    dev_id: list[int] = config[CONF_ID]
    dev_name: str = config[CONF_NAME]
    eep: list[int] = config[CONF_EEP]

    _migrate_to_new_unique_id(hass, dev_id, channel)
    async_add_entities([EnOceanSwitch(dev_id, eep, dev_name, channel)])


def generate_unique_id(dev_id: list[int], channel: int|None) -> str:
    """Generate a valid unique id."""
    return f"{to_hex_string(dev_id)}-{Platform.SWITCH}{f'-{channel}' if channel is not None else ''}"


def _migrate_to_new_unique_id(hass: HomeAssistant, dev_id, channel) -> None:
    """Migrate old unique ids to new unique ids."""
    all_old_unique_ids = [
        f"{combine_hex(dev_id)}"
        f"{combine_hex(dev_id)}-{channel}"
    ]

    ent_reg = er.async_get(hass)

    for old_unique_id in all_old_unique_ids:
        entity_id = ent_reg.async_get_entity_id(Platform.SWITCH, DOMAIN, old_unique_id)
        if entity_id is not None:
            new_unique_id = generate_unique_id(dev_id, channel)
            try:
                ent_reg.async_update_entity(entity_id, new_unique_id=new_unique_id)
            except ValueError:
                LOGGER.warning(
                    "Skip migration of id [%s] to [%s] because it already exists",
                    old_unique_id,
                    new_unique_id,
                )
            else:
                LOGGER.debug(
                    "Migrating unique_id from [%s] to [%s]",
                    old_unique_id,
                    new_unique_id,
                )


class EnOceanSwitch(EO4HASwitch, EnOceanEntity, SwitchEntity):
    """ Representation of an EnOcean switch device. """

    def __init__(self, entity_config: dict, description: EnOceanSwitchEntityDescription, entity_options: dict) -> None:
        """ Initialize the EnOcean switch device. """
        dev_id = entity_config[CONF_ID]
        dev_id_str = to_hex_string(dev_id)
        super().__init__(dev_id, entity_config[CONF_EEP])
        self.channel = entity_options[CONF_CHANNEL]
        self._attr_unique_id = description.unique_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_id_str)},)
        self.entity_description= description
        self._logger.debug(f"Initialized {type(self).__name__}, ID {dev_id_str}, {repr(self.eep)}")

    def value_changed(self, packet: RadioPacket) -> None:
        """ Update the internal state of the switch. """
        result = self.parse_packet(packet)
        if not result:
            return
        if "status" in result:
            if result["status"] != self._attr_is_on:
                self._attr_is_on = result["status"]
                self._attr_extra_state_attributes = result.get('extra_state_attr', {})
                self.schedule_update_ha_state()


TEACH_MODE_SWITCH_DESCRIPTION = SwitchEntityDescription(
    key="button",
    entity_category=EntityCategory.CONFIG,
    has_entity_name=True,
    name="Teach Modus",
    translation_key="teach_mode"
)

class TeachModeSwitch(EnOceanEntity, SwitchEntity):
    """ Representation of a button to en-/disable the teach in mode. """

    _attr_name: str = "Teach in"
    _attr_device_class = SwitchDeviceClass.SWITCH
    entity_description: SwitchEntityDescription = TEACH_MODE_SWITCH_DESCRIPTION

    def __init__(self, gateway: EnOceanGateway):
        self._attr_unique_id = f"{gateway.sender_id_str}-enocean_teach_mode"
        super().__init__(dev_id=gateway.sender_id, eep=None)
        self.gateway: EnOceanGateway = gateway
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, gateway.sender_id_str)},)
        self._attr_is_on = gateway.teach_in

    def turn_on(self, **kwargs: Any) -> None:
        """ Turn on the switch. """
        self._attr_is_on = True
        self.gateway.teach_in = True

    def turn_off(self, **kwargs: Any) -> None:
        """ Turn off the switch. """
        self._attr_is_on = False
        self.gateway.teach_in = False

    def value_changed(self, packet: RadioPacket):
        """ Update the internal state of the switch. """
        # This is needed to avoid a NotImplementedError
        pass
