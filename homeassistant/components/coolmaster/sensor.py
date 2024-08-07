"""Sensor platform for CoolMasterNet integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DATA_INFO, DOMAIN
from .entity import CoolmasterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CoolMasterNet sensor platform."""
    info = hass.data[DOMAIN][config_entry.entry_id][DATA_INFO]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        CoolmasterCleanFilter(coordinator, unit_id, info)
        for unit_id in coordinator.data
    )


class CoolmasterCleanFilter(CoolmasterEntity, SensorEntity):
    """Representation of a unit's error code."""

    _attr_has_entity_name = True
    entity_description = SensorEntityDescription(
        key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Error code",
        icon="mdi:alert",
    )

    @property
    def native_value(self) -> str:
        """Return the error code or OK."""
        return self._unit.error_code or "OK"
