#!/usr/bin/env python3
"""
Unit tests for the messages table functionality in MessagesDatabase.

Tests the new messages table schema, CRUD operations, and integration
with the existing database structure.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import List, Dict, Any

import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from database.messages_db import MessagesDatabase


class TestMessagesTable(unittest.TestCase):
    """Test cases for the new messages table functionality"""

    def setUp(self):
        """Set up test database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.messages_db = MessagesDatabase(self.db_path)
        
        # Create the database with all tables
        self.assertTrue(self.messages_db.create_database())

    def tearDown(self):
        """Clean up after each test"""
        Path(self.db_path).unlink(missing_ok=True)

    def test_messages_table_creation(self):
        """Test that the messages table is created with correct schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
            )
            self.assertIsNotNone(cursor.fetchone())
            
            # Check schema
            cursor.execute("PRAGMA table_info(messages)")
            columns = cursor.fetchall()
            
            # Expected columns: (cid, name, type, notnull, dflt_value, pk)
            expected_columns = {
                "message_id": ("TEXT", 1, 1),  # (type, notnull, pk)
                "user_id": ("TEXT", 1, 0),
                "contents": ("TEXT", 1, 0),
                "is_from_me": ("BOOLEAN", 0, 0),
                "created_at": ("TEXT", 1, 0),
            }
            
            for column in columns:
                cid, name, col_type, notnull, dflt_value, pk = column
                if name in expected_columns:
                    expected_type, expected_notnull, expected_pk = expected_columns[name]
                    self.assertEqual(col_type, expected_type)
                    self.assertEqual(notnull, expected_notnull)
                    self.assertEqual(pk, expected_pk)

    def test_messages_table_indexes(self):
        """Test that proper indexes are created for the messages table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all indexes for messages table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='messages'"
            )
            indexes = {row[0] for row in cursor.fetchall()}
            
            expected_indexes = {
                "idx_messages_message_id",
                "idx_messages_user_id", 
                "idx_messages_created_at",
                "idx_messages_is_from_me"
            }
            
            # Check that all expected indexes exist
            for expected_index in expected_indexes:
                self.assertIn(expected_index, indexes)

    def test_insert_single_message(self):
        """Test inserting a single message"""
        message_data = {
            "message_id": "msg_001",
            "user_id": "user_001", 
            "contents": "Hello, world!",
            "is_from_me": True,
            "created_at": "2023-12-01T10:00:00",
        }
        
        success = self.messages_db.insert_message(**message_data)
        self.assertTrue(success)
        
        # Verify the message was inserted
        retrieved_message = self.messages_db.get_message_by_id("msg_001")
        self.assertIsNotNone(retrieved_message)
        self.assertEqual(retrieved_message["message_id"], "msg_001")
        self.assertEqual(retrieved_message["user_id"], "user_001")
        self.assertEqual(retrieved_message["contents"], "Hello, world!")
        self.assertEqual(retrieved_message["is_from_me"], True)
        self.assertEqual(retrieved_message["created_at"], "2023-12-01T10:00:00")

    def test_insert_message_with_special_characters(self):
        """Test inserting a message with special characters and emojis"""
        message_data = {
            "message_id": "msg_002",
            "user_id": "user_002",
            "contents": "Hello! 👋 This has special chars: 'quotes', \"double quotes\", & ampersands",
            "is_from_me": False,
            "created_at": "2023-12-01T10:01:00",
        }
        
        success = self.messages_db.insert_message(**message_data)
        self.assertTrue(success)
        
        retrieved_message = self.messages_db.get_message_by_id("msg_002")
        self.assertIsNotNone(retrieved_message)
        self.assertEqual(retrieved_message["contents"], message_data["contents"])

    def test_insert_messages_batch(self):
        """Test batch insertion of multiple messages"""
        messages = [
            {
                "message_id": f"msg_{i:03d}",
                "user_id": f"user_{i % 3}",  # 3 different users
                "contents": f"Message content {i}",
                "is_from_me": i % 2 == 0,  # Alternate between True/False
                "created_at": f"2023-12-01T{10 + i // 60:02d}:{i % 60:02d}:00",
            }
            for i in range(10)
        ]
        
        inserted_count = self.messages_db.insert_messages_batch(messages)
        self.assertEqual(inserted_count, 10)
        
        # Verify all messages were inserted
        all_messages = self.messages_db.get_all_messages()
        self.assertEqual(len(all_messages), 10)

    def test_get_message_by_id(self):
        """Test retrieving a message by its ID"""
        # Insert test message
        message_data = {
            "message_id": "test_msg",
            "user_id": "test_user",
            "contents": "Test message content",
            "is_from_me": True,
            "created_at": "2023-12-01T12:00:00",
        }
        self.messages_db.insert_message(**message_data)
        
        # Test successful retrieval
        retrieved = self.messages_db.get_message_by_id("test_msg")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["message_id"], "test_msg")
        
        # Test non-existent message
        non_existent = self.messages_db.get_message_by_id("nonexistent")
        self.assertIsNone(non_existent)

    def test_get_messages_by_user(self):
        """Test retrieving messages for a specific user"""
        # Insert messages for different users
        messages = [
            {"message_id": "msg_1", "user_id": "user_a", "contents": "Message 1", "is_from_me": True, "created_at": "2023-12-01T10:00:00"},
            {"message_id": "msg_2", "user_id": "user_a", "contents": "Message 2", "is_from_me": False, "created_at": "2023-12-01T10:01:00"},
            {"message_id": "msg_3", "user_id": "user_b", "contents": "Message 3", "is_from_me": True, "created_at": "2023-12-01T10:02:00"},
            {"message_id": "msg_4", "user_id": "user_a", "contents": "Message 4", "is_from_me": True, "created_at": "2023-12-01T10:03:00"},
        ]
        
        for msg in messages:
            self.messages_db.insert_message(**msg)
        
        # Get messages for user_a
        user_a_messages = self.messages_db.get_messages_by_user("user_a")
        self.assertEqual(len(user_a_messages), 3)
        
        # Check they're ordered by created_at DESC
        self.assertEqual(user_a_messages[0]["message_id"], "msg_4")  # Most recent
        self.assertEqual(user_a_messages[1]["message_id"], "msg_2")
        self.assertEqual(user_a_messages[2]["message_id"], "msg_1")  # Oldest
        
        # Test with limit
        limited_messages = self.messages_db.get_messages_by_user("user_a", limit=2)
        self.assertEqual(len(limited_messages), 2)
        self.assertEqual(limited_messages[0]["message_id"], "msg_4")

    def test_get_all_messages(self):
        """Test retrieving all messages"""
        # Insert test messages
        messages = [
            {"message_id": f"msg_{i}", "user_id": "user_1", "contents": f"Content {i}", 
             "is_from_me": True, "created_at": f"2023-12-01T10:0{i}:00"}
            for i in range(5)
        ]
        
        for msg in messages:
            self.messages_db.insert_message(**msg)
        
        # Get all messages
        all_messages = self.messages_db.get_all_messages()
        self.assertEqual(len(all_messages), 5)
        
        # Test with limit
        limited_messages = self.messages_db.get_all_messages(limit=3)
        self.assertEqual(len(limited_messages), 3)

    def test_clear_messages_table(self):
        """Test clearing all messages from the table"""
        # Insert test messages
        messages = [
            {"message_id": f"msg_{i}", "user_id": "user_1", "contents": f"Content {i}",
             "is_from_me": True, "created_at": f"2023-12-01T10:0{i}:00"}
            for i in range(3)
        ]
        
        for msg in messages:
            self.messages_db.insert_message(**msg)
        
        # Verify messages exist
        self.assertEqual(len(self.messages_db.get_all_messages()), 3)
        
        # Clear table
        success = self.messages_db.clear_messages_table()
        self.assertTrue(success)
        
        # Verify table is empty
        self.assertEqual(len(self.messages_db.get_all_messages()), 0)

    def test_boolean_handling(self):
        """Test proper handling of boolean values for is_from_me"""
        test_cases = [
            {"is_from_me": True, "expected": True},
            {"is_from_me": False, "expected": False},
            {"is_from_me": 1, "expected": True},
            {"is_from_me": 0, "expected": False},
        ]
        
        for i, case in enumerate(test_cases):
            message_data = {
                "message_id": f"bool_test_{i}",
                "user_id": "test_user",
                "contents": f"Boolean test {i}",
                "is_from_me": case["is_from_me"],
                "created_at": "2023-12-01T12:00:00",
            }
            
            success = self.messages_db.insert_message(**message_data)
            self.assertTrue(success)
            
            retrieved = self.messages_db.get_message_by_id(f"bool_test_{i}")
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["is_from_me"], case["expected"])
            self.assertIsInstance(retrieved["is_from_me"], bool)

    def test_empty_and_whitespace_content(self):
        """Test handling of empty and whitespace-only content"""
        # Empty content should be allowed (will be handled by validation layer)
        message_data = {
            "message_id": "empty_test",
            "user_id": "test_user",
            "contents": "",
            "is_from_me": True,
            "created_at": "2023-12-01T12:00:00",
        }
        
        success = self.messages_db.insert_message(**message_data)
        self.assertTrue(success)
        
        retrieved = self.messages_db.get_message_by_id("empty_test")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["contents"], "")

    def test_large_content(self):
        """Test handling of large message content"""
        # Create a large message (10KB)
        large_content = "A" * 10000
        
        message_data = {
            "message_id": "large_test",
            "user_id": "test_user",
            "contents": large_content,
            "is_from_me": False,
            "created_at": "2023-12-01T12:00:00",
        }
        
        success = self.messages_db.insert_message(**message_data)
        self.assertTrue(success)
        
        retrieved = self.messages_db.get_message_by_id("large_test")
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved["contents"]), 10000)
        self.assertEqual(retrieved["contents"], large_content)

    def test_duplicate_message_id_handling(self):
        """Test handling of duplicate message IDs"""
        message_data = {
            "message_id": "duplicate_test",
            "user_id": "test_user",
            "contents": "First message",
            "is_from_me": True,
            "created_at": "2023-12-01T12:00:00",
        }
        
        # First insertion should succeed
        success1 = self.messages_db.insert_message(**message_data)
        self.assertTrue(success1)
        
        # Second insertion with same message_id should fail
        message_data["contents"] = "Second message"
        success2 = self.messages_db.insert_message(**message_data)
        self.assertFalse(success2)
        
        # Verify original message is still there
        retrieved = self.messages_db.get_message_by_id("duplicate_test")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["contents"], "First message")


if __name__ == "__main__":
    unittest.main()