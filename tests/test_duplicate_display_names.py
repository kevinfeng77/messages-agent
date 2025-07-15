#!/usr/bin/env python3
"""Test for duplicate display name handling with message count prioritization"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from src.database.messages_db import MessagesDatabase
from src.user.user import User


def find_chat_by_display_name_with_db(db: MessagesDatabase, display_name: str) -> tuple[int, str]:
    """
    Find chat_id and first user_id by display name using provided database.
    If multiple chats have the same display name, returns the one with the most messages.
    
    Args:
        db: The database instance to use
        display_name: The display name to search for
        
    Returns:
        Tuple of (chat_id, user_id)
        
    Raises:
        ValueError: If display name not found or no users found for the chat
    """
    chats = db.get_chats_by_display_name(display_name)
    
    if not chats:
        raise ValueError(f"No chat found with display name '{display_name}'")
    
    # Take the first chat (which has the highest message count due to ordering)
    chat = chats[0]
    chat_id = chat['chat_id']
    user_ids = chat.get('user_ids', [])
    
    if not user_ids:
        raise ValueError(f"No users found for chat '{display_name}'")
    
    # Use the first user_id
    user_id = user_ids[0]
    
    return chat_id, user_id


class TestDuplicateDisplayNames(unittest.TestCase):
    """Test cases for handling duplicate display names by message count"""

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

    def test_find_chat_by_display_name_selects_most_messages(self):
        """Test that find_chat_by_display_name returns the chat with the most messages when duplicates exist"""
        # Create test users
        users = [
            User("user1", "User", "One", "+1111111111", "user1@example.com", 1),
            User("user2", "User", "Two", "+2222222222", "user2@example.com", 2),
            User("user3", "User", "Three", "+3333333333", "user3@example.com", 3),
        ]
        for user in users:
            self.messages_db.insert_user(user)

        # Insert test chats with the same display name
        chats = [
            {"chat_id": 300, "display_name": "Duplicate Chat", "user_ids": ["user1"]},
            {"chat_id": 301, "display_name": "Duplicate Chat", "user_ids": ["user2"]}, 
            {"chat_id": 302, "display_name": "Duplicate Chat", "user_ids": ["user3"]},
        ]
        self.messages_db.insert_chats_batch(chats)

        # Insert messages to create different message counts
        # Chat 300: 1 message
        messages_300 = [{"message_id": "msg1", "user_id": "user1", "contents": "Hello", "is_from_me": 0, "created_at": 1000}]
        self.messages_db.insert_messages_batch(messages_300)
        chat_messages_300 = [{"chat_id": 300, "message_id": "msg1", "message_date": 1000}]
        self.messages_db.insert_chat_messages_batch(chat_messages_300)

        # Chat 301: 3 messages (highest count - should be selected)
        messages_301 = [
            {"message_id": "msg2", "user_id": "user2", "contents": "Hi", "is_from_me": 0, "created_at": 2000},
            {"message_id": "msg3", "user_id": "user2", "contents": "How are you?", "is_from_me": 0, "created_at": 3000},
            {"message_id": "msg4", "user_id": "user2", "contents": "Great!", "is_from_me": 1, "created_at": 4000},
        ]
        self.messages_db.insert_messages_batch(messages_301)
        chat_messages_301 = [
            {"chat_id": 301, "message_id": "msg2", "message_date": 2000},
            {"chat_id": 301, "message_id": "msg3", "message_date": 3000},
            {"chat_id": 301, "message_id": "msg4", "message_date": 4000},
        ]
        self.messages_db.insert_chat_messages_batch(chat_messages_301)

        # Chat 302: 2 messages
        messages_302 = [
            {"message_id": "msg5", "user_id": "user3", "contents": "Test", "is_from_me": 0, "created_at": 5000},
            {"message_id": "msg6", "user_id": "user3", "contents": "Message", "is_from_me": 1, "created_at": 6000},
        ]
        self.messages_db.insert_messages_batch(messages_302)
        chat_messages_302 = [
            {"chat_id": 302, "message_id": "msg5", "message_date": 5000},
            {"chat_id": 302, "message_id": "msg6", "message_date": 6000},
        ]
        self.messages_db.insert_chat_messages_batch(chat_messages_302)

        # Test find_chat_by_display_name - should return chat 301 (highest message count)
        chat_id, user_id = find_chat_by_display_name_with_db(self.messages_db, "Duplicate Chat")
        
        # Should return chat 301 which has the most messages (3)
        self.assertEqual(chat_id, 301)
        self.assertEqual(user_id, "user2")

    def test_find_chat_by_display_name_handles_zero_messages(self):
        """Test that find_chat_by_display_name works when some chats have zero messages"""
        # Create test users
        users = [
            User("user1", "User", "One", "+1111111111", "user1@example.com", 1),
            User("user2", "User", "Two", "+2222222222", "user2@example.com", 2),
        ]
        for user in users:
            self.messages_db.insert_user(user)

        # Insert test chats with the same display name
        chats = [
            {"chat_id": 400, "display_name": "Zero Message Chat", "user_ids": ["user1"]},
            {"chat_id": 401, "display_name": "Zero Message Chat", "user_ids": ["user2"]},
        ]
        self.messages_db.insert_chats_batch(chats)

        # Insert messages only for chat 401
        messages_401 = [{"message_id": "msg1", "user_id": "user2", "contents": "Only message", "is_from_me": 0, "created_at": 1000}]
        self.messages_db.insert_messages_batch(messages_401)
        chat_messages_401 = [{"chat_id": 401, "message_id": "msg1", "message_date": 1000}]
        self.messages_db.insert_chat_messages_batch(chat_messages_401)

        # Test find_chat_by_display_name - should return chat 401 (1 message vs 0)
        chat_id, user_id = find_chat_by_display_name_with_db(self.messages_db, "Zero Message Chat")
        
        self.assertEqual(chat_id, 401)
        self.assertEqual(user_id, "user2")

    def test_find_chat_by_display_name_unique_chat_still_works(self):
        """Test that find_chat_by_display_name still works correctly for unique display names"""
        # Create test user
        user = User("user1", "User", "One", "+1111111111", "user1@example.com", 1)
        self.messages_db.insert_user(user)

        # Insert a chat with unique display name
        chat = {"chat_id": 500, "display_name": "Unique Chat Name", "user_ids": ["user1"]}
        self.messages_db.insert_chats_batch([chat])

        # Test find_chat_by_display_name with unique name
        chat_id, user_id = find_chat_by_display_name_with_db(self.messages_db, "Unique Chat Name")
        
        self.assertEqual(chat_id, 500)
        self.assertEqual(user_id, "user1")

    def test_find_chat_by_display_name_no_chat_found(self):
        """Test that find_chat_by_display_name raises appropriate error when no chat is found"""
        with self.assertRaises(ValueError) as context:
            find_chat_by_display_name_with_db(self.messages_db, "Non-existent Chat")
        
        self.assertIn("No chat found with display name 'Non-existent Chat'", str(context.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)