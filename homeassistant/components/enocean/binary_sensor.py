"""Support for EnOcean binary sensors."""

from __future__ import annotations

from enocean.utils import combine_hex
import voluptuous as vol

from enocean4ha_bridge import EnOceanGateway, EO4HABinarySensor
from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA as BINARY_SENSOR_PLATFORM_SCHEMA,
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription
)
from homeassistant.const import CONF_DEVICE_CLASS, CONF_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import CONF_EEP, DATA_ENOCEAN, ENOCEAN_DONGLE, LOGGER, CONF_BUTTON, DOMAIN

from .enocean_entity import EnOceanEntity
from . import EnOceanConfigEntry
from ...helpers.device_registry import DeviceInfo
from ...helpers import device_registry as dr


DEFAULT_NAME = "EnOcean binary sensor"
DEPENDENCIES = ["enocean"]
EVENT_BUTTON_PRESSED = "button_pressed"

PLATFORM_SCHEMA = BINARY_SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_EEP): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Required(CONF_BUTTON): vol.In([None, "AO", "AI", "BO", "BI"])
    }
)



async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    LOGGER.info(f"binary_sensor.async_setup_entry: {config_entry=}")
    # if 'device_type' in config_entry.data:
    #     if config_entry.data['device_type'] == Platform.BINARY_SENSOR:
    #         description = BinarySensorEntityDescription(
    #             key=Platform.BINARY_SENSOR,
    #             name="BinarySensor",
    #             translation_key="binary_sensor",
    #             unique_id=f"{combine_hex(dev_id)}-{config_entry.data[CONF_ID]}-{config_entry.data[]}",
    #         )
    #         sensor = sensors[config_entry.data['device_type']][0]
    #         sensor_description = sensors[config_entry.data['device_type']][1]
    #         async_add_entities([EnOceanBinarySensor(config_entry, sensor_description)])


    # eo_gateway = config_entry.runtime_data


    # new_devices = []
    # for roller in hub.rollers:
    #     new_devices.append(BatterySensor(roller))
    #     new_devices.append(IlluminanceSensor(roller))
    # if new_devices:
    #     async_add_entities(new_devices)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Binary Sensor platform for EnOcean."""
    dev_id: list[int] = config[CONF_ID]
    dev_name: str = config[CONF_NAME]
    device_class: BinarySensorDeviceClass | None = config.get(CONF_DEVICE_CLASS)
    eep: list[int] = config[CONF_EEP]
    button: str | None = config.get(CONF_BUTTON)

    add_entities([EnOceanBinarySensor(dev_id, eep, dev_name, device_class, button, config)])


class EnOceanBinarySensor(EnOceanEntity, BinarySensorEntity):
    """Representation of EnOcean binary sensors such as wall switches.

    Supported EEPs (EnOcean Equipment Profiles):
    - F6-02-01 (Light and Blind Control - Application Style 2)
    - F6-02-02 (Light and Blind Control - Application Style 1)
    """

    def __init__(
        self,
        dev_id: list[int],
        eep: list[int],
        dev_name: str,
        device_class: BinarySensorDeviceClass | None,
        button: str | None,
        config
    ) -> None:
        """Initialize the EnOcean binary sensor."""
        super().__init__(dev_id, eep)
        self._attr_device_class = device_class
        self.which = -1
        self.onoff = -1
        self.button = button
        self._attr_unique_id = f"{combine_hex(dev_id)}-{device_class}-button_{button}"
        self._attr_name = dev_name
        self.eo_sensor = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, combine_hex(self.dev_id))},
            manufacturer="Signify",
            suggested_area="Kitchen",
            name=self.name,
            model="self.modelname",
            model_id="self.modelid",
            sw_version="self.swversion",
            hw_version="self.hwversion",
        )

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        # device_registry = dr.async_get(self.hass)
        # device_registry.async_get_or_create(
        #     config_entry_id=self.entity_id,
        #     #connections={(dr.CONNECTION_NETWORK_MAC, config.mac)},
        #     identifiers={(DOMAIN, combine_hex(self.dev_id))},
        #     manufacturer="Signify",
        #     suggested_area="Kitchen",
        #     name=self.name,
        #     model="self.modelname",
        #     model_id="self.modelid",
        #     sw_version="self.swversion",
        #     hw_version="self.hwversion",
        # )
        try:
            dongle: EnOceanGateway = self.hass.data[DATA_ENOCEAN]
        except KeyError:
            LOGGER.warning("binary_sensor: no gateway configured")
            return
        self.eo_sensor = EO4HABinarySensor(gateway=dongle, dev_id=self.dev_id, eep=self.eep, button=self.button, loglevel=LOGGER.getEffectiveLevel())
        await super().async_added_to_hass()

    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, combine_hex(self.dev_id))},
            manufacturer="Signify",
            suggested_area="Kitchen",
            name=self.name,
            model="self.modelname",
            model_id="self.modelid",
            sw_version="self.swversion",
            hw_version="self.hwversion",
        )

    def value_changed(self, packet):
        """Fire an event with the data that have changed."""
        result = self.eo_sensor.parse_packet(
            packet=packet,
            actual_which=self.which,
            actual_onoff=self.onoff
        )
        if "legacy" in result:
            pushed, self.which, self.onoff = result["legacy"]
            if pushed != self._attr_state:
                self._attr_state = pushed
                self.schedule_update_ha_state()

            self.hass.bus.fire(
                EVENT_BUTTON_PRESSED,
                {
                    "id": self.dev_id,
                    "pushed": pushed,
                    "which": self.which,
                    "onoff": self.onoff,
                },
            )
        else:
            if result["status"] != self._attr_is_on:
                self._attr_is_on = result["status"]
                self.schedule_update_ha_state()