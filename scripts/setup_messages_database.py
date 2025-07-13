#!/usr/bin/env python3
"""
Streamlined Messages Database Setup Script

This script creates and populates the messages.db database from scratch.
It assumes a clean state and focuses on direct database creation rather than migrations.

Usage:
    python scripts/setup_messages_database_new.py
"""

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.messages_db import MessagesDatabase
from src.extractors.addressbook_extractor import AddressBookExtractor
from src.user.handle_matcher import HandleMatcher
from src.utils.logger_config import get_logger

# Import the messages table migrator for data population
sys.path.append(str(Path(__file__).parent / "migration"))
from migrate_messages_table import MessagesTableMigrator

logger = get_logger(__name__)


def extract_handles_from_messages_db(chat_db_path: str) -> List[tuple]:
    """
    Extract all handles from the Messages database copy
    
    Args:
        chat_db_path: Path to Messages database copy
        
    Returns:
        List of (handle_id, handle_identifier) tuples
    """
    chat_db_path_obj = Path(chat_db_path)
    
    if not chat_db_path_obj.exists():
        logger.error(f"Messages database copy not found at {chat_db_path}")
        return []
    
    try:
        with sqlite3.connect(str(chat_db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT ROWID, id
                FROM handle
                ORDER BY ROWID
            """)
            
            handles = cursor.fetchall()
            logger.info(f"Extracted {len(handles)} handles from Messages database")
            return handles
            
    except sqlite3.Error as e:
        logger.error(f"Error extracting handles: {e}")
        return []


def process_handles(
    messages_db: MessagesDatabase,
    handle_matcher: HandleMatcher,
    handles: List[tuple],
) -> Dict[str, int]:
    """
    Process handles and create/match users
    
    Args:
        messages_db: MessagesDatabase instance
        handle_matcher: HandleMatcher instance
        handles: List of (handle_id, handle_identifier) tuples
        
    Returns:
        Dictionary with processing statistics
    """
    if not handles:
        logger.error("No handles found to process")
        return {"error": "No handles found"}
    
    # Get existing users with handle_ids to avoid duplicates
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
    
    for handle_id, handle_identifier in handles:
        try:
            # Skip if user already exists with this handle_id
            if handle_id in existing_handle_users:
                logger.debug(f"Skipping handle_id {handle_id} - user already exists")
                stats["skipped_existing"] += 1
                continue
            
            # Try to match or create user
            user = handle_matcher.match_handle_to_user(handle_id, handle_identifier)
            
            if user:
                if user.handle_id == handle_id:
                    stats["new_users_created"] += 1
                    logger.debug(f"Created/matched user for handle_id {handle_id}: {user}")
                else:
                    # Update existing user with handle_id
                    success = messages_db.update_user_handle_id(user.user_id, handle_id)
                    if success:
                        stats["existing_users_matched"] += 1
                        logger.debug(f"Updated existing user {user.user_id} with handle_id {handle_id}")
                    else:
                        stats["errors"] += 1
                        logger.error(f"Failed to update user {user.user_id} with handle_id {handle_id}")
            else:
                stats["errors"] += 1
                logger.error(f"Failed to create/match user for handle_id {handle_id}")
                
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Error processing handle_id {handle_id} ({handle_identifier}): {e}")
    
    return stats


def populate_chat_users_relationships(messages_db: MessagesDatabase, chat_db_path: str) -> Dict[str, int]:
    """
    Populate chat_users relationships from the Messages database
    
    Args:
        messages_db: MessagesDatabase instance
        chat_db_path: Path to the Messages database copy
        
    Returns:
        Dictionary with population statistics
    """
    logger.info("Starting chat_users relationships population...")
    
    try:
        chat_db_path_obj = Path(chat_db_path)
        
        if not chat_db_path_obj.exists():
            logger.error(f"Messages database not found at {chat_db_path}")
            return {"error": "Messages database not found", "relationships_created": 0}
        
        # Get handle_id to user_id mapping
        handle_to_user = {}
        all_users = messages_db.get_all_users()
        for user in all_users:
            if user.handle_id:
                handle_to_user[user.handle_id] = user.user_id
        
        logger.info(f"Found {len(handle_to_user)} handle_id to user_id mappings")
        
        # Extract chat-handle relationships from source
        relationships = []
        with sqlite3.connect(str(chat_db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT chj.chat_id, chj.handle_id
                FROM chat_handle_join chj
                ORDER BY chj.chat_id, chj.handle_id
            """)
            
            raw_relationships = cursor.fetchall()
            logger.info(f"Found {len(raw_relationships)} chat-handle relationships in source")
            
            for chat_id, handle_id in raw_relationships:
                if handle_id in handle_to_user:
                    user_id = handle_to_user[handle_id]
                    relationships.append({
                        "chat_id": int(chat_id),
                        "user_id": user_id
                    })
                else:
                    logger.debug(f"No user found for handle_id {handle_id} in chat {chat_id}")
        
        logger.info(f"Created {len(relationships)} chat-user relationships to insert")
        
        # Clear existing chat_users relationships
        with sqlite3.connect(str(messages_db.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_users")
            conn.commit()
        
        # Insert relationships in batches
        relationships_created = 0
        batch_size = 1000
        
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]
            
            with sqlite3.connect(str(messages_db.db_path)) as conn:
                cursor = conn.cursor()
                
                for rel in batch:
                    try:
                        cursor.execute(
                            "INSERT OR IGNORE INTO chat_users (chat_id, user_id) VALUES (?, ?)",
                            (rel["chat_id"], rel["user_id"])
                        )
                        relationships_created += 1
                    except sqlite3.Error as e:
                        logger.warning(f"Error inserting chat_user relationship {rel}: {e}")
                
                conn.commit()
            
            logger.info(f"Inserted batch {i//batch_size + 1}: {len(batch)} relationships")
        
        # Get statistics
        with sqlite3.connect(str(messages_db.db_path)) as conn:
            cursor = conn.cursor()
            
            # Count chats with users
            cursor.execute("""
                SELECT COUNT(DISTINCT c.chat_id)
                FROM chats c
                JOIN chat_users cu ON c.chat_id = cu.chat_id
            """)
            chats_with_users = cursor.fetchone()[0]
            
            # Count chats without users
            cursor.execute("""
                SELECT COUNT(*)
                FROM chats c
                LEFT JOIN chat_users cu ON c.chat_id = cu.chat_id
                WHERE cu.chat_id IS NULL
            """)
            chats_without_users = cursor.fetchone()[0]
        
        logger.info(f"Successfully created {relationships_created} chat-user relationships")
        
        return {
            "relationships_created": relationships_created,
            "chats_with_users": chats_with_users,
            "chats_without_users": chats_without_users,
            "total_relationships_found": len(raw_relationships),
            "relationships_mapped": len(relationships)
        }
        
    except Exception as e:
        logger.error(f"Error during chat_users relationships population: {e}")
        return {"error": str(e), "relationships_created": 0}


def populate_database_content(messages_db: MessagesDatabase, chat_db_path: str) -> Dict[str, int]:
    """
    Populate all database content from the Messages database copy
    
    Args:
        messages_db: MessagesDatabase instance
        chat_db_path: Path to the Messages database copy
        
    Returns:
        Dictionary with population statistics
    """
    logger.info("Starting database content population...")
    
    try:
        # Initialize the migrator
        migrator = MessagesTableMigrator(
            source_db_path=chat_db_path,
            target_db_path=str(messages_db.db_path)
        )
        
        # Get pre-migration stats
        pre_stats = migrator.get_migration_stats()
        logger.info(f"Pre-migration: {pre_stats['source_stats']['messages_with_text']} messages with text in source")
        
        # Migrate chats first
        logger.info("Migrating chats...")
        chats_success = migrator.migrate_chats(batch_size=1000)
        
        if not chats_success:
            logger.error("Chats migration failed")
            return {"error": "Chats migration failed"}
        
        # Migrate messages
        logger.info("Migrating messages...")
        messages_success = migrator.migrate_messages(batch_size=1000, limit=None)
        
        if not messages_success:
            logger.error("Messages migration failed")
            return {"error": "Messages migration failed"}
        
        # Migrate chat-message relationships
        logger.info("Migrating chat-message relationships...")
        chat_messages_success = migrator.migrate_chat_messages(batch_size=1000)
        
        if not chat_messages_success:
            logger.error("Chat-message relationships migration failed")
            return {"error": "Chat-message migration failed"}
        
        # Get post-migration stats
        post_stats = migrator.get_migration_stats()
        messages_migrated = post_stats['target_stats']['total_messages']
        
        # Get counts
        chats = migrator.extract_chats()
        chats_count = len(chats)
        chat_messages = migrator.extract_chat_messages_with_dates()
        chat_messages_count = len(chat_messages)
        
        logger.info(f"Successfully migrated {chats_count} chats, {messages_migrated} messages and {chat_messages_count} chat-message relationships")
        
        return {
            "chats_migrated": chats_count,
            "messages_migrated": messages_migrated,
            "chat_messages_migrated": chat_messages_count,
            "source_messages": pre_stats['source_stats']['messages_with_text'],
            "migration_coverage": post_stats['target_stats']['total_messages'] / max(pre_stats['source_stats']['messages_with_text'], 1)
        }
        
    except Exception as e:
        logger.error(f"Error during database content population: {e}")
        return {"error": str(e)}


def validate_test_cases(messages_db: MessagesDatabase) -> Dict[str, bool]:
    """
    Validate critical test cases
    
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
        logger.info(f"Handle 27 user: {user_handle_27} - Wayne Ellerbe match: {is_wayne}")
    else:
        validation_results["wayne_ellerbe_handle_27"] = False
        logger.warning("No user found with handle_id=27")
    
    return validation_results


def main():
    """Main setup function for messages database"""
    print("=== Streamlined Messages Database Setup ===\n")
    
    # Database paths
    db_path = "./data/messages.db"
    chat_db_path = "./data/copy/chat_copy.db"
    
    # Check that database copy exists
    if not Path(chat_db_path).exists():
        print("❌ Messages database copy not found!")
        print(f"   Expected at: {chat_db_path}")
        print("   Please run: python scripts/copy_messages_database.py")
        return False
    
    print(f"✅ Found Messages database copy at {chat_db_path}")
    
    # Initialize messages database
    print("\n1. Creating messages database...")
    messages_db = MessagesDatabase(db_path)
    
    if not messages_db.create_database():
        print("❌ Failed to create messages database")
        return False
    
    print(f"✅ Created messages database at {db_path}")
    
    # Extract users from address book
    print("\n2. Extracting users from address book...")
    extractor = AddressBookExtractor()
    
    # Get extraction statistics
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
        # Insert users into database
        print(f"\n3. Inserting {len(users)} users into database...")
        inserted_count = messages_db.insert_users_batch(users)
        
        if inserted_count == len(users):
            print(f"✅ Successfully inserted all {inserted_count} users")
        else:
            print(f"⚠️  Inserted {inserted_count} out of {len(users)} users")
    else:
        print("⚠️  No users extracted from address book")
    
    # Process handles from Messages database
    print("\n4. Processing handles from Messages database...")
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
    
    # Populate database content (chats, messages, chat_messages)
    print("\n5. Populating database content...")
    content_stats = populate_database_content(messages_db, chat_db_path)
    
    if "error" in content_stats:
        print(f"❌ Database content population failed: {content_stats['error']}")
        return False
    
    chats_migrated = content_stats.get("chats_migrated", 0)
    messages_migrated = content_stats.get("messages_migrated", 0)
    chat_messages_migrated = content_stats.get("chat_messages_migrated", 0)
    coverage = content_stats.get("migration_coverage", 0) * 100
    
    print(f"✅ Database content population completed:")
    print(f"   - Chats migrated: {chats_migrated}")
    print(f"   - Messages migrated: {messages_migrated}")
    print(f"   - Chat-message relationships migrated: {chat_messages_migrated}")
    print(f"   - Migration coverage: {coverage:.1f}%")
    
    # Populate chat_users relationships
    print("\n6. Populating chat-user relationships...")
    chat_users_stats = populate_chat_users_relationships(messages_db, chat_db_path)
    
    if "error" in chat_users_stats:
        print(f"❌ Chat-user relationships population failed: {chat_users_stats['error']}")
        return False
    
    relationships_created = chat_users_stats.get("relationships_created", 0)
    chats_with_users = chat_users_stats.get("chats_with_users", 0)
    chats_without_users = chat_users_stats.get("chats_without_users", 0)
    
    print(f"✅ Chat-user relationships population completed:")
    print(f"   - Relationships created: {relationships_created}")
    print(f"   - Chats with users: {chats_with_users}")
    print(f"   - Chats without users: {chats_without_users}")
    
    # Validate test cases
    print("\n7. Validating test cases...")
    validation = validate_test_cases(messages_db)
    
    allison_pass = validation.get("allison_shi_handle_3", False)
    wayne_pass = validation.get("wayne_ellerbe_handle_27", False)
    
    print(f"   - Allison Shi test case: {'✅ PASS' if allison_pass else '❌ FAIL'}")
    print(f"   - Wayne Ellerbe test case: {'✅ PASS' if wayne_pass else '❌ FAIL'}")
    
    # Final database statistics
    print("\n8. Final database statistics:")
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
    print(f"   - Chat-User Relationships: {relationships_created}")
    
    # Success summary
    all_critical_passed = allison_pass and wayne_pass
    success_rate = (
        (process_stats["new_users_created"] + process_stats["existing_users_matched"])
        / process_stats["total_handles"]
        * 100
    )
    
    print(f"\n🎉 Messages database setup completed successfully!")
    print(f"   Database location: {db_path}")
    print(f"   Total users: {db_stats['total_users']}")
    print(f"   Total messages: {messages_migrated}")
    print(f"   Total chats: {chats_migrated}")
    print(f"   Chat-user relationships: {relationships_created}")
    print(f"   Handle processing success rate: {success_rate:.1f}%")
    print(f"   Messages migration coverage: {coverage:.1f}%")
    print(f"   Test cases: {'✅ All passed' if all_critical_passed else '⚠️ Some failed'}")
    
    return all_critical_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)