"""Tests for MessagesDatabase class"""

import unittest
import tempfile
import sqlite3
from pathlib import Path

from src.database.messages_db import MessagesDatabase
from src.user.user import User


class TestMessagesDatabase(unittest.TestCase):
    """Test cases for MessagesDatabase class"""

    def setUp(self):
        """Set up test fixtures with temporary database"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_messages.db"
        self.db = MessagesDatabase(str(self.test_db_path))
        
        # Create test users
        self.test_users = [
            User(
                user_id="user-1",
                first_name="John",
                last_name="Doe",
                phone_number="(555) 123-4567",
                email="john@example.com"
            ),
            User(
                user_id="user-2",
                first_name="Jane",
                last_name="Smith",
                phone_number="(555) 987-6543",
                email="jane@example.com"
            ),
            User(
                user_id="user-3",
                first_name="Bob",
                last_name="Johnson",
                phone_number="(555) 555-5555",
                email=""
            ),
            User(
                user_id="user-4",
                first_name="Alice",
                last_name="Brown",
                phone_number="",
                email="alice@example.com"
            )
        ]

    def tearDown(self):
        """Clean up test fixtures"""
        if self.test_db_path.exists():
            self.test_db_path.unlink()

    def test_create_database(self):
        """Test creating the messages database"""
        self.assertTrue(self.db.create_database())
        self.assertTrue(self.db.database_exists())
        self.assertTrue(self.db.table_exists('users'))

    def test_create_database_idempotent(self):
        """Test that creating database multiple times is safe"""
        self.assertTrue(self.db.create_database())
        self.assertTrue(self.db.create_database())  # Should not fail
        self.assertTrue(self.db.table_exists('users'))

    def test_database_exists_false_initially(self):
        """Test that database_exists returns False before creation"""
        self.assertFalse(self.db.database_exists())

    def test_table_exists_false_initially(self):
        """Test that table_exists returns False before creation"""
        self.assertFalse(self.db.table_exists('users'))

    def test_insert_user_single(self):
        """Test inserting a single user"""
        self.db.create_database()
        
        user = self.test_users[0]
        self.assertTrue(self.db.insert_user(user))
        
        # Verify user was inserted
        retrieved_user = self.db.get_user_by_id(user.user_id)
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.user_id, user.user_id)
        self.assertEqual(retrieved_user.first_name, user.first_name)
        self.assertEqual(retrieved_user.last_name, user.last_name)

    def test_insert_user_without_database(self):
        """Test that inserting user fails without database"""
        user = self.test_users[0]
        self.assertFalse(self.db.insert_user(user))

    def test_insert_users_batch(self):
        """Test inserting multiple users in batch"""
        self.db.create_database()
        
        inserted_count = self.db.insert_users_batch(self.test_users)
        self.assertEqual(inserted_count, len(self.test_users))
        
        # Verify all users were inserted
        all_users = self.db.get_all_users()
        self.assertEqual(len(all_users), len(self.test_users))

    def test_insert_users_batch_empty_list(self):
        """Test inserting empty list of users"""
        self.db.create_database()
        
        inserted_count = self.db.insert_users_batch([])
        self.assertEqual(inserted_count, 0)

    def test_get_user_by_id_exists(self):
        """Test getting user by ID when user exists"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        user = self.db.get_user_by_id("user-1")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "user-1")
        self.assertEqual(user.first_name, "John")

    def test_get_user_by_id_not_exists(self):
        """Test getting user by ID when user doesn't exist"""
        self.db.create_database()
        
        user = self.db.get_user_by_id("nonexistent")
        self.assertIsNone(user)

    def test_get_users_by_phone(self):
        """Test getting users by phone number"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        users = self.db.get_users_by_phone("(555) 123-4567")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].first_name, "John")

    def test_get_users_by_phone_not_found(self):
        """Test getting users by phone when not found"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        users = self.db.get_users_by_phone("(999) 999-9999")
        self.assertEqual(len(users), 0)

    def test_get_users_by_email(self):
        """Test getting users by email address"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        users = self.db.get_users_by_email("jane@example.com")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].first_name, "Jane")

    def test_get_users_by_email_case_insensitive(self):
        """Test getting users by email is case insensitive"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        users = self.db.get_users_by_email("JANE@EXAMPLE.COM")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].first_name, "Jane")

    def test_get_users_by_email_not_found(self):
        """Test getting users by email when not found"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        users = self.db.get_users_by_email("notfound@example.com")
        self.assertEqual(len(users), 0)

    def test_get_all_users(self):
        """Test getting all users"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        all_users = self.db.get_all_users()
        self.assertEqual(len(all_users), len(self.test_users))

    def test_get_all_users_with_limit(self):
        """Test getting all users with limit"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        limited_users = self.db.get_all_users(limit=2)
        self.assertEqual(len(limited_users), 2)

    def test_get_all_users_empty_database(self):
        """Test getting all users from empty database"""
        self.db.create_database()
        
        all_users = self.db.get_all_users()
        self.assertEqual(len(all_users), 0)

    def test_clear_users_table(self):
        """Test clearing users table"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        # Verify users exist
        self.assertEqual(len(self.db.get_all_users()), len(self.test_users))
        
        # Clear table
        self.assertTrue(self.db.clear_users_table())
        
        # Verify table is empty
        self.assertEqual(len(self.db.get_all_users()), 0)

    def test_get_database_stats(self):
        """Test getting database statistics"""
        self.db.create_database()
        self.db.insert_users_batch(self.test_users)
        
        stats = self.db.get_database_stats()
        
        # Check expected keys
        expected_keys = [
            'database_path', 'database_size_bytes', 'total_users',
            'users_with_phone', 'users_with_email', 'users_with_both'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        # Check expected values
        self.assertEqual(stats['total_users'], len(self.test_users))
        self.assertEqual(stats['users_with_phone'], 3)  # John, Jane, Bob
        self.assertEqual(stats['users_with_email'], 3)  # John, Jane, Alice
        self.assertGreater(stats['database_size_bytes'], 0)

    def test_get_database_stats_empty(self):
        """Test getting database statistics for empty database"""
        self.db.create_database()
        
        stats = self.db.get_database_stats()
        self.assertEqual(stats['total_users'], 0)
        self.assertEqual(stats['users_with_phone'], 0)
        self.assertEqual(stats['users_with_email'], 0)

    def test_get_table_schema(self):
        """Test getting table schema"""
        self.db.create_database()
        
        schema = self.db.get_table_schema('users')
        self.assertIsNotNone(schema)
        
        # Check that we have the expected columns
        column_names = [col[1] for col in schema]
        expected_columns = ['user_id', 'first_name', 'last_name', 'phone_number', 'email']
        
        for expected_col in expected_columns:
            self.assertIn(expected_col, column_names)

    def test_get_table_schema_nonexistent(self):
        """Test getting schema for nonexistent table"""
        self.db.create_database()
        
        schema = self.db.get_table_schema('nonexistent_table')
        self.assertEqual(schema, [])  # Empty list for nonexistent table


class TestMessagesDatabaseIntegration(unittest.TestCase):
    """Integration tests for MessagesDatabase"""

    def test_full_workflow(self):
        """Test complete database workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "integration_test.db"
            db = MessagesDatabase(str(db_path))
            
            # 1. Create database
            self.assertTrue(db.create_database())
            
            # 2. Insert users
            test_user = User(
                user_id="integration-test",
                first_name="Integration",
                last_name="Test",
                phone_number="(555) 000-0000",
                email="integration@test.com"
            )
            
            self.assertTrue(db.insert_user(test_user))
            
            # 3. Query user
            retrieved_user = db.get_user_by_id("integration-test")
            self.assertIsNotNone(retrieved_user)
            self.assertEqual(retrieved_user.email, "integration@test.com")
            
            # 4. Search by phone and email
            phone_users = db.get_users_by_phone("(555) 000-0000")
            self.assertEqual(len(phone_users), 1)
            
            email_users = db.get_users_by_email("integration@test.com")
            self.assertEqual(len(email_users), 1)
            
            # 5. Get statistics
            stats = db.get_database_stats()
            self.assertEqual(stats['total_users'], 1)
            
            # 6. Clear and verify
            self.assertTrue(db.clear_users_table())
            final_stats = db.get_database_stats()
            self.assertEqual(final_stats['total_users'], 0)

    def test_database_persistence(self):
        """Test that database persists across connections"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "persistence_test.db"
            
            # Create database and insert user
            db1 = MessagesDatabase(str(db_path))
            db1.create_database()
            
            test_user = User(
                user_id="persistence-test",
                first_name="Persist",
                last_name="Test",
                phone_number="(555) 111-1111",
                email="persist@test.com"
            )
            
            db1.insert_user(test_user)
            
            # Create new connection and verify data persists
            db2 = MessagesDatabase(str(db_path))
            retrieved_user = db2.get_user_by_id("persistence-test")
            
            self.assertIsNotNone(retrieved_user)
            self.assertEqual(retrieved_user.first_name, "Persist")
            self.assertEqual(retrieved_user.email, "persist@test.com")


if __name__ == '__main__':
    unittest.main()