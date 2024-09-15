"""Representation of an EnOcean dongle."""

import glob

import serial

from enocean.communicators import SerialCommunicator
from .const import LOGGER


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
