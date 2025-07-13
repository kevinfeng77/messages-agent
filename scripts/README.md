# Scripts Directory

This directory contains all operational scripts for the Message Agent system, organized by purpose.

## Directory Structure

```
scripts/
├── copy_messages_database.py      # Messages database copying (SERENE-49)
├── setup_messages_database.py     # Streamlined setup script (SERENE-49)
├── debug/                          # Debugging and diagnostic scripts
│   ├── debug_addressbook_data.py  # Address book diagnostics
│   └── debug_binary.py            # Binary encoding diagnostics
├── migration/                      # Database migration scripts
│   └── migrate_messages_table.py  # Core messages table migration
└── validation/                     # Validation and testing scripts
    ├── validate_chat_migration.py # Chat migration validation
    ├── validate_messages_database.py # Database validation
    └── validate_messages_table.py # Messages table validation
```

## Main Scripts

### `copy_messages_database.py` 📋 **Database Copy Script**
**SERENE-49: Clean database copying functionality:**
- Creates safe copy of macOS Messages database
- Handles WAL/SHM files properly
- Places copy in correct `data/copy/` subdirectory
- Provides database statistics

**Usage:**
```bash
python scripts/copy_messages_database.py
# or via just command
just copy
```

### `setup_messages_database.py` ⭐ **Streamlined Setup Script**
**SERENE-49: Complete setup without migration complexity:**
- Creates messages database with full schema
- Extracts users from macOS Address Book  
- Processes Messages database handles
- Populates all tables (chats, messages, chat_users)
- Validates test cases and provides comprehensive reporting

**Usage:**
```bash
python scripts/setup_messages_database.py
# or via just command
just setup  # runs: clean -> copy -> create
```

## Organized Subfolders

- **`debug/`** - Diagnostic scripts for troubleshooting issues
- **`migration/`** - Database schema and data migration scripts  
- **`validation/`** - Testing and validation scripts

See individual README files in each subfolder for detailed documentation.

## Recommended Workflow (SERENE-49)

1. **Complete Setup**: `just setup` for full end-to-end setup from clean state
2. **Individual Steps**: Use `just copy` or `just create` for specific operations
3. **Validation**: Use scripts in `validation/` to verify everything works correctly
4. **Troubleshooting**: Use scripts in `debug/` if issues arise

## Just Commands

- `just setup` - Complete setup: clean -> copy -> create
- `just copy` - Copy Messages database only
- `just create` - Create and populate messages.db only  
- `just clean` - Clean data directory
- `just validate` - Run validation scripts

## Design Principles (SERENE-49)

- **Separation of Concerns**: Copy and setup are distinct operations
- **No Migration Complexity**: Fresh setup doesn't need migration logic
- **Organization**: Scripts grouped by purpose for easy maintenance
- **Command Integration**: Just commands provide unified workflow
- **Safety**: All operations include error handling and validation