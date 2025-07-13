#!/usr/bin/env python3
"""Unit tests for core chat history retrieval functionality."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from src.message_maker.chat_history import get_chat_history_for_message_generation
from src.message_maker.types import ChatMessage
from src.database.messages_db import MessagesDatabase


class TestChatHistoryFunction(unittest.TestCase):
    """Unit tests for get_chat_history_for_message_generation function."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Initialize database
        self.messages_db = MessagesDatabase(self.db_path)
        self.assertTrue(self.messages_db.create_database())

        # Set up test data
        self._setup_test_data()

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary database file
        Path(self.db_path).unlink(missing_ok=True)

    def _setup_test_data(self):
        """Set up test data in the database."""
        # Insert test users
        test_users = [
            {
                "user_id": "user1",
                "first_name": "Alice",
                "last_name": "Smith",
                "phone_number": "+1234567890",
                "email": "alice@example.com",
                "handle_id": 1
            },
            {
                "user_id": "user2", 
                "first_name": "Bob",
                "last_name": "Jones",
                "phone_number": "+1987654321",
                "email": "bob@example.com",
                "handle_id": 2
            }
        ]

        for user_data in test_users:
            from src.user.user import User
            user = User(**user_data)
            self.messages_db.insert_user(user)

        # Insert test chat
        self.test_chat_id = 123
        self.messages_db.insert_chat(
            chat_id=self.test_chat_id,
            display_name="Test Chat",
            user_ids=["user1", "user2"]
        )

        # Insert test messages
        test_messages = [
            {
                "message_id": 1,
                "user_id": "user1",
                "contents": "Hello there!",
                "is_from_me": True,
                "created_at": "2023-01-01T10:00:00Z"
            },
            {
                "message_id": 2,
                "user_id": "user2", 
                "contents": "Hi! How are you?",
                "is_from_me": False,
                "created_at": "2023-01-01T10:01:00Z"
            },
            {
                "message_id": 3,
                "user_id": "user1",
                "contents": "I'm doing great, thanks!",
                "is_from_me": True,
                "created_at": "2023-01-01T10:02:00Z"
            },
            {
                "message_id": 4,
                "user_id": "user2",
                "contents": "That's wonderful to hear!",
                "is_from_me": False,
                "created_at": "2023-01-01T10:03:00Z"
            }
        ]

        for msg in test_messages:
            self.messages_db.insert_message(**msg)

        # Insert chat-message relationships
        chat_messages = [
            {
                "chat_id": self.test_chat_id,
                "message_id": 1,
                "message_date": "2023-01-01T10:00:00Z"
            },
            {
                "chat_id": self.test_chat_id,
                "message_id": 2,
                "message_date": "2023-01-01T10:01:00Z"
            },
            {
                "chat_id": self.test_chat_id,
                "message_id": 3,
                "message_date": "2023-01-01T10:02:00Z"
            },
            {
                "chat_id": self.test_chat_id,
                "message_id": 4,
                "message_date": "2023-01-01T10:03:00Z"
            }
        ]

        for cm in chat_messages:
            self.messages_db.insert_chat_message(**cm)

    @patch('src.message_maker.chat_history.Path')
    def test_get_chat_history_success(self, mock_path):
        """Test successful retrieval of chat history."""
        # Mock the database path to use our test database
        mock_path.return_value = Path(self.db_path)

        # Test from user1's perspective
        messages = get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id), 
            user_id="user1"
        )

        # Verify we got all messages
        self.assertEqual(len(messages), 4)

        # Verify chronological order (oldest first)
        expected_contents = [
            "Hello there!",
            "Hi! How are you?", 
            "I'm doing great, thanks!",
            "That's wonderful to hear!"
        ]
        actual_contents = [msg.contents for msg in messages]
        self.assertEqual(actual_contents, expected_contents)

        # Verify is_from_me is correctly set relative to user1
        expected_is_from_me = [True, False, True, False]
        actual_is_from_me = [msg.is_from_me for msg in messages]
        self.assertEqual(actual_is_from_me, expected_is_from_me)

    @patch('src.message_maker.chat_history.Path')
    def test_get_chat_history_consistent_is_from_me(self, mock_path):
        """Test that is_from_me is consistent regardless of user_id parameter."""
        # Mock the database path to use our test database
        mock_path.return_value = Path(self.db_path)

        # Test with different user_id parameters
        messages1 = get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id),
            user_id="user1"
        )
        
        messages2 = get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id),
            user_id="user2"
        )

        # In the implicit "me" data model, is_from_me should be the same
        # regardless of user_id parameter since it's stored in the database
        is_from_me_1 = [msg.is_from_me for msg in messages1]
        is_from_me_2 = [msg.is_from_me for msg in messages2]
        self.assertEqual(is_from_me_1, is_from_me_2)
        
        # Verify the expected pattern from our test data
        expected_is_from_me = [True, False, True, False]
        self.assertEqual(is_from_me_1, expected_is_from_me)

    @patch('src.message_maker.chat_history.Path')
    def test_get_chat_history_empty_chat(self, mock_path):
        """Test retrieval for empty chat."""
        # Mock the database path to use our test database
        mock_path.return_value = Path(self.db_path)

        # Create empty chat
        empty_chat_id = 999
        self.messages_db.insert_chat(
            chat_id=empty_chat_id,
            display_name="Empty Chat",
            user_ids=["user1"]
        )

        messages = get_chat_history_for_message_generation(
            chat_id=str(empty_chat_id),
            user_id="user1"
        )

        self.assertEqual(len(messages), 0)

    def test_get_chat_history_invalid_chat_id(self):
        """Test error handling for invalid chat_id formats."""
        # Test non-numeric chat_id
        with self.assertRaises(ValueError) as context:
            get_chat_history_for_message_generation(
                chat_id="invalid",
                user_id="user1"
            )
        self.assertIn("must be convertible to integer", str(context.exception))

        # Test None chat_id
        with self.assertRaises(ValueError):
            get_chat_history_for_message_generation(
                chat_id=None,
                user_id="user1"
            )

        # Test empty string chat_id
        with self.assertRaises(ValueError):
            get_chat_history_for_message_generation(
                chat_id="",
                user_id="user1"
            )

    @patch('src.message_maker.chat_history.Path')
    def test_get_chat_history_nonexistent_chat(self, mock_path):
        """Test retrieval for nonexistent chat."""
        # Mock the database path to use our test database
        mock_path.return_value = Path(self.db_path)

        messages = get_chat_history_for_message_generation(
            chat_id="99999",
            user_id="user1"
        )

        self.assertEqual(len(messages), 0)

    @patch('src.message_maker.chat_history.sqlite3.connect')
    def test_database_error_handling(self, mock_connect):
        """Test proper handling of database errors."""
        # Mock database error
        mock_connect.side_effect = sqlite3.Error("Database connection failed")

        with self.assertRaises(sqlite3.Error):
            get_chat_history_for_message_generation(
                chat_id=str(self.test_chat_id),
                user_id="user1"
            )

    @patch('src.message_maker.chat_history.Path')
    def test_chat_message_validation(self, mock_path):
        """Test that retrieved messages are properly validated."""
        # Mock the database path to use our test database
        mock_path.return_value = Path(self.db_path)

        messages = get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id),
            user_id="user1"
        )

        # Verify each message is valid
        for message in messages:
            # Should not raise validation error
            message.validate()
            
            # Verify required fields
            self.assertIsInstance(message.contents, str)
            self.assertTrue(len(message.contents) > 0)
            self.assertIsInstance(message.is_from_me, bool)
            self.assertIsInstance(message.created_at, str)
            self.assertTrue(len(message.created_at) > 0)

    @patch('src.message_maker.chat_history.Path')
    def test_message_order_consistency(self, mock_path):
        """Test that message ordering is consistent across multiple calls."""
        # Mock the database path to use our test database
        mock_path.return_value = Path(self.db_path)

        # Get messages multiple times
        messages1 = get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id),
            user_id="user1"
        )
        
        messages2 = get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id),
            user_id="user1"
        )

        # Should have same order
        self.assertEqual(len(messages1), len(messages2))
        for i, (msg1, msg2) in enumerate(zip(messages1, messages2)):
            self.assertEqual(msg1.contents, msg2.contents, f"Message {i} contents differ")
            self.assertEqual(msg1.is_from_me, msg2.is_from_me, f"Message {i} is_from_me differs")
            self.assertEqual(msg1.created_at, msg2.created_at, f"Message {i} created_at differs")

    @patch('src.message_maker.chat_history.Path')
    def test_large_message_content(self, mock_path):
        """Test handling of very large message content."""
        # Mock the database path to use our test database
        mock_path.return_value = Path(self.db_path)

        # Create a large message (10KB)
        large_content = "A" * 10000
        
        # Set up test data with large message
        large_chat_id = 888
        self.messages_db.insert_chat(large_chat_id, "Large Message Chat", ["user1"])
        
        self.messages_db.insert_message(999, "user1", large_content, True, "2023-01-01T10:00:00Z")
        self.messages_db.insert_chat_message(large_chat_id, 999, "2023-01-01T10:00:00Z")

        # Should handle large content without issues
        messages = get_chat_history_for_message_generation(
            str(large_chat_id), "user1"
        )
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].contents, large_content)

    @patch('src.message_maker.chat_history.Path')
    def test_special_characters_in_messages(self, mock_path):
        """Test handling of special characters and Unicode in messages."""
        # Mock the database path to use our test database
        mock_path.return_value = Path(self.db_path)

        special_content = "Hello! 🎉 こんにちは Special chars: @#$%^&*()[]{}|\\:;\"'<>,.?/"
        
        # Set up test data
        special_chat_id = 777
        self.messages_db.insert_chat(special_chat_id, "Special Chars Chat", ["user1"])
        
        self.messages_db.insert_message(888, "user1", special_content, True, "2023-01-01T10:00:00Z")
        self.messages_db.insert_chat_message(special_chat_id, 888, "2023-01-01T10:00:00Z")

        # Should handle special characters without issues
        messages = get_chat_history_for_message_generation(
            str(special_chat_id), "user1"
        )
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].contents, special_content)


if __name__ == "__main__":
    unittest.main()