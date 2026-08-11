"""Unit tests for Urban Solar API client."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.urban_solar_energy.api import (
    API_URL,
    FIRST_DATA_DATE,
    QUERY,
    UrbanSolarApiError,
    UrbanSolarAuthenticationError,
    UrbanSolarClient,
)


# Load test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_session():
    """Create a mock aiohttp ClientSession."""
    session = MagicMock(spec=aiohttp.ClientSession)
    return session


@pytest.fixture
def client(mock_session):
    """Create an UrbanSolarClient instance with mock session."""
    return UrbanSolarClient(
        session=mock_session,
        email="test@example.com",
        password="test_password",
        pdl="1234567890",
    )


class TestUrbanSolarClientInitialization:
    """Tests for UrbanSolarClient initialization."""

    def test_init_creates_unique_session_id(self, mock_session):
        """Test that each client gets a unique session ID."""
        client1 = UrbanSolarClient(mock_session, "email1", "pass1", "pdl1")
        client2 = UrbanSolarClient(mock_session, "email2", "pass2", "pdl2")
        
        assert client1._session_id != client2._session_id
        assert len(client1._session_id) > 0
        assert len(client2._session_id) > 0

    def test_init_stores_credentials(self, client, mock_session):
        """Test that credentials are stored correctly."""
        assert client._email == "test@example.com"
        assert client._password == "test_password"
        assert client._pdl == "1234567890"
        assert client._session == mock_session


class TestUrbanSolarClientHeaders:
    """Tests for header generation."""

    def test_headers_include_content_type(self, client):
        """Test that headers include Content-Type."""
        headers = client._headers()
        assert headers["Content-Type"] == "application/json"

    def test_headers_include_session_id(self, client):
        """Test that headers include X-Session-Id."""
        headers = client._headers()
        assert "X-Session-Id" in headers
        assert headers["X-Session-Id"] == client._session_id


class TestUrbanSolarClientPriceForDay:
    """Tests for _price_for_day method."""

    def test_price_for_day_matching_period(self, client):
        """Test finding price for a day within a pricing period."""
        pricing = [
            {"startDate": "2025-01-01T00:00:00Z", "endDate": "2025-03-31T23:59:59Z", "price": 0.12},
            {"startDate": "2025-04-01T00:00:00Z", "endDate": None, "price": 0.13},
        ]
        
        # Test day in first period
        assert client._price_for_day(pricing, "2025-01-15") == 0.12
        assert client._price_for_day(pricing, "2025-02-28") == 0.12
        assert client._price_for_day(pricing, "2025-03-31") == 0.12
        
        # Test day in second period (no end date)
        assert client._price_for_day(pricing, "2025-04-01") == 0.13
        assert client._price_for_day(pricing, "2025-12-31") == 0.13

    def test_price_for_day_before_period(self, client):
        """Test that price is None for days before all periods."""
        pricing = [
            {"startDate": "2025-01-01T00:00:00Z", "endDate": None, "price": 0.12},
        ]
        
        assert client._price_for_day(pricing, "2024-12-31") is None

    def test_price_for_day_after_period(self, client):
        """Test that price is None for days after period end."""
        pricing = [
            {"startDate": "2025-01-01T00:00:00Z", "endDate": "2025-03-31T23:59:59Z", "price": 0.12},
        ]
        
        assert client._price_for_day(pricing, "2025-04-01") is None

    def test_price_for_day_empty_pricing(self, client):
        """Test that price is None when pricing list is empty."""
        assert client._price_for_day([], "2025-01-01") is None

    def test_price_for_day_exact_boundaries(self, client):
        """Test price at exact period boundaries."""
        pricing = [
            {"startDate": "2025-01-01T00:00:00Z", "endDate": "2025-01-31T23:59:59Z", "price": 0.12},
        ]
        
        # Start date (inclusive)
        assert client._price_for_day(pricing, "2025-01-01") == 0.12
        # End date (inclusive)
        assert client._price_for_day(pricing, "2025-01-31") == 0.12


class TestUrbanSolarClientAggregate:
    """Tests for _aggregate method."""

    def test_aggregate_basic_data(self, client):
        """Test aggregation of basic production data."""
        data = load_fixture("urban_solar_response.json")
        result = client._aggregate(data["data"])
        
        # Check structure
        assert "generated_at" in result
        assert "monthly" in result
        assert "current_month" in result
        assert "total" in result
        assert "wallet_eur" in result
        
        # Check total production
        # January: (10000 + 15000 + 12000) / 1000 = 37 kWh
        # February: (8000 + 11000) / 1000 = 19 kWh
        # March: (9500 + 0 + 13000) / 1000 = 22.5 kWh
        # Total: 37 + 19 + 22.5 = 78.5 kWh
        assert result["total"]["production_kwh"] == 78.5
        
        # Check total value (all at 0.12 €/kWh)
        # 78.5 * 0.12 = 9.42 €
        assert result["total"]["value_eur"] == 9.42

    def test_aggregate_monthly_data(self, client):
        """Test that monthly data is correctly structured."""
        data = load_fixture("urban_solar_response.json")
        result = client._aggregate(data["data"])
        
        monthly = result["monthly"]
        assert len(monthly) == 3  # Jan, Feb, Mar
        
        # Check January data
        jan = next(m for m in monthly if m["month"] == "2025-01")
        assert jan["production_kwh"] == 37.0  # (10000 + 15000 + 12000) / 1000
        assert jan["price_eur_per_kwh"] == 0.12
        assert jan["value_eur"] == 4.44  # 37 * 0.12

    def test_aggregate_wallet_calculation(self, client):
        """Test wallet calculation from unbilled volumes."""
        data = load_fixture("urban_solar_response.json")
        result = client._aggregate(data["data"])
        
        # Wallet should be: (50 * 0.12) + (30 * 0.12) = 6 + 3.6 = 9.6 €
        # March has notInvoicedVolume = 0, so it's not included
        assert result["wallet_eur"] == 9.6

    def test_aggregate_empty_data(self, client):
        """Test aggregation with empty data."""
        data = load_fixture("urban_solar_empty_response.json")
        result = client._aggregate(data["data"])
        
        assert result["total"]["production_kwh"] == 0.0
        assert result["total"]["value_eur"] == 0.0
        assert result["wallet_eur"] == 0.0
        assert result["monthly"] == []
        assert result["current_month"] is None

    def test_aggregate_current_month(self, client):
        """Test that current_month points to the last month."""
        data = load_fixture("urban_solar_response.json")
        result = client._aggregate(data["data"])
        
        # Current month should be March (last in the list)
        assert result["current_month"]["month"] == "2025-03"
        assert result["current_month"]["production_kwh"] == 22.5

    def test_aggregate_with_none_values(self, client):
        """Test aggregation when counter values are None."""
        data = {
            "getInjectionIndexes": [
                {"d": "2025-01-01", "c": [{"c": "counter1", "v": None}]},
                {"d": "2025-01-02", "c": [{"c": "counter1", "v": 10000}]},
            ],
            "getBMSPricing": [{"startDate": "2025-01-01T00:00:00Z", "endDate": None, "price": 0.10}],
            "getBMSInjectionFromLastYear": {"consumptions": []},
        }
        result = client._aggregate(data)
        
        # None values should be treated as 0
        assert result["total"]["production_kwh"] == 10.0  # Only 10000 Wh = 10 kWh


class TestUrbanSolarClientAggregateEdgeCases:
    """Edge case tests for _aggregate method."""

    def test_aggregate_missing_pricing(self, client):
        """Test aggregation when pricing data is missing."""
        data = {
            "getInjectionIndexes": [
                {"d": "2025-01-01", "c": [{"c": "counter1", "v": 10000}]},
            ],
            "getBMSPricing": [],
            "getBMSInjectionFromLastYear": {"consumptions": []},
        }
        result = client._aggregate(data)
        
        assert result["monthly"][0]["price_eur_per_kwh"] is None
        assert result["monthly"][0]["value_eur"] is None
        assert result["total"]["value_eur"] == 0.0

    def test_aggregate_missing_consumptions(self, client):
        """Test aggregation when consumption data is missing."""
        data = {
            "getInjectionIndexes": [],
            "getBMSPricing": [],
            "getBMSInjectionFromLastYear": {"consumptions": None},
        }
        # Should handle None consumptions gracefully
        result = client._aggregate(data)
        assert result["wallet_eur"] == 0.0

    def test_aggregate_empty_consumptions_list(self, client):
        """Test aggregation with empty consumptions list."""
        data = {
            "getInjectionIndexes": [],
            "getBMSPricing": [],
            "getBMSInjectionFromLastYear": {"consumptions": [{"consumptions": []}]},
        }
        result = client._aggregate(data)
        assert result["wallet_eur"] == 0.0


@pytest.mark.asyncio
class TestUrbanSolarClientAsyncFetch:
    """Tests for async_fetch method."""

    @patch("custom_components.urban_solar_energy.api.datetime")
    async def test_async_fetch_success(self, mock_datetime, client, mock_session):
        """Test successful data fetch and aggregation."""
        # Setup mock date
        mock_date = MagicMock()
        mock_date.today.return_value = date(2025, 3, 20)
        mock_date.isoformat.return_value = "2025-03-20"
        mock_datetime.date = mock_date
        
        # Mock login
        mock_login = AsyncMock()
        client._async_login = mock_login
        
        # Mock response with async json method
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=load_fixture("urban_solar_response.json"))
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        result = await client.async_fetch()
        
        # Verify login was called
        mock_login.assert_called_once()
        
        # Verify GraphQL request was made
        mock_session.post.assert_called()
        
        # Verify result structure
        assert "total" in result
        assert "monthly" in result
        assert "wallet_eur" in result

    @patch("custom_components.urban_solar_energy.api.datetime")
    async def test_async_fetch_authentication_error(self, mock_datetime, client, mock_session):
        """Test that authentication error is raised when login fails."""
        mock_date = MagicMock()
        mock_date.today.return_value = date(2025, 3, 20)
        mock_datetime.date = mock_date
        
        # Mock login to raise authentication error
        client._async_login = AsyncMock(side_effect=UrbanSolarAuthenticationError("Invalid credentials"))
        
        with pytest.raises(UrbanSolarAuthenticationError):
            await client.async_fetch()

    @patch("custom_components.urban_solar_energy.api.datetime")
    async def test_async_fetch_graphql_error(self, mock_datetime, client, mock_session):
        """Test that API error is raised when GraphQL returns errors."""
        mock_date = MagicMock()
        mock_date.today.return_value = date(2025, 3, 20)
        mock_datetime.date = mock_date
        
        # Mock successful login
        client._async_login = AsyncMock()
        
        # Mock response with GraphQL errors
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=load_fixture("urban_solar_error_response.json"))
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(UrbanSolarApiError):
            await client.async_fetch()

    @patch("custom_components.urban_solar_energy.api.datetime")
    async def test_async_fetch_http_401(self, mock_datetime, client, mock_session):
        """Test that authentication error is raised for 401 status."""
        mock_date = MagicMock()
        mock_date.today.return_value = date(2025, 3, 20)
        mock_datetime.date = mock_date
        
        # Mock successful login
        client._async_login = AsyncMock()
        
        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status = 401
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(UrbanSolarAuthenticationError):
            await client.async_fetch()

    @patch("custom_components.urban_solar_energy.api.datetime")
    async def test_async_fetch_http_403(self, mock_datetime, client, mock_session):
        """Test that authentication error is raised for 403 status."""
        mock_date = MagicMock()
        mock_date.today.return_value = date(2025, 3, 20)
        mock_datetime.date = mock_date
        
        # Mock successful login
        client._async_login = AsyncMock()
        
        # Mock 403 response
        mock_response = MagicMock()
        mock_response.status = 403
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(UrbanSolarAuthenticationError):
            await client.async_fetch()

    @patch("custom_components.urban_solar_energy.api.datetime")
    async def test_async_fetch_client_error(self, mock_datetime, client, mock_session):
        """Test that API error is raised for client errors."""
        mock_date = MagicMock()
        mock_date.today.return_value = date(2025, 3, 20)
        mock_datetime.date = mock_date
        
        # Mock successful login
        client._async_login = AsyncMock()
        
        # Mock client error
        mock_session.post.return_value.__aenter__.side_effect = aiohttp.ClientError("Connection timeout")
        
        with pytest.raises(UrbanSolarApiError):
            await client.async_fetch()


@pytest.mark.asyncio
class TestUrbanSolarClientLogin:
    """Tests for _async_login method."""

    async def test_login_success(self, client, mock_session):
        """Test successful login."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        await client._async_login()
        
        # Verify login endpoint was called
        mock_session.post.assert_called()
        call_args = mock_session.post.call_args
        assert f"{API_URL}/login" in str(call_args)
        
        # Verify Authorization header
        headers = call_args.kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    async def test_login_401_error(self, client, mock_session):
        """Test login with 401 status raises authentication error."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(UrbanSolarAuthenticationError):
            await client._async_login()

    async def test_login_403_error(self, client, mock_session):
        """Test login with 403 status raises authentication error."""
        mock_response = MagicMock()
        mock_response.status = 403
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(UrbanSolarAuthenticationError):
            await client._async_login()

    async def test_login_client_error(self, client, mock_session):
        """Test login with client error raises API error."""
        mock_session.post.return_value.__aenter__.side_effect = aiohttp.ClientError("Network error")
        
        with pytest.raises(UrbanSolarApiError):
            await client._async_login()

    async def test_login_remember_me(self, client, mock_session):
        """Test that login sends rememberMe=True."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        await client._async_login()
        
        call_args = mock_session.post.call_args
        json_data = call_args.kwargs.get("json", {})
        assert json_data.get("rememberMe") is True


