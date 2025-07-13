#!/usr/bin/env python3
"""
Complete setup script for the messages.db database

This script performs the full setup process:
1. Creates the messages database with users table
2. Populates users from address book
3. Migrates database schema (adds handle_id column if needed)
4. Processes Messages database handles and creates/matches users
5. Validates the complete setup

Combines functionality from setup, migration, and population scripts.
"""

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.manager import DatabaseManager
from src.database.messages_db import MessagesDatabase  
from src.extractors.addressbook_extractor import AddressBookExtractor
from src.user.handle_matcher import HandleMatcher
from src.utils.logger_config import get_logger

# Import the messages table migrator
sys.path.append(str(Path(__file__).parent / "migration"))
from migrate_messages_table import MessagesTableMigrator

logger = get_logger(__name__)


def migrate_add_handle_id_column(db_path: str) -> bool:
    """
    Add handle_id column to users table if it doesn't exist

    Args:
        db_path: Path to the messages database

    Returns:
        True if successful, False otherwise
    """
    db_path_obj = Path(db_path)

    if not db_path_obj.exists():
        logger.error(f"Database not found at {db_path}")
        return False

    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # Check if handle_id column already exists
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            if "handle_id" in column_names:
                logger.info("handle_id column already exists, no migration needed")
                return True

            # Add handle_id column
            logger.info("Adding handle_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN handle_id INTEGER")

            # Create index for handle_id
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_handle_id ON users(handle_id)"
            )

            conn.commit()
            logger.info("Successfully added handle_id column and index")
            return True

    except sqlite3.Error as e:
        logger.error(f"Error migrating database: {e}")
        return False


def extract_handles_from_messages_db(chat_db_path: str) -> List[Tuple[int, str]]:
    """
    Extract all handles from the Messages database

    Args:
        chat_db_path: Path to Messages database copy

    Returns:
        List of (handle_id, handle_id_value) tuples
    """
    chat_db_path_obj = Path(chat_db_path)

    if not chat_db_path_obj.exists():
        logger.error(f"Messages database not found at {chat_db_path}")
        return []

    try:
        with sqlite3.connect(str(chat_db_path)) as conn:
            cursor = conn.cursor()

            # Get all handles with their ROWID and id
            cursor.execute(
                """
                SELECT ROWID, id
                FROM handle
                ORDER BY ROWID
            """
            )

            handles = cursor.fetchall()
            logger.info(f"Extracted {len(handles)} handles from Messages database")
            return handles

    except sqlite3.Error as e:
        logger.error(f"Error extracting handles: {e}")
        return []


def process_handles(
    messages_db: MessagesDatabase,
    handle_matcher: HandleMatcher,
    handles: List[Tuple[int, str]],
) -> Dict[str, int]:
    """
    Process all handles and create/match users

    Args:
        messages_db: MessagesDatabase instance
        handle_matcher: HandleMatcher instance
        handles: List of (handle_id, handle_id_value) tuples

    Returns:
        Dictionary with processing statistics
    """
    if not handles:
        logger.error("No handles found to process")
        return {"error": "No handles found"}

    existing_handle_users = {}
    existing_users = messages_db.get_all_users()

    for user in existing_users:
        if user.handle_id is not None:
            existing_handle_users[user.handle_id] = user.user_id

    stats = {
        "total_handles": len(handles),
        "existing_users": len(existing_handle_users),
        "new_users_created": 0,
        "existing_users_matched": 0,
        "skipped_existing": 0,
        "errors": 0,
    }

    for handle_id, handle_id_value in handles:
        try:
            # Skip if user already exists with this handle_id
            if handle_id in existing_handle_users:
                logger.debug(f"Skipping handle_id {handle_id} - user already exists")
                stats["skipped_existing"] += 1
                continue

            # Try to match or create user
            user = handle_matcher.match_handle_to_user(handle_id, handle_id_value)

            if user:
                if user.handle_id == handle_id:
                    stats["new_users_created"] += 1
                    logger.debug(
                        f"Created/matched user for handle_id {handle_id}: {user}"
                    )
                else:
                    # Update existing user with handle_id
                    success = messages_db.update_user_handle_id(user.user_id, handle_id)
                    if success:
                        stats["existing_users_matched"] += 1
                        logger.debug(
                            f"Updated existing user {user.user_id} with handle_id {handle_id}"
                        )
                    else:
                        stats["errors"] += 1
                        logger.error(
                            f"Failed to update user {user.user_id} with handle_id {handle_id}"
                        )
            else:
                stats["errors"] += 1
                logger.error(f"Failed to create/match user for handle_id {handle_id}")

        except Exception as e:
            stats["errors"] += 1
            logger.error(
                f"Error processing handle_id {handle_id} ({handle_id_value}): {e}"
            )

    return stats


