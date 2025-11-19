# Tests for Aerofly FS4 IGC Recorder

This directory contains the test suite for the Aerofly FS4 IGC Recorder project.

## Setup

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Run all tests:
```bash
pytest
```

### Run with coverage:
```bash
pytest --cov=app --cov-report=html --cov-report=term
```

### Run specific test file:
```bash
pytest tests/test_parser.py
```

### Run specific test:
```bash
pytest tests/test_parser.py::TestForeFlightParser::test_parse_valid_xgps_data
```

### Run with verbose output:
```bash
pytest -v
```

### Run async tests:
```bash
pytest -v tests/test_igc_writer.py
```

## Test Coverage

Current test files:
- `test_parser.py` - Tests for ForeFlight data parser
- `test_models.py` - Tests for data models and validation
- `test_settings.py` - Tests for settings management
- `test_igc_writer.py` - Tests for IGC file writer

## Writing New Tests

- Place test files in this directory with `test_` prefix
- Use pytest fixtures for common setup
- Use `@pytest.mark.asyncio` for async tests
- Follow existing test patterns for consistency

## Continuous Integration

Tests are automatically run on:
- Pull requests
- Pushes to main branch
- Via GitHub Actions (when configured)
