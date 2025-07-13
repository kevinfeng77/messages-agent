#!/usr/bin/env python3
"""
Integration tests for the messages table migration functionality.

Tests the complete migration process from source Messages database 
to the new messages table with text decoding.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from scripts.migration.migrate_messages_table import MessagesTableMigrator
from database.messages_db import MessagesDatabase
from messaging.decoder import extract_message_text


class TestMessagesMigration(unittest.TestCase):
    """Integration tests for messages table migration"""

    def setUp(self):
        """Set up test databases for each test"""
        # Create temporary source database
        self.temp_source_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_source_db.close()
        self.source_db_path = self.temp_source_db.name

        # Create temporary target database
        self.temp_target_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_target_db.close()
        self.target_db_path = self.temp_target_db.name

        # Create mock source database with Messages app schema
        self.create_mock_source_database()

        # Initialize migrator
        self.migrator = MessagesTableMigrator(
            source_db_path=self.source_db_path,
            target_db_path=self.target_db_path
        )

    def tearDown(self):
        """Clean up after each test"""
        Path(self.source_db_path).unlink(missing_ok=True)
        Path(self.target_db_path).unlink(missing_ok=True)

    def create_mock_source_database(self):
        """Create a mock source database with Messages app schema and test data"""
        with sqlite3.connect(self.source_db_path) as conn:
            cursor = conn.cursor()

            # Create handle table
            cursor.execute("""
                CREATE TABLE handle (
                    ROWID INTEGER PRIMARY KEY,
                    id TEXT UNIQUE,
                    country TEXT,
                    service TEXT
                )
            """)

            # Create message table  
            cursor.execute("""
                CREATE TABLE message (
                    ROWID INTEGER PRIMARY KEY,
                    guid TEXT UNIQUE,
                    text TEXT,
                    attributedBody BLOB,
                    handle_id INTEGER,
                    is_from_me INTEGER,
                    date INTEGER,
                    service TEXT,
                    FOREIGN KEY (handle_id) REFERENCES handle (ROWID)
                )
            """)

            # Create chat table
            cursor.execute("""
                CREATE TABLE chat (
                    ROWID INTEGER PRIMARY KEY,
                    guid TEXT UNIQUE,
                    display_name TEXT,
                    chat_identifier TEXT,
                    service_name TEXT
                )
            """)

            # Create chat_message_join table
            cursor.execute("""
                CREATE TABLE chat_message_join (
                    chat_id INTEGER,
                    message_id INTEGER,
                    message_date INTEGER,
                    PRIMARY KEY (chat_id, message_id),
                    FOREIGN KEY (chat_id) REFERENCES chat (ROWID),
                    FOREIGN KEY (message_id) REFERENCES message (ROWID)
                )
            """)

            # Insert test handles
            test_handles = [
                (1, "+15551234567", "US", "iMessage"),
                (2, "test@example.com", None, "iMessage"),
                (3, "+15559876543", "US", "SMS"),
            ]
            
            cursor.executemany(
                "INSERT INTO handle (ROWID, id, country, service) VALUES (?, ?, ?, ?)",
                test_handles
            )

            # Insert test messages
            # Using Unix timestamp offset for macOS date format
            base_date = 1701432000 - 978307200  # 2023-12-01 12:00:00 in macOS format
            
            test_messages = [
                (1, "msg-001", "Hello, how are you?", None, 1, 0, base_date, "iMessage"),
                (2, "msg-002", "I'm doing well, thanks!", None, None, 1, base_date + 60, "iMessage"),
                (3, "msg-003", None, b"binary_attributed_body_data", 2, 0, base_date + 120, "iMessage"),
                (4, "msg-004", "Meeting at 3pm 📅", None, 1, 0, base_date + 180, "iMessage"),
                (5, "msg-005", "", None, 3, 1, base_date + 240, "SMS"),  # Empty text
                (6, "msg-006", "Long message content that should be preserved during migration and testing", None, 2, 0, base_date + 300, "iMessage"),
            ]
            
            cursor.executemany(
                "INSERT INTO message (ROWID, guid, text, attributedBody, handle_id, is_from_me, date, service) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                test_messages
            )

            # Insert test chat
            cursor.execute(
                "INSERT INTO chat (ROWID, guid, display_name, chat_identifier, service_name) VALUES (?, ?, ?, ?, ?)",
                (1, "chat-001", "Test Chat", "chat001", "iMessage")
            )

            # Link messages to chat
            chat_message_links = [
                (1, 1, base_date),
                (1, 2, base_date + 60),
                (1, 3, base_date + 120),
                (1, 4, base_date + 180),
                (1, 5, base_date + 240),
                (1, 6, base_date + 300),
            ]
            
            cursor.executemany(
                "INSERT INTO chat_message_join (chat_id, message_id, message_date) VALUES (?, ?, ?)",
                chat_message_links
            )

            conn.commit()

    def test_source_database_validation(self):
        """Test validation of source database structure"""
        # Valid database should pass validation
        self.assertTrue(self.migrator.validate_source_database())

        # Test with missing table
        with sqlite3.connect(self.source_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE handle")
            conn.commit()

        self.assertFalse(self.migrator.validate_source_database())

    def test_extract_messages_with_text(self):
        """Test extraction of messages with decoded text"""
        messages = self.migrator.extract_messages_with_text()
        
        # Should extract messages with text content (excluding empty ones)
        self.assertGreater(len(messages), 0)
        
        # Check message structure
        for message in messages:
            self.assertIn("message_id", message)
            self.assertIn("user_id", message)
            self.assertIn("contents", message)
            self.assertIn("is_from_me", message)
            self.assertIn("created_at", message)
            
            # Verify data types
            self.assertIsInstance(message["message_id"], str)
            self.assertIsInstance(message["user_id"], str)
            self.assertIsInstance(message["contents"], str)
            self.assertIsInstance(message["is_from_me"], bool)
            self.assertIsInstance(message["created_at"], str)
            
            # Contents should not be empty after processing
            self.assertNotEqual(message["contents"].strip(), "")

    def test_extract_messages_with_limit(self):
        """Test extraction with message limit"""
        # Extract with limit
        limited_messages = self.migrator.extract_messages_with_text(limit=3)
        self.assertLessEqual(len(limited_messages), 3)
        
        # Extract without limit  
        all_messages = self.migrator.extract_messages_with_text()
        self.assertGreaterEqual(len(all_messages), len(limited_messages))

    def test_text_decoding_integration(self):
        """Test that text decoding is properly integrated"""
        messages = self.migrator.extract_messages_with_text()
        
        # Find message with regular text
        text_message = next((msg for msg in messages if "Hello, how are you?" in msg["contents"]), None)
        self.assertIsNotNone(text_message)
        self.assertEqual(text_message["contents"], "Hello, how are you?")
        
        # Find message with emoji
        emoji_message = next((msg for msg in messages if "📅" in msg["contents"]), None)
        self.assertIsNotNone(emoji_message)
        self.assertIn("Meeting at 3pm 📅", emoji_message["contents"])

    def test_user_id_mapping(self):
        """Test proper mapping of handle_id to user_id"""
        messages = self.migrator.extract_messages_with_text()
        
        # Check that user_ids are properly mapped from handle identifiers
        user_ids = {msg["user_id"] for msg in messages}
        expected_user_ids = {"+15551234567", "test@example.com", "+15559876543"}
        
        # Should have user_ids from handle identifiers
        self.assertTrue(expected_user_ids.issubset(user_ids))

    def test_timestamp_conversion(self):
        """Test proper conversion of macOS timestamps to ISO format"""
        messages = self.migrator.extract_messages_with_text()
        
        for message in messages:
            created_at = message["created_at"]
            
            # Should be valid ISO format timestamp
            try:
                parsed_date = datetime.fromisoformat(created_at)
                self.assertIsInstance(parsed_date, datetime)
            except ValueError:
                self.fail(f"Invalid timestamp format: {created_at}")

    def test_complete_migration(self):
        """Test complete migration process"""
        # Run migration
        success = self.migrator.migrate_messages(batch_size=3, limit=5)
        self.assertTrue(success)
        
        # Verify target database has messages
        messages_db = MessagesDatabase(self.target_db_path)
        migrated_messages = messages_db.get_all_messages()
        
        self.assertGreater(len(migrated_messages), 0)
        self.assertLessEqual(len(migrated_messages), 5)  # Respects limit
        
        # Verify message structure in target database
        for message in migrated_messages:
            self.assertIn("message_id", message)
            self.assertIn("user_id", message)
            self.assertIn("contents", message)
            self.assertIn("is_from_me", message)
            self.assertIn("created_at", message)

    def test_migration_batch_processing(self):
        """Test migration with different batch sizes"""
        # Test with small batch size
        success = self.migrator.migrate_messages(batch_size=2)
        self.assertTrue(success)
        
        messages_db = MessagesDatabase(self.target_db_path)
        migrated_messages = messages_db.get_all_messages()
        self.assertGreater(len(migrated_messages), 0)

    def test_migration_stats(self):
        """Test migration statistics functionality"""
        # Get pre-migration stats
        pre_stats = self.migrator.get_migration_stats()
        self.assertIn("source_stats", pre_stats)
        self.assertIn("target_stats", pre_stats)
        
        # Run migration
        self.migrator.migrate_messages(limit=3)
        
        # Get post-migration stats
        post_stats = self.migrator.get_migration_stats()
        self.assertGreater(post_stats["target_stats"]["total_messages"], 0)

    def test_migration_idempotency(self):
        """Test that running migration multiple times doesn't duplicate data"""
        # Run migration first time
        success1 = self.migrator.migrate_messages(limit=3)
        self.assertTrue(success1)
        
        messages_db = MessagesDatabase(self.target_db_path)
        first_count = len(messages_db.get_all_messages())
        
        # Run migration second time (should clear and re-migrate)
        success2 = self.migrator.migrate_messages(limit=3)
        self.assertTrue(success2)
        
        second_count = len(messages_db.get_all_messages())
        
        # Should have same count (not duplicated)
        self.assertEqual(first_count, second_count)

    def test_migration_with_corrupted_data(self):
        """Test migration handling of corrupted or invalid data"""
        # Add some corrupted data to source database
        with sqlite3.connect(self.source_db_path) as conn:
            cursor = conn.cursor()
            
            # Insert message with NULL text and attributedBody (should be filtered out)
            cursor.execute(
                "INSERT INTO message (ROWID, guid, text, attributedBody, handle_id, is_from_me, date, service) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (100, "corrupt-msg", None, None, 1, 0, 1701432000, "iMessage")
            )
            
            # Insert message with invalid handle_id
            cursor.execute(
                "INSERT INTO message (ROWID, guid, text, attributedBody, handle_id, is_from_me, date, service) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (101, "invalid-handle-msg", "Valid text", None, 999, 0, 1701432000, "iMessage")
            )
            
            conn.commit()
        
        # Migration should still succeed
        success = self.migrator.migrate_messages()
        self.assertTrue(success)
        
        # Should have extracted valid messages
        messages_db = MessagesDatabase(self.target_db_path)
        migrated_messages = messages_db.get_all_messages()
        self.assertGreater(len(migrated_messages), 0)


if __name__ == "__main__":
    unittest.main()