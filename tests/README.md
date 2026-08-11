# Tests for Urban Solar Home Assistant Integration

This directory contains unit tests for the Urban Solar Energy Home Assistant integration.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and fixtures
├── README.md                # This file
├── fixtures/                # Test data fixtures
│   ├── __init__.py
│   ├── urban_solar_response.json    # Normal API response
│   ├── urban_solar_empty_response.json  # Empty data response
│   └── urban_solar_error_response.json  # Error response
├── test_api.py              # Tests for UrbanSolarClient
├── test_coordinator.py     # Tests for UrbanSolarDataUpdateCoordinator
├── test_sensor.py           # Tests for sensor entities
└── test_init.py             # Tests for integration initialization
```

## Running Tests

### Prerequisites

Install the test dependencies:

```bash
pip install -r requirements_test.txt
```

### Running All Tests

```bash
pytest
```

### Running Specific Tests

```bash
# Run tests for a specific module
pytest tests/test_api.py

# Run tests for a specific class
pytest tests/test_api.py::TestUrbanSolarClientInitialization

# Run a specific test
pytest tests/test_api.py::TestUrbanSolarClientInitialization::test_init_creates_unique_session_id

# Run with coverage
pytest --cov=custom_components/urban_solar_energy --cov-report=term-missing
```

## Test Coverage

The tests cover the following components:

### `test_api.py`
- **UrbanSolarClient initialization**: Session ID generation, credential storage
- **Header generation**: Content-Type, X-Session-Id
- **Price calculation**: `_price_for_day` method with various date ranges
- **Data aggregation**: `_aggregate` method with normal, empty, and edge case data
- **Async operations**: `async_fetch` and `_async_login` with success and error cases
- **Error handling**: Authentication errors, API errors, client errors
- **Constants**: API_URL, FIRST_DATA_DATE, QUERY validation
- **Exceptions**: Custom exception classes and inheritance

### `test_coordinator.py`
- **Coordinator initialization**: Client storage, domain, update interval
- **Data update**: `_async_update_data` with success and error cases
- **Error handling**: ConfigEntryAuthFailed, UpdateFailed exceptions
- **Properties**: Initial state of data, last_update_success, last_update_time
- **Logging**: Debug and error logging verification
- **Inheritance**: DataUpdateCoordinator inheritance

### `test_sensor.py`
- **Sensor descriptions**: All 5 sensor types and their metadata
- **Sensor initialization**: Description, coordinator, unique ID, device info
- **Native values**: Value calculation for each sensor type
- **Extra state attributes**: Monthly data exposure for current_month_production
- **Error handling**: Missing data, exceptions
- **Setup function**: `async_setup_entry` with success and error cases
- **Inheritance**: CoordinatorEntity and SensorEntity inheritance

### `test_init.py`
- **Integration setup**: `async_setup_entry` with success and error cases
- **Integration unload**: `async_unload_entry` with success and failure cases
- **Platform forwarding**: Sensor platform setup
- **Constants**: DOMAIN, PLATFORMS, config keys

## Fixtures

The test fixtures include:

1. **urban_solar_response.json**: A complete API response with:
   - Daily injection indexes for January, February, March 2025
   - BMS pricing periods
   - Unbilled volume data for wallet calculation

2. **urban_solar_empty_response.json**: Empty data for edge case testing

3. **urban_solar_error_response.json**: GraphQL error response for error handling tests

## Test Data Calculations

The test data in `urban_solar_response.json` is designed to produce specific results:

- **Total production**: 78.5 kWh (37 + 19 + 22.5)
- **Total value**: 9.42 € (78.5 * 0.12)
- **Wallet**: 9.6 € ((50 * 0.12) + (30 * 0.12))
- **Monthly data**: 3 months with production and value data

## Adding New Tests

When adding new tests:

1. Place test files in the `tests/` directory with the `test_` prefix
2. Use pytest fixtures for common test dependencies
3. Follow the existing test structure and naming conventions
4. Add new fixtures to the `fixtures/` directory if needed
5. Update this README if significant changes are made

## Best Practices

- Keep tests focused on a single functionality
- Use descriptive test names that explain what is being tested
- Mock external dependencies (API calls, Home Assistant objects)
- Test both success and error cases
- Keep tests independent of each other
