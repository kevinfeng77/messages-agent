#!/usr/bin/env python3
"""Comprehensive tests for chats table functionality"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from src.database.messages_db import MessagesDatabase
from src.user.user import User


class TestChatsTable(unittest.TestCase):
    """Test cases for chats table creation and operations"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.messages_db = MessagesDatabase(self.db_path)

        # Create the database and tables
        self.assertTrue(self.messages_db.create_database())

    def tearDown(self):
        """Clean up test fixtures"""
        # Remove the temporary database file
        Path(self.db_path).unlink(missing_ok=True)

    def test_chats_table_creation(self):
        """Test that chats table is created with correct schema"""
        # Check that chats table exists
        self.assertTrue(self.messages_db.table_exists("chats"))

        # Check table schema
        schema = self.messages_db.get_table_schema("chats")
        self.assertIsNotNone(schema)

        # Verify columns (users field removed in normalized design)
        column_names = [col[1] for col in schema]
        expected_columns = ["chat_id", "display_name"]

        for col in expected_columns:
            self.assertIn(col, column_names, f"Column {col} not found in chats table")

        # Verify chat_users table exists
        self.assertTrue(self.messages_db.table_exists("chat_users"))

        # Check chat_users schema
        chat_users_schema = self.messages_db.get_table_schema("chat_users")
        self.assertIsNotNone(chat_users_schema)

        chat_users_columns = [col[1] for col in chat_users_schema]
        expected_chat_users_columns = ["chat_id", "user_id"]

        for col in expected_chat_users_columns:
            self.assertIn(
                col, chat_users_columns, f"Column {col} not found in chat_users table"
            )

    def test_insert_single_chat(self):
        """Test inserting a single chat"""
        chat_id = "123"
        display_name = "Test Chat"
        user_ids = ["user1", "user2", "user3"]

        # Insert chat
        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        # Verify chat was inserted
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertIsNotNone(chat)
        self.assertEqual(chat["chat_id"], chat_id)
        self.assertEqual(chat["display_name"], display_name)
        self.assertEqual(chat["user_ids"], user_ids)

    def test_insert_chat_with_empty_users(self):
        """Test inserting a chat with no users"""
        chat_id = "456"
        display_name = "Empty Chat"
        user_ids = []

        # Insert chat
        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        # Verify chat was inserted
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertIsNotNone(chat)
        self.assertEqual(chat["user_ids"], [])

    def test_insert_chats_batch(self):
        """Test batch inserting multiple chats"""
        chats = [
            {
                "chat_id": "100",
                "display_name": "Batch Chat 1",
                "user_ids": ["user1", "user2"],
            },
            {
                "chat_id": "101",
                "display_name": "Batch Chat 2",
                "user_ids": ["user3", "user4", "user5"],
            },
            {"chat_id": "102", "display_name": "Batch Chat 3", "user_ids": []},
        ]

        # Insert chats in batch
        inserted_count = self.messages_db.insert_chats_batch(chats)
        self.assertEqual(inserted_count, 3)

        # Verify each chat was inserted correctly
        for chat_data in chats:
            chat = self.messages_db.get_chat_by_id(chat_data["chat_id"])
            self.assertIsNotNone(chat)
            self.assertEqual(chat["display_name"], chat_data["display_name"])
            self.assertEqual(chat["user_ids"], chat_data["user_ids"])

    def test_get_chat_by_id_not_found(self):
        """Test getting a chat that doesn't exist"""
        chat = self.messages_db.get_chat_by_id("nonexistent")
        self.assertIsNone(chat)

    def test_get_chats_by_display_name(self):
        """Test getting chats by display name"""
        # Insert test chats
        chats = [
            {"chat_id": "200", "display_name": "Unique Chat", "user_ids": ["user1"]},
            {"chat_id": "201", "display_name": "Duplicate Name", "user_ids": ["user2"]},
            {"chat_id": "202", "display_name": "Duplicate Name", "user_ids": ["user3"]},
        ]

        self.messages_db.insert_chats_batch(chats)

        # Test unique display name
        unique_chats = self.messages_db.get_chats_by_display_name("Unique Chat")
        self.assertEqual(len(unique_chats), 1)
        self.assertEqual(unique_chats[0]["chat_id"], "200")

        # Test duplicate display name
        duplicate_chats = self.messages_db.get_chats_by_display_name("Duplicate Name")
        self.assertEqual(len(duplicate_chats), 2)
        chat_ids = [chat["chat_id"] for chat in duplicate_chats]
        self.assertIn("201", chat_ids)
        self.assertIn("202", chat_ids)

        # Test non-existent display name
        empty_chats = self.messages_db.get_chats_by_display_name("Non-existent")
        self.assertEqual(len(empty_chats), 0)

    def test_get_all_chats(self):
        """Test getting all chats"""
        # Initially empty
        all_chats = self.messages_db.get_all_chats()
        self.assertEqual(len(all_chats), 0)

        # Insert test chats
        test_chats = [
            {"chat_id": "300", "display_name": "Chat 1", "user_ids": ["user1"]},
            {"chat_id": "301", "display_name": "Chat 2", "user_ids": ["user2"]},
            {"chat_id": "302", "display_name": "Chat 3", "user_ids": ["user3"]},
        ]

        self.messages_db.insert_chats_batch(test_chats)

        # Test getting all chats
        all_chats = self.messages_db.get_all_chats()
        self.assertEqual(len(all_chats), 3)

        # Test with limit
        limited_chats = self.messages_db.get_all_chats(limit=2)
        self.assertEqual(len(limited_chats), 2)

    def test_clear_chats_table(self):
        """Test clearing the chats table"""
        # Insert test chats
        test_chats = [
            {"chat_id": "400", "display_name": "Chat 1", "user_ids": ["user1"]},
            {"chat_id": "401", "display_name": "Chat 2", "user_ids": ["user2"]},
        ]

        self.messages_db.insert_chats_batch(test_chats)

        # Verify chats exist
        self.assertEqual(len(self.messages_db.get_all_chats()), 2)

        # Clear table
        result = self.messages_db.clear_chats_table()
        self.assertTrue(result)

        # Verify table is empty
        self.assertEqual(len(self.messages_db.get_all_chats()), 0)

    def test_user_ids_normalized_storage(self):
        """Test that user_ids are properly stored in normalized chat_users table"""
        chat_id = "500"
        display_name = "Normalized Storage Test"
        user_ids = ["user_a", "user_b", "user_c"]

        # Insert chat
        self.messages_db.insert_chat(chat_id, display_name, user_ids)

        # Check raw database storage in chat_users table
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM chat_users WHERE chat_id = ? ORDER BY user_id",
                (chat_id,),
            )
            stored_user_ids = [row[0] for row in cursor.fetchall()]

            # Should have all user IDs stored separately
            expected_sorted = sorted(user_ids)
            self.assertEqual(stored_user_ids, expected_sorted)

        # Check that retrieval works correctly
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(sorted(chat["user_ids"]), sorted(user_ids))

    def test_empty_batch_insert(self):
        """Test inserting an empty batch of chats"""
        result = self.messages_db.insert_chats_batch([])
        self.assertEqual(result, 0)

    def test_database_error_handling(self):
        """Test error handling for database operations"""
        # Test with closed database (simulate error)
        with patch.object(sqlite3, "connect", side_effect=sqlite3.Error("Test error")):
            result = self.messages_db.insert_chat("error_test", "Error Chat", ["user1"])
            self.assertFalse(result)

            chat = self.messages_db.get_chat_by_id("error_test")
            self.assertIsNone(chat)


