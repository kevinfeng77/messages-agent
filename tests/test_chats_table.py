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
        chat_id = 123
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
        chat_id = 456
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
        chat = self.messages_db.get_chat_by_id(99999)
        self.assertIsNone(chat)

    def test_get_chats_by_display_name(self):
        """Test getting chats by display name"""
        # Insert test chats
        chats = [
            {"chat_id": 200, "display_name": "Unique Chat", "user_ids": ["user1"]},
            {"chat_id": 201, "display_name": "Duplicate Name", "user_ids": ["user2"]},
            {"chat_id": 202, "display_name": "Duplicate Name", "user_ids": ["user3"]},
        ]

        self.messages_db.insert_chats_batch(chats)

        # Test unique display name
        unique_chats = self.messages_db.get_chats_by_display_name("Unique Chat")
        self.assertEqual(len(unique_chats), 1)
        self.assertEqual(unique_chats[0]["chat_id"], 200)

        # Test duplicate display name
        duplicate_chats = self.messages_db.get_chats_by_display_name("Duplicate Name")
        self.assertEqual(len(duplicate_chats), 2)
        chat_ids = [chat["chat_id"] for chat in duplicate_chats]
        self.assertIn(201, chat_ids)
        self.assertIn(202, chat_ids)

        # Test non-existent display name
        empty_chats = self.messages_db.get_chats_by_display_name("Non-existent")
        self.assertEqual(len(empty_chats), 0)

    def test_get_chats_by_display_name_ordered_by_message_count(self):
        """Test that chats with duplicate display names are ordered by message count (highest first)"""
        # Insert test chats with duplicate display names
        chats = [
            {"chat_id": 250, "display_name": "Message Count Test", "user_ids": ["user1"]},
            {"chat_id": 251, "display_name": "Message Count Test", "user_ids": ["user2"]},
            {"chat_id": 252, "display_name": "Message Count Test", "user_ids": ["user3"]},
        ]
        self.messages_db.insert_chats_batch(chats)

        # Insert some test users and messages to create different message counts
        from src.user.user import User
        users = [
            User("user1", "User", "One", "+1111111111", "user1@example.com", 1),
            User("user2", "User", "Two", "+2222222222", "user2@example.com", 2),
            User("user3", "User", "Three", "+3333333333", "user3@example.com", 3),
        ]
        for user in users:
            self.messages_db.insert_user(user)

        # Insert messages for each chat to create different message counts
        # Chat 250: 1 message
        messages_250 = [{"message_id": "msg1", "user_id": "user1", "contents": "Hello", "is_from_me": 0, "created_at": 1000}]
        self.messages_db.insert_messages_batch(messages_250)
        chat_messages_250 = [{"chat_id": 250, "message_id": "msg1", "message_date": 1000}]
        self.messages_db.insert_chat_messages_batch(chat_messages_250)

        # Chat 251: 3 messages (highest count)
        messages_251 = [
            {"message_id": "msg2", "user_id": "user2", "contents": "Hi", "is_from_me": 0, "created_at": 2000},
            {"message_id": "msg3", "user_id": "user2", "contents": "How are you?", "is_from_me": 0, "created_at": 3000},
            {"message_id": "msg4", "user_id": "user2", "contents": "Great!", "is_from_me": 1, "created_at": 4000},
        ]
        self.messages_db.insert_messages_batch(messages_251)
        chat_messages_251 = [
            {"chat_id": 251, "message_id": "msg2", "message_date": 2000},
            {"chat_id": 251, "message_id": "msg3", "message_date": 3000},
            {"chat_id": 251, "message_id": "msg4", "message_date": 4000},
        ]
        self.messages_db.insert_chat_messages_batch(chat_messages_251)

        # Chat 252: 2 messages
        messages_252 = [
            {"message_id": "msg5", "user_id": "user3", "contents": "Test", "is_from_me": 0, "created_at": 5000},
            {"message_id": "msg6", "user_id": "user3", "contents": "Message", "is_from_me": 1, "created_at": 6000},
        ]
        self.messages_db.insert_messages_batch(messages_252)
        chat_messages_252 = [
            {"chat_id": 252, "message_id": "msg5", "message_date": 5000},
            {"chat_id": 252, "message_id": "msg6", "message_date": 6000},
        ]
        self.messages_db.insert_chat_messages_batch(chat_messages_252)

        # Get chats by display name - should be ordered by message count (highest first)
        ordered_chats = self.messages_db.get_chats_by_display_name("Message Count Test")
        
        # Verify all 3 chats are returned
        self.assertEqual(len(ordered_chats), 3)
        
        # Verify they are ordered by message count (highest first)
        # Chat 251 has 3 messages (should be first)
        # Chat 252 has 2 messages (should be second)  
        # Chat 250 has 1 message (should be third)
        self.assertEqual(ordered_chats[0]["chat_id"], 251)
        self.assertEqual(ordered_chats[0]["message_count"], 3)
        
        self.assertEqual(ordered_chats[1]["chat_id"], 252)
        self.assertEqual(ordered_chats[1]["message_count"], 2)
        
        self.assertEqual(ordered_chats[2]["chat_id"], 250)
        self.assertEqual(ordered_chats[2]["message_count"], 1)

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
        chat_id = 500
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

    def test_chat_user_relationship_validation(self):
        """Test that chats maintain correct user relationships"""
        # Create test users
        self._create_test_users()

        # Create a chat with specific users (simulating what the legacy migration would do)
        chat_id = 100
        display_name = "Quantabes"
        user_ids = ["user1", "user2"]  # John Wang, Eric Mueller
        
        # Insert the chat
        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        # Verify the chat was created correctly
        all_chats = self.messages_db.get_all_chats()
        quantabes_chats = [c for c in all_chats if c["display_name"] == "Quantabes"]
        self.assertEqual(len(quantabes_chats), 1)

        quantabes_chat = quantabes_chats[0]
        self.assertEqual(len(quantabes_chat["user_ids"]), 2)
        self.assertIn("user1", quantabes_chat["user_ids"])  # John Wang
        self.assertIn("user2", quantabes_chat["user_ids"])  # Eric Mueller
        
        # Verify user details are correct
        all_users = self.messages_db.get_all_users()
        user_dict = {user.user_id: user for user in all_users}
        
        self.assertEqual(user_dict["user1"].first_name, "John")
        self.assertEqual(user_dict["user1"].last_name, "Wang")
        self.assertEqual(user_dict["user2"].first_name, "Eric")
        self.assertEqual(user_dict["user2"].last_name, "Mueller")

    def test_database_statistics_tracking(self):
        """Test that database maintains accurate counts and statistics"""
        # Create test users
        self._create_test_users()
        
        # Create multiple chats with different user configurations
        test_chats = [
            {"chat_id": 101, "display_name": "Quantabes", "user_ids": ["user1", "user2"]},
            {"chat_id": 102, "display_name": "Test Group", "user_ids": ["user3"]},
        ]
        
        for chat_data in test_chats:
            result = self.messages_db.insert_chat(
                chat_data["chat_id"], 
                chat_data["display_name"], 
                chat_data["user_ids"]
            )
            self.assertTrue(result)

        # Verify statistics
        all_chats = self.messages_db.get_all_chats()
        all_users = self.messages_db.get_all_users()
        
        # Should have 2 chats and 3 users
        self.assertEqual(len(all_chats), 2)
        self.assertEqual(len(all_users), 3)
        
        # Verify chat counts by user participation
        quantabes_chat = next(c for c in all_chats if c["display_name"] == "Quantabes")
        test_group_chat = next(c for c in all_chats if c["display_name"] == "Test Group")
        
        self.assertEqual(len(quantabes_chat["user_ids"]), 2)
        self.assertEqual(len(test_group_chat["user_ids"]), 1)
        
        # Test data integrity - all referenced users should exist
        all_user_ids = {user.user_id for user in all_users}
        for chat in all_chats:
            for user_id in chat["user_ids"]:
                self.assertIn(user_id, all_user_ids, f"User {user_id} referenced in chat but doesn't exist")

    def test_data_validation_requirements(self):
        """Test specific data validation requirements using the existing validator"""
        from scripts.validation.validate_chat_migration import ChatMigrationValidator

        # Set up data using modern database operations
        self._create_test_users()
        
        # Create the Quantabes chat that the validator expects
        quantabes_chat_id = 100
        result = self.messages_db.insert_chat(
            quantabes_chat_id, 
            "Quantabes", 
            ["user1", "user2"]  # John Wang and Eric Mueller
        )
        self.assertTrue(result)
        
        # Create additional test chat for completeness
        test_chat_id = 101
        result = self.messages_db.insert_chat(
            test_chat_id,
            "Test Group", 
            ["user3"]
        )
        self.assertTrue(result)

        # Use the existing validator to test data quality
        validator = ChatMigrationValidator(self.source_db_path, self.target_db_path)

        # Test Quantabes-specific validation (this validates the business logic)
        quantabes_valid = validator.validate_quantabes_chat()
        self.assertTrue(quantabes_valid, "Quantabes chat validation should pass with John Wang and Eric Mueller")

        # Test that the validator can retrieve chat samples correctly
        all_chats = self.messages_db.get_all_chats()
        self.assertGreaterEqual(len(all_chats), 2, "Should have at least 2 chats for testing")
        
        # Verify that the specific users we expect are in the Quantabes chat
        quantabes_chats = self.messages_db.get_chats_by_display_name("Quantabes")
        self.assertEqual(len(quantabes_chats), 1, "Should have exactly one Quantabes chat")
        
        quantabes_chat = quantabes_chats[0]
        user_ids = quantabes_chat["user_ids"]
        
        # Get the actual user details to verify names
        users_in_chat = []
        for user_id in user_ids:
            user = self.messages_db.get_user_by_id(user_id)
            if user:
                users_in_chat.append(f"{user.first_name} {user.last_name}")
        
        self.assertIn("John Wang", users_in_chat, "John Wang should be in Quantabes chat")
        self.assertIn("Eric Mueller", users_in_chat, "Eric Mueller should be in Quantabes chat")


if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)
