"""Support for EnOcean light sources."""

from __future__ import annotations

import math
from typing import Any

from enocean.utils import combine_hex
import voluptuous as vol

from enocean.protocol.constants import PACKET, RORG
from enocean.protocol.packet import RadioPacket

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    PLATFORM_SCHEMA as LIGHT_PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_CHANNEL, CONF_EEP
from .device import EnOceanEntity

DEFAULT_NAME = "EnOcean Light"

PLATFORM_SCHEMA = LIGHT_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ID, default=[]): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHANNEL, default=0): cv.positive_int,
        vol.Optional(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
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
    channel: int = config[CONF_CHANNEL]

    async_add_entities([EnOceanLight(dev_id, dev_name, channel)])


class EnOceanLight(EnOceanEntity, LightEntity):
    """Representation of an EnOcean light source."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_brightness = 50
    _attr_is_on = False

    def __init__(self, dev_id: list[int], dev_name: str, channel: int) -> None:
        """Initialize the EnOcean light source."""
        super().__init__(dev_id)
        self._channel = channel
        self._attr_unique_id = f"{combine_hex(dev_id)}-{channel}"
        self._attr_name = dev_name

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the light source on or sets a specific dimmer value."""
        if (brightness := kwargs.get(ATTR_BRIGHTNESS)) is not None:
            self._attr_brightness = brightness

        bval = math.floor(self._attr_brightness / 256.0 * 100.0)
        if bval == 0:
            bval = 1

        self.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=RORG.VLD,
            rorg_func=0x01,
            rorg_type=0x12,
            command=0x01,
            DV=0x00,
            IO=self._channel,
            OV=bval,
        )
        self._attr_is_on = True

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the light source off."""
        self.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=RORG.VLD,
            rorg_func=0x01,
            rorg_type=0x12,
            command=0x01,
            DV=0x00,
            IO=self._channel,
            OV=0x00,
        )
        self._attr_is_on = False

    def value_changed(self, packet: RadioPacket):
        """Update the internal state of this device.

        Dimmer devices like Eltako FUD61 send telegram in different RORGs.
        We only care about the 4BS (0xA5).
        """
        brightness = self._attr_brightness
        is_on = self._attr_is_on
        if packet.rorg == RORG.BS4 and packet.data[1] == 0x02:
            val = packet.data[2]
            brightness = math.floor(val / 100.0 * 256.0)
            is_on = bool(val != 0)
        if packet.rorg == RORG.VLD:
            packet.parse_eep(rorg_func=0x01, rorg_type=0x12)
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self._channel:
                    brightness = math.floor(output / 100.0 * 256.0)
                    is_on = output > 0

        if brightness != self._attr_brightness or is_on != self._attr_is_on:
            self._attr_brightness = brightness
            self._attr_is_on = is_on
            self.schedule_update_ha_state()