class TestChatMigrationIntegration(unittest.TestCase):
    """Integration tests for chat migration functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary databases
        self.temp_source_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_source_db.close()
        self.source_db_path = self.temp_source_db.name

        self.temp_target_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_target_db.close()
        self.target_db_path = self.temp_target_db.name

        # Create source database with test data
        self._create_source_database()

        # Create target database
        self.messages_db = MessagesDatabase(self.target_db_path)
        self.messages_db.create_database()

    def tearDown(self):
        """Clean up test fixtures"""
        Path(self.source_db_path).unlink(missing_ok=True)
        Path(self.target_db_path).unlink(missing_ok=True)

    def _create_source_database(self):
        """Create a mock source database with chat and chat_handle_join tables"""
        with sqlite3.connect(self.source_db_path) as conn:
            cursor = conn.cursor()

            # Create chat table
            cursor.execute(
                """
                CREATE TABLE chat (
                    ROWID INTEGER PRIMARY KEY,
                    display_name TEXT,
                    chat_identifier TEXT,
                    service_name TEXT
                )
            """
            )

            # Create handle table
            cursor.execute(
                """
                CREATE TABLE handle (
                    ROWID INTEGER PRIMARY KEY,
                    id TEXT NOT NULL,
                    service TEXT NOT NULL
                )
            """
            )

            # Create chat_handle_join table
            cursor.execute(
                """
                CREATE TABLE chat_handle_join (
                    chat_id INTEGER,
                    handle_id INTEGER
                )
            """
            )

            # Insert test data
            # Chat 1: Quantabes
            cursor.execute(
                "INSERT INTO chat VALUES (1, 'Quantabes', '+12345678901', 'iMessage')"
            )
            cursor.execute(
                "INSERT INTO handle VALUES (101, '+12345678901', 'iMessage')"
            )
            cursor.execute(
                "INSERT INTO handle VALUES (102, '+12345678902', 'iMessage')"
            )
            cursor.execute("INSERT INTO chat_handle_join VALUES (1, 101)")
            cursor.execute("INSERT INTO chat_handle_join VALUES (1, 102)")

            # Chat 2: Test Group
            cursor.execute(
                "INSERT INTO chat VALUES (2, 'Test Group', 'chat123', 'iMessage')"
            )
            cursor.execute(
                "INSERT INTO handle VALUES (103, '+12345678903', 'iMessage')"
            )
            cursor.execute("INSERT INTO chat_handle_join VALUES (2, 103)")

            conn.commit()

    def _create_test_users(self):
        """Create test users in target database"""
        test_users = [
            User("user1", "John", "Wang", "+12345678901", "john@example.com", 101),
            User("user2", "Eric", "Mueller", "+12345678902", "eric@example.com", 102),
            User("user3", "Test", "User", "+12345678903", "test@example.com", 103),
        ]

        for user in test_users:
            self.messages_db.insert_user(user)

    def test_migration_with_users(self):
        """Test full migration process with user mapping"""
        # Import here to avoid circular imports in test setup
        from scripts.migration.migrate_chats import ChatMigrator

        # Create test users
        self._create_test_users()

        # Run migration
        migrator = ChatMigrator(self.source_db_path, self.target_db_path)
        success = migrator.migrate_chats()
        self.assertTrue(success)

        # Verify results
        all_chats = self.messages_db.get_all_chats()
        self.assertEqual(len(all_chats), 2)

        # Find Quantabes chat
        quantabes_chats = [c for c in all_chats if c["display_name"] == "Quantabes"]
        self.assertEqual(len(quantabes_chats), 1)

        quantabes_chat = quantabes_chats[0]
        self.assertEqual(len(quantabes_chat["user_ids"]), 2)
        self.assertIn("user1", quantabes_chat["user_ids"])  # John Wang
        self.assertIn("user2", quantabes_chat["user_ids"])  # Eric Mueller

    def test_migration_stats(self):
        """Test migration statistics generation"""
        from scripts.migration.migrate_chats import ChatMigrator

        self._create_test_users()

        migrator = ChatMigrator(self.source_db_path, self.target_db_path)
        migrator.migrate_chats()

        stats = migrator.get_migration_stats()

        self.assertIn("source", stats)
        self.assertIn("target", stats)
        self.assertEqual(stats["source"]["total_chats"], 2)
        self.assertEqual(stats["target"]["migrated_chats"], 2)
        self.assertEqual(stats["migration_success_rate"], 100.0)

    def test_validation_script(self):
        """Test the validation script functionality"""
        from scripts.validation.validate_chat_migration import ChatMigrationValidator

        # Set up data
        self._create_test_users()

        # Run migration first
        from scripts.migration.migrate_chats import ChatMigrator

        migrator = ChatMigrator(self.source_db_path, self.target_db_path)
        migrator.migrate_chats()

        # Run validation
        validator = ChatMigrationValidator(self.source_db_path, self.target_db_path)

        # Test Quantabes validation
        quantabes_valid = validator.validate_quantabes_chat()
        self.assertTrue(quantabes_valid)

        # Test completeness validation
        completeness = validator.validate_migration_completeness()
        if not completeness["validation_passed"]:
            print(f"Validation errors: {completeness.get('errors', [])}")
            print(f"Validation warnings: {completeness.get('warnings', [])}")
        self.assertTrue(completeness["validation_passed"])

        # Test sample retrieval
        samples = validator.get_chat_samples(limit=2)
        self.assertEqual(len(samples), 2)


if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)
