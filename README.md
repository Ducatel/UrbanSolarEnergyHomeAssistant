# Urban Solar Energy for Home Assistant

**Unofficial HACS integration to track surplus injection and its valuation from Urban Solar Energy.**

[![Unit Tests](https://github.com/Ducatel/UrbanSolarEnergyHomeAssistant/actions/workflows/tests.yml/badge.svg)](https://github.com/Ducatel/UrbanSolarEnergyHomeAssistant/actions/workflows/tests.yml)
[![codecov](https://codecov.io/github/Ducatel/UrbanSolarEnergyHomeAssistant/graph/badge.svg?token=KQ6SPT69M0)](https://codecov.io/github/Ducatel/UrbanSolarEnergyHomeAssistant)

---

## Features

This integration allows you to monitor your photovoltaic production and resale data from **Urban Solar Energy** directly in Home Assistant. It provides the following sensors:

- **Total Production** (kWh) – Cumulative energy production.
- **Current Wallet** (€) – Balance calculated from unbilled volumes (matches Urban Solar portal).
- **Estimated Total Value** (€) – Estimated value of all production based on historical prices.
- **Monthly Production** (kWh) – Production for the current month, with a `monthly` attribute containing detailed history per month.
- **Current Purchase Price** (€/kWh) – Current buyback rate for your surplus energy.

**Data is automatically refreshed every 6 hours.**

---

## Installation

### Option 1: Using HACS (Recommended)

1. **Publish this repository to GitHub** (if not already done).
2. In Home Assistant, go to **HACS > Integrations > + (Add) > Custom repositories**.
3. Add the repository URL as a **Custom Repository** of type **Integration**.
4. Search for and install **Urban Solar** from HACS.
5. Restart Home Assistant.
6. Go to **Settings > Devices & Services > Add Integration** and select **Urban Solar**.
7. Enter your **email**, **password**, and **PDL (Point of Delivery)** when prompted.

### Option 2: Manual Installation

1. Copy the `custom_components/urban_solar_energy/` folder into your Home Assistant's `custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & Services > Add Integration** and select **Urban Solar**.
4. Enter your credentials (email, password, PDL).

---

## Configuration

The integration requires the following information during setup:

| Field       | Description                                                                 | Example           |
|-------------|-----------------------------------------------------------------------------|-------------------|
| **Email**   | Your Urban Solar Energy account email.                                     | `user@example.com` |
| **Password**| Your Urban Solar Energy account password.                                  | `••••••••`         |
| **PDL**     | Your **Point of Delivery** (PDL) identifier (found in your Urban Solar account or bills). | `0123456789` |

> **⚠️ Security Note:**
> - Credentials are **stored securely** in Home Assistant's configuration entries (encrypted).
> - They are **never logged** or exposed in the integration's code.
> - They are **only used** to authenticate with the Urban Solar API.

---

## Entities

Once configured, the integration creates the following entities in Home Assistant:

### Sensors

| Entity ID (Example) | Name | Unit | Description |
|--------------------|------|------|-------------|
| `sensor.urban_solar_<pdl>_total_production` | Total Production | kWh | Total energy produced (all-time). |
| `sensor.urban_solar_<pdl>_wallet` | Current Wallet | € | Balance from unbilled volumes (matches Urban Solar portal). |
| `sensor.urban_solar_<pdl>_estimated_value` | Estimated Total Value | € | Estimated value of all production. |
| `sensor.urban_solar_<pdl>_current_month_production` | Monthly Production | kWh | Production for the current month. |
| `sensor.urban_solar_<pdl>_current_price` | Current Purchase Price | €/kWh | Current buyback rate. |

### Attributes

The **Monthly Production** sensor (`current_month_production`) includes the following attributes:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `month` | Current month in `YYYY-MM` format. | `"2026-08"` |
| `monthly` | List of monthly production/value data. | See below |
| `last_updated` | Timestamp of the last data update. | `"2026-08-10T12:00:00+00:00"` |

**Example `monthly` attribute:**
```json
[
  {
    "month": "2025-01",
    "production_kwh": 300.5,
    "price_eur_per_kwh": 0.065,
    "value_eur": 19.53
  },
  {
    "month": "2025-02",
    "production_kwh": 280.0,
    "price_eur_per_kwh": 0.067,
    "value_eur": 18.76
  }
]
```

---

## Data Refresh

- **Default Interval:** 6 hours (configurable in `const.py`).
- **Manual Refresh:** Restart Home Assistant or trigger a service call to `homeassistant.update_entity` for the sensor.

> **Note:** Frequent refreshes may be rate-limited by the Urban Solar API. Use the default interval unless necessary.

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **"Invalid credentials" error** | Verify your email, password, and PDL. Reset your password if needed. |
| **"Cannot connect" error** | Check your internet connection. The Urban Solar API may be temporarily unavailable. |
| **No sensors appear** | Ensure the integration setup completed successfully. Check Home Assistant logs for errors. |
| **Data not updating** | Wait for the next refresh cycle (6 hours by default). Restart Home Assistant to force an update. |

### Enable Debug Logging

To diagnose issues, enable debug logging for the integration:

1. Go to **Settings > System > Logging**.
2. Add the following configuration:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.urban_solar_energy: debug
   ```
3. Restart Home Assistant and check the logs for detailed error messages.

---

## Limitations

1. **Historical Data:** The Urban Solar API only provides data starting from **January 1, 2025**. Earlier data will not be included.
2. **Wallet vs. Estimated Value:**
   - The **wallet** (`wallet_eur`) is calculated by Urban Solar and includes only **unbilled volumes**.
   - The **estimated value** (`estimated_value`) is calculated locally from all production data and may differ slightly.
3. **Multi-PDL Support:** Currently, only one PDL per configuration entry is supported. For multiple PDLs, create separate entries.

---

## Development

### Project Structure

```
custom_components/urban_solar_energy/
├── __init__.py          # Integration setup and entry management
├── api.py              # Urban Solar API client (authentication, GraphQL queries)
├── const.py            # Constants (domain, configuration keys, update interval)
├── coordinator.py      # Data update coordinator (caching, periodic refresh)
├── config_flow.py      # Configuration flow (user input, validation)
├── sensor.py           # Sensor entities (definitions, value calculations)
├── manifest.json       # Integration metadata (name, version, etc.)
└── strings.json        # Localized strings (French)

tests/
├── __init__.py          # Test package initialization
├── conftest.py          # Pytest configuration and global fixtures
├── README.md            # Test documentation
├── pytest.ini           # Pytest configuration
├── fixtures/            # Mock data for testing
│   ├── urban_solar_response.json    # Complete API response
│   ├── urban_solar_empty_response.json  # Empty response
│   └── urban_solar_error_response.json  # Error response
├── test_api.py          # 38 tests for UrbanSolarClient
├── test_coordinator.py  # 16 tests for coordinator
├── test_sensor.py       # 32 tests for sensor entities
└── test_init.py         # 8 tests for integration initialization
```


### Dev Container

This project includes a **Dev Container** configuration for VS Code:
- **Base Image:** `mcr.microsoft.com/devcontainers/python:3.14`
- **Extensions:** Python, Pylance, Debugpy
- **Forwarded Port:** 8123 (Home Assistant)


### Running Tests

The project includes a **comprehensive unit test suite** (94 tests) to validate the integration functionality.

1. **Install test dependencies:**
   ```bash
   pip install -r requirements_test.txt
   ```

2. **Run all tests:**
   ```bash
   pytest
   ```

3. **Run with code coverage:**
   ```bash
   pytest --cov=custom_components/urban_solar_energy --cov-report=term-missing
   ```

4. **Run specific tests:**
   ```bash
   # Specific module
   pytest tests/test_api.py
   
   # Specific class
   pytest tests/test_api.py::TestUrbanSolarClientInitialization
   
   # Specific test
   pytest tests/test_api.py::TestUrbanSolarClientInitialization::test_init_creates_unique_session_id
   ```

#### Test Coverage

- **API Client:** Initialization, headers, price calculation, data aggregation, error handling
- **Coordinator:** Initialization, data updates, error handling, properties
- **Sensors:** Descriptions, initialization, native values, extra attributes, inheritance
- **Integration:** Setup, unload, platform forwarding

---

## Contributing

1. **Fork** this repository.
2. **Create a branch** for your changes.
3. **Test** your changes locally using the test suite.
4. **Submit a pull request** with a clear description of your changes.

> **Note:** All pull requests should pass the existing tests. Add new tests for any new functionality.

---

## License

This integration is **unofficial** and not affiliated with Urban Solar Energy. It is provided as-is for personal use.

---

## Support

- **Issues:** [GitHub Issues](https://github.com/davidducatel/UrbanSolarEnergyHomeAssistant/issues)
- **Discussions:** [GitHub Discussions](https://github.com/davidducatel/UrbanSolarEnergyHomeAssistant/discussions)
- **Home Assistant Community:** [Forum](https://community.home-assistant.io/)
