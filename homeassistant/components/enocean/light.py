"""Support for EnOcean light sources."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from enocean.protocol.packet import RadioPacket
from enocean.utils import combine_hex
from enocean4ha_bridge import EnOceanGateway, EO4HALight, EO4HAError
from homeassistant.components.light import (
    PLATFORM_SCHEMA as LIGHT_PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_CHANNEL, CONF_EEP, DATA_ENOCEAN, CONF_DIMMABLE, ENOCEAN_DONGLE, LOGGER
from .enocean_entity import EnOceanEntity

DEFAULT_NAME = "EnOcean Light"

PLATFORM_SCHEMA = LIGHT_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ID, default=[]): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHANNEL, default=0): cv.positive_int,
        vol.Optional(CONF_DIMMABLE, default=True): cv.boolean
    }
)


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


class EnOceanLight(EnOceanEntity, LightEntity):
    """Representation of an EnOcean light source."""

    def __init__(self, dev_id: list[int], eep: list[int], dev_name: str, channel: int, dimmable: bool) -> None:
        """Initialize the EnOcean light source."""
        super().__init__(dev_id, eep)
        self.channel = channel
        self._attr_unique_id = f"{combine_hex(dev_id)}-{channel}"
        self._attr_name = dev_name
        self.eo_light = None
        if dimmable:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_brightness = 50
        else:
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("light: no gateway configured")
            return
        self.eo_light = EO4HALight(
            gateway=dongle,
            dev_id=self.dev_id,
            channel=self.channel,
            eep=self.eep,
            loglevel=LOGGER.getEffectiveLevel()
        )
        await super().async_added_to_hass()

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the light source on or sets a specific dimmer value."""
        self.eo_light.turn_on(actual_brightness=self._attr_brightness, **kwargs)
        self._attr_is_on = True

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the light source off."""
        self.eo_light.turn_off(**kwargs)
        self._attr_is_on = False

    def value_changed(self, packet: RadioPacket):
        """Update the internal state of this device."""
        try:
            brightness, is_on = self.eo_light.parse_packet(packet)
        except EO4HAError:
            pass
        else:
            if brightness != self._attr_brightness or is_on != self._attr_is_on:
                self._attr_brightness = brightness
                self._attr_is_on = is_on
                self.schedule_update_ha_state()
