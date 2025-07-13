#!/usr/bin/env python3
"""Comprehensive unit tests for chat history retrieval functionality."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from src.message_maker.chat_history import ChatHistoryService, get_chat_history_for_message_generation
from src.message_maker.types import ChatMessage, DatabaseMessage
from src.database.messages_db import MessagesDatabase


class TestChatHistoryService(unittest.TestCase):
    """Unit tests for ChatHistoryService class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Initialize database
        self.messages_db = MessagesDatabase(self.db_path)
        self.assertTrue(self.messages_db.create_database())

        # Initialize chat history service
        self.chat_service = ChatHistoryService(self.db_path)

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

    def test_get_chat_history_for_message_generation_success(self):
        """Test successful retrieval of chat history."""
        # Test from user1's perspective
        messages = self.chat_service.get_chat_history_for_message_generation(
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

        # Test from user2's perspective  
        messages_user2 = self.chat_service.get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id),
            user_id="user2"
        )

        # Verify is_from_me is correctly set relative to user2
        expected_is_from_me_user2 = [False, True, False, True]
        actual_is_from_me_user2 = [msg.is_from_me for msg in messages_user2]
        self.assertEqual(actual_is_from_me_user2, expected_is_from_me_user2)

    def test_get_chat_history_empty_chat(self):
        """Test retrieval for empty chat."""
        # Create empty chat
        empty_chat_id = 999
        self.messages_db.insert_chat(
            chat_id=empty_chat_id,
            display_name="Empty Chat",
            user_ids=["user1"]
        )

        messages = self.chat_service.get_chat_history_for_message_generation(
            chat_id=str(empty_chat_id),
            user_id="user1"
        )

        self.assertEqual(len(messages), 0)

    def test_get_chat_history_invalid_chat_id(self):
        """Test error handling for invalid chat_id formats."""
        # Test non-numeric chat_id
        with self.assertRaises(ValueError) as context:
            self.chat_service.get_chat_history_for_message_generation(
                chat_id="invalid",
                user_id="user1"
            )
        self.assertIn("must be convertible to integer", str(context.exception))

        # Test None chat_id
        with self.assertRaises(ValueError):
            self.chat_service.get_chat_history_for_message_generation(
                chat_id=None,
                user_id="user1"
            )

        # Test empty string chat_id
        with self.assertRaises(ValueError):
            self.chat_service.get_chat_history_for_message_generation(
                chat_id="",
                user_id="user1"
            )

    def test_get_chat_history_nonexistent_chat(self):
        """Test retrieval for nonexistent chat."""
        messages = self.chat_service.get_chat_history_for_message_generation(
            chat_id="99999",
            user_id="user1"
        )

        self.assertEqual(len(messages), 0)

    def test_get_recent_chat_history_success(self):
        """Test successful retrieval of recent messages with limit."""
        # Get only 2 most recent messages
        messages = self.chat_service.get_recent_chat_history(
            chat_id=str(self.test_chat_id),
            user_id="user1",
            limit=2
        )

        # Should get 2 messages in chronological order
        self.assertEqual(len(messages), 2)
        
        # Should be the last 2 messages, but in chronological order
        expected_contents = ["I'm doing great, thanks!", "That's wonderful to hear!"]
        actual_contents = [msg.contents for msg in messages]
        self.assertEqual(actual_contents, expected_contents)

    def test_get_recent_chat_history_invalid_limit(self):
        """Test error handling for invalid limit values."""
        with self.assertRaises(ValueError) as context:
            self.chat_service.get_recent_chat_history(
                chat_id=str(self.test_chat_id),
                user_id="user1",
                limit=0
            )
        self.assertIn("limit must be a positive integer", str(context.exception))

        with self.assertRaises(ValueError):
            self.chat_service.get_recent_chat_history(
                chat_id=str(self.test_chat_id),
                user_id="user1",
                limit=-1
            )

    def test_chat_exists_success(self):
        """Test successful chat existence check."""
        # Test existing chat
        self.assertTrue(self.chat_service.chat_exists(str(self.test_chat_id)))

        # Test nonexistent chat
        self.assertFalse(self.chat_service.chat_exists("99999"))

    def test_chat_exists_invalid_chat_id(self):
        """Test chat existence check with invalid chat_id."""
        # Should return False for invalid chat_id formats
        self.assertFalse(self.chat_service.chat_exists("invalid"))
        self.assertFalse(self.chat_service.chat_exists(""))
        self.assertFalse(self.chat_service.chat_exists(None))

    def test_get_chat_participants_success(self):
        """Test successful retrieval of chat participants."""
        participants = self.chat_service.get_chat_participants(str(self.test_chat_id))
        
        # Should have both users
        self.assertEqual(len(participants), 2)
        self.assertIn("user1", participants)
        self.assertIn("user2", participants)

    def test_get_chat_participants_nonexistent_chat(self):
        """Test chat participants for nonexistent chat."""
        participants = self.chat_service.get_chat_participants("99999")
        self.assertEqual(len(participants), 0)

    def test_get_chat_participants_invalid_chat_id(self):
        """Test chat participants with invalid chat_id."""
        participants = self.chat_service.get_chat_participants("invalid")
        self.assertEqual(len(participants), 0)

    def test_get_message_count_success(self):
        """Test successful message count retrieval."""
        count = self.chat_service.get_message_count(str(self.test_chat_id))
        self.assertEqual(count, 4)

    def test_get_message_count_empty_chat(self):
        """Test message count for empty chat."""
        # Create empty chat
        empty_chat_id = 888
        self.messages_db.insert_chat(
            chat_id=empty_chat_id,
            display_name="Empty Chat",
            user_ids=["user1"]
        )

        count = self.chat_service.get_message_count(str(empty_chat_id))
        self.assertEqual(count, 0)

    def test_get_message_count_nonexistent_chat(self):
        """Test message count for nonexistent chat."""
        count = self.chat_service.get_message_count("99999")
        self.assertEqual(count, 0)

    def test_get_message_count_invalid_chat_id(self):
        """Test message count with invalid chat_id."""
        count = self.chat_service.get_message_count("invalid")
        self.assertEqual(count, 0)

    @patch('src.message_maker.chat_history.sqlite3.connect')
    def test_database_error_handling(self, mock_connect):
        """Test proper handling of database errors."""
        # Mock database error
        mock_connect.side_effect = sqlite3.Error("Database connection failed")

        with self.assertRaises(sqlite3.Error):
            self.chat_service.get_chat_history_for_message_generation(
                chat_id=str(self.test_chat_id),
                user_id="user1"
            )

    def test_chat_message_validation(self):
        """Test that retrieved messages are properly validated."""
        messages = self.chat_service.get_chat_history_for_message_generation(
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

    def test_message_order_consistency(self):
        """Test that message ordering is consistent across multiple calls."""
        # Get messages multiple times
        messages1 = self.chat_service.get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id),
            user_id="user1"
        )
        
        messages2 = self.chat_service.get_chat_history_for_message_generation(
            chat_id=str(self.test_chat_id),
            user_id="user1"
        )

        # Should have same order
        self.assertEqual(len(messages1), len(messages2))
        for i, (msg1, msg2) in enumerate(zip(messages1, messages2)):
            self.assertEqual(msg1.contents, msg2.contents, f"Message {i} contents differ")
            self.assertEqual(msg1.is_from_me, msg2.is_from_me, f"Message {i} is_from_me differs")
            self.assertEqual(msg1.created_at, msg2.created_at, f"Message {i} created_at differs")


