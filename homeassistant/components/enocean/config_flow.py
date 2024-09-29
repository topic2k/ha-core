"""Config flows for the ENOcean integration."""
import re
from typing import Any

import voluptuous as vol

from enocean4ha_bridge import EnOceanGateway
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE, CONF_DEVICE_CLASS, CONF_ID, CONF_NAME, Platform
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, ERROR_INVALID_DONGLE_PATH, LOGGER, CONF_EEP, DATA_ENOCEAN, ENOCEAN_DONGLE, CONF_BUTTON, \
    SENSOR_TYPE_WINDOWHANDLE, VALIDATOR_DEVICE_ID, VALIDATOR_EEP
from .binary_sensor import PLATFORM_SCHEMA as EO_BINARY_SENSOR_PLATFORM_SCHEMA
from homeassistant.components.binary_sensor import DEVICE_CLASSES_SCHEMA, PLATFORM_SCHEMA as BINARY_SENSOR_PLATFORM_SCHEMA
from .sensor import EnOceanWindowHandle
from ...data_entry_flow import section
from ...helpers.selector import selector, SelectSelector, SelectSelectorConfig

DEFAULT_NAME_WINDOW_HANDLE = "EnOcean window handle"

class EnOceanFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle the enOcean config flows."""

    VERSION = 1
    MANUAL_PATH_VALUE = "Custom path"

    def __init__(self) -> None:
        """Initialize the EnOcean config flow."""
        self.dongle_path = None
        self.discovery_info = None

    # async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
    #     """Import a yaml configuration."""
    #     if not await self.validate_enocean_conf(import_data):
    #         LOGGER.warning(
    #             "Cannot import yaml configuration: %s is not a valid dongle path",
    #             import_data[CONF_DEVICE],
    #         )
    #         return self.async_abort(reason="invalid_dongle_path")
    #
    #     return self.create_enocean_entry(import_data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle an EnOcean config flow start."""

        entries = self._async_current_entries()
        if not entries:
            return await self.async_step_detect()

        # for entry in :
        #     if entry.runtime_data.sender_id_str == entry.unique_id:
        #         return self.async_abort(reason="single_instance_allowed")
        # if curr_ids := self._async_current_entries():
        return self.async_show_menu(
            menu_options=[
                "add_binary_sensor",
                "add_light",
                "add_humidity_sensor",
                "add_illuminance_sensor",
                "add_occupancy_sensor",
                "add_powersensor_sensor",
                "add_temperature_sensor",
                "add_windowhandle_sensor",
                "add_switch"
            ],
        )

    async def async_step_detect(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Propose a list of detected dongles."""
        errors = {}

        if user_input is not None:
            if user_input[CONF_DEVICE] == self.MANUAL_PATH_VALUE:
                return await self.async_step_manual()
            try:
                gateway: EnOceanGateway = EnOceanGateway(self.hass, user_input[CONF_DEVICE])
                await gateway.load()
            except ConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return await self.create_gateway_entry(gateway, user_input[CONF_DEVICE])

        bridges = await self.hass.async_add_executor_job(EnOceanGateway.detect)
        if len(bridges) == 0:
            return await self.async_step_manual(user_input)

        bridges.append(self.MANUAL_PATH_VALUE)
        return self.async_show_form(
            step_id="detect",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE): vol.In(bridges)}),
            errors=errors or {},
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Request manual USB dongle path."""
        default_value = None
        errors = {}
        if user_input is not None:
            try:
                gateway: EnOceanGateway = EnOceanGateway(self.hass, user_input[CONF_DEVICE])
            except ConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return await self.create_gateway_entry(gateway, user_input[CONF_DEVICE])

            # default_value = user_input[CONF_DEVICE]
            # errors = {CONF_DEVICE: ERROR_INVALID_DONGLE_PATH}

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE, default=default_value): str}),
            errors=errors,
        )

    # async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
    #     return await self.async_step_detect()
    #
    #     # default_value = None
    #     # errors = {}
    #     # if user_input is not None:
    #     #     if await self.validate_enocean_conf(user_input):
    #     #         return await self.create_enocean_entry(user_input)
    #     #     default_value = user_input[CONF_DEVICE]
    #     #     errors = {CONF_DEVICE: ERROR_INVALID_DONGLE_PATH}
    #     #
    #     # return self.async_show_form(
    #     #     step_id="reconfigure",
    #     #     data_schema=vol.Schema(
    #     #         {vol.Required(CONF_DEVICE, default=default_value): str}
    #     #     ),
    #     #     errors=errors,
    #     # )

    # async def async_step_add_binary_sensor(
    #     self, user_input: dict[str, Any] | None = None
    # ) -> ConfigFlowResult:
    #     """ Add a binary sensor device. """
    #     default_value = None
    #     errors = {}
    #     if user_input is not None:
    #         LOGGER.info(user_input)
    #         return None
    #     #     if await self.validate_enocean_conf(user_input):
    #     #         return self.create_enocean_entry(user_input)
    #     #     default_value = user_input[CONF_DEVICE]
    #     #     errors = {CONF_DEVICE: ERROR_INVALID_DONGLE_PATH}
    #
    #     # PLATFORM_SCHEMA = vol.Schema(
    #     #     {
    #     #         vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
    #     #         vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
    #     #         vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    #     #         vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    #     #         vol.Optional(CONF_BUTTON): vol.In([None, "AO", "AI", "BO", "BI"])
    #     #     }
    #     # )
    #
    #     return self.async_show_form(
    #         step_id="add_binary_sensor",
    #         data_schema=vol.Schema({
    #             vol.Required(CONF_ID): str,
    #             vol.Required(CONF_EEP): str,
    #             vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    #             vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    #             vol.Optional(CONF_BUTTON): vol.In(["AO", "AI", "BO", "BI"])
    #         }),
    #         errors=errors,
    #     )

    async def async_step_add_binary_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Add a binary sensor device. """
        errors = {}
        if user_input is not None:
            LOGGER.info(user_input)
            dev_id_valid = re.match(VALIDATOR_DEVICE_ID, user_input[CONF_ID])
            eep_valid = re.match(VALIDATOR_EEP, user_input[CONF_EEP])
            if dev_id_valid and eep_valid:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_ID: list( int(x, base=16) for x in dev_id_valid.groups()),
                        "device_type": Platform.BINARY_SENSOR},
                    options={CONF_EEP: list( int(x, base=16) for x in eep_valid.groups())}
                )
            if not dev_id_valid:
                errors[CONF_ID] = "device_id_not_ok"
            if not eep_valid:
                errors[CONF_EEP] = "unknown_eep"

        known_devices = [
            "nodon_SIN-2-1-01",
            "nodon_SIN-2-2-01",
            "nodon_PIR-2-1-01",
            "nodon_MSP-2-1-11",
            "nodon_STP-2-1-05",
            "nodon_STPH-2-1-05",
            "Hoppe_SecuSignal",
            "EnOcean_PTM210"
        ]
        data_schema = {
            vol.Required(CONF_ID, default=user_input[CONF_ID] if user_input else ''): cv.string,  # cv.matches_regex(VALIDATOR_DEVICE_ID),
            vol.Required(CONF_EEP, default=user_input[CONF_EEP] if user_input else "F6-10-00"): cv.string,  # cv.matches_regex(VALIDATOR_EEP),
            vol.Optional(CONF_NAME, default=user_input[CONF_NAME] if user_input else DEFAULT_NAME_WINDOW_HANDLE): cv.string,
            vol.Required('known_device'): SelectSelector(SelectSelectorConfig(options=known_devices, translation_key="known_devices"))
        }

        return self.async_show_form(
            step_id="add_binary_sensor",
            data_schema=vol.Schema(data_schema),
            errors=errors
        )

    async def async_step_add_windowhandle_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Add a binary sensor device. """
        errors = {}
        if user_input is not None:
            LOGGER.info(user_input)
            dev_id_valid = re.match(VALIDATOR_DEVICE_ID, user_input[CONF_ID])
            eep_valid = re.match(VALIDATOR_EEP, user_input[CONF_EEP])
            if dev_id_valid and eep_valid:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_ID: list( int(x, base=16) for x in dev_id_valid.groups()),
                        "device_type": SENSOR_TYPE_WINDOWHANDLE},
                    options={CONF_EEP: list( int(x, base=16) for x in eep_valid.groups())}
                )
            if not dev_id_valid:
                errors[CONF_ID] = "device_id_not_ok"
            if not eep_valid:
                errors[CONF_EEP] = "unknown_eep"

        data_schema = {
            vol.Required(CONF_ID, default=user_input[CONF_ID] if user_input else ''): cv.string,  # cv.matches_regex(VALIDATOR_DEVICE_ID),
            vol.Required(CONF_EEP, default=user_input[CONF_EEP] if user_input else "F6-10-00"): cv.string,  # cv.matches_regex(VALIDATOR_EEP),
            vol.Optional(CONF_NAME, default=user_input[CONF_NAME] if user_input else DEFAULT_NAME_WINDOW_HANDLE): cv.string,
        }

        return self.async_show_form(
            step_id="add_windowhandle_sensor",
            data_schema=vol.Schema(data_schema),
            errors=errors
        )

    async def validate_enocean_conf(self, dongle_path) -> bool:
        """Return True if the user_input contains a valid dongle path."""
        # dongle_path = user_input[CONF_DEVICE]
        return await self.hass.async_add_executor_job(EnOceanGateway.validate_path, dongle_path)

    async def create_gateway_entry(self, gateway, device):
        """Create an entry for the provided configuration."""
        # x = await self.async_set_unique_id(f"dongle_{user_input[CONF_DEVICE]}")
        # self._abort_if_unique_id_configured()

        await self.async_set_unique_id(gateway.sender_id_str, raise_on_progress=False)
        self._abort_if_unique_id_configured(updates={CONF_DEVICE: device})
        gateway.unload()
        return self.async_create_entry(
            title="EnOcean Gateway",
            data={CONF_DEVICE: device},
            description="Gateway for communicating with Encean devices."
        )
