""" Platform for button integration. """

from dataclasses import dataclass

from enocean.protocol.eep import EEPSoup
from enocean.utils import to_hex_string
from enocean4ha_bridge import EnOceanGateway

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import CONF_ENTITIES, CONF_ENTITY_CATEGORY, CONF_ID, CONF_NAME, EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EnOceanConfigEntry
from .const import (
    CONF_CHANNEL,
    CONF_CHANNEL_COUNT,
    CONF_CMD_OR_DIR,
    CONF_EEP,
    CONF_GATEWAY,
    CONF_PROFILE_SHORTCUT,
    DEVICE_CLASS_PROFILE_SHORTCUT,
    DOMAIN, PLATFORMS,
)
from .enocean_entity import EnOceanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """ Set up the button platform. """

    if CONF_GATEWAY in config_entry.data:
        return

    if not config_entry.data[CONF_ENTITIES].get(Platform.BUTTON):
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

    for entity_options in entity_config[CONF_ENTITIES][Platform.BUTTON]:
        for channel in range(entity_config[CONF_CHANNEL_COUNT]):
            profile = EEPSoup.find_profile(*entity_config[CONF_EEP], **entity_options[CONF_CMD_OR_DIR])
            name = profile.findChild(shortcut=entity_options[CONF_PROFILE_SHORTCUT])["description"]
            category = entity_options.get(CONF_ENTITY_CATEGORY)
            description = EnOceanButtonEntityDescription(
                key=Platform.BUTTON,
                device_class=DEVICE_CLASS_PROFILE_SHORTCUT,
                entity_category=EntityCategory(category) if category else None,
                name=f"{entity_config[CONF_NAME]} {name} {CONF_CHANNEL} {channel}",
                unique_id=f"{dev_id_str}-profile_shortcut-{entity_options[CONF_PROFILE_SHORTCUT]}-{Platform.BUTTON}-channel_{channel}"
            )
            entity_options[CONF_CHANNEL] = channel
            entities.append(EnOceanButton(entity_config, description, entity_options))

    async_add_entities(entities)
    await hass.config_entries.async_forward_entry_unload(config_entry, Platform.BUTTON)

async def async_unload_entry(hass: HomeAssistant, config_entry: EnOceanConfigEntry) -> bool:
    """Unload ENOcean config entry."""
    print("UNLOAD BUTTON")
    # enocean_dongle = hass.data[DOMAIN]
    # enocean_dongle.unload()
    # hass.data.pop(DOMAIN)

    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    if unload_ok := await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS):
        if hasattr(config_entry, 'runtime_data'):
            gateway: EnOceanGateway = config_entry.runtime_data
            unload_ok = gateway.unload()
            # if unload_ok := gateway.unload():
            #     hass.data.pop(DOMAIN)

    return unload_ok


@dataclass(frozen=True, kw_only=True)
class EnOceanButtonEntityDescription(ButtonEntityDescription):
    """ Describes EnOcean button entity. """
    unique_id: str


class EnOceanButton(EnOceanEntity, ButtonEntity):
    """ Representation of an EnOcean button."""

    def __init__(self, entity_config: dict, description: EnOceanButtonEntityDescription, entity_options: dict):
        dev_id = entity_config[CONF_ID]
        dev_id_str = to_hex_string(dev_id)
        super().__init__(dev_id, entity_config[CONF_EEP])
        self._attr_unique_id = description.unique_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, dev_id_str)},)
        self.entity_description = description
        self.channel = entity_options.get(CONF_CHANNEL)

    def press(self) -> None:
        """ Press the button. """
        self._logger.info(f"BUTTON {self.name} pressed")

    def value_changed(self, packet):
        """ Update the internal state of the device when a packet arrives. """
        pass
