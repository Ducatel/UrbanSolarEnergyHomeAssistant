"""Data update coordinator for Urban Solar.

This module provides the UrbanSolarDataUpdateCoordinator class, which manages
periodic data updates from the Urban Solar API and caches the results for
all sensor entities to use.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UrbanSolarApiError, UrbanSolarAuthenticationError, UrbanSolarClient
from .const import DOMAIN, UPDATE_INTERVAL

# Logger for coordinator operations
_LOGGER = logging.getLogger(__name__)


class UrbanSolarDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for fetching and caching Urban Solar data.
    
    This class extends Home Assistant's DataUpdateCoordinator to:
    - Periodically fetch data from the Urban Solar API.
    - Cache the data for all sensor entities to use.
    - Handle errors (e.g., authentication failures, API timeouts).
    
    Attributes:
        client: UrbanSolarClient instance for making API requests.
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: UrbanSolarClient
    ) -> None:
        """Initialize the coordinator.
        
        Args:
            hass: Home Assistant core instance.
            entry: Configuration entry for this integration.
            client: UrbanSolarClient instance for API requests.
        """
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,  # Update every 6 hours (from const.py)
            always_update=False,  # Only update when interval expires (not on every call)
        )
        self.client = client  # Store the API client for later use

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and return the latest data from Urban Solar API.
        
        This method is called automatically by the coordinator at the specified
        update interval (default: every 6 hours).
        
        Returns:
            dict: Aggregated data from the Urban Solar API (see api._aggregate for structure).
            
        Raises:
            ConfigEntryAuthFailed: If authentication fails (triggers re-authentication flow).
            UpdateFailed: If there is an API error or other issue.
        """
        _LOGGER.debug("Starting _async_update_data for coordinator")
        try:
            data = await self.client.async_fetch()
            _LOGGER.debug("Data fetched successfully: %s", data)
            return data
        except UrbanSolarAuthenticationError as err:
            _LOGGER.error("Authentication failed in coordinator: %s", err)
            # Raise ConfigEntryAuthFailed to trigger Home Assistant's re-authentication flow
            raise ConfigEntryAuthFailed from err
        except UrbanSolarApiError as err:
            _LOGGER.error("API error in coordinator: %s", err)
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            _LOGGER.error("Unexpected error in coordinator: %s", err)
            raise UpdateFailed(str(err)) from err
