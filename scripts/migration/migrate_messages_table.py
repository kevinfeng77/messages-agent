#!/usr/bin/env python3
"""
Migration script to create and populate the new messages table.

This script:
1. Creates the new messages table with simplified schema
2. Extracts messages from the source Messages database
3. Decodes message text using the messaging decoder
4. Populates the new messages table with coalesced text content

Usage:
    python scripts/migration/migrate_messages_table.py
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add src to path for imports
src_path = str(Path(__file__).parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from database.manager import DatabaseManager
from database.messages_db import MessagesDatabase
from messaging.decoder import extract_message_text
from utils.logger_config import get_logger

logger = get_logger(__name__)


class MessagesTableMigrator:
    """Migrator for creating and populating the new messages table"""

    def __init__(
        self,
        source_db_path: str = "./data/chat_copy.db",
        target_db_path: str = "./data/messages.db",
    ):
        self.source_db_path = Path(source_db_path)
        self.target_db_path = Path(target_db_path)
        # Don't use DatabaseManager for migration - just access the database directly
        self.messages_db = MessagesDatabase(str(self.target_db_path))

    def validate_source_database(self) -> bool:
        """
        Validate that the source database exists and has required tables

        Returns:
            True if valid, False otherwise
        """
        if not self.source_db_path.exists():
            logger.error(f"Source database not found: {self.source_db_path}")
            return False

        try:
            with sqlite3.connect(str(self.source_db_path)) as conn:
                cursor = conn.cursor()

                # Check for required tables
                required_tables = ["message", "handle", "chat", "chat_message_join"]
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                existing_tables = {row[0] for row in cursor.fetchall()}

                missing_tables = set(required_tables) - existing_tables
                if missing_tables:
                    logger.error(f"Missing required tables: {missing_tables}")
                    return False

                logger.info("Source database validation successful")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error validating source database: {e}")
            return False

    def extract_messages_with_text(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Extract messages from source database with decoded text

        Args:
            limit: Optional limit on number of messages to extract

        Returns:
            List of message dictionaries with decoded text
        """
        try:
            with sqlite3.connect(str(self.source_db_path)) as conn:
                cursor = conn.cursor()

                # Query to get messages with handle information
                query = """
                    SELECT 
                        m.ROWID as message_id,
                        m.text,
                        m.attributedBody,
                        m.handle_id,
                        m.is_from_me,
                        m.date,
                        h.id as handle_identifier
                    FROM message m
                    LEFT JOIN handle h ON m.handle_id = h.ROWID
                    WHERE m.text IS NOT NULL OR m.attributedBody IS NOT NULL
                    ORDER BY m.date DESC
                """

                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query)
                raw_messages = cursor.fetchall()

                logger.info(f"Extracted {len(raw_messages)} raw messages from source database")

                # Process messages and decode text
                messages = []
                for row in raw_messages:
                    (
                        message_id,
                        text,
                        attributed_body,
                        handle_id,
                        is_from_me,
                        date,
                        handle_identifier,
                    ) = row

                    # Decode message text using the messaging decoder
                    decoded_text = extract_message_text(text, attributed_body)

                    # Skip messages without any text content
                    if not decoded_text or decoded_text.strip() == "":
                        continue

                    # Convert macOS timestamp to ISO format
                    # macOS uses seconds since 2001-01-01, convert to Unix timestamp
                    if date:
                        try:
                            unix_timestamp = date + 978307200  # Offset from 2001-01-01 to 1970-01-01
                            # Validate timestamp is reasonable (between 1970 and 2100)
                            if 0 <= unix_timestamp <= 4102444800:  # 2100-01-01
                                created_at = datetime.fromtimestamp(unix_timestamp).isoformat()
                            else:
                                # Use current time for invalid timestamps
                                created_at = datetime.now().isoformat()
                        except (OSError, ValueError, OverflowError):
                            # Handle invalid timestamp values
                            created_at = datetime.now().isoformat()
                    else:
                        created_at = datetime.now().isoformat()

                    # Use handle_identifier as user_id, or generate one if missing
                    user_id = handle_identifier if handle_identifier else f"unknown_user_{handle_id}"

                    message_data = {
                        "message_id": str(message_id),
                        "user_id": user_id,
                        "contents": decoded_text,
                        "is_from_me": bool(is_from_me),
                        "created_at": created_at,
                    }

                    messages.append(message_data)

                logger.info(f"Successfully processed {len(messages)} messages with decoded text")
                return messages

        except sqlite3.Error as e:
            logger.error(f"Error extracting messages from source database: {e}")
            return []

    def migrate_messages(self, batch_size: int = 1000, limit: Optional[int] = None) -> bool:
        """
        Migrate messages from source to target database

        Args:
            batch_size: Number of messages to process in each batch
            limit: Optional limit on total messages to migrate

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate source database
            if not self.validate_source_database():
                return False

            # Ensure target database exists with correct schema
            if not self.messages_db.create_database():
                logger.error("Failed to create target database")
                return False

            # Clear existing messages if any
            self.messages_db.clear_messages_table()

            # Extract messages with decoded text
            logger.info("Extracting messages from source database...")
            messages = self.extract_messages_with_text(limit=limit)

            if not messages:
                logger.warning("No messages found to migrate")
                return True

            # Insert messages in batches
            total_inserted = 0
            for i in range(0, len(messages), batch_size):
                batch = messages[i : i + batch_size]
                inserted_count = self.messages_db.insert_messages_batch(batch)
                total_inserted += inserted_count

                logger.info(
                    f"Processed batch {i//batch_size + 1}: "
                    f"inserted {inserted_count}/{len(batch)} messages"
                )

            logger.info(f"Migration completed successfully: {total_inserted} messages migrated")
            return True

        except Exception as e:
            logger.error(f"Error during message migration: {e}")
            return False

    def get_migration_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the migration

        Returns:
            Dictionary with migration statistics
        """
        try:
            # Source database stats
            source_stats = {"total_messages": 0, "messages_with_text": 0}
            
            if self.source_db_path.exists():
                with sqlite3.connect(str(self.source_db_path)) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT COUNT(*) FROM message")
                    source_stats["total_messages"] = cursor.fetchone()[0]
                    
                    cursor.execute(
                        "SELECT COUNT(*) FROM message WHERE text IS NOT NULL OR attributedBody IS NOT NULL"
                    )
                    source_stats["messages_with_text"] = cursor.fetchone()[0]

            # Target database stats
            target_stats = {"total_messages": 0}
            
            if self.target_db_path.exists():
                target_messages = self.messages_db.get_all_messages()
                target_stats["total_messages"] = len(target_messages)

            return {
                "source_database": str(self.source_db_path),
                "target_database": str(self.target_db_path),
                "source_stats": source_stats,
                "target_stats": target_stats,
                "migration_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting migration stats: {e}")
            return {"error": str(e)}


def main():
    """Main function to run the messages table migration"""
    logger.info("Starting messages table migration...")

    # Initialize migrator
    migrator = MessagesTableMigrator()

    # Get pre-migration stats
    pre_stats = migrator.get_migration_stats()
    logger.info(f"Pre-migration stats: {pre_stats}")

    # Run migration
    # For testing, limit to 1000 messages initially
    success = migrator.migrate_messages(batch_size=500, limit=1000)

    # Get post-migration stats
    post_stats = migrator.get_migration_stats()
    logger.info(f"Post-migration stats: {post_stats}")

    if success:
        logger.info("Messages table migration completed successfully!")
        return 0
    else:
        logger.error("Messages table migration failed!")
        return 1


if __name__ == "__main__":
    exit(main())