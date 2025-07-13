# Migration Scripts

This folder contains database migration scripts for the Message Agent system.

**Note (SERENE-49)**: Most migration functionality has been consolidated into the streamlined setup process. This directory now contains only the core messages table migration logic used by the setup script.

## Scripts

### `migrate_messages_table.py`
Core messages table migration functionality:
- Extracts messages from Messages database with text decoding
- Migrates chats, messages, and chat-message relationships  
- Handles batch processing for large datasets
- Used internally by the streamlined setup script

## Usage

These migration scripts are primarily used internally by the main setup process:

```bash
# Use the streamlined setup instead of individual migrations
just setup

# Or call setup script directly
python scripts/setup_messages_database.py
```

## Migration Logic Now in Setup

The following migration functionality has been moved to `setup_messages_database.py`:

- **Handle ID Management**: Users table creation with handle_id column
- **Chat Migration**: Extraction and normalization of chat data
- **User Matching**: Handle-to-user mapping and relationship creation
- **Data Population**: Complete database population from Messages database

## Safety Features

- **Fresh Database Creation**: Setup creates clean database from scratch
- **Comprehensive Validation**: Built-in test case validation
- **Error Handling**: Robust error handling throughout process
- **Statistical Reporting**: Detailed success metrics and coverage reports

## When to Use

- **Fresh Setup**: Use `just setup` for new installations
- **Development**: Core migration logic is in `migrate_messages_table.py`
- **Custom Implementations**: Extend migration logic for specific use cases