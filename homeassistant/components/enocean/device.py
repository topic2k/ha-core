"""Representation of an EnOcean device."""

from enocean.utils import combine_hex

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import SIGNAL_RECEIVE_MESSAGE


class EnOceanEntity(Entity):
    """Parent class for all entities associated with the EnOcean component."""

    def __init__(self, dev_id: list[int]) -> None:
        """Initialize the device."""
        self.dev_id = dev_id
        self.dev_id_int = combine_hex(dev_id)

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_RECEIVE_MESSAGE, self._message_received_callback
            )
        )

    def _message_received_callback(self, packet):
        """Handle incoming packets."""

        if packet.sender_int == combine_hex(self.dev_id):
            self.value_changed(packet)

    def value_changed(self, packet):
        """Update the internal state of the device when a packet arrives."""
        raise NotImplementedError
