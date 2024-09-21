"""Support for EnOcean switches."""

from __future__ import annotations

from typing import Any

from enocean.protocol.packet import RadioPacket
from enocean.utils import combine_hex
from enocean4ha_bridge import EnOceanGateway, EO4HASwitch
import voluptuous as vol

from homeassistant.components.switch import (
    PLATFORM_SCHEMA as SWITCH_PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import CONF_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_CHANNEL, CONF_EEP, DOMAIN, LOGGER, DATA_ENOCEAN, ENOCEAN_DONGLE
from .device import EnOceanEntity

DEFAULT_NAME = "EnOcean Switch"

PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHANNEL, default=0): cv.positive_int,
    }
)


def generate_unique_id(dev_id: list[int], channel: int) -> str:
    """Generate a valid unique id."""
    return f"{combine_hex(dev_id)}-{channel}"


def _migrate_to_new_unique_id(hass: HomeAssistant, dev_id, channel) -> None:
    """Migrate old unique ids to new unique ids."""
    old_unique_id = f"{combine_hex(dev_id)}"

    ent_reg = er.async_get(hass)
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


class EnOceanSwitch(EnOceanEntity, SwitchEntity):
    """Representation of an EnOcean switch device."""

    _attr_is_on = False

    def __init__(self, dev_id: list[int], eep: list[int], dev_name: str, channel: int) -> None:
        """Initialize the EnOcean switch device."""
        super().__init__(dev_id, eep)
        self.channel = channel
        self._attr_unique_id = generate_unique_id(dev_id, channel)
        self._attr_name = dev_name
        self._attr_extra_state_attributes = {}
        self.eo_switch = None

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN][ENOCEAN_DONGLE]
        self.eo_switch = EO4HASwitch(
            gateway=dongle,
            dev_id=self.dev_id,
            channel=self.channel,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )
        await super().async_added_to_hass()

    def turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        self.eo_switch.turn_on(**kwargs)
        self._attr_is_on = True

    def turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        self.eo_switch.turn_off(**kwargs)
        self._attr_is_on = False

    def value_changed(self, packet: RadioPacket):
        """Update the internal state of the switch."""
        state, extra_attr = self.eo_switch.parse_packet(packet, self._attr_is_on)
        if state != self._attr_is_on:
            self._attr_is_on = state
            self._attr_extra_state_attributes = extra_attr
            self.schedule_update_ha_state()
