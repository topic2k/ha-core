"""Support for EnOcean devices."""

import homeassistant.helpers.config_validation as cv

from enocean4ha_bridge import EnOceanGateway
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.util.hass_dict import HassKey
from .const import DOMAIN, LOGGER, CONF_GATEWAY


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
]


type EnOceanConfigEntry = ConfigEntry[EnOceanGateway]

ENOCEAN_KEY: HassKey[EnOceanGateway] = HassKey(DOMAIN)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config_entry: EnOceanConfigEntry) -> bool:
    """Set up the EnOcean component."""
    # # support for text-based configuration (legacy)
    # if DOMAIN not in config_entry:
    #     return True
    #
    # if hass.config_entries.async_entries(DOMAIN):
    #     # We can only have one dongle. If there is already one in the config,
    #     # there is no need to import the yaml based config.
    #     return True
    #
    # hass.async_create_task(
    #     hass.config_entries.flow.async_init(
    #         DOMAIN, context={"source": SOURCE_IMPORT}, data=config_entry[DOMAIN]
    #     )
    # )

    # hass.data[ENOCEAN_KEY] = EnOceanGateway(hass)
    # await hass.data[ENOCEAN_KEY].async_request_refresh()
    # LOGGER.info(f"init.async_setup: {config_entry=}")
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: EnOceanConfigEntry) -> bool:
    """Set up an EnOcean dongle for the given entry."""
    # LOGGER.info(f"init.async_setup_entry")
    if CONF_GATEWAY in config_entry.data:
        hass.data.setdefault(DOMAIN, {})
        gateway = EnOceanGateway(hass, config_entry.data[CONF_GATEWAY], LOGGER.getEffectiveLevel())
        await gateway.load()
        hass.data[DOMAIN] = gateway
        # Store an instance of the "connecting" class that does the work of speaking
        # with your actual devices.
        config_entry.runtime_data = gateway

        dr = device_registry.async_get(hass)
        dev = dr.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={('serial', config_entry.data[CONF_GATEWAY])},
            identifiers={(DOMAIN, gateway.sender_id_str)},
            manufacturer=gateway.manufacturer,
            name="EnOcean Gateway",
            model=gateway.product,
            model_id=f"Base ID: {gateway.sender_id_str}",
        )

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Reload entry when its updated.
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: EnOceanConfigEntry) -> bool:
    """Unload ENOcean config entry."""
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


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(config_entry.entry_id)
