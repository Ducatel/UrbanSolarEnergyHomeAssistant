"""HTTP client for the Urban Solar customer portal.

This module provides the UrbanSolarClient class to interact with the Urban Solar Energy API.
It handles authentication, GraphQL queries, and data aggregation for photovoltaic production data.
"""

from __future__ import annotations

import base64
import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import aiohttp

# Base URL for the Urban Solar API
API_URL = "https://espace-client.urbansolar.energy/api"
# First date for which data is available (Urban Solar API limitation)
FIRST_DATA_DATE = "2025-01-01"

# Logger for API-related operations
_LOGGER = logging.getLogger(__name__)

# GraphQL query to fetch production data, pricing, and wallet information
QUERY = """
query Data($pdl: String!, $startDate: DateTime!, $endDate: DateTime!) {
  # Get daily injection indexes (production data in Wh)
  getInjectionIndexes(pdl: $pdl, startDate: $startDate, endDate: $endDate) {
    d  # Date of the reading
    c { c v }  # Counters: c = counter ID, v = value in Wh
  }
  # Get BMS (Buyback Market System) pricing periods
  getBMSPricing { startDate endDate price }
  # Get consumption/injection data from the last year (for wallet calculation)
  getBMSInjectionFromLastYear(pdlId: $pdl) {
    consumptions {
      startDate
      endDate
      consumptions { volume notInvoicedVolume type price isInvoiced }
    }
  }
}
"""


class UrbanSolarApiError(Exception):
    """Base exception for Urban Solar API errors.
    
    Raised when there is a general issue with the API (e.g., network error, invalid response).
    """


class UrbanSolarAuthenticationError(UrbanSolarApiError):
    """Exception raised when Urban Solar credentials are rejected.
    
    This occurs when the email, password, or PDL (Point of Delivery) is invalid.
    """


