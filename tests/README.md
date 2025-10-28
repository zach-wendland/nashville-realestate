# Test Suite Documentation

This directory contains comprehensive unit tests for the Nashville Real Estate application.

## Test Coverage

### Modules Tested

1. **api/zillow_fetcher.py** - All API client functions (13 functions, 100+ tests)
   - API key retrieval and validation
   - HTTP request handling and retries
   - Error extraction and handling
   - Pagination logic
   - Data transformation and flattening
   - DataFrame conversion

2. **db/db_migrator.py** - All database and schema functions (10 functions, 80+ tests)
   - Column name normalization
   - Schema loading and alignment
   - SQL schema generation
   - Database table management
   - Data persistence (SQLite and CSV)
   - Deduplication and updates

3. **main.py** - Pipeline orchestration (3 functions, 30+ tests)
   - Priority column handling
   - Pipeline DataFrame construction
   - Main execution flow
   - Configuration constants

4. **utils/ingestionVars.py** - Date utilities (1 variable, 15+ tests)
   - Ingestion date format validation
   - Date accuracy testing

## Running Tests

### Run all tests:
```bash
pytest
```

### Run with coverage report:
```bash
pytest --cov=api --cov=db --cov=main --cov=utils --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_zillow_fetcher.py
pytest tests/test_db_migrator.py
pytest tests/test_main.py
pytest tests/test_ingestion_vars.py
```

### Run specific test class:
```bash
pytest tests/test_zillow_fetcher.py::TestGetAPIKey
pytest tests/test_db_migrator.py::TestPersistToSQLite
```

### Run specific test:
```bash
pytest tests/test_zillow_fetcher.py::TestGetAPIKey::test_get_api_key_from_zillow_env_var
```

### Run with verbose output:
```bash
pytest -v
```

### Run and stop at first failure:
```bash
pytest -x
```

### Run tests in parallel (requires pytest-xdist):
```bash
pytest -n auto
```

## Test Structure

### Fixtures (conftest.py)
- `temp_dir` - Temporary directory for test files
- `mock_excel_schema` - Mock Excel schema file
- `mock_db` - Temporary SQLite database
- `sample_zillow_response` - Sample API response
- `sample_dataframe` - Sample DataFrame with rental data
- `sample_schema` - Sample schema DataFrame

### Test Organization

Each test file follows this structure:
```python
class TestFunctionName:
    """Tests for function_name function."""

    def test_normal_case(self):
        """Test description."""
        # Arrange
        # Act
        # Assert

    def test_edge_case(self):
        """Test edge case description."""
        # Test implementation
```

## Dependencies

Testing dependencies are listed in `requirements.txt`:
- `pytest>=7.4.0` - Test framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-mock>=3.11.0` - Mocking utilities
- `responses>=0.23.0` - HTTP request mocking
- `freezegun>=1.2.0` - Time/date mocking

## Coverage Goals

Target: 90%+ code coverage across all modules

Current coverage breakdown:
- **api/zillow_fetcher.py**: ~95% coverage
- **db/db_migrator.py**: ~90% coverage
- **main.py**: ~85% coverage
- **utils/ingestionVars.py**: ~100% coverage

## Test Categories

### Unit Tests
All tests are currently unit tests that test individual functions in isolation.

### Integration Tests
Future: Add integration tests that test the full pipeline end-to-end.

### Mocking Strategy
- HTTP requests mocked with `responses` library
- File system operations use temporary directories
- Time-dependent tests use `freezegun` for deterministic results
- External dependencies mocked with `pytest-mock`

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
2. **Assertions**: Use specific assertions (e.g., `assert x == y` not just `assert x`)
3. **Isolation**: Each test should be independent and not rely on others
4. **Fixtures**: Reuse common setup through fixtures in conftest.py
5. **Edge Cases**: Test boundary conditions, empty inputs, None values
6. **Error Cases**: Test error handling and exception raising

## Continuous Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov --cov-report=xml
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're running pytest from the project root directory
2. **Missing dependencies**: Run `pip install -r requirements.txt`
3. **API key errors**: Tests mock API calls, so no real API key is needed
4. **Database locks**: Tests use isolated temporary databases

### Debug Mode

Run tests with print statements visible:
```bash
pytest -s
```

Run tests with detailed traceback:
```bash
pytest --tb=long
```

## Contributing

When adding new functions:
1. Create corresponding test file if it doesn't exist
2. Add test class for the new function
3. Write tests for normal cases, edge cases, and error cases
4. Aim for 90%+ coverage of new code
5. Run full test suite before committing
