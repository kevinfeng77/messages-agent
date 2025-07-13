# Scripts Directory

This directory contains all operational scripts for the Message Agent system, organized by purpose.

## Directory Structure

```
scripts/
├── setup_messages_database.py     # Main setup script (consolidated)
├── run_full_migration.py          # Legacy migration runner
├── debug/                          # Debugging and diagnostic scripts
│   ├── debug_addressbook_data.py  # Address book diagnostics
│   └── debug_binary.py            # Binary encoding diagnostics
├── migration/                      # Database migration scripts
│   ├── migrate_add_handle_id_column.py  # Add handle_id column
│   └── migrate_database.py        # Full database migration
└── validation/                     # Validation and testing scripts
    ├── validate_handle_id_implementation.py  # Handle ID validation
    ├── validate_implementation.py # General validation
    └── validate_messages_database.py         # Database validation
```

## Main Scripts

### `setup_messages_database.py` ⭐ **Primary Setup Script**
**Complete end-to-end setup for the Message Agent system:**
- Creates messages database with users table
- Extracts users from macOS Address Book
- Migrates database schema (adds handle_id column)
- Processes Messages database handles
- Creates/matches users with handle mapping
- Validates test cases and provides comprehensive reporting

**Usage:**
```bash
python scripts/setup_messages_database.py
```

**What it does:**
1. Creates `./data/messages.db` with proper schema
2. Extracts ~367 users from Address Book
3. Adds handle_id column and indexes
4. Processes ~834 handles from Messages database
5. Achieves 95.8% success rate in handle mapping
6. Validates specific test cases (Allison Shi, Wayne Ellerbe)

### `run_full_migration.py`
Legacy script for comprehensive database migration with contact joining.

## Organized Subfolders

- **`debug/`** - Diagnostic scripts for troubleshooting issues
- **`migration/`** - Database schema and data migration scripts  
- **`validation/`** - Testing and validation scripts

See individual README files in each subfolder for detailed documentation.

## Recommended Workflow

1. **Initial Setup**: Run `setup_messages_database.py` for complete system setup
2. **Validation**: Use scripts in `validation/` to verify everything works correctly
3. **Troubleshooting**: Use scripts in `debug/` if issues arise
4. **Updates**: Use scripts in `migration/` for schema updates on existing systems

## Design Principles

- **Consolidation**: Main setup script combines multiple operations for simplicity
- **Organization**: Scripts grouped by purpose for easy maintenance
- **Safety**: All operations include error handling and validation
- **Documentation**: Each folder has detailed README with usage examples