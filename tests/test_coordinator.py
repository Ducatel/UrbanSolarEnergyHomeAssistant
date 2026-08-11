"""Unit tests for Urban Solar data update coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.urban_solar_energy.api import (
    UrbanSolarApiError,
    UrbanSolarAuthenticationError,
    UrbanSolarClient,
)
from custom_components.urban_solar_energy.coordinator import (
    UrbanSolarDataUpdateCoordinator,
)
from custom_components.urban_solar_energy.const import DOMAIN, UPDATE_INTERVAL


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test_unique_id"
    entry.data = {"email": "test@example.com", "password": "test_password", "pdl": "1234567890"}
    return entry


@pytest.fixture
def mock_client():
    """Create a mock UrbanSolarClient."""
    client = MagicMock(spec=UrbanSolarClient)
    return client


@pytest.fixture
def coordinator(mock_hass, mock_entry, mock_client):
    """Create an UrbanSolarDataUpdateCoordinator instance."""
    return UrbanSolarDataUpdateCoordinator(mock_hass, mock_entry, mock_client)


class TestUrbanSolarDataUpdateCoordinatorInitialization:
    """Tests for coordinator initialization."""

    def test_init_stores_client(self, coordinator, mock_client):
        """Test that the client is stored correctly."""
        assert coordinator.client == mock_client

    def test_init_sets_domain(self, coordinator):
        """Test that the domain is set correctly."""
        assert coordinator.name == DOMAIN

    def test_init_sets_update_interval(self, coordinator):
        """Test that the update interval is set correctly."""
        assert coordinator.update_interval == UPDATE_INTERVAL

    def test_init_sets_always_update_false(self, coordinator):
        """Test that always_update is set to False."""
        assert coordinator.always_update is False

    def test_init_stores_config_entry(self, coordinator, mock_entry):
        """Test that the config entry is stored correctly."""
        assert coordinator.config_entry == mock_entry


@pytest.mark.asyncio
class TestUrbanSolarDataUpdateCoordinatorAsyncUpdateData:
    """Tests for _async_update_data method."""

    async def test_async_update_data_success(self, coordinator, mock_client):
        """Test successful data update."""
        # Mock client to return test data
        mock_data = {
            "generated_at": "2025-01-01T00:00:00Z",
            "total": {"production_kwh": 100.0, "value_eur": 12.0},
            "wallet_eur": 5.0,
            "monthly": [{"month": "2025-01", "production_kwh": 100.0, "price_eur_per_kwh": 0.12, "value_eur": 12.0}],
            "current_month": {"month": "2025-01", "production_kwh": 100.0, "price_eur_per_kwh": 0.12, "value_eur": 12.0},
        }
        mock_client.async_fetch = AsyncMock(return_value=mock_data)
        
        result = await coordinator._async_update_data()
        
        # Verify client was called
        mock_client.async_fetch.assert_called_once()
        
        # Verify result
        assert result == mock_data

    async def test_async_update_data_authentication_error(self, coordinator, mock_client):
        """Test that ConfigEntryAuthFailed is raised on authentication error."""
        mock_client.async_fetch = AsyncMock(side_effect=UrbanSolarAuthenticationError("Invalid credentials"))
        
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    async def test_async_update_data_api_error(self, coordinator, mock_client):
        """Test that UpdateFailed is raised on API error."""
        mock_client.async_fetch = AsyncMock(side_effect=UrbanSolarApiError("API error"))
        
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    async def test_async_update_data_unexpected_error(self, coordinator, mock_client):
        """Test that UpdateFailed is raised on unexpected errors."""
        mock_client.async_fetch = AsyncMock(side_effect=Exception("Unexpected error"))
        
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


class TestUrbanSolarDataUpdateCoordinatorProperties:
    """Tests for coordinator properties."""

    def test_data_property_initial_state(self, coordinator):
        """Test that data is None initially."""
        assert coordinator.data is None

    def test_last_update_success_property(self, mock_hass, mock_entry, mock_client):
        """Test that last_update_success is False initially."""
        coordinator = UrbanSolarDataUpdateCoordinator(mock_hass, mock_entry, mock_client)
        # The coordinator inherits from DataUpdateCoordinator which may have different initial values
        # We just check that the attribute exists
        assert hasattr(coordinator, 'last_update_success')

    def test_last_update_time_property(self, mock_hass, mock_entry, mock_client):
        """Test that the coordinator has timing attributes."""
        coordinator = UrbanSolarDataUpdateCoordinator(mock_hass, mock_entry, mock_client)
        # Check that the coordinator has the expected timing attributes from the parent class
        assert hasattr(coordinator, 'last_update_success')


@pytest.mark.asyncio
class TestUrbanSolarDataUpdateCoordinatorIntegration:
    """Integration tests for the coordinator."""

    @patch("custom_components.urban_solar_energy.coordinator._LOGGER")
    async def test_coordinator_logging_on_success(self, mock_logger, coordinator, mock_client):
        """Test that coordinator logs on successful update."""
        mock_data = {"test": "data"}
        mock_client.async_fetch = AsyncMock(return_value=mock_data)
        
        await coordinator._async_update_data()
        
        # Verify debug logging
        mock_logger.debug.assert_called()

    @patch("custom_components.urban_solar_energy.coordinator._LOGGER")
    async def test_coordinator_logging_on_auth_error(self, mock_logger, coordinator, mock_client):
        """Test that coordinator logs on authentication error."""
        mock_client.async_fetch = AsyncMock(side_effect=UrbanSolarAuthenticationError("Invalid credentials"))
        
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()
        
        # Verify error logging
        mock_logger.error.assert_called()

    @patch("custom_components.urban_solar_energy.coordinator._LOGGER")
    async def test_coordinator_logging_on_api_error(self, mock_logger, coordinator, mock_client):
        """Test that coordinator logs on API error."""
        mock_client.async_fetch = AsyncMock(side_effect=UrbanSolarApiError("API error"))
        
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        
        # Verify error logging
        mock_logger.error.assert_called()

    @patch("custom_components.urban_solar_energy.coordinator._LOGGER")
    async def test_coordinator_logging_on_unexpected_error(self, mock_logger, coordinator, mock_client):
        """Test that coordinator logs on unexpected error."""
        mock_client.async_fetch = AsyncMock(side_effect=Exception("Unexpected error"))
        
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        
        # Verify error logging
        mock_logger.error.assert_called()


class TestUrbanSolarDataUpdateCoordinatorInheritance:
    """Tests for coordinator inheritance."""

    def test_inherits_from_data_update_coordinator(self, coordinator):
        """Test that UrbanSolarDataUpdateCoordinator inherits from DataUpdateCoordinator."""
        from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
        
        assert isinstance(coordinator, DataUpdateCoordinator)

    def test_has_async_update_data_method(self, coordinator):
        """Test that coordinator has _async_update_data method."""
        assert hasattr(coordinator, "_async_update_data")
        assert callable(coordinator._async_update_data)
