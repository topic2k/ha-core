""" Config flows for the EnOcean integration. """

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.helpers import config_validation as cv, device_registry as dr
from enocean.utils import to_hex_string
from enocean4ha_bridge import EnOceanGateway, EO4HAFlowHandler
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.valve import ValveDeviceClass
from homeassistant.helpers.typing import DiscoveryInfoType, VolDictType
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_COMMAND, CONF_DEVICE_CLASS,
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_ENTITY_CATEGORY,
    CONF_ID,
    CONF_MAXIMUM, CONF_MINIMUM, CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT, EntityCategory,
    Platform
)
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode
)
from .const import (
    CONF_BUTTON,
    CONF_BUTTONS_AB,
    CONF_COLOR_MODE,
    CONF_DEVICE_TYPE,
    CONF_EEP,
    CONF_GATEWAY,
    CONF_MANUFACTURER, CONF_MEASUREMENT_MODE, CONF_REPORT_MEASUREMENT, DEVICE_CLASS_WINDOWHANDLE,
    DOMAIN,
    CONF_CHANNEL_COUNT,
    CONF_CMD_OR_DIR, CONF_PROFILE_SHORTCUT,
    DEVICE_CLASS_PROFILE_SHORTCUT,
    ERROR_DEVICE_ID_FAULTY,
    ERROR_EEP_FAULTY,
    ERROR_INVALID_DONGLE_PATH,
    MANUAL_PATH_VALUE,
    VALIDATOR_DEVICE_ID,
    VALIDATOR_EEP
)
from homeassistant.components.input_number import CONF_STEP
from homeassistant.components.light import ColorMode
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.data_entry_flow import section


_LOGGER = logging.getLogger(__name__)


