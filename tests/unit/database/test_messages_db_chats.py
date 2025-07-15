#!/usr/bin/env python3
"""Unit tests for MessagesDatabase chat functionality"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.database.messages_db import MessagesDatabase


class TestMessagesDatabaseChats(unittest.TestCase):
    """Unit tests for chat-related functionality in MessagesDatabase"""

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

    def test_database_creation_includes_chats_table(self):
        """Test that create_database() creates chats table"""
        # Check that chats table exists
        self.assertTrue(self.messages_db.table_exists("chats"))

        # Check schema
        schema = self.messages_db.get_table_schema("chats")
        self.assertIsNotNone(schema)

        # Check for required columns (users field removed in normalized design)
        columns = [col[1] for col in schema]
        self.assertIn("chat_id", columns)
        self.assertIn("display_name", columns)
        self.assertNotIn("users", columns)  # Should not have users field anymore

    def test_database_creation_includes_chat_users_table(self):
        """Test that create_database() creates chat_users junction table"""
        # Check that chat_users table exists
        self.assertTrue(self.messages_db.table_exists("chat_users"))

        # Check schema
        schema = self.messages_db.get_table_schema("chat_users")
        self.assertIsNotNone(schema)

        # Check for required columns
        columns = [col[1] for col in schema]
        self.assertIn("chat_id", columns)
        self.assertIn("user_id", columns)

    def test_chats_table_indexes(self):
        """Test that proper indexes are created for chats and chat_users tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check for chats table indexes
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='chats'
            """
            )
            chats_indexes = [row[0] for row in cursor.fetchall()]

            # Should have index on display_name (chat_id is primary key so doesn't need explicit index)
            expected_chats_indexes = ["idx_chats_display_name"]
            for index_name in expected_chats_indexes:
                self.assertIn(
                    index_name, chats_indexes, f"Missing chats index: {index_name}"
                )

            # Check for chat_users table indexes
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='chat_users'
            """
            )
            chat_users_indexes = [row[0] for row in cursor.fetchall()]

            # Should have indexes on both chat_id and user_id
            expected_chat_users_indexes = [
                "idx_chat_users_chat_id",
                "idx_chat_users_user_id",
            ]
            for index_name in expected_chat_users_indexes:
                self.assertIn(
                    index_name,
                    chat_users_indexes,
                    f"Missing chat_users index: {index_name}",
                )

    def test_insert_chat_basic(self):
        """Test basic chat insertion"""
        chat_id = 12345
        display_name = "Test Chat"
        user_ids = ["user1", "user2"]

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        # Verify insertion
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertIsNotNone(chat)
        self.assertEqual(chat["chat_id"], chat_id)
        self.assertEqual(chat["display_name"], display_name)
        self.assertEqual(chat["user_ids"], user_ids)

    def test_insert_chat_special_characters(self):
        """Test chat insertion with special characters"""
        chat_id = 20001
        display_name = "Chat with 🎉 emojis & symbols!"
        user_ids = ["user@domain.com", "user+tag@example.org"]

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(chat["display_name"], display_name)
        self.assertEqual(sorted(chat["user_ids"]), sorted(user_ids))

    def test_insert_chat_empty_user_list(self):
        """Test inserting chat with empty user list"""
        chat_id = 20002
        display_name = "Empty Chat"
        user_ids = []

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(chat["user_ids"], [])

    def test_insert_chat_none_user_list(self):
        """Test inserting chat with None as user list"""
        chat_id = 20003
        display_name = "None Users Chat"
        user_ids = None

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(chat["user_ids"], [])

    def test_insert_chats_batch_success(self):
        """Test successful batch insertion of chats"""
        chats = [
            {
                "chat_id": 20004,
                "display_name": "Batch Chat 1",
                "user_ids": ["u1", "u2"],
            },
            {"chat_id": 20005, "display_name": "Batch Chat 2", "user_ids": ["u3"]},
            {"chat_id": 20006, "display_name": "Batch Chat 3", "user_ids": []},
        ]

        count = self.messages_db.insert_chats_batch(chats)
        self.assertEqual(count, 3)

        # Verify all chats were inserted
        for chat_data in chats:
            chat = self.messages_db.get_chat_by_id(chat_data["chat_id"])
            self.assertIsNotNone(chat)
            self.assertEqual(chat["display_name"], chat_data["display_name"])
            self.assertEqual(chat["user_ids"], chat_data["user_ids"])

    def test_insert_chats_batch_empty(self):
        """Test batch insertion with empty list"""
        count = self.messages_db.insert_chats_batch([])
        self.assertEqual(count, 0)

    def test_get_chat_by_id_not_found(self):
        """Test getting non-existent chat"""
        chat = self.messages_db.get_chat_by_id(99999)
        self.assertIsNone(chat)

    def test_get_chats_by_display_name_exact_match(self):
        """Test getting chats by exact display name match"""
        # Insert test chats
        test_chats = [
            {"chat_id": 20007, "display_name": "Exact Match", "user_ids": ["u1"]},
            {
                "chat_id": 20008,
                "display_name": "exact match",
                "user_ids": ["u2"],
            },  # Different case
            {
                "chat_id": 20009,
                "display_name": "Exact Match",
                "user_ids": ["u3"],
            },  # Duplicate
        ]

        self.messages_db.insert_chats_batch(test_chats)

        # Test exact case match
        matches = self.messages_db.get_chats_by_display_name("Exact Match")
        self.assertEqual(len(matches), 2)  # Should match exact1 and exact3

        chat_ids = [chat["chat_id"] for chat in matches]
        self.assertIn(20007, chat_ids)
        self.assertIn(20009, chat_ids)
        self.assertNotIn(20008, chat_ids)  # Different case

    def test_get_chats_by_display_name_no_match(self):
        """Test getting chats with non-existent display name"""
        matches = self.messages_db.get_chats_by_display_name("Non-existent Chat")
        self.assertEqual(len(matches), 0)

    def test_get_all_chats_empty(self):
        """Test getting all chats when table is empty"""
        chats = self.messages_db.get_all_chats()
        self.assertEqual(len(chats), 0)

    def test_get_all_chats_with_data(self):
        """Test getting all chats with data"""
        # Insert test chats
        test_chats = [
            {"chat_id": 20010, "display_name": "Chat 1", "user_ids": ["u1"]},
            {"chat_id": 20011, "display_name": "Chat 2", "user_ids": ["u2"]},
            {"chat_id": 20012, "display_name": "Chat 3", "user_ids": ["u3"]},
        ]

        self.messages_db.insert_chats_batch(test_chats)

        chats = self.messages_db.get_all_chats()
        self.assertEqual(len(chats), 3)

    def test_get_all_chats_with_limit(self):
        """Test getting all chats with limit"""
        # Insert 5 test chats
        test_chats = [
            {"chat_id": 20013 + i, "display_name": f"Chat {i}", "user_ids": [f"u{i}"]}
            for i in range(5)
        ]

        self.messages_db.insert_chats_batch(test_chats)

        # Test limit
        chats = self.messages_db.get_all_chats(limit=3)
        self.assertEqual(len(chats), 3)

    def test_clear_chats_table_empty(self):
        """Test clearing empty chats table"""
        result = self.messages_db.clear_chats_table()
        self.assertTrue(result)

    def test_clear_chats_table_with_data(self):
        """Test clearing chats table with data"""
        # Insert test chats
        test_chats = [
            {"chat_id": 20018, "display_name": "Chat 1", "user_ids": ["u1"]},
            {"chat_id": 20019, "display_name": "Chat 2", "user_ids": ["u2"]},
        ]

        self.messages_db.insert_chats_batch(test_chats)

        # Verify data exists
        self.assertEqual(len(self.messages_db.get_all_chats()), 2)

        # Clear table
        result = self.messages_db.clear_chats_table()
        self.assertTrue(result)

        # Verify table is empty
        self.assertEqual(len(self.messages_db.get_all_chats()), 0)

    def test_user_ids_normalized_storage(self):
        """Test that user IDs are properly stored in normalized chat_users table"""
        chat_id = 20020
        display_name = "Normalized Test"
        user_ids = ["user,with,commas", "normal_user", "user@email.com"]

        # Insert chat
        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        # Check raw storage in chat_users table
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM chat_users WHERE chat_id = ? ORDER BY user_id",
                (chat_id,),
            )
            stored_user_ids = [row[0] for row in cursor.fetchall()]

            # Should have all user IDs stored correctly
            expected_sorted = sorted(user_ids)
            self.assertEqual(stored_user_ids, expected_sorted)

        # Check retrieval still works correctly
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(sorted(chat["user_ids"]), sorted(user_ids))

    def test_large_user_list(self):
        """Test handling of large user lists"""
        chat_id = 20021
        display_name = "Large User List"
        user_ids = [f"user_{i}" for i in range(100)]  # 100 users

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(len(chat["user_ids"]), 100)
        self.assertEqual(sorted(chat["user_ids"]), sorted(user_ids))

    def test_unicode_handling(self):
        """Test handling of Unicode characters in chat data"""
        chat_id = 20022
        display_name = "Unicode Test 中文 ñäñó 🚀"
        user_ids = ["用户1", "usuário2", "пользователь3"]

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(chat["display_name"], display_name)
        self.assertEqual(sorted(chat["user_ids"]), sorted(user_ids))

    def test_concurrent_access(self):
        """Test basic concurrent access patterns"""
        import threading
        import time

        results = []

        def insert_chat(thread_id):
            chat_id = 20023 + thread_id
            display_name = f"Thread Chat {thread_id}"
            user_ids = [f"user_{thread_id}"]

            result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
            results.append((thread_id, result))

        # Create and start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=insert_chat, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all insertions succeeded
        self.assertEqual(len(results), 5)
        for thread_id, result in results:
            self.assertTrue(result, f"Thread {thread_id} failed")

        # Verify all chats are in database
        all_chats = self.messages_db.get_all_chats()
        self.assertEqual(len(all_chats), 5)

    def test_add_user_to_chat(self):
        """Test adding a user to an existing chat"""
        chat_id = 20028
        display_name = "Add User Test"
        initial_users = ["user1", "user2"]

        # Create chat with initial users
        result = self.messages_db.insert_chat(chat_id, display_name, initial_users)
        self.assertTrue(result)

        # Add a new user
        result = self.messages_db.add_user_to_chat(chat_id, "user3")
        self.assertTrue(result)

        # Verify user was added
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertIn("user3", chat["user_ids"])
        self.assertEqual(len(chat["user_ids"]), 3)

        # Test adding duplicate user (should not fail due to INSERT OR IGNORE)
        result = self.messages_db.add_user_to_chat(chat_id, "user1")
        self.assertTrue(result)

        # Should still have only 3 users
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(len(chat["user_ids"]), 3)

    def test_remove_user_from_chat(self):
        """Test removing a user from a chat"""
        chat_id = 20029
        display_name = "Remove User Test"
        initial_users = ["user1", "user2", "user3"]

        # Create chat with users
        result = self.messages_db.insert_chat(chat_id, display_name, initial_users)
        self.assertTrue(result)

        # Remove a user
        result = self.messages_db.remove_user_from_chat(chat_id, "user2")
        self.assertTrue(result)

        # Verify user was removed
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertNotIn("user2", chat["user_ids"])
        self.assertEqual(len(chat["user_ids"]), 2)

        # Test removing non-existent user (should not fail)
        result = self.messages_db.remove_user_from_chat(chat_id, "nonexistent")
        self.assertTrue(result)

    def test_get_chats_for_user(self):
        """Test getting all chats for a specific user"""
        # Create multiple chats with different user combinations
        chats_data = [
            {
                "chat_id": 20030,
                "display_name": "Chat 1",
                "user_ids": ["user1", "user2"],
            },
            {
                "chat_id": 20031,
                "display_name": "Chat 2",
                "user_ids": ["user1", "user3"],
            },
            {
                "chat_id": 20032,
                "display_name": "Chat 3",
                "user_ids": ["user2", "user3"],
            },
            {"chat_id": 20033, "display_name": "Chat 4", "user_ids": ["user4"]},
        ]

        self.messages_db.insert_chats_batch(chats_data)

        # Get chats for user1
        user1_chats = self.messages_db.get_chats_for_user("user1")
        self.assertEqual(len(user1_chats), 2)
        chat_ids = [chat["chat_id"] for chat in user1_chats]
        self.assertIn(20030, chat_ids)
        self.assertIn(20031, chat_ids)

        # Get chats for user4
        user4_chats = self.messages_db.get_chats_for_user("user4")
        self.assertEqual(len(user4_chats), 1)
        self.assertEqual(user4_chats[0]["chat_id"], 20033)

        # Get chats for non-existent user
        empty_chats = self.messages_db.get_chats_for_user("nonexistent")
        self.assertEqual(len(empty_chats), 0)

    def test_get_chat_users_with_details(self):
        """Test getting full user details for chat participants"""
        # First create some users in the users table
        from src.user.user import User

        test_users = [
            User("user1", "John", "Doe", "+1234567890", "john@example.com", None),
            User("user2", "Jane", "Smith", "+9876543210", "jane@example.com", None),
        ]

        for user in test_users:
            self.messages_db.insert_user(user)

        # Create a chat with these users
        chat_id = 20034
        display_name = "Details Test"
        user_ids = ["user1", "user2"]

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        # Get user details for the chat
        user_details = self.messages_db.get_chat_users_with_details(chat_id)
        self.assertEqual(len(user_details), 2)

        # Verify details are correct
        user_names = [
            f"{user['first_name']} {user['last_name']}" for user in user_details
        ]
        self.assertIn("John Doe", user_names)
        self.assertIn("Jane Smith", user_names)

        # Test with chat that has no users
        empty_chat_id = 20035
        self.messages_db.insert_chat(empty_chat_id, "Empty Details Test", [])
        empty_details = self.messages_db.get_chat_users_with_details(empty_chat_id)
        self.assertEqual(len(empty_details), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
