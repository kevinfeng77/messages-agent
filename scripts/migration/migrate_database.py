#!/usr/bin/env python3
"""Helper script to run database migration"""

import sys
from pathlib import Path

# Add parent directory to path for src package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.manager import DatabaseManager
from src.database.migrator import DatabaseMigrator
from src.utils.logger_config import setup_logging, get_logger


def main():
    """Main migration workflow"""
    setup_logging()
    logger = get_logger(__name__)

    print("🔄 Starting Messages Database Migration...")

    # Step 1: Create fresh copy of Messages database
    print("\n1. Creating fresh copy of Messages database...")
    db_manager = DatabaseManager(data_dir="./data")

    if not db_manager.verify_source_database():
        print("❌ Cannot access Messages database. Please check permissions.")
        return 1

    source_db = db_manager.create_safe_copy()
    if not source_db:
        print("❌ Failed to create database copy")
        return 1

    print(f"✅ Source database ready: {source_db}")

    # Step 2: Run migration
    print("\n2. Migrating to joined format with contact names...")
    target_db = "./data/messages_complete_contacts.db"

    migrator = DatabaseMigrator(source_db_path=source_db, target_db_path=target_db)

    try:
        # Create schema
        migrator.create_target_schema()

        # Migrate data
        total = migrator.migrate_data()

        # Add account mapping
        migrator.add_account_mapping()

        # Show results
        stats = migrator.get_migration_stats()

        print(f"\n✅ Migration Complete!")
        print(f"📊 Total messages: {total:,}")
        print(f"📤 Sent: {stats.get('sent_messages', 0):,}")
        print(f"📥 Received: {stats.get('received_messages', 0):,}")
        print(f"👥 Unique contacts: {stats.get('unique_contacts', 0):,}")
        print(f"📱 Services: {stats.get('services', {})}")
        print(f"💾 Database created: {target_db}")

        print(f"\n🎯 You can now use TablePlus to view: {Path(target_db).absolute()}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"❌ Migration failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