class EnOceanFlowHandler(EO4HAFlowHandler, ConfigFlow, domain=DOMAIN):
    """ Handle the EnOcean config flows. """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the EnOcean config flow."""
        self._discovered_device = None
        self._user_input: dict[str, Any] | None = None

    # async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
    #     """Import a yaml configuration."""
    #     if not await self.validate_enocean_conf(import_data):
    #         LOGGER.warning(
    #             "Cannot import yaml configuration: %s is not a valid dongle path",
    #             import_data[CONF_GATEWAY],
    #         )
    #         return self.async_abort(reason="invalid_dongle_path")
    #
    #     return self.create_enocean_entry(import_data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Handle an EnOcean config flow start. """

        entries = self._async_current_entries()
        if not entries or not any([hasattr(x,'runtime_data') for x in entries]):
            return await self.async_step_detect()

        return await self.async_step_add_device()

    async def async_step_detect(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Propose a list of detected dongles. """
        errors = {}

        if user_input is not None:
            if user_input[CONF_GATEWAY] == MANUAL_PATH_VALUE:
                return await self.async_step_manual()
            try:
                gateway: EnOceanGateway = EnOceanGateway(self.hass, user_input[CONF_GATEWAY])
                await gateway.load()
            except ConnectionError:
                errors[CONF_GATEWAY] = ERROR_INVALID_DONGLE_PATH
            else:
                return await self.create_gateway_entry(gateway, user_input[CONF_GATEWAY])

        bridges = await self.hass.async_add_executor_job(EnOceanGateway.detect)
        if len(bridges) == 0:
            return await self.async_step_manual(user_input)

        bridges.append(MANUAL_PATH_VALUE)
        return self.async_show_form(
            step_id="detect",
            data_schema=vol.Schema({vol.Required(CONF_GATEWAY): vol.In(bridges)}),
            errors=errors or {},
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Request manual USB dongle path. """
        default_path = None
        errors = {}
        if user_input is not None:
            try:
                gateway: EnOceanGateway = EnOceanGateway(self.hass, user_input[CONF_GATEWAY])
            except ConnectionError:
                errors[CONF_GATEWAY] = ERROR_INVALID_DONGLE_PATH
                default_path = user_input[CONF_GATEWAY]
            else:
                return await self.create_gateway_entry(gateway, user_input[CONF_GATEWAY])

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(schema=CONF_GATEWAY, default=default_path): cv.string}),
            errors=errors,
        )

    async def async_step_add_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Request base information for new device """
        errors = {}
        default_dev_id = None
        default_eep = None
        default_name = "New EnOcean Device"

        if self._discovered_device is not None:
            default_dev_id = self._discovered_device[CONF_ID]
            default_eep = self._discovered_device[CONF_EEP]
            self._user_input = {CONF_MANUFACTURER: self._discovered_device[CONF_MANUFACTURER]}

        if user_input is not None:
            dev_id_valid = re.match(VALIDATOR_DEVICE_ID, user_input[CONF_ID])
            eep_valid = re.match(VALIDATOR_EEP, user_input[CONF_EEP])
            if dev_id_valid and eep_valid:
                user_input[CONF_ID] = list( int(x, base=16) for x in dev_id_valid.groups())
                user_input[CONF_EEP] = list( int(x, base=16) for x in eep_valid.groups())
                if self._discovered_device is not None:
                    user_input[CONF_MANUFACTURER]  = self._discovered_device[CONF_MANUFACTURER]
                self._user_input = user_input
                return await self.async_step_add_device_options()

            if not dev_id_valid:
                errors[CONF_ID] = ERROR_DEVICE_ID_FAULTY
            if not eep_valid:
                errors[CONF_EEP] = ERROR_EEP_FAULTY

            default_dev_id = user_input[CONF_ID]
            default_eep = user_input[CONF_EEP]
            default_name = user_input[CONF_NAME]

        data_schema = {
            # vol.Required(CONF_ID, default=default_dev_id): cv.matches_regex(VALIDATOR_DEVICE_ID),  # ==> TypeError: issubclass() arg 1 must be a class
            vol.Required(CONF_ID, default=default_dev_id): cv.string,
            # vol.Required(CONF_EEP, default=default_eep): cv.matches_regex(VALIDATOR_EEP),  # ==> TypeError: issubclass() arg 1 must be a class
            vol.Required(CONF_EEP, default=default_eep): cv.string,
            vol.Optional(CONF_NAME, default=default_name): cv.string,
        }

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema(data_schema),
            errors=errors
        )

    async def async_step_integration_discovery(
        self, discovery_info: DiscoveryInfoType
    ) -> ConfigFlowResult:
        """ Handle integration discovery. """
        await self.async_set_unique_id(discovery_info[CONF_ID])

        if self.hass.config_entries.flow.async_has_matching_flow(self):
            return self.async_abort(reason="already_in_progress")
        self._abort_if_unique_id_configured()

        for entry in self._async_current_entries(include_ignore=False):
            if entry.unique_id == discovery_info[CONF_ID]:
                # if async_update_entry_from_discovery(self.hass, entry, device):
                #     self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_abort(reason="already_configured")

        self._discovered_device = discovery_info
        return await self.async_step_add_device()

    async def async_step_add_device_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Request aaditional device information """
        errors = {}

        if user_input is not None:
            if not 'no_options_available' in user_input:
                self._user_input.update(user_input)

            options_data = await self.get_entry_options_data(user_input)
            if isinstance(options_data, dict) and 'type' in options_data:
                return options_data
            elif isinstance(options_data, dict) and CONF_ENTITIES in options_data:
                return self.async_create_entry(title=options_data[CONF_NAME], data=options_data)
            errors["base"] = "no match in device options matcher"

        try:
            data_schema = await self.get_device_options_schema()
        except ValueError:
            return self.async_abort(
                reason=f"EEP {to_hex_string(self._user_input[CONF_EEP], '-')} is not yet supported.")

        if not data_schema:
            return await self.async_step_add_device_options({'no_options_available': True})

        return self.async_show_form(
            step_id="add_device_options",
            data_schema=vol.Schema(data_schema),
            errors=errors
        )

    async def async_step_light_device_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Request aaditional device information """
        errors = {}

        if user_input is not None:
            if not 'no_options_available' in user_input:
                self._user_input.update(user_input)
            data = {
                CONF_NAME: self._user_input[CONF_NAME],
                CONF_ID: self._user_input[CONF_ID],
                CONF_EEP: self._user_input[CONF_EEP],
                CONF_CHANNEL_COUNT: self._user_input[CONF_CHANNEL_COUNT],
                CONF_ENTITIES: {
                    Platform.LIGHT: [{CONF_DEVICE_CLASS: None, CONF_COLOR_MODE: user_input[CONF_COLOR_MODE]}, ],
                }
            }
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        data_schema = {
            vol.Required(CONF_COLOR_MODE): vol.In([ColorMode.ONOFF, ColorMode.BRIGHTNESS]),
        }
        return self.async_show_form(
            step_id="light_device_options",
            data_schema=vol.Schema(data_schema),
            errors=errors
        )

    async def validate_enocean_conf(self, dongle_path) -> bool:
        """Return True if the user_input contains a valid dongle path."""
        # dongle_path = user_input[CONF_GATEWAY]
        return await self.hass.async_add_executor_job(EnOceanGateway.validate_path, dongle_path)

    async def create_gateway_entry(self, gateway, device):
        """Create an entry for the provided configuration."""
        # x = await self.async_set_unique_id(f"dongle_{user_input[CONF_GATEWAY]}")
        # self._abort_if_unique_id_configured()

        await self.async_set_unique_id(gateway.sender_id_str, raise_on_progress=False)
        self._abort_if_unique_id_configured(updates={CONF_GATEWAY: device})
        gateway.unload()
        return self.async_create_entry(
            title="EnOcean Gateway",
            data={CONF_GATEWAY: device},
            description="Gateway for communicating with Encean devices."
        )
