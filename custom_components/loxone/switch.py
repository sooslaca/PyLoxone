"""
Loxone Switches

For more details about this component, please refer to the documentation at
https://github.com/JoDehli/PyLoxone
"""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import LoxoneEntity
from .const import SENDDOMAIN
from .helpers import (add_room_and_cat_to_value_values, get_all,
                      get_or_create_device)
from .miniserver import get_miniserver_from_hass

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Loxone Switch."""
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry."""
    miniserver = get_miniserver_from_hass(hass)
    loxconfig = miniserver.lox_config.json
    entities = []

    for switch_entity in get_all(loxconfig, ["Switch", "TimedSwitch", "Intercom"]):

        switch_entity = add_room_and_cat_to_value_values(loxconfig, switch_entity)

        if switch_entity["type"] in ["Switch"]:
            new_switch = LoxoneSwitch(**switch_entity)
            entities.append(new_switch)

        elif switch_entity["type"] == "TimedSwitch":
            new_switch = LoxoneTimedSwitch(**switch_entity)
            entities.append(new_switch)

        elif switch_entity["type"] == "Intercom":
            if "subControls" in switch_entity:
                for sub_name in switch_entity["subControls"]:
                    subcontol = switch_entity["subControls"][sub_name]

                    _ = subcontol
                    _ = add_room_and_cat_to_value_values(loxconfig, _)
                    _.update(
                        {
                            "name": "{} - {}".format(
                                switch_entity["name"], subcontol["name"]
                            )
                        }
                    )

                    new_switch = LoxoneIntercomSubControl(**_)
                    entities.append(new_switch)

    async_add_entities(entities)


class LoxoneTimedSwitch(LoxoneEntity, SwitchEntity):
    """Representation of a loxone switch"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._icon = None
        self._assumed = False
        self._state = STATE_UNKNOWN
        self._delay_remain = 0.0
        self._delay_time_total = 0.0

        if "deactivationDelay" in self.states:
            self._deactivation_delay = self.states["deactivationDelay"]
        else:
            self._deactivation_delay = ""

        if "deactivationDelayTotal" in self.states:
            self._deactivation_delay_total = self.states["deactivationDelayTotal"]
        else:
            self._deactivation_delay_total = ""

        self.type = "TimeSwitch"
        self._attr_device_info = get_or_create_device(
            self.unique_id, self.name, self.type, self.room
        )

    @property
    def should_poll(self):
        """No polling needed for a demo switch."""
        return False

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return self._icon

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return self._assumed

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.hass.bus.fire(SENDDOMAIN, dict(uuid=self.uuidAction, value="pulse"))
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.hass.bus.fire(SENDDOMAIN, dict(uuid=self.uuidAction, value="off"))
        self._state = False
        self.schedule_update_ha_state()

    async def event_handler(self, e):
        should_update = False
        if self._deactivation_delay in e.data:
            if e.data[self._deactivation_delay] == 0.0:
                self._state = False
            else:
                self._state = True

            self._delay_remain = int(e.data[self._deactivation_delay])
            should_update = True

        if self._deactivation_delay_total in e.data:
            self._delay_time_total = int(e.data[self._deactivation_delay_total])
            should_update = True

        if should_update:
            self.async_schedule_update_ha_state()

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes.

        Implemented by platform classes.
        """
        state_dict = {
            "uuid": self.uuidAction,
            "room": self.room,
            "category": self.cat,
            "device_type": self.type,
            "platform": "loxone",
        }

        if self._state == 0.0:
            state_dict.update({"delay_time_total": str(self._delay_time_total)})

        else:
            state_dict.update(
                {
                    "delay": str(self._delay_remain),
                    "delay_time_total": str(self._delay_time_total),
                }
            )
        return state_dict


class LoxoneSwitch(LoxoneEntity, SwitchEntity):
    """Representation of a loxone switch"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        """Initialize the Loxone switch."""
        self._state = STATE_UNKNOWN
        self._icon = None
        self._assumed = False

        self.type = "Switch"
        self._attr_device_info = get_or_create_device(
            self.unique_id, self.name, self.type, self.room
        )

    @property
    def should_poll(self):
        """No polling needed for a demo switch."""
        return False

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return self._icon

    @property
    def assumed_state(self):
        """Return if the state is based on assumptions."""
        return self._assumed

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        if not self._state:
            self.hass.bus.fire(SENDDOMAIN, dict(uuid=self.uuidAction, value="On"))
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        if self._state:
            self.hass.bus.fire(SENDDOMAIN, dict(uuid=self.uuidAction, value="Off"))
            self._state = False
            self.schedule_update_ha_state()

    async def event_handler(self, event):
        if self.uuidAction in event.data or self.states["active"] in event.data:
            if self.states["active"] in event.data:
                self._state = event.data[self.states["active"]]
            self.async_schedule_update_ha_state()

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes.

        Implemented by platform classes.
        """
        return {
            "uuid": self.uuidAction,
            "state_uuid": self.states["active"],
            "room": self.room,
            "category": self.cat,
            "device_type": self.type,
            "platform": "loxone",
        }


class LoxoneIntercomSubControl(LoxoneSwitch):
    def __init__(self, **kwargs):
        LoxoneSwitch.__init__(self, **kwargs)

        self.type = "IntercomSubControl"
        self._attr_device_info = get_or_create_device(
            self.unique_id, self.name, self.type, self.room
        )

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.hass.bus.fire(SENDDOMAIN, dict(uuid=self.uuidAction, value="on"))
        self._state = True
        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes.

        Implemented by platform classes.
        """
        return {
            "uuid": self.uuidAction,
            "state_uuid": self.states["active"],
            "room": self.room,
            "category": self.cat,
            "device_type": self.type,
            "platform": "loxone",
        }
