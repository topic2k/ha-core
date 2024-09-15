"""Representation of an EnOcean dongle."""

import glob
import logging
from os.path import basename, normpath

from enocean.communicators import SerialCommunicator
from enocean.protocol.constants import PACKET, RETURN_CODE
from enocean.protocol.packet import RadioPacket, ResponsePacket
import enocean.utils
import serial

from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send

from .const import SIGNAL_RECEIVE_MESSAGE, SIGNAL_SEND_MESSAGE, LOGGER



class EnOceanDongle:
    """Representation of an EnOcean dongle.

    The dongle is responsible for receiving the ENOcean frames,
    creating devices if needed, and dispatching messages to platforms.
    """

    def __init__(self, hass, serial_path):
        """Initialize the EnOcean dongle."""

        self._communicator = SerialCommunicator(
            port=serial_path, callback=self.callback
        )
        self._communicator.logger.setLevel(LOGGER.getEffectiveLevel())
        self.serial_path = serial_path
        self.identifier = basename(normpath(serial_path))
        self.hass = hass
        self.dispatcher_disconnect_handle = None

    @property
    def sender_id(self):
        return self._communicator.base_id

    @property
    def sender_id_str(self):
        return enocean.utils.to_hex_string(self._communicator.base_id)

    async def async_setup(self):
        """Finish the setup of the bridge and supported platforms."""
        self._communicator.start()
        self.dispatcher_disconnect_handle = async_dispatcher_connect(
            self.hass, SIGNAL_SEND_MESSAGE, self._send_message_callback
        )
        # the following triggers a command to get the base id of the dongle
        _ = self._communicator.base_id

    def unload(self):
        """Disconnect callbacks established at init time."""
        if self.dispatcher_disconnect_handle:
            self.dispatcher_disconnect_handle()
            self.dispatcher_disconnect_handle = None

    def _send_message_callback(self, command):
        """Send a command through the EnOcean dongle."""
        self._communicator.send(command)

    def callback(self, packet):
        """Handle EnOcean device's callback.

        This is the callback function called by python-enocan whenever there
        is an incoming packet.
        """

        if isinstance(packet, RadioPacket):
            dispatcher_send(self.hass, SIGNAL_RECEIVE_MESSAGE, packet)
        elif isinstance(packet, ResponsePacket):
            if (
                packet.packet_type == PACKET.RESPONSE
                and packet.response == RETURN_CODE.OK
                and len(packet.response_data) == 4
            ):
                # Base ID is set from the response data.
                self._communicator.base_id = packet.response_data
                LOGGER.debug(f"controller id: {enocean.utils.to_hex_string(self._communicator.base_id)}")


def detect():
    """Return a list of candidate paths for USB ENOcean dongles.

    This method is currently a bit simplistic, it may need to be
    improved to support more configurations and OS.
    """
    globs_to_test = ["/dev/tty*FTOA2PV*", "/dev/serial/by-id/*EnOcean*"]
    found_paths = []
    for current_glob in globs_to_test:
        found_paths.extend(glob.glob(current_glob))

    return found_paths


def validate_path(path: str):
    """Return True if the provided path points to a valid serial port, False otherwise."""
    try:
        # Creating the serial communicator will raise an exception
        # if it cannot connect
        SerialCommunicator(port=path)
    except serial.SerialException as exception:
        LOGGER.warning(f"Dongle path {path} is invalid: {str(exception)}")
        return False
    return True
