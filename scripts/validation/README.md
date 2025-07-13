# Validation Scripts

This folder contains validation and testing scripts to verify the correctness and completeness of the Message Agent system implementation.

## Scripts

### `validate_handle_id_implementation.py`
Comprehensive validation of the handle_id feature (SERENE-47):
- Validates specific test cases (Allison Shi, Wayne Ellerbe)
- Tests phone number normalization
- Verifies fallback user creation
- Provides detailed reporting and statistics

### `validate_implementation.py`
General implementation validation:
- Validates core system functionality
- Tests data extraction and processing
- Verifies database operations

### `validate_messages_database.py`
Validates the messages database setup and integrity:
- Checks database schema correctness
- Validates data extraction from Messages database
- Tests contact resolution and matching

## Usage

Run validation scripts from the project root:

```bash
# Validate handle_id implementation
python scripts/validation/validate_handle_id_implementation.py

# Validate general implementation
python scripts/validation/validate_implementation.py

# Validate messages database
python scripts/validation/validate_messages_database.py
```

## Output

All validation scripts provide:
- **Pass/Fail Status**: Clear indication of test results
- **Detailed Reports**: Comprehensive analysis of issues found
- **Performance Metrics**: Processing statistics and success rates
- **Recommendations**: Suggested fixes for any problems

## When to Use

- **After Setup**: Run after initial system setup to verify everything works
- **After Changes**: Validate after making code changes or updates
- **Before Deployment**: Final validation before putting system into production
- **Troubleshooting**: Diagnose issues when system behavior is unexpected