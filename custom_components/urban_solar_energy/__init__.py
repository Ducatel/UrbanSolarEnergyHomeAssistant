"""Urban Solar Energy integration for Home Assistant.

This integration fetches photovoltaic production and resale data from Urban Solar Energy
and exposes it as sensors in Home Assistant.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import UrbanSolarApiError, UrbanSolarClient
from .const import CONF_EMAIL, CONF_PASSWORD, CONF_PDL, DOMAIN
from .coordinator import UrbanSolarDataUpdateCoordinator

# Logger for this integration
_LOGGER = logging.getLogger(__name__)

# Platforms supported by this integration (only sensors for now)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Urban Solar integration from a config entry.
    
    Args:
        hass: Home Assistant core instance.
        entry: Configuration entry containing user credentials and PDL (Point of Delivery).
        
    Returns:
        bool: True if setup was successful.
        
    Raises:
        ConfigEntryNotReady: If initial data fetch fails (e.g., API unavailable).
    """
    _LOGGER.debug("Starting async_setup_entry for Urban Solar (entry_id: %s)", entry.entry_id)
    
    # Initialize the API client with user credentials
    client = UrbanSolarClient(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_PDL],
    )
    
    # Create the coordinator to manage data updates
    coordinator = UrbanSolarDataUpdateCoordinator(hass, entry, client)
    _LOGGER.debug("Coordinator created for entry_id: %s", entry.entry_id)

    try:
        _LOGGER.debug("Calling async_config_entry_first_refresh")
        # Fetch initial data to validate the configuration
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("First refresh completed successfully")
    except UrbanSolarApiError as err:
        _LOGGER.error("Failed to retrieve Urban Solar data: %s", err)
        raise ConfigEntryNotReady(f"Unable to retrieve Urban Solar data: {err}") from err

    # Store the coordinator in Home Assistant's data for later use
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _LOGGER.debug("Storing coordinator in hass.data and forwarding entry setups")
    
    # Forward setup to all platforms (e.g., sensor)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("async_setup_entry completed successfully for entry_id: %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Urban Solar config entry.
    
    Args:
        hass: Home Assistant core instance.
        entry: Configuration entry to unload.
        
    Returns:
        bool: True if unloading was successful.
    """
    # Unload all platforms (e.g., sensor) for this entry
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Clean up the coordinator from Home Assistant's data
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
