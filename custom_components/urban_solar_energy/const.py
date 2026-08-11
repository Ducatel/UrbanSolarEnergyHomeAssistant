"""Constants for the Urban Solar integration.

This module defines constants used across the Urban Solar Home Assistant integration,
including configuration keys and update intervals.
"""

from datetime import timedelta

# Domain name for this integration (used in entity IDs, service names, etc.)
DOMAIN = "urban_solar_energy"

# Configuration entry keys
CONF_EMAIL = "email"      # User email for Urban Solar authentication
CONF_PASSWORD = "password"  # User password for Urban Solar authentication
CONF_PDL = "pdl"          # Point of Delivery (PDL) identifier

# How often to refresh data from the Urban Solar API (default: every 6 hours)
UPDATE_INTERVAL = timedelta(hours=6)