class UrbanSolarClient:
    """Client for interacting with the Urban Solar Energy API.
    
    This class handles authentication, GraphQL queries, and data aggregation
    to retrieve photovoltaic production and resale data.
    
    Attributes:
        _session: aiohttp client session for making HTTP requests.
        _email: User email for authentication.
        _password: User password for authentication.
        _pdl: Point of Delivery (PDL) identifier.
        _session_id: Unique session identifier for tracking requests.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        pdl: str,
    ) -> None:
        """Initialize the Urban Solar API client.
        
        Args:
            session: aiohttp ClientSession for HTTP requests.
            email: User email for authentication.
            password: User password for authentication.
            pdl: Point of Delivery (PDL) identifier.
        """
        self._session = session
        self._email = email
        self._password = password
        self._pdl = pdl
        self._session_id = str(uuid4())  # Unique ID for tracking API requests

    async def async_fetch(self) -> dict[str, Any]:
        """Fetch all data from Urban Solar API and return aggregated results.
        
        This method:
        1. Authenticates with the Urban Solar API.
        2. Fetches production data, pricing, and wallet information via GraphQL.
        3. Aggregates the data into monthly totals and current values.
        
        Returns:
            dict: Aggregated data containing:
                - total: Total production (kWh) and estimated value (€).
                - wallet_eur: Current wallet balance (€).
                - current_month: Production and pricing for the current month.
                - monthly: List of monthly production/value data.
                - generated_at: Timestamp of when the data was fetched.
                
        Raises:
            UrbanSolarAuthenticationError: If authentication fails.
            UrbanSolarApiError: If there is an issue with the API request or response.
        """
        _LOGGER.debug("Starting async_fetch for PDL: %s", self._pdl)
        try:
            await self._async_login()
            _LOGGER.debug("Login successful for PDL: %s", self._pdl)
        except Exception as e:
            _LOGGER.error("Login failed for PDL %s: %s", self._pdl, e)
            raise

        # Prepare the GraphQL query payload
        payload = {
            "operationName": "Data",
            "variables": {
                "pdl": self._pdl,
                "startDate": f"{FIRST_DATA_DATE}T00:00:00.000Z",
                "endDate": f"{date.today().isoformat()}T23:59:59.000Z",
            },
            "query": QUERY,
        }
        _LOGGER.debug("Sending GraphQL request with payload: %s", payload)
        
        try:
            async with self._session.post(
                f"{API_URL}/graphql",
                headers=self._headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),  # 30-second timeout
            ) as response:
                _LOGGER.debug("GraphQL response status: %s", response.status)
                
                # Handle authentication errors
                if response.status in (401, 403):
                    _LOGGER.error("Authentication refused by Urban Solar (status: %s)", response.status)
                    raise UrbanSolarAuthenticationError("Authentication refused by Urban Solar")
                
                response.raise_for_status()
                result = await response.json()
                _LOGGER.debug("GraphQL response data received")
        except aiohttp.ClientError as err:
            _LOGGER.error("Client error during GraphQL request: %s", err)
            raise UrbanSolarApiError(str(err)) from err

        # Check for GraphQL errors in the response
        if errors := result.get("errors"):
            _LOGGER.error("GraphQL errors: %s", errors)
            raise UrbanSolarApiError(str(errors))
        
        _LOGGER.debug("Aggregating data from GraphQL response")
        aggregated_data = self._aggregate(result["data"])
        _LOGGER.debug("Data aggregation completed: %s", aggregated_data)
        return aggregated_data

    async def _async_login(self) -> None:
        """Authenticate with the Urban Solar API using Basic Auth.
        
        This method creates a session cookie by sending credentials to the /login endpoint.
        The cookie is automatically handled by the aiohttp session for subsequent requests.
        
        Raises:
            UrbanSolarAuthenticationError: If credentials are invalid.
            UrbanSolarApiError: If there is a network or API error.
        """
        # Encode credentials for Basic Auth (email:password)
        raw_credentials = f"{self._email}:{quote(self._password, safe='')}"
        basic_auth = base64.b64encode(raw_credentials.encode("utf-8")).decode("ascii")
        
        # Add Authorization header to the default headers
        headers = self._headers() | {"Authorization": f"Basic {basic_auth}"}
        
        try:
            async with self._session.post(
                f"{API_URL}/login",
                headers=headers,
                json={"rememberMe": True},  # Request persistent session
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                # Check for authentication failure
                if response.status in (401, 403):
                    raise UrbanSolarAuthenticationError("Invalid Urban Solar credentials")
                response.raise_for_status()
        except aiohttp.ClientError as err:
            raise UrbanSolarApiError(str(err)) from err

    def _headers(self) -> dict[str, str]:
        """Generate default headers for API requests.
        
        Returns:
            dict: Headers including Content-Type and a unique session ID.
        """
        return {"Content-Type": "application/json", "X-Session-Id": self._session_id}

    def _aggregate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Aggregate raw API data into structured monthly and total values.
        
        This method:
        1. Converts daily production readings (in Wh) to monthly totals (in kWh).
        2. Matches production data with pricing information for each day.
        3. Calculates monetary values for each month and totals.
        4. Computes the current wallet balance from unbilled volumes.
        
        Args:
            data: Raw data from the Urban Solar API (GraphQL response).
            
        Returns:
            dict: Structured data containing:
                - generated_at: Timestamp of aggregation.
                - monthly: List of monthly data (month, production_kwh, price, value_eur).
                - current_month: Data for the current month (or None).
                - total: Total production (kWh) and estimated value (€).
                - wallet_eur: Current wallet balance (€).
        """
        # Extract pricing data from the API response
        pricing = data["getBMSPricing"]
        
        # Dictionary to accumulate monthly production and pricing
        months: dict[str, dict[str, float | None]] = defaultdict(
            lambda: {"production_kwh": 0.0, "price_eur_per_kwh": None}
        )

        # Process daily injection readings
        for reading in data["getInjectionIndexes"]:
            day = reading["d"]  # Date of the reading (YYYY-MM-DD)
            month = day[:7]    # Extract year-month (YYYY-MM)
            
            # Sum daily injection values (in Wh) and convert to kWh
            # Note: 'v' is the daily injection in Wh; None values are treated as 0
            production_kwh = sum((counter["v"] or 0) for counter in reading["c"]) / 1000
            months[month]["production_kwh"] += production_kwh
            months[month]["price_eur_per_kwh"] = self._price_for_day(pricing, day)

        # Build the monthly list and calculate totals
        monthly = []
        total_production_kwh = 0.0
        total_value_eur = 0.0
        
        for month, values in sorted(months.items()):
            production_kwh = round(float(values["production_kwh"]), 3)
            price = values["price_eur_per_kwh"]
            value_eur = round(production_kwh * price, 2) if price is not None else None
            
            monthly.append(
                {
                    "month": month,
                    "production_kwh": production_kwh,
                    "price_eur_per_kwh": price,
                    "value_eur": value_eur,
                }
            )
            total_production_kwh += production_kwh
            if value_eur is not None:
                total_value_eur += value_eur

        # Calculate the current wallet balance (Urban Solar's definition):
        # Only unbilled BMS volumes are included, at their corresponding price.
        consumptions_data = data["getBMSInjectionFromLastYear"]["consumptions"] or []
        wallet_eur = round(
            sum(
                consumption["notInvoicedVolume"] * consumption["price"]
                for period in consumptions_data
                if (consumption := (period["consumptions"] or [{}])[0]).get(
                    "notInvoicedVolume"
                )
                and consumption.get("price")
            ),
            2,  # Round to 2 decimal places (cents)
        )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "monthly": monthly,
            "current_month": monthly[-1] if monthly else None,
            "total": {
                "production_kwh": round(total_production_kwh, 3),
                "value_eur": round(total_value_eur, 2),
            },
            "wallet_eur": wallet_eur,
        }

    @staticmethod
    def _price_for_day(pricing: list[dict[str, Any]], day: str) -> float | None:
        """Find the applicable price for a given day from the pricing list.
        
        Args:
            pricing: List of pricing periods from the API (each with startDate, endDate, price).
            day: Date to find the price for (format: YYYY-MM-DD).
            
        Returns:
            float | None: The price in €/kWh for the given day, or None if no matching period is found.
        """
        for item in pricing:
            # Check if the day falls within the pricing period
            # Note: startDate and endDate are in ISO format (YYYY-MM-DDTHH:MM:SSZ)
            if item["startDate"][:10] <= day and (
                item["endDate"] is None or day <= item["endDate"][:10]
            ):
                return item["price"]
        return None
