"""Unit tests for Urban Solar integration initialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.urban_solar_energy.api import (
    UrbanSolarApiError,
    UrbanSolarClient,
)
from custom_components.urban_solar_energy.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_PDL,
    DOMAIN,
)
from custom_components.urban_solar_energy import PLATFORMS
from custom_components.urban_solar_energy import async_setup_entry, async_unload_entry


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock ConfigEntry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test_unique_id"
    entry.data = {
        CONF_EMAIL: "test@example.com",
        CONF_PASSWORD: "test_password",
        CONF_PDL: "1234567890",
    }
    return entry


@pytest.fixture
def mock_client():
    """Create a mock UrbanSolarClient."""
    client = MagicMock(spec=UrbanSolarClient)
    return client


@pytest.fixture
def mock_coordinator(mock_hass, mock_entry, mock_client):
    """Create a mock coordinator."""
    from custom_components.urban_solar_energy.coordinator import (
        UrbanSolarDataUpdateCoordinator,
    )
    coordinator = MagicMock(spec=UrbanSolarDataUpdateCoordinator)
    return coordinator


@pytest.mark.asyncio
class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    @patch("custom_components.urban_solar_energy.async_get_clientsession")
    @patch("custom_components.urban_solar_energy.UrbanSolarDataUpdateCoordinator")
    async def test_async_setup_entry_success(
        self, mock_coordinator_class, mock_get_session, mock_hass, mock_entry
    ):
        """Test successful integration setup."""
        # Mock the session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Mock the coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        
        # Mock the async_forward_entry_setups to return a coroutine
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        result = await async_setup_entry(mock_hass, mock_entry)
        
        # Verify result
        assert result is True
        
        # Verify client was created
        mock_get_session.assert_called_once_with(mock_hass)
        mock_coordinator_class.assert_called_once()
        
        # Verify coordinator was stored in hass.data
        assert DOMAIN in mock_hass.data
        assert mock_entry.entry_id in mock_hass.data[DOMAIN]
        
        # Verify first refresh was called
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
        
        # Verify platforms were forwarded
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()

    @patch("custom_components.urban_solar_energy.async_get_clientsession")
    @patch("custom_components.urban_solar_energy.UrbanSolarDataUpdateCoordinator")
    async def test_async_setup_entry_api_error(
        self, mock_coordinator_class, mock_get_session, mock_hass, mock_entry
    ):
        """Test that ConfigEntryNotReady is raised on API error."""
        # Mock the session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Mock the coordinator to raise an API error on first refresh
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=UrbanSolarApiError("API unavailable")
        )
        mock_coordinator_class.return_value = mock_coordinator
        
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(mock_hass, mock_entry)

    @patch("custom_components.urban_solar_energy.async_get_clientsession")
    @patch("custom_components.urban_solar_energy.UrbanSolarDataUpdateCoordinator")
    async def test_async_setup_entry_platforms_forwarded(
        self, mock_coordinator_class, mock_get_session, mock_hass, mock_entry
    ):
        """Test that platforms are forwarded correctly."""
        # Mock the session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Mock the coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        
        # Mock the async_forward_entry_setups to return a coroutine
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_entry)
        
        # Verify platforms were forwarded
        call_args = mock_hass.config_entries.async_forward_entry_setups.call_args
        assert call_args[0][0] == mock_entry
        assert call_args[0][1] == PLATFORMS

    @patch("custom_components.urban_solar_energy._LOGGER")
    @patch("custom_components.urban_solar_energy.async_get_clientsession")
    @patch("custom_components.urban_solar_energy.UrbanSolarDataUpdateCoordinator")
    async def test_async_setup_entry_logging(
        self, mock_coordinator_class, mock_get_session, mock_logger, mock_hass, mock_entry
    ):
        """Test that setup logs appropriately."""
        # Mock the session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Mock the coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        
        # Mock the async_forward_entry_setups to return a coroutine
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        await async_setup_entry(mock_hass, mock_entry)
        
        # Verify debug logging
        mock_logger.debug.assert_called()


@pytest.mark.asyncio
class TestAsyncUnloadEntry:
    """Tests for async_unload_entry function."""

    async def test_async_unload_entry_success(self, mock_hass, mock_entry):
        """Test successful integration unload."""
        # Setup initial state
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: "test_coordinator"}
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        result = await async_unload_entry(mock_hass, mock_entry)
        
        # Verify result
        assert result is True
        
        # Verify platforms were unloaded
        mock_hass.config_entries.async_unload_platforms.assert_called_once()
        
        # Verify coordinator was removed from hass.data
        assert mock_entry.entry_id not in mock_hass.data[DOMAIN]

    async def test_async_unload_entry_platforms_fail(self, mock_hass, mock_entry):
        """Test unload when platforms fail to unload."""
        # Setup initial state
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: "test_coordinator"}
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        
        result = await async_unload_entry(mock_hass, mock_entry)
        
        # Verify result
        assert result is False
        
        # Verify coordinator was NOT removed from hass.data
        assert mock_entry.entry_id in mock_hass.data[DOMAIN]


class TestConstants:
    """Tests for module constants."""

    def test_domain(self):
        """Test that DOMAIN is correctly defined."""
        assert DOMAIN == "urban_solar_energy"

    def test_platforms(self):
        """Test that PLATFORMS contains expected platforms."""
        from homeassistant.const import Platform
        
        assert Platform.SENSOR in PLATFORMS
        assert len(PLATFORMS) == 1

    def test_config_keys(self):
        """Test that config keys are correctly defined."""
        assert CONF_EMAIL == "email"
        assert CONF_PASSWORD == "password"
        assert CONF_PDL == "pdl"
