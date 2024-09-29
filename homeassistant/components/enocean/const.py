"""Constants for the ENOcean integration."""

import logging

from homeassistant.const import Platform

DOMAIN = "enocean"
DATA_ENOCEAN = "enocean"
ENOCEAN_DONGLE = "dongle"

ERROR_INVALID_DONGLE_PATH = "invalid_dongle_path"

SIGNAL_RECEIVE_MESSAGE = "enocean.receive_message"
SIGNAL_SEND_MESSAGE = "enocean.send_message"

LOGGER = logging.getLogger(__package__)
LOGGER.setLevel(logging.DEBUG)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONF_CHANNEL = "channel"
CONF_EEP = "eep"
CONF_DIMMABLE = "dimmable"
CONF_BUTTON = "button"

SENSOR_TYPES = [
    SENSOR_TYPE_HUMIDITY := "humidity",
    SENSOR_TYPE_ILLUMINANCE := "illuminance",
    SENSOR_TYPE_OCCUPANCY := "occupancy",
    SENSOR_TYPE_POWER := "powersensor",
    SENSOR_TYPE_TEMPERATURE := "temperature",
    SENSOR_TYPE_WINDOWHANDLE := "windowhandle",
]

VALIDATOR_DEVICE_ID = r"^(?P<a>[a-fA-F0-9]{2})[: -]?(?P<b>[a-fA-F0-9]{2})[: -]?(?P<c>[a-fA-F0-9]{2})[: -]?(?P<d>[a-fA-F0-9]{2})$"
VALIDATOR_EEP = r"^(?P<a>A5|D2|D5|F6|a5|d2|d5|f6)[: -]?(?P<b>[a-fA-F0-9]{2})[: -]?(?P<c>[a-fA-F0-9]{2})$"
