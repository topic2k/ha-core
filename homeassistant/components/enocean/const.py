"""Constants for the ENOcean integration."""

import logging
from typing import Final

from homeassistant.const import Platform


LOGGER = logging.getLogger(__package__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN: Final  = "enocean"

CONF_GATEWAY: Final = "gateway"
CONF_CHANNEL: Final  = "channel"
CONF_EEP: Final  = "eep"
CONF_CHANNEL_COUNT: Final = "channel_count"
CONF_COLOR_MODE: Final  = "color_mode"
CONF_BUTTON: Final  = "button"
CONF_BUTTONS_AB: Final = "buttons_ab"
CONF_BINARY_DEVICE_TYPE: Final = "binary_device_type"
CONF_CMD_OR_DIR: Final = "cmd_or_dir"
CONF_SENSOR_DEVICE_TYPE: Final = "sensor_device_type"
CONF_DEVICE_TYPE: Final = "device_type"
CONF_PROFILE_SHORTCUT: Final = "shortcut"
CONF_SELECT_OPTIONS: Final = "options"
CONF_MEASUREMENT_MODE: Final = "measurement_mode"
CONF_REPORT_MEASUREMENT: Final = "report_measurement"
CONF_MANUFACTURER: Final = "manufacturer"

ERROR_INVALID_DONGLE_PATH: Final  = "invalid_dongle_path"
ERROR_DEVICE_ID_FAULTY: Final = "device_id_faulty"
ERROR_EEP_FAULTY: Final = "eep_faulty"
ERROR_SELECT_AT_LEAST_ONE: Final = "slect_at_least_one"

SIGNAL_RECEIVE_MESSAGE: Final  = "enocean.receive_message"
SIGNAL_SEND_MESSAGE: Final  = "enocean.send_message"

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]

SENSOR_TYPES = [
    SENSOR_TYPE_ENERGY := "energy",
    SENSOR_TYPE_HUMIDITY := "humidity",
    SENSOR_TYPE_ILLUMINANCE := "illuminance",
    SENSOR_TYPE_POWER := "powersensor",
    SENSOR_TYPE_TEMPERATURE := "temperature",
    SENSOR_TYPE_WINDOWHANDLE := "windowhandle",
]

DEVICE_CLASS_WINDOWHANDLE: Final = "windowhandle"
DEVICE_CLASS_PROFILE_SHORTCUT: Final = "profile_shortcut"

VALIDATOR_DEVICE_ID = r"^(?P<a>[a-fA-F0-9]{2})[: -]?(?P<b>[a-fA-F0-9]{2})[: -]?(?P<c>[a-fA-F0-9]{2})[: -]?(?P<d>[a-fA-F0-9]{2})$"
VALIDATOR_EEP = r"^(?P<a>A5|D2|D5|F6|a5|d2|d5|f6)[: -]?(?P<b>[a-fA-F0-9]{2})[: -]?(?P<c>[a-fA-F0-9]{2})$"

MANUAL_PATH_VALUE: Final = "Custom path"
EXTRA_STATE_ATTRIBUTES: Final = "extra_state_attr"