def validate_test_cases(messages_db: MessagesDatabase) -> Dict[str, bool]:
    """
    Validate the specific test cases mentioned in SERENE-47

    Args:
        messages_db: MessagesDatabase instance

    Returns:
        Dictionary with validation results
    """
    validation_results = {}

    # Test case 1: +19495272398 -> Allison Shi (handle_id=3)
    user_handle_3 = messages_db.get_user_by_handle_id(3)
    if user_handle_3:
        is_allison = (
            "allison" in user_handle_3.first_name.lower()
            and "shi" in user_handle_3.last_name.lower()
        )
        validation_results["allison_shi_handle_3"] = is_allison
        logger.info(f"Handle 3 user: {user_handle_3} - Allison Shi match: {is_allison}")
    else:
        validation_results["allison_shi_handle_3"] = False
        logger.warning("No user found with handle_id=3")

    # Test case 2: wayne26110@gmail.com -> Wayne Ellerbe (handle_id=27)
    user_handle_27 = messages_db.get_user_by_handle_id(27)
    if user_handle_27:
        is_wayne = (
            "wayne" in user_handle_27.first_name.lower()
            and "ellerbe" in user_handle_27.last_name.lower()
        )
        validation_results["wayne_ellerbe_handle_27"] = is_wayne
        logger.info(
            f"Handle 27 user: {user_handle_27} - Wayne Ellerbe match: {is_wayne}"
        )
    else:
        validation_results["wayne_ellerbe_handle_27"] = False
        logger.warning("No user found with handle_id=27")

    return validation_results


def populate_messages_table(db_path: str, chat_db_path: str) -> Dict[str, int]:
    """
    Populate the messages table from the Messages database
    
    Args:
        db_path: Path to the messages.db database
        chat_db_path: Path to the Messages database copy
        
    Returns:
        Dictionary with population statistics
    """
    logger.info("Starting messages table population...")
    
    try:
        # Initialize the migrator
        migrator = MessagesTableMigrator(
            source_db_path=chat_db_path,
            target_db_path=db_path
        )
        
        # Get pre-migration stats
        pre_stats = migrator.get_migration_stats()
        logger.info(f"Pre-migration: {pre_stats['source_stats']['messages_with_text']} messages with text in source")
        
        # Run the migration with reasonable batch size and no limit
        success = migrator.migrate_messages(batch_size=1000, limit=None)
        
        if not success:
            logger.error("Messages table migration failed")
            return {"error": "Migration failed", "messages_migrated": 0}
        
        # Get post-migration stats
        post_stats = migrator.get_migration_stats()
        messages_migrated = post_stats['target_stats']['total_messages']
        
        logger.info(f"Successfully migrated {messages_migrated} messages to messages table")
        
        return {
            "messages_migrated": messages_migrated,
            "source_messages": pre_stats['source_stats']['messages_with_text'],
            "migration_coverage": post_stats['target_stats']['total_messages'] / max(pre_stats['source_stats']['messages_with_text'], 1)
        }
        
    except Exception as e:
        logger.error(f"Error during messages table population: {e}")
        return {"error": str(e), "messages_migrated": 0}


