"""Configuration flow for Urban Solar integration.

This module handles the user interface for configuring the Urban Solar integration,
including validation of credentials and PDL (Point of Delivery) during setup.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import UrbanSolarApiError, UrbanSolarAuthenticationError, UrbanSolarClient
from .const import CONF_EMAIL, CONF_PASSWORD, CONF_PDL, DOMAIN

# Logger for configuration flow operations
_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configuration flow handler for Urban Solar integration.
    
    This class manages the user interface for adding and configuring
    the Urban Solar integration in Home Assistant.
    
    Attributes:
        VERSION: Configuration flow version (increment when making breaking changes).
    """

    VERSION = 1  # Increment this if you make breaking changes to the config flow

    def _schema(self, defaults: dict[str, Any] | None = None) -> vol.Schema:
        """Create a configuration schema for the Urban Solar integration.
        
        Args:
            defaults: Optional dictionary of default values for the form fields.
            
        Returns:
            vol.Schema: A schema defining the configuration form fields.
        """
        defaults = defaults or {}
        return vol.Schema(
            {
                # Email field (required)
                vol.Required(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): str,
                # Password field (required)
                vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): str,
                # PDL (Point of Delivery) field (required)
                vol.Required(CONF_PDL, default=defaults.get(CONF_PDL, "")): str,
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial configuration step (user form submission).
        
        This method is called when the user submits the configuration form.
        It validates the credentials and creates a new config entry if successful.
        
        Args:
            user_input: Dictionary containing user-submitted form data (email, password, PDL).
            
        Returns:
            ConfigFlowResult: Result of the configuration step (form or entry creation).
        """
        _LOGGER.debug("Starting async_step_user")
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Log the input (redact password for security)
            _LOGGER.debug("Validating user input: email=%s, pdl=%s", 
                          user_input.get(CONF_EMAIL, "REDACTED"), 
                          user_input.get(CONF_PDL, "REDACTED"))
            
            try:
                # Validate the credentials by making a test API call
                await self._async_validate_input(user_input)
                _LOGGER.debug("Input validation successful")
            except UrbanSolarAuthenticationError as e:
                _LOGGER.error("Authentication failed: %s", e)
                errors["base"] = "invalid_auth"  # Show "Invalid credentials" error in the form
            except UrbanSolarApiError as e:
                _LOGGER.error("API error during validation: %s", e)
                errors["base"] = "cannot_connect"  # Show "Cannot connect" error in the form
            except Exception as e:
                _LOGGER.error("Unexpected error during validation: %s", e)
                errors["base"] = "unknown"  # Show generic error in the form
            else:
                # Set the unique ID to the PDL (to prevent duplicate entries for the same PDL)
                await self.async_set_unique_id(user_input[CONF_PDL])
                self._abort_if_unique_id_configured()  # Abort if this PDL is already configured
                
                _LOGGER.debug("Creating config entry for PDL: %s", user_input[CONF_PDL])
                # Create the config entry with the user's input data
                return self.async_create_entry(
                    title=f"Urban Solar ({user_input[CONF_PDL]})", 
                    data=user_input
                )

        _LOGGER.debug("Showing form with errors: %s", errors)
        # Show the configuration form (with errors if any)
        return self.async_show_form(
            step_id="user", 
            data_schema=self._schema(user_input), 
            errors=errors
        )

    async def _async_validate_input(self, data: dict[str, Any]) -> None:
        """Validate user input by testing the API connection.
        
        Args:
            data: Dictionary containing user input (email, password, PDL).
            
        Raises:
            UrbanSolarAuthenticationError: If credentials are invalid.
            UrbanSolarApiError: If there is an API error (e.g., network issue).
        """
        # Create a temporary client to test the credentials
        client = UrbanSolarClient(
            async_get_clientsession(self.hass),
            data[CONF_EMAIL],
            data[CONF_PASSWORD],
            data[CONF_PDL],
        )
        # Fetch data to validate the credentials (will raise an exception if invalid)
        await client.async_fetch()
