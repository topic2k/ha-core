""" Support for EnOcean valves. """
from dataclasses import dataclass

from enocean.protocol.packet import RadioPacket
from enocean.utils import to_hex_string
from enocean4ha_bridge import EO4HAValve

from homeassistant.components.valve import ValveDeviceClass, ValveEntity, ValveEntityDescription, ValveEntityFeature
from homeassistant.const import CONF_ENTITIES, CONF_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EnOceanConfigEntry
from .const import CONF_EEP, CONF_GATEWAY, DOMAIN
from .enocean_entity import EnOceanEntity


@dataclass(frozen=True, kw_only=True)
class EnOceanValveEntityDescription(ValveEntityDescription):
    """ Describes EnOcean valve entity. """
    unique_id: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EnOceanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """ Set up the valve platform. """

    if CONF_GATEWAY in config_entry.data:
        return

    if not config_entry.data[CONF_ENTITIES].get(Platform.VALVE):
        return

    entities = []
    entity_config = dict(config_entry.data)
    dev_id_str = to_hex_string(entity_config[CONF_ID])

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN,dev_id_str)},
        name=config_entry.title,
        model=f"Base ID: {dev_id_str}",
        model_id=f"EEP: {to_hex_string(entity_config[CONF_EEP], sep='-')}",
    )

    for entity_options in entity_config[CONF_ENTITIES][Platform.VALVE]:
        description = EnOceanValveEntityDescription(
            key=Platform.VALVE,
            device_class=ValveDeviceClass.WATER,
            reports_position=True,
            name=f"{entity_config[CONF_NAME]} {Platform.VALVE}",
            unique_id=f"{dev_id_str}-valve",
        )
        entities.append(EnOceanValve(entity_config, description, entity_options))

    async_add_entities(entities)


class EnOceanValve(EO4HAValve, EnOceanEntity, ValveEntity):
    """ Representation of an EnOcean valve device. """

    def __init__(self, entity_config: dict, description: EnOceanValveEntityDescription, entity_options: dict) -> None:
        """ Initialize the EnOcean valve device. """
        dev_id = entity_config[CONF_ID]
        dev_id_str = to_hex_string(dev_id)
        super().__init__(dev_id, entity_config[CONF_EEP])
        self._attr_unique_id = description.unique_id
        self._attr_device_info: DeviceInfo = DeviceInfo(identifiers={(DOMAIN, dev_id_str)},)
        self.entity_description  = description
        self._attr_supported_features: ValveEntityFeature = ValveEntityFeature.SET_POSITION
        self._logger.debug(f"Initialized {type(self).__name__}, ID {dev_id_str}, {repr(self.eep)}")

    async def async_set_valve_position(self, position: int) -> None:
        """ Move the valve to a specific position. """
        pass

    def value_changed(self, packet: RadioPacket) -> None:
        """ Update the internal state of the valve. """
        result = self.parse_packet(packet)
        if not result:
            return
        if "status" in result:
            if result["status"] != self._attr_current_valve_position:
                self._attr_current_valve_position = result["status"]
                self._attr_extra_state_attributes = result.get('extra_state_attr', {})
                self.schedule_update_ha_state()


