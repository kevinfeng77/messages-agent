#!/usr/bin/env python3
"""Setup script for the new messages.db database with users table populated from address book"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.messages_db import MessagesDatabase
from src.user.user import AddressBookExtractor
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def main():
    """Main setup function for messages database"""
    print("=== Messages Database Setup ===\n")
    
    # Initialize database manager
    db_path = "./data/messages.db"
    messages_db = MessagesDatabase(db_path)
    
    # Create the database and users table
    print("1. Creating messages database...")
    if not messages_db.create_database():
        print("❌ Failed to create messages database")
        return False
    
    print(f"✅ Created messages database at {db_path}")
    
    # Extract users from address book
    print("\n2. Extracting users from address book...")
    extractor = AddressBookExtractor()
    
    # Get extraction statistics first
    stats = extractor.get_extraction_stats()
    print(f"📊 Address book statistics:")
    print(f"   - Found {stats['total_databases']} AddressBook databases")
    print(f"   - Total records: {stats['total_records']}")
    print(f"   - Records with phone: {stats['records_with_phone']}")
    print(f"   - Records with email: {stats['records_with_email']}")
    
    # Extract users
    users = extractor.extract_users()
    print(f"✅ Extracted {len(users)} unique users from address book")
    
    if not users:
        print("⚠️  No users extracted from address book")
        return True
    
    # Show sample users
    print(f"\n📝 Sample users:")
    for i, user in enumerate(users[:5]):
        print(f"   {i+1}. {user}")
    if len(users) > 5:
        print(f"   ... and {len(users) - 5} more")
    
    # Insert users into database
    print(f"\n3. Inserting {len(users)} users into database...")
    inserted_count = messages_db.insert_users_batch(users)
    
    if inserted_count == len(users):
        print(f"✅ Successfully inserted all {inserted_count} users")
    else:
        print(f"⚠️  Inserted {inserted_count} out of {len(users)} users")
    
    # Get database statistics
    print("\n4. Database statistics:")
    db_stats = messages_db.get_database_stats()
    for key, value in db_stats.items():
        if key == 'database_size_bytes':
            size_kb = value / 1024
            print(f"   - {key.replace('_', ' ').title()}: {size_kb:.1f} KB")
        else:
            print(f"   - {key.replace('_', ' ').title()}: {value}")
    
    print(f"\n🎉 Messages database setup complete!")
    print(f"   Database location: {db_path}")
    print(f"   Users table contains {db_stats['total_users']} users")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)