def main():
    """Main setup function for messages database"""
    print("=== Complete Messages Database Setup ===\n")

    # Initialize database manager
    db_path = "./data/messages.db"
    messages_db = MessagesDatabase(db_path)

    # Step 1: Create the database and users table
    print("1. Creating messages database...")
    if not messages_db.create_database():
        print("❌ Failed to create messages database")
        return False

    print(f"✅ Created messages database at {db_path}")

    # Step 2: Extract users from address book
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

    if users:
        # Show sample users
        print(f"\n📝 Sample users:")
        for i, user in enumerate(users[:3]):
            print(f"   {i+1}. {user}")
        if len(users) > 3:
            print(f"   ... and {len(users) - 3} more")

        # Insert users into database
        print(f"\n3. Inserting {len(users)} users into database...")
        inserted_count = messages_db.insert_users_batch(users)

        if inserted_count == len(users):
            print(f"✅ Successfully inserted all {inserted_count} users")
        else:
            print(f"⚠️  Inserted {inserted_count} out of {len(users)} users")
    else:
        print("⚠️  No users extracted from address book")

    # Step 3: Migrate database schema (add handle_id column)
    print("\n4. Migrating database schema...")
    if migrate_add_handle_id_column(db_path):
        print("✅ Database schema migration completed")
    else:
        print("❌ Database schema migration failed")
        return False

    # Step 4: Setup Messages database copy
    print("\n5. Setting up Messages database copy...")
    db_manager = DatabaseManager()
    if not db_manager.create_safe_copy():
        print("❌ Failed to create safe database copy")
        return False
    print("✅ Messages database copy created")

    # Step 5: Process handles from Messages database
    print("\n6. Processing handles from Messages database...")

    chat_db_path = "./data/chat_copy.db"
    handles = extract_handles_from_messages_db(chat_db_path)

    if not handles:
        print("❌ No handles found in Messages database")
        return False

    print(f"📊 Found {len(handles)} handles to process")

    # Initialize handle matcher and process handles
    handle_matcher = HandleMatcher(db_path)
    process_stats = process_handles(messages_db, handle_matcher, handles)

    if "error" in process_stats:
        print(f"❌ Error processing handles: {process_stats['error']}")
        return False

    print(f"✅ Handle processing completed:")
    print(f"   - Total handles: {process_stats['total_handles']}")
    print(f"   - New users created: {process_stats['new_users_created']}")
    print(f"   - Existing users matched: {process_stats['existing_users_matched']}")
    print(f"   - Errors: {process_stats['errors']}")

    # Step 6: Validate test cases
    print("\n7. Validating test cases...")
    validation = validate_test_cases(messages_db)

    allison_pass = validation.get("allison_shi_handle_3", False)
    wayne_pass = validation.get("wayne_ellerbe_handle_27", False)

    print(f"   - Allison Shi test case: {'✅ PASS' if allison_pass else '❌ FAIL'}")
    print(f"   - Wayne Ellerbe test case: {'✅ PASS' if wayne_pass else '❌ FAIL'}")

    # Step 7: Populate messages table
    print("\n8. Populating messages table...")
    messages_stats = populate_messages_table(db_path, chat_db_path)
    
    if "error" in messages_stats:
        print(f"❌ Messages table population failed: {messages_stats['error']}")
        return False
    
    messages_migrated = messages_stats.get("messages_migrated", 0)
    source_messages = messages_stats.get("source_messages", 0)
    coverage = messages_stats.get("migration_coverage", 0) * 100
    
    print(f"✅ Messages table population completed:")
    print(f"   - Source messages with text: {source_messages}")
    print(f"   - Messages migrated: {messages_migrated}")
    print(f"   - Migration coverage: {coverage:.1f}%")

    # Step 9: Final database statistics
    print("\n9. Final database statistics:")
    db_stats = messages_db.get_database_stats()

    # Calculate handle-specific stats
    all_users = messages_db.get_all_users()
    users_with_handle_id = len([u for u in all_users if u.handle_id is not None])
    users_without_handle_id = len([u for u in all_users if u.handle_id is None])

    for key, value in db_stats.items():
        if key == "database_size_bytes":
            size_kb = value / 1024
            print(f"   - {key.replace('_', ' ').title()}: {size_kb:.1f} KB")
        else:
            print(f"   - {key.replace('_', ' ').title()}: {value}")

    print(f"   - Users With Handle Id: {users_with_handle_id}")
    print(f"   - Users Without Handle Id: {users_without_handle_id}")
    print(f"   - Messages In Table: {messages_migrated}")

    # Success summary
    all_critical_passed = allison_pass and wayne_pass
    success_rate = (
        (process_stats["new_users_created"] + process_stats["existing_users_matched"])
        / process_stats["total_handles"]
        * 100
    )

    print(f"\n🎉 Complete messages database setup finished!")
    print(f"   Database location: {db_path}")
    print(f"   Total users: {db_stats['total_users']}")
    print(f"   Total messages: {messages_migrated}")
    print(f"   Handle processing success rate: {success_rate:.1f}%")
    print(f"   Messages migration coverage: {coverage:.1f}%")
    print(
        f"   Test cases: {'✅ All passed' if all_critical_passed else '⚠️ Some failed'}"
    )

    return all_critical_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