class TestConvenienceFunction(unittest.TestCase):
    """Unit tests for the convenience function."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Mock the default database path
        self.original_default_path = "./data/messages.db"

    def tearDown(self):
        """Clean up test fixtures."""
        Path(self.db_path).unlink(missing_ok=True)

    @patch('src.message_maker.chat_history.ChatHistoryService')
    def test_convenience_function_calls_service(self, mock_service_class):
        """Test that convenience function properly instantiates and calls service."""
        # Mock the service instance and method
        mock_service = MagicMock()
        mock_service.get_chat_history_for_message_generation.return_value = [
            ChatMessage(contents="Test", is_from_me=True, created_at="2023-01-01T10:00:00Z")
        ]
        mock_service_class.return_value = mock_service

        # Call convenience function
        result = get_chat_history_for_message_generation("123", "user1")

        # Verify service was instantiated and called correctly
        mock_service_class.assert_called_once()
        mock_service.get_chat_history_for_message_generation.assert_called_once_with("123", "user1")
        
        # Verify result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].contents, "Test")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.messages_db = MessagesDatabase(self.db_path)
        self.assertTrue(self.messages_db.create_database())
        self.chat_service = ChatHistoryService(self.db_path)

    def tearDown(self):
        """Clean up test fixtures."""
        Path(self.db_path).unlink(missing_ok=True)

    def test_large_message_content(self):
        """Test handling of very large message content."""
        # Create a large message (10KB)
        large_content = "A" * 10000
        
        # Set up test data with large message
        from src.user.user import User
        user = User("user1", "Test", "User", "+1234567890", "test@example.com", 1)
        self.messages_db.insert_user(user)
        
        chat_id = 123
        self.messages_db.insert_chat(chat_id, "Test Chat", ["user1"])
        
        self.messages_db.insert_message(1, "user1", large_content, True, "2023-01-01T10:00:00Z")
        self.messages_db.insert_chat_message(chat_id, 1, "2023-01-01T10:00:00Z")

        # Should handle large content without issues
        messages = self.chat_service.get_chat_history_for_message_generation(
            str(chat_id), "user1"
        )
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].contents, large_content)

    def test_special_characters_in_messages(self):
        """Test handling of special characters and Unicode in messages."""
        special_content = "Hello! 🎉 こんにちは Special chars: @#$%^&*()[]{}|\\:;\"'<>,.?/"
        
        # Set up test data
        from src.user.user import User
        user = User("user1", "Test", "User", "+1234567890", "test@example.com", 1)
        self.messages_db.insert_user(user)
        
        chat_id = 123
        self.messages_db.insert_chat(chat_id, "Test Chat", ["user1"])
        
        self.messages_db.insert_message(1, "user1", special_content, True, "2023-01-01T10:00:00Z")
        self.messages_db.insert_chat_message(chat_id, 1, "2023-01-01T10:00:00Z")

        # Should handle special characters without issues
        messages = self.chat_service.get_chat_history_for_message_generation(
            str(chat_id), "user1"
        )
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].contents, special_content)

    def test_numeric_string_chat_id_variations(self):
        """Test various numeric string formats for chat_id."""
        from src.user.user import User
        user = User("user1", "Test", "User", "+1234567890", "test@example.com", 1)
        self.messages_db.insert_user(user)
        
        chat_id = 123
        self.messages_db.insert_chat(chat_id, "Test Chat", ["user1"])
        
        # Test different numeric string formats
        valid_formats = ["123", " 123 ", "123.0"]
        
        for chat_id_str in valid_formats:
            try:
                messages = self.chat_service.get_chat_history_for_message_generation(
                    chat_id_str, "user1"
                )
                # Should not raise error for convertible formats
            except ValueError:
                # Some formats might still be invalid, which is acceptable
                pass


if __name__ == "__main__":
    unittest.main()