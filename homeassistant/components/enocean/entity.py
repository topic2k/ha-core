"""Representation of an EnOcean device."""

from enocean.protocol.packet import Packet
from enocean.utils import combine_hex

from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity import Entity

from .const import DATA_ENOCEAN, ENOCEAN_DONGLE, SIGNAL_RECEIVE_MESSAGE, SIGNAL_SEND_MESSAGE
from .dongle import EnOceanDongle


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

    def send_command(self, packet_type, rorg, rorg_func, rorg_type, command, **kwargs):
        """Send a command via the EnOcean dongle."""

        dongle: EnOceanDongle = self.hass.data[DATA_ENOCEAN][ENOCEAN_DONGLE]
        packet = Packet.create(
            packet_type=packet_type,
            rorg=rorg,
            rorg_func=rorg_func,
            rorg_type=rorg_type,
            command=command,
            sender=dongle.sender_id,
            destination=self.dev_id,
            **kwargs
        )
        dispatcher_send(self.hass, SIGNAL_SEND_MESSAGE, packet)