class TestConstants:
    """Tests for module constants."""

    def test_api_url(self):
        """Test that API_URL is correctly defined."""
        assert API_URL == "https://espace-client.urbansolar.energy/api"

    def test_first_data_date(self):
        """Test that FIRST_DATA_DATE is correctly defined."""
        assert FIRST_DATA_DATE == "2025-01-01"

    def test_query_exists(self):
        """Test that QUERY contains expected elements."""
        assert "getInjectionIndexes" in QUERY
        assert "getBMSPricing" in QUERY
        assert "getBMSInjectionFromLastYear" in QUERY


class TestExceptions:
    """Tests for custom exceptions."""

    def test_api_error_inheritance(self):
        """Test that UrbanSolarApiError is an Exception."""
        assert issubclass(UrbanSolarApiError, Exception)

    def test_authentication_error_inheritance(self):
        """Test that UrbanSolarAuthenticationError inherits from UrbanSolarApiError."""
        assert issubclass(UrbanSolarAuthenticationError, UrbanSolarApiError)

    def test_api_error_message(self):
        """Test that UrbanSolarApiError can carry a message."""
        error = UrbanSolarApiError("Test error")
        assert str(error) == "Test error"

    def test_authentication_error_message(self):
        """Test that UrbanSolarAuthenticationError can carry a message."""
        error = UrbanSolarAuthenticationError("Invalid credentials")
        assert str(error) == "Invalid credentials"
