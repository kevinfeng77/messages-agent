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

### `validate_chat_migration.py`
Validates the chat migration process and results:
- Verifies migration completeness and accuracy
- Validates specific test cases (e.g., Quantabes chat requirements)
- Tests normalized structure and junction table integrity
- Provides detailed migration statistics

### `validate_messages_database.py`
Validates the messages database setup and integrity:
- Checks database schema correctness
- Validates data extraction from Messages database
- Tests contact resolution and matching

## Usage

Run validation scripts from the project root:

```bash
# Validate chat migration results
python scripts/validation/validate_chat_migration.py

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