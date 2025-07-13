# Validation Scripts

This folder contains validation and testing scripts to verify the correctness and completeness of the Message Agent system implementation.

**Note (SERENE-49)**: Some validation scripts have been removed as their functionality is now built into the streamlined setup process.

## Scripts

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

### `validate_messages_table.py`
Validates messages table migration and content:
- Verifies message extraction and text decoding
- Tests message-chat relationships
- Validates data integrity and completeness

## Usage

Run validation scripts from the project root:

```bash
# Run all validations via just command
just validate

# Or run individual validation scripts
python scripts/validation/validate_chat_migration.py
python scripts/validation/validate_messages_database.py
python scripts/validation/validate_messages_table.py
```

## Built-in Validation

The streamlined setup process (`just setup`) includes built-in validation:
- **Test Case Validation**: Automatically validates Allison Shi and Wayne Ellerbe test cases
- **Statistical Reporting**: Provides success rates and coverage metrics
- **Error Detection**: Reports any issues during setup process

## Output

All validation scripts provide:
- **Pass/Fail Status**: Clear indication of test results
- **Detailed Reports**: Comprehensive analysis of issues found
- **Performance Metrics**: Processing statistics and success rates
- **Recommendations**: Suggested fixes for any problems

## When to Use

- **After Setup**: Run `just validate` after `just setup` to verify everything works
- **Development**: Use individual scripts to test specific components
- **Troubleshooting**: Diagnose issues when system behavior is unexpected
- **CI/CD**: Integrate validation into automated testing pipelines