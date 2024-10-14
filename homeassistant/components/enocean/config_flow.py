"""Config flows for the ENOcean integration."""

import re
from typing import Any

import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from enocean.utils import to_hex_string
from enocean4ha_bridge import EnOceanGateway
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.valve import ValveDeviceClass
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
    CONF_MEASUREMENT_MODE, CONF_REPORT_MEASUREMENT, DEVICE_CLASS_WINDOWHANDLE,
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


class EnOceanFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle the enOcean config flows."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the EnOcean config flow."""
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

        if user_input is not None:
            dev_id_valid = re.match(VALIDATOR_DEVICE_ID, user_input[CONF_ID])
            eep_valid = re.match(VALIDATOR_EEP, user_input[CONF_EEP])
            if dev_id_valid and eep_valid:
                user_input[CONF_ID] = list( int(x, base=16) for x in dev_id_valid.groups())
                user_input[CONF_EEP] = list( int(x, base=16) for x in eep_valid.groups())
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

    async def async_step_add_device_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """ Request aaditional device information """
        errors = {}

        if user_input is not None:
            if not 'no_options_available' in user_input:
                self._user_input.update(user_input)

            result = await self.match_user_input_device_options(user_input)
            if isinstance(result, dict) and 'type' in result:
                return result
            elif isinstance(result, dict) and CONF_ENTITIES in result:
                return self.async_create_entry(title=result[CONF_NAME], data=result)
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

    async def get_device_options_schema(self):
        binary_device_classes = ['<None>',]
        binary_device_classes.extend(BinarySensorDeviceClass._member_names_)
        _binary_device_class_schema_data = {
            vol.Required(CONF_DEVICE_CLASS): SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    multiple=False,
                    options=binary_device_classes,
                    translation_key=CONF_DEVICE_CLASS,
                    sort=True
                ),
            )
        }
        sensor_device_classes = ['<None>',]
        sensor_device_classes.extend(SensorDeviceClass._member_names_)
        _sensor_device_class_schema_data = {
            vol.Required(CONF_DEVICE_CLASS): SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    multiple=False,
                    options=sensor_device_classes,
                    translation_key=CONF_DEVICE_CLASS,
                    sort=True
                ),
            )
        }
        match self._user_input[CONF_EEP]:
            case [0xD2, 0x01, _]:
                rm_options = [
                    SelectOptionDict(value='0', label="Query only"),
                    SelectOptionDict(value='1', label="Query and auto reporting"),
                ]
                ep_options = [
                    SelectOptionDict(value='0', label="Energy measurement"),
                    SelectOptionDict(value='1', label="Power measurement"),
                ]
                # rm_options = [
                #     SelectOptionDict(value='0', label="Query only"),
                #     SelectOptionDict(value='1', label="Query and auto reporting"),
                # ]
                # ep_options = [
                #     SelectOptionDict(value='0', label="Energy measurement"),
                #     SelectOptionDict(value='1', label="Power measurement"),
                # ]
                data = {
                    vol.Required(CONF_DEVICE_TYPE): vol.In([Platform.SWITCH, Platform.LIGHT]),
                    vol.Required(CONF_CHANNEL_COUNT): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
                    vol.Required(CONF_REPORT_MEASUREMENT, default='1'): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.DROPDOWN,
                            multiple=False,
                            options=rm_options,
                            translation_key=CONF_REPORT_MEASUREMENT,
                            sort=False
                        ),
                    ),
                    vol.Required(CONF_MEASUREMENT_MODE, default='1'): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.DROPDOWN,
                            multiple=False,
                            options=ep_options,
                            translation_key=CONF_MEASUREMENT_MODE,
                            sort=False
                        ),
                    ),
                    'light_options': section(
                        schema={vol.Optional(CONF_COLOR_MODE): bool},
                        options={'collapsed': False}
                    ),
                }
                return data
            case [0xA5, 0x02 | 0x04 | 0x08, _] | [0xA5, 0x07, 0x03] | [0xA5, 0x20, 0x06] | [0xF6, 0x10, 0x00]:
                return None
            case [0xF6, 0x01, 0x01] | [0xF6, 0x04, 0x01] | [0xD5, 0x00, 0x01]:
                return _binary_device_class_schema_data
            case [0xF6, 0x02, _]:
                buttons = [
                    SelectOptionDict(value="A0", label="Button A0"),
                    SelectOptionDict(value="A1", label="Button A1"),
                    SelectOptionDict(value="B0", label="Button B0"),
                    SelectOptionDict(value="B1", label="Button B1"),
                ]
                data = _binary_device_class_schema_data
                data.update({
                    vol.Required(CONF_BUTTONS_AB): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            multiple=True,
                            options=buttons,
                            translation_key=CONF_BUTTONS_AB,
                        ),
                    ),
                })
                return data
            case _:
                raise ValueError

    async def match_user_input_device_options(self, user_input):
        data = {
            CONF_NAME: self._user_input[CONF_NAME],
            CONF_ID: self._user_input[CONF_ID],
            CONF_EEP: self._user_input[CONF_EEP],
        }
        match self._user_input[CONF_EEP]:
            case [0xD2, 0x01, _]:
                data[CONF_CHANNEL_COUNT] = user_input[CONF_CHANNEL_COUNT]
                data[CONF_REPORT_MEASUREMENT] = user_input[CONF_REPORT_MEASUREMENT]
                data[CONF_MEASUREMENT_MODE] = user_input[CONF_MEASUREMENT_MODE]
                if user_input[CONF_DEVICE_TYPE] == Platform.LIGHT:
                    colormode = ColorMode.BRIGHTNESS if user_input[CONF_COLOR_MODE] else ColorMode.ONOFF
                    data[CONF_ENTITIES] = {Platform.LIGHT: [{CONF_COLOR_MODE: colormode},],}
                else:
                    data[CONF_ENTITIES] = {Platform.SWITCH: [{CONF_DEVICE_CLASS: SwitchDeviceClass.SWITCH}],}
                data[CONF_ENTITIES].update({
                    Platform.BUTTON: [
                        # {CONF_NAME: 'Query Actuator Measurement', CONF_COMMAND: {"CMD": 6}},
                        {CONF_PROFILE_SHORTCUT: "RE", CONF_CMD_OR_DIR: {"command": 5}},
                    ],
                    Platform.NUMBER: [
                        {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_PROFILE_SHORTCUT: "AOT", CONF_CMD_OR_DIR: {"command": 13}, CONF_MINIMUM: 0.0, CONF_MAXIMUM: 6553.5, CONF_STEP: 0.1, CONF_UNIT_OF_MEASUREMENT: 's'},
                        {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_PROFILE_SHORTCUT: "DOT", CONF_CMD_OR_DIR: {"command": 13}, CONF_MINIMUM: 0.0, CONF_MAXIMUM: 6553.5, CONF_STEP: 0.1, CONF_UNIT_OF_MEASUREMENT: 's'},
                        {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_PROFILE_SHORTCUT: "MAT", CONF_CMD_OR_DIR: {"command": 5}, CONF_MINIMUM: 0, CONF_MAXIMUM: 2550, CONF_STEP: 1, CONF_UNIT_OF_MEASUREMENT: 's'},
                        {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_PROFILE_SHORTCUT: "MIT", CONF_CMD_OR_DIR: {"command": 5}, CONF_MINIMUM: 0, CONF_MAXIMUM: 255, CONF_STEP: 1, CONF_UNIT_OF_MEASUREMENT: 's'},
                    ],
                    Platform.SELECT: [
                        {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_CMD_OR_DIR: {"command": 11},CONF_PROFILE_SHORTCUT: "EBM"},
                        {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_CMD_OR_DIR: {"command": 11},CONF_PROFILE_SHORTCUT: "SWT"},
                        {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_CMD_OR_DIR: {"command": 5},CONF_PROFILE_SHORTCUT: "RM", 'default': user_input[CONF_REPORT_MEASUREMENT]},
                        {CONF_ENTITY_CATEGORY: EntityCategory.CONFIG, CONF_CMD_OR_DIR: {"command": 5},CONF_PROFILE_SHORTCUT: "ep", 'default': user_input[CONF_MEASUREMENT_MODE]},
                    ],
                })
            case [0xA5, 0x02, _]:
                data[CONF_ENTITIES] = {
                    Platform.SENSOR: [{CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE}],
                }
            case [0xA5, 0x04, _]:
                data[CONF_ENTITIES] = {
                    Platform.SENSOR: [
                        {CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
                        {CONF_DEVICE_CLASS: SensorDeviceClass.HUMIDITY}
                    ],
                }
            case [0xA5, 0x07, 0x03]:
                data[CONF_ENTITIES] = {
                    Platform.SENSOR: [{CONF_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE}],
                    Platform.BINARY_SENSOR: [{CONF_DEVICE_CLASS: BinarySensorDeviceClass.MOTION}]
                }
            case [0xA5, 0x08, _]:
                data[CONF_ENTITIES] = {
                    Platform.SENSOR: [
                        {CONF_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE},
                        {CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
                    ],
                    Platform.BINARY_SENSOR: [
                        {CONF_DEVICE_CLASS: BinarySensorDeviceClass.MOTION},
                        {CONF_DEVICE_CLASS: BinarySensorDeviceClass.OCCUPANCY},
                    ]
                }
            case [0xA5, 0x20, 0x06]:
                data[CONF_ENTITIES] = {
                    Platform.VALVE: [
                        {CONF_DEVICE_CLASS: ValveDeviceClass.WATER},
                    ],
                    Platform.SENSOR: [
                        {CONF_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
                        {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_PROFILE_SHORTCUT: "LOM"},
                        {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_PROFILE_SHORTCUT: "LO"},
                        {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_PROFILE_SHORTCUT: "TSL"},
                        {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_PROFILE_SHORTCUT: "ENIE"},
                        {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_PROFILE_SHORTCUT: "ES"},
                        {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_PROFILE_SHORTCUT: "RCE"},
                        {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_PROFILE_SHORTCUT: "RSS"},
                        {CONF_DEVICE_CLASS: DEVICE_CLASS_PROFILE_SHORTCUT, CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC, CONF_PROFILE_SHORTCUT: "ACO"},
                    ],
                    Platform.BINARY_SENSOR: [
                        {CONF_DEVICE_CLASS: BinarySensorDeviceClass.WINDOW, CONF_PROFILE_SHORTCUT: "DWO"},
                    ],
                }
            case[0xF6, 0x01, 0x01] | [0xF6, 0x04, 0x01] | [0xD5, 0x00, 0x01]:
                data[CONF_ENTITIES] = {
                    Platform.BINARY_SENSOR: [{CONF_DEVICE_CLASS: user_input[CONF_DEVICE_CLASS]}]
                }
            case [0xF6, 0x02, _]:
                data[CONF_ENTITIES] = {
                    Platform.BINARY_SENSOR: [
                        {CONF_DEVICE_CLASS: None, CONF_BUTTON: "A0", CONF_ENABLED: "A0" in user_input[CONF_BUTTONS_AB]},
                        {CONF_DEVICE_CLASS: None, CONF_BUTTON: "A1", CONF_ENABLED: "A1" in user_input[CONF_BUTTONS_AB]},
                        {CONF_DEVICE_CLASS: None, CONF_BUTTON: "B0", CONF_ENABLED: "B0" in user_input[CONF_BUTTONS_AB]},
                        {CONF_DEVICE_CLASS: None, CONF_BUTTON: "B1", CONF_ENABLED: "B1" in user_input[CONF_BUTTONS_AB]},
                    ],
                }
            case [0xF6, 0x10, 0x00]:
                data[CONF_ENTITIES] = {
                    Platform.SENSOR: [{CONF_DEVICE_CLASS: DEVICE_CLASS_WINDOWHANDLE}, ],
                }
            case _:
                return self.async_abort(reason="uups, something is missing here")
        return data

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
