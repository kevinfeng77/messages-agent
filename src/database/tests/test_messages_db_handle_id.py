"""Tests for MessagesDatabase handle_id functionality"""

import unittest
import tempfile
import shutil
from pathlib import Path

from src.database.messages_db import MessagesDatabase
from src.user.user import User


class TestMessagesDatabaseHandleId(unittest.TestCase):
    """Test MessagesDatabase with handle_id functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_messages.db"
        self.db = MessagesDatabase(str(self.test_db_path))
        self.db.create_database()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_create_database_with_handle_id(self):
        """Test database creation includes handle_id column"""
        self.assertTrue(self.db.database_exists())
        self.assertTrue(self.db.table_exists())
        
        # Check schema includes handle_id
        schema = self.db.get_table_schema()
        self.assertIsNotNone(schema)
        
        column_names = [col[1] for col in schema]
        self.assertIn('handle_id', column_names)
    
    def test_insert_user_with_handle_id(self):
        """Test inserting user with handle_id"""
        user = User(
            user_id="test-1",
            first_name="Test",
            last_name="User",
            phone_number="(555) 123-4567",
            email="test@example.com",
            handle_id=42
        )
        
        success = self.db.insert_user(user)
        self.assertTrue(success)
        
        # Retrieve and verify
        retrieved = self.db.get_user_by_id("test-1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.handle_id, 42)
    
    def test_insert_user_without_handle_id(self):
        """Test inserting user without handle_id (None)"""
        user = User(
            user_id="test-2",
            first_name="Test",
            last_name="User2",
            phone_number="(555) 987-6543",
            email="test2@example.com",
            handle_id=None
        )
        
        success = self.db.insert_user(user)
        self.assertTrue(success)
        
        # Retrieve and verify
        retrieved = self.db.get_user_by_id("test-2")
        self.assertIsNotNone(retrieved)
        self.assertIsNone(retrieved.handle_id)
    
    def test_batch_insert_with_handle_ids(self):
        """Test batch insert with handle_ids"""
        users = [
            User(
                user_id=f"test-{i}",
                first_name=f"Test{i}",
                last_name="User",
                phone_number=f"(555) 123-456{i}",
                email=f"test{i}@example.com",
                handle_id=i * 10
            )
            for i in range(1, 4)
        ]
        
        count = self.db.insert_users_batch(users)
        self.assertEqual(count, 3)
        
        # Verify each user
        for i in range(1, 4):
            user = self.db.get_user_by_id(f"test-{i}")
            self.assertIsNotNone(user)
            self.assertEqual(user.handle_id, i * 10)
    
    def test_get_user_by_handle_id(self):
        """Test retrieving user by handle_id"""
        # Insert test users
        users = [
            User("user-1", "John", "Doe", "(555) 123-4567", "john@example.com", 100),
            User("user-2", "Jane", "Smith", "(555) 987-6543", "jane@example.com", 200),
            User("user-3", "Bob", "Wilson", "(555) 555-5555", "bob@example.com", None),
        ]
        
        for user in users:
            self.db.insert_user(user)
        
        # Test retrieving by handle_id
        user_100 = self.db.get_user_by_handle_id(100)
        self.assertIsNotNone(user_100)
        self.assertEqual(user_100.first_name, "John")
        self.assertEqual(user_100.handle_id, 100)
        
        user_200 = self.db.get_user_by_handle_id(200)
        self.assertIsNotNone(user_200)
        self.assertEqual(user_200.first_name, "Jane")
        self.assertEqual(user_200.handle_id, 200)
        
        # Test non-existent handle_id
        user_999 = self.db.get_user_by_handle_id(999)
        self.assertIsNone(user_999)
        
        # Test None handle_id
        user_none = self.db.get_user_by_handle_id(None)
        self.assertIsNone(user_none)
    
    def test_update_user_handle_id(self):
        """Test updating user's handle_id"""
        # Insert user without handle_id
        user = User(
            user_id="test-update",
            first_name="Update",
            last_name="Test",
            phone_number="(555) 999-9999",
            email="update@example.com",
            handle_id=None
        )
        self.db.insert_user(user)
        
        # Update handle_id
        success = self.db.update_user_handle_id("test-update", 500)
        self.assertTrue(success)
        
        # Verify update
        updated_user = self.db.get_user_by_id("test-update")
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.handle_id, 500)
        
        # Verify we can find by handle_id
        by_handle = self.db.get_user_by_handle_id(500)
        self.assertIsNotNone(by_handle)
        self.assertEqual(by_handle.user_id, "test-update")
    
    def test_update_nonexistent_user_handle_id(self):
        """Test updating handle_id for non-existent user"""
        success = self.db.update_user_handle_id("nonexistent", 999)
        self.assertFalse(success)
    
    def test_handle_id_uniqueness(self):
        """Test that handle_id values can be unique per user"""
        # Insert users with different handle_ids
        user1 = User("user-1", "User", "One", "(555) 111-1111", "user1@example.com", 1)
        user2 = User("user-2", "User", "Two", "(555) 222-2222", "user2@example.com", 2)
        
        self.db.insert_user(user1)
        self.db.insert_user(user2)
        
        # Verify each can be retrieved by their handle_id
        retrieved1 = self.db.get_user_by_handle_id(1)
        retrieved2 = self.db.get_user_by_handle_id(2)
        
        self.assertIsNotNone(retrieved1)
        self.assertIsNotNone(retrieved2)
        self.assertEqual(retrieved1.user_id, "user-1")
        self.assertEqual(retrieved2.user_id, "user-2")
    
    def test_get_all_users_includes_handle_id(self):
        """Test that get_all_users returns handle_id"""
        # Insert users with and without handle_id
        users = [
            User("user-1", "John", "Doe", "(555) 123-4567", "john@example.com", 10),
            User("user-2", "Jane", "Smith", "(555) 987-6543", "jane@example.com", None),
        ]
        
        for user in users:
            self.db.insert_user(user)
        
        all_users = self.db.get_all_users()
        self.assertEqual(len(all_users), 2)
        
        # Find users by user_id
        john = next(u for u in all_users if u.user_id == "user-1")
        jane = next(u for u in all_users if u.user_id == "user-2")
        
        self.assertEqual(john.handle_id, 10)
        self.assertIsNone(jane.handle_id)
    
    def test_phone_email_search_with_handle_id(self):
        """Test that phone/email searches return handle_id"""
        user = User(
            user_id="search-test",
            first_name="Search",
            last_name="Test",
            phone_number="(555) 123-4567",
            email="search@example.com",
            handle_id=777
        )
        self.db.insert_user(user)
        
        # Search by phone
        by_phone = self.db.get_users_by_phone("(555) 123-4567")
        self.assertEqual(len(by_phone), 1)
        self.assertEqual(by_phone[0].handle_id, 777)
        
        # Search by email
        by_email = self.db.get_users_by_email("search@example.com")
        self.assertEqual(len(by_email), 1)
        self.assertEqual(by_email[0].handle_id, 777)
    
    def test_database_stats_with_handle_ids(self):
        """Test database statistics work with handle_id column"""
        # Insert test users
        users = [
            User("user-1", "John", "Doe", "(555) 123-4567", "john@example.com", 1),
            User("user-2", "Jane", "Smith", "(555) 987-6543", "jane@example.com", 2),
            User("user-3", "Bob", "Wilson", "", "bob@example.com", None),
        ]
        
        for user in users:
            self.db.insert_user(user)
        
        stats = self.db.get_database_stats()
        
        self.assertEqual(stats['total_users'], 3)
        self.assertEqual(stats['users_with_phone'], 2)  # John and Jane have phones
        self.assertEqual(stats['users_with_email'], 3)  # All have emails


if __name__ == '__main__':
    unittest.main()