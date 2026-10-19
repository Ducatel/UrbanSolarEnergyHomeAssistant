"""Sensor entities for Urban Solar production and valuation.

This module defines the sensor entities exposed by the Urban Solar integration.
It includes sensors for:
- Total production (kWh)
- Current wallet balance (€)
- Estimated total value (€)
- Current month production (kWh)
- Current purchase price (€/kWh)
"""

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PDL, DOMAIN
from .coordinator import UrbanSolarDataUpdateCoordinator

# Logger for sensor-related operations
_LOGGER = logging.getLogger(__name__)


class UrbanSolarSensorDescription(SensorEntityDescription):
    """Description class for Urban Solar sensor entities.
    
    This class extends SensorEntityDescription to define the metadata
    for each sensor (e.g., name, unit of measurement, device class).
    
    Note: This is a simple subclass with no additional attributes.
    All sensor-specific logic (e.g., value calculation) is handled in the
    UrbanSolarSensor class.
    """


# Tuple of all sensor descriptions for this integration
# List of all sensor descriptions for the Urban Solar integration
DESCRIPTIONS: tuple[UrbanSolarSensorDescription, ...] = (
    # Total production sensor (kWh)
    UrbanSolarSensorDescription(
        key="total_production",
        name="Production totale",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        entity_registry_enabled_default=True,
        entity_registry_visible_default=True,
    ),
    # Current wallet balance sensor (€)
    UrbanSolarSensorDescription(
        key="wallet",
        name="Cagnotte actuelle",
        native_unit_of_measurement="€",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        entity_registry_enabled_default=True,
        entity_registry_visible_default=True,
    ),
    # Estimated total value sensor (€)
    UrbanSolarSensorDescription(
        key="estimated_value",
        name="Valeur estimée totale",
        native_unit_of_measurement="€",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        entity_registry_enabled_default=False,
        entity_registry_visible_default=False,
    ),
    # Current month production sensor (kWh)
    UrbanSolarSensorDescription(
        key="current_month_production",
        name="Production du mois",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        entity_registry_enabled_default=True,
        entity_registry_visible_default=True,
    ),
    # Current purchase price sensor (€/kWh)
    UrbanSolarSensorDescription(
        key="current_price",
        name="Prix d'achat actuel",
        native_unit_of_measurement="€/kWh",
        entity_registry_enabled_default=True,
        entity_registry_visible_default=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Urban Solar sensor entities.
    
    This function is called by Home Assistant to initialize the sensor platform
    for this integration. It creates one sensor entity for each description in DESCRIPTIONS.
    
    Args:
        hass: Home Assistant core instance.
        entry: Configuration entry for this integration.
        async_add_entities: Callback to add entities to Home Assistant.
    """
    _LOGGER.debug("Starting async_setup_entry for sensor platform (entry_id: %s)", entry.entry_id)
    
    try:
        # Retrieve the coordinator stored during integration setup
        coordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.debug("Coordinator found for entry_id: %s", entry.entry_id)
    except KeyError:
        # This should not happen if setup was successful, but handle it gracefully
        _LOGGER.error("Coordinator NOT FOUND in hass.data for entry_id: %s. Available keys: %s", 
                      entry.entry_id, list(hass.data.get(DOMAIN, {}).keys()))
        return
    
    _LOGGER.debug("Creating sensor entities for %d descriptions", len(DESCRIPTIONS))
    # Create a sensor entity for each description
    entities = [UrbanSolarSensor(coordinator, entry, description) for description in DESCRIPTIONS]
    _LOGGER.debug("Created %d sensor entities: %s", len(entities), [e.unique_id for e in entities])
    
    # Add all entities to Home Assistant
    async_add_entities(entities)
    _LOGGER.debug("Sensor entities added to Home Assistant")


class UrbanSolarSensor(CoordinatorEntity[UrbanSolarDataUpdateCoordinator], SensorEntity):
    """Sensor entity for Urban Solar data.
    
    This class represents a single sensor entity in Home Assistant, backed by
    the UrbanSolarDataUpdateCoordinator. It dynamically calculates its value
    based on the data fetched from the Urban Solar API.
    
    Attributes:
        _attr_has_entity_name: If True, the entity name is derived from the device name.
        entity_description: Metadata for this sensor (name, unit, device class, etc.).
        _attr_unique_id: Unique identifier for this entity.
        _attr_device_info: Device information (manufacturer, model, etc.).
        _attr_key: Key used to identify which value to extract from coordinator.data.
    """

    _attr_has_entity_name = True  # Use the device name as the entity name

    def __init__(
        self,
        coordinator: UrbanSolarDataUpdateCoordinator,
        entry: ConfigEntry,
        description: UrbanSolarSensorDescription,
    ) -> None:
        """Initialize the Urban Solar sensor entity.
        
        Args:
            coordinator: Coordinator that manages data updates.
            entry: Configuration entry for this integration.
            description: Sensor description (metadata).
        """
        _LOGGER.debug("Initializing UrbanSolarSensor for key: %s, entry_id: %s", description.key, entry.entry_id)
        super().__init__(coordinator)
        self.entity_description = description
        
        # Set a unique ID for this entity (format: <entry_unique_id>_<sensor_key>)
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        
        # Set device information (shown in the device registry)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},  # Unique identifier for the device
            name=f"Urban Solar {entry.data[CONF_PDL]}",  # Device name (includes PDL)
            manufacturer="Urban Solar Energy",      # Manufacturer name
            model="Customer portal",                 # Device model
        )
        
        # Store the key to identify which value to extract from coordinator.data
        self._attr_key = description.key
        _LOGGER.debug("UrbanSolarSensor initialized: unique_id=%s, name=%s", self.unique_id, self.name)

    @property
    def native_value(self) -> float | None:
        """Return the sensor's current value.
        
        This property dynamically calculates the sensor's value based on the
        data fetched from the Urban Solar API. The value is determined by the
        sensor's key (stored in self._attr_key).
        
        Returns:
            float | None: The current value of the sensor, or None if data is unavailable.
        """
        try:
            data = self.coordinator.data
            
            # Extract the value based on the sensor's key
            if self._attr_key == "total_production":
                # Total production in kWh (from all-time data)
                return data["total"]["production_kwh"]
            elif self._attr_key == "wallet":
                # Current wallet balance in € (unbilled volumes only)
                return data["wallet_eur"]
            elif self._attr_key == "estimated_value":
                # Estimated total value in € (all production * price)
                return data["total"]["value_eur"]
            elif self._attr_key == "current_month_production":
                # Production for the current month in kWh (or None if no data)
                return data["current_month"]["production_kwh"] if data["current_month"] else None
            elif self._attr_key == "current_price":
                # Current purchase price in €/kWh (or None if no data)
                return data["current_month"]["price_eur_per_kwh"] if data["current_month"] else None
            
            # Fallback for unknown keys
            return None
        except Exception as e:
            _LOGGER.error("Error calculating native_value for sensor %s: %s", self.unique_id, e)
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes for the sensor.
        
        For the 'current_month_production' sensor, this exposes:
        - month: The current month (YYYY-MM).
        - monthly: List of all monthly production/value data.
        - last_updated: Timestamp of when the data was last fetched.
        
        Returns:
            dict[str, Any] | None: Extra attributes, or None if not applicable.
        """
        # Only expose extra attributes for the current_month_production sensor
        if self.entity_description.key != "current_month_production":
            return None
        
        return {
            # Current month (YYYY-MM format)
            "month": self.coordinator.data["current_month"]["month"]
            if self.coordinator.data["current_month"]
            else None,
            # List of all monthly data (for history)
            "monthly": self.coordinator.data["monthly"],
            # Timestamp of when the data was last fetched
            "last_updated": self.coordinator.data["generated_at"],
        }
