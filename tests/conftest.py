"""Pytest configuration for Urban Solar tests."""

import sys
from pathlib import Path

# Add the project root to the Python path so we can import custom_components
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# This allows importing from custom_components.urban_solar_energy
