#!/usr/bin/env python3
"""Unit tests for MessagesDatabase chat functionality"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

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

        # Check for required columns
        columns = [col[1] for col in schema]
        self.assertIn("chat_id", columns)
        self.assertIn("display_name", columns)
        self.assertIn("users", columns)

    def test_chats_table_indexes(self):
        """Test that proper indexes are created for chats table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check for indexes
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='chats'
            """
            )
            indexes = [row[0] for row in cursor.fetchall()]

            # Should have indexes on chat_id and display_name
            index_names = ["idx_chats_chat_id", "idx_chats_display_name"]
            for index_name in index_names:
                self.assertIn(index_name, indexes, f"Missing index: {index_name}")

    def test_insert_chat_basic(self):
        """Test basic chat insertion"""
        chat_id = "test_chat_1"
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
        chat_id = "special_chat"
        display_name = "Chat with 🎉 emojis & symbols!"
        user_ids = ["user@domain.com", "user+tag@example.org"]

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(chat["display_name"], display_name)
        self.assertEqual(chat["user_ids"], user_ids)

    def test_insert_chat_empty_user_list(self):
        """Test inserting chat with empty user list"""
        chat_id = "empty_chat"
        display_name = "Empty Chat"
        user_ids = []

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(chat["user_ids"], [])

    def test_insert_chat_none_user_list(self):
        """Test inserting chat with None as user list"""
        chat_id = "none_chat"
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
                "chat_id": "batch1",
                "display_name": "Batch Chat 1",
                "user_ids": ["u1", "u2"],
            },
            {"chat_id": "batch2", "display_name": "Batch Chat 2", "user_ids": ["u3"]},
            {"chat_id": "batch3", "display_name": "Batch Chat 3", "user_ids": []},
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
        chat = self.messages_db.get_chat_by_id("nonexistent")
        self.assertIsNone(chat)

    def test_get_chats_by_display_name_exact_match(self):
        """Test getting chats by exact display name match"""
        # Insert test chats
        test_chats = [
            {"chat_id": "exact1", "display_name": "Exact Match", "user_ids": ["u1"]},
            {
                "chat_id": "exact2",
                "display_name": "exact match",
                "user_ids": ["u2"],
            },  # Different case
            {
                "chat_id": "exact3",
                "display_name": "Exact Match",
                "user_ids": ["u3"],
            },  # Duplicate
        ]

        self.messages_db.insert_chats_batch(test_chats)

        # Test exact case match
        matches = self.messages_db.get_chats_by_display_name("Exact Match")
        self.assertEqual(len(matches), 2)  # Should match exact1 and exact3

        chat_ids = [chat["chat_id"] for chat in matches]
        self.assertIn("exact1", chat_ids)
        self.assertIn("exact3", chat_ids)
        self.assertNotIn("exact2", chat_ids)  # Different case

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
            {"chat_id": "all1", "display_name": "Chat 1", "user_ids": ["u1"]},
            {"chat_id": "all2", "display_name": "Chat 2", "user_ids": ["u2"]},
            {"chat_id": "all3", "display_name": "Chat 3", "user_ids": ["u3"]},
        ]

        self.messages_db.insert_chats_batch(test_chats)

        chats = self.messages_db.get_all_chats()
        self.assertEqual(len(chats), 3)

    def test_get_all_chats_with_limit(self):
        """Test getting all chats with limit"""
        # Insert 5 test chats
        test_chats = [
            {"chat_id": f"limit{i}", "display_name": f"Chat {i}", "user_ids": [f"u{i}"]}
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
            {"chat_id": "clear1", "display_name": "Chat 1", "user_ids": ["u1"]},
            {"chat_id": "clear2", "display_name": "Chat 2", "user_ids": ["u2"]},
        ]

        self.messages_db.insert_chats_batch(test_chats)

        # Verify data exists
        self.assertEqual(len(self.messages_db.get_all_chats()), 2)

        # Clear table
        result = self.messages_db.clear_chats_table()
        self.assertTrue(result)

        # Verify table is empty
        self.assertEqual(len(self.messages_db.get_all_chats()), 0)

    def test_user_ids_comma_separation(self):
        """Test that user IDs are properly stored as comma-separated values"""
        chat_id = "comma_test"
        display_name = "Comma Test"
        user_ids = ["user,with,commas", "normal_user", "user@email.com"]

        # Insert chat
        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        # Check raw storage in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT users FROM chats WHERE chat_id = ?", (chat_id,))
            raw_users = cursor.fetchone()[0]

            # Should be pipe-separated
            expected = "user,with,commas|normal_user|user@email.com"
            self.assertEqual(raw_users, expected)

        # Check retrieval still works correctly
        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(chat["user_ids"], user_ids)

    def test_large_user_list(self):
        """Test handling of large user lists"""
        chat_id = "large_test"
        display_name = "Large User List"
        user_ids = [f"user_{i}" for i in range(100)]  # 100 users

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(len(chat["user_ids"]), 100)
        self.assertEqual(chat["user_ids"], user_ids)

    def test_unicode_handling(self):
        """Test handling of Unicode characters in chat data"""
        chat_id = "unicode_test"
        display_name = "Unicode Test 中文 ñäñó 🚀"
        user_ids = ["用户1", "usuário2", "пользователь3"]

        result = self.messages_db.insert_chat(chat_id, display_name, user_ids)
        self.assertTrue(result)

        chat = self.messages_db.get_chat_by_id(chat_id)
        self.assertEqual(chat["display_name"], display_name)
        self.assertEqual(chat["user_ids"], user_ids)

    def test_concurrent_access(self):
        """Test basic concurrent access patterns"""
        import threading
        import time

        results = []

        def insert_chat(thread_id):
            chat_id = f"thread_{thread_id}"
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
