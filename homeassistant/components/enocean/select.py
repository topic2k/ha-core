""" Support for EnOcean select entities. """

from dataclasses import dataclass

import voluptuous as vol

from enocean.protocol.eep import EEPSoup
from enocean.utils import to_hex_string
from enocean4ha_bridge import EO4HASelect

from homeassistant.components.select import (
    PLATFORM_SCHEMA as SELECT_PLATFORM_SCHEMA,
    SelectEntity,
    SelectEntityDescription
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_ENTITIES,
    CONF_ENTITY_CATEGORY,
    CONF_ID,
    CONF_NAME,
    EntityCategory,
    Platform
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (config_validation as cv, device_registry as dr)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import EnOceanConfigEntry
from .const import (
    CONF_CHANNEL,
    CONF_CHANNEL_COUNT,
    CONF_CMD_OR_DIR, CONF_EEP,
    CONF_GATEWAY,
    CONF_MEASUREMENT_MODE, CONF_PROFILE_SHORTCUT,
    CONF_REPORT_MEASUREMENT, CONF_SELECT_OPTIONS,
    DEVICE_CLASS_PROFILE_SHORTCUT,
    DOMAIN,
)
from .enocean_entity import EnOceanEntity

DEFAULT_NAME = "EnOcean select"


PLATFORM_SCHEMA = SELECT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): cv.string,
    }
)

@dataclass(frozen=True, kw_only=True)
class EnOceanSelectEntityDescription(SelectEntityDescription):
    """ Describes EnOcean sensor entity. """
    unique_id: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """ Set up select based on a config entry. """

    if CONF_GATEWAY in config_entry.data:
        return

    if not config_entry.data[CONF_ENTITIES].get(Platform.SELECT):
        return

    entities = []
    entity_config = dict(config_entry.data)
    dev_id_str = to_hex_string(entity_config[CONF_ID])

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, dev_id_str)},
        name=config_entry.title,
        model=f"Base ID: {dev_id_str}",
        model_id=f"EEP: {to_hex_string(entity_config[CONF_EEP], sep='-')}",
    )

    for entity_options in entity_config[CONF_ENTITIES][Platform.SELECT]:
        if CONF_CHANNEL_COUNT in entity_config:
            profile = EEPSoup.find_profile(*entity_config[CONF_EEP], **entity_options[CONF_CMD_OR_DIR])
            child = profile.findChild(shortcut=entity_options[CONF_PROFILE_SHORTCUT])
            name = child["description"]
            options_from_eep = child.find_all('item')
            options = {option["description"]: int(option["value"]) for option in options_from_eep}
            entity_options[CONF_SELECT_OPTIONS] = options
            category = entity_options.get(CONF_ENTITY_CATEGORY, None)
            for channel in range(entity_config[CONF_CHANNEL_COUNT]):
                entity_options[CONF_CHANNEL] = channel
                description = EnOceanSelectEntityDescription(
                    device_class=DEVICE_CLASS_PROFILE_SHORTCUT,
                    entity_category=EntityCategory(category) if category else None,
                    key=f"{dev_id_str}-shortcut-{entity_options[CONF_PROFILE_SHORTCUT]}-channel_{channel}",
                    name=f"{entity_config[CONF_NAME]} {name} Channel {channel}",
                    options=list(options.keys()),
                    unique_id=f"{dev_id_str}-shortcut-{entity_options[CONF_PROFILE_SHORTCUT]}-channel_{channel}",
                )
                entities.append(EnOceanSelectEntity(entity_config, description, entity_options))
        else:
            profile = EEPSoup.find_profile(*entity_config[CONF_EEP], command=11)
            child = profile.findChild(shortcut=entity_options[CONF_PROFILE_SHORTCUT])
            name = child["description"]
            options_from_eep = child.find_all('item')
            options = {option["description"]: option["value"] for option in options_from_eep}
            entity_options[CONF_SELECT_OPTIONS] = options
            category = entity_options.get(CONF_ENTITY_CATEGORY, None)
            description = EnOceanSelectEntityDescription(
                device_class=DEVICE_CLASS_PROFILE_SHORTCUT,
                entity_category=EntityCategory(category) if category else None,
                key=f"{dev_id_str}-shortcut-{entity_options[CONF_PROFILE_SHORTCUT]}",
                name=f"{entity_config[CONF_NAME]} {name}",
                options=list(options.keys()),
                unique_id=f"{dev_id_str}-shortcut-{entity_options[CONF_PROFILE_SHORTCUT]}",
            )
            entities.append(EnOceanSelectEntity(entity_config, description, entity_options))

    async_add_entities(entities)


async def async_setup_platform(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """ Set up an EnOcean sensor device. """
    dev_id: list[int] = config_entry[CONF_ID]
    dev_name: str = config_entry[CONF_NAME]
    eep: list[int] = config_entry[CONF_EEP]
    sensor_type: str = config_entry[CONF_DEVICE_CLASS]
    dev_id_str = to_hex_string(dev_id)

    entities = []
    async_add_entities(entities)


class EnOceanSelectEntity(EO4HASelect, EnOceanEntity, SelectEntity):
    """ Representation of an EnOcean select entity. """
    _attr_current_option: str | None = None

    def __init__(
            self,
            entity_config: dict,
            description: EnOceanSelectEntityDescription,
            entity_options: dict
    ) -> None:
        """ Initialize the EnOcean select device. """
        super().__init__(entity_config[CONF_ID], entity_config[CONF_EEP])
        dev_id_str = to_hex_string(self.dev_id)
        self.select_options_dict = entity_options.get(CONF_SELECT_OPTIONS, {})
        self.shortcut = entity_options.get(CONF_PROFILE_SHORTCUT)
        self.channel = entity_options.get(CONF_CHANNEL)
        self.report_measurement = entity_config[CONF_REPORT_MEASUREMENT]
        self.measurement_mode = entity_config[CONF_MEASUREMENT_MODE]
        self._attr_unique_id = description.unique_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_id_str)})
        self.entity_description = description
        self._logger.info(f"Initialized {type(self).__name__}, ID {dev_id_str}, {repr(self.eep)}")

    async def async_added_to_hass(self) -> None:
        """ Call when entity about to be added to hass. """
        await super().async_added_to_hass()
        await self.set_measurement(self.report_measurement, self.measurement_mode)
        await self.async_query_status()
        await self.async_query_external_interface_settings()
        await self.async_query_measurement()

    def value_changed(self, packet):
        """ Update the internal state of the sensor. """
        result: dict|None = self.parse_packet(packet)
        if not result:
            return
        if "status" in result:
            if result["status"] != self._attr_current_option:
                self._attr_current_option = result["status"]
                self._attr_extra_state_attributes = result.get('extra_state_attr', {})
                self.schedule_update_ha_state()
