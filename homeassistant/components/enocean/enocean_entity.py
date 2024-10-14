""" Representation of an EnOcean entity. """

import logging

import voluptuous as vol

from enocean.protocol.constants import PACKET
from enocean.utils import combine_hex
from enocean4ha_bridge import EnOceanGateway
from enocean4ha_bridge.common import EEPInfo
from homeassistant.helpers import entity_platform
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from .const import DOMAIN, LOGGER, SIGNAL_RECEIVE_MESSAGE


class EnOceanEntity(Entity):
    """ Parent class for all entities associated with the EnOcean component. """
    gateway: EnOceanGateway
    _logger = logging.getLogger(DOMAIN)

    def __init__(self, dev_id: list[int], eep: list[int]|None) -> None:
        """ Initialize the enity. """
        self.dev_id = dev_id
        self.eep = EEPInfo(*eep) if eep is not None else None

        platform = entity_platform.async_get_current_platform()
        platform.async_register_entity_service(
            name="send_cmd",
            schema={vol.Required('kw_args'): dict,},
            func="send_cmd",
        )

    async def async_added_to_hass(self):
        """ Register callbacks. """
        try:
            self.gateway: EnOceanGateway = self.hass.data[DOMAIN]
        except KeyError:
            LOGGER.warning(f"{type(self).__name__}: no gateway configured")
            return

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_RECEIVE_MESSAGE, self._message_received_callback
            )
        )

    def _message_received_callback(self, packet):
        """ Handle incoming packets. """
        if packet.sender_int == combine_hex(self.dev_id):
            self.value_changed(packet)

    def value_changed(self, packet):
        """ Update the internal state of the device when a packet arrives. """
        raise NotImplementedError

    def send_cmd(self, kw_args: dict | None=None):
        self._logger.info(f"{self.name}: send_cmd ({kw_args})")
        cmd = kw_args.pop('CMD', None)
        if not cmd:
            return

        self.gateway.send_command(
            packet_type=PACKET.RADIO_ERP1,
            rorg=self.eep.rorg,
            rorg_func=self.eep.func,
            rorg_type=self.eep.func_type,
            command=cmd,
            destination=self.dev_id,
            **kw_args
        )
