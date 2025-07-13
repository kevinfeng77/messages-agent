# Migration Scripts

This folder contains database migration scripts for updating the Message Agent database schema and migrating data between versions.

## Scripts

### `migrate_add_handle_id_column.py`
Adds the `handle_id` column to existing users tables:
- Safely adds the column without data loss
- Creates appropriate indexes for performance
- Handles cases where column already exists

### `migrate_chats.py`
Migrates chat data from Messages database to normalized structure:
- Extracts chats and handles from Messages database
- Maps handle_ids to user_ids using existing users table
- Creates normalized chats and chat_users tables
- Validates migration completeness

### `migrate_database.py`
Performs comprehensive database migrations:
- Migrates Messages database to include contact information
- Joins message data with contact names from address book
- Creates denormalized tables for efficient querying

## Usage

Run migration scripts from the project root:

```bash
# Add handle_id column to existing database
python scripts/migration/migrate_add_handle_id_column.py

# Migrate chat data from Messages database
python scripts/migration/migrate_chats.py

# Perform full database migration with contacts
python scripts/migration/migrate_database.py
```

## Safety Features

- **Backup Creation**: All migrations create database backups before proceeding
- **Rollback Support**: Failed migrations can be rolled back
- **Idempotent Operations**: Safe to run multiple times
- **Schema Validation**: Verifies schema before and after migration

## When to Use

- **Schema Updates**: When updating existing installations with new database columns
- **Data Migration**: When moving from old database formats to new ones
- **Contact Integration**: When adding contact resolution to existing message databases