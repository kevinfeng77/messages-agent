"""Test suite for polling state management in MessagesDatabase"""

import os
import tempfile
import unittest
from datetime import datetime

from src.database.messages_db import MessagesDatabase


class TestPollingState(unittest.TestCase):
    """Test cases for polling state management"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database file
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.test_db_fd)
        
        # Initialize MessagesDatabase
        self.messages_db = MessagesDatabase(self.test_db_path)
        self.messages_db.create_database()
    
    def tearDown(self):
        """Clean up test environment"""
        os.unlink(self.test_db_path)
    
    def test_create_polling_state_table(self):
        """Test creating polling state table"""
        result = self.messages_db.create_polling_state_table()
        self.assertTrue(result)
        
        # Check table exists
        self.assertTrue(self.messages_db.table_exists("polling_state"))
        
        # Check schema
        schema = self.messages_db.get_table_schema("polling_state")
        self.assertIsNotNone(schema)
        
        # Should have required columns
        column_names = [col[1] for col in schema]
        expected_columns = [
            "id", "last_processed_rowid", "last_sync_timestamp", 
            "total_messages_processed", "sync_status", "created_at", "updated_at"
        ]
        for col in expected_columns:
            self.assertIn(col, column_names)
    
    def test_initialize_polling_state(self):
        """Test initializing polling state"""
        result = self.messages_db.initialize_polling_state()
        self.assertTrue(result)
        
        # Check state was created
        state = self.messages_db.get_polling_state()
        self.assertIsNotNone(state)
        self.assertEqual(state["last_processed_rowid"], 0)
        self.assertEqual(state["total_messages_processed"], 0)
        self.assertEqual(state["sync_status"], "initialized")
        
        # Check timestamps are valid
        self.assertIsNotNone(state["created_at"])
        self.assertIsNotNone(state["updated_at"])
        self.assertIsNotNone(state["last_sync_timestamp"])
        
        # Should be able to parse timestamps
        datetime.fromisoformat(state["created_at"])
        datetime.fromisoformat(state["updated_at"])
        datetime.fromisoformat(state["last_sync_timestamp"])
    
    def test_initialize_polling_state_idempotent(self):
        """Test that initializing polling state multiple times doesn't create duplicates"""
        # Initialize first time
        result1 = self.messages_db.initialize_polling_state()
        self.assertTrue(result1)
        
        state1 = self.messages_db.get_polling_state()
        
        # Initialize second time
        result2 = self.messages_db.initialize_polling_state()
        self.assertTrue(result2)
        
        state2 = self.messages_db.get_polling_state()
        
        # Should be the same record
        self.assertEqual(state1["created_at"], state2["created_at"])
        self.assertEqual(state1["last_processed_rowid"], state2["last_processed_rowid"])
    
    def test_get_polling_state_not_initialized(self):
        """Test getting polling state when not initialized"""
        state = self.messages_db.get_polling_state()
        self.assertIsNone(state)
    
    def test_update_polling_state(self):
        """Test updating polling state"""
        # Initialize first
        self.messages_db.initialize_polling_state()
        
        # Update with new values
        result = self.messages_db.update_polling_state(
            last_processed_rowid=100,
            messages_processed_count=25,
            sync_status="syncing"
        )
        self.assertTrue(result)
        
        # Check updated values
        state = self.messages_db.get_polling_state()
        self.assertEqual(state["last_processed_rowid"], 100)
        self.assertEqual(state["total_messages_processed"], 25)
        self.assertEqual(state["sync_status"], "syncing")
        
        # Update again to test cumulative count
        result = self.messages_db.update_polling_state(
            last_processed_rowid=150,
            messages_processed_count=10,
            sync_status="idle"
        )
        self.assertTrue(result)
        
        state = self.messages_db.get_polling_state()
        self.assertEqual(state["last_processed_rowid"], 150)
        self.assertEqual(state["total_messages_processed"], 35)  # 25 + 10
        self.assertEqual(state["sync_status"], "idle")
    
    def test_update_polling_state_not_initialized(self):
        """Test updating polling state when not initialized"""
        result = self.messages_db.update_polling_state(
            last_processed_rowid=100,
            messages_processed_count=5
        )
        self.assertFalse(result)
    
    def test_set_sync_status(self):
        """Test setting sync status"""
        # Initialize first
        self.messages_db.initialize_polling_state()
        
        # Set different statuses
        test_statuses = ["polling", "syncing", "idle", "error"]
        
        for status in test_statuses:
            result = self.messages_db.set_sync_status(status)
            self.assertTrue(result)
            
            state = self.messages_db.get_polling_state()
            self.assertEqual(state["sync_status"], status)
    
    def test_set_sync_status_not_initialized(self):
        """Test setting sync status when not initialized"""
        result = self.messages_db.set_sync_status("polling")
        self.assertFalse(result)
    
    def test_polling_state_constraints(self):
        """Test polling state table constraints"""
        # Initialize first
        self.messages_db.initialize_polling_state()
        
        # Try to insert another record with id=1 (should fail due to CHECK constraint)
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            with sqlite3.connect(self.test_db_path) as conn:
                cursor = conn.cursor()
                current_time = datetime.now().isoformat()
                cursor.execute(
                    """
                    INSERT INTO polling_state 
                    (id, last_processed_rowid, last_sync_timestamp, total_messages_processed, 
                     sync_status, created_at, updated_at)
                    VALUES (2, 0, ?, 0, 'test', ?, ?)
                    """,
                    (current_time, current_time, current_time)
                )
                conn.commit()
    
    def test_polling_state_timestamps_update(self):
        """Test that timestamps are properly updated"""
        # Initialize
        self.messages_db.initialize_polling_state()
        state1 = self.messages_db.get_polling_state()
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Update state
        self.messages_db.update_polling_state(
            last_processed_rowid=50,
            messages_processed_count=10
        )
        state2 = self.messages_db.get_polling_state()
        
        # Timestamps should be different
        self.assertNotEqual(state1["updated_at"], state2["updated_at"])
        self.assertNotEqual(state1["last_sync_timestamp"], state2["last_sync_timestamp"])
        
        # Created timestamp should remain the same
        self.assertEqual(state1["created_at"], state2["created_at"])
    
    def test_polling_state_with_database_creation(self):
        """Test that polling state table is created with main database"""
        # Create a new database instance
        test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(test_db_fd)
        
        try:
            messages_db = MessagesDatabase(test_db_path)
            result = messages_db.create_database()
            self.assertTrue(result)
            
            # Polling state table should exist
            self.assertTrue(messages_db.table_exists("polling_state"))
            
            # Should be able to initialize immediately
            result = messages_db.initialize_polling_state()
            self.assertTrue(result)
            
            state = messages_db.get_polling_state()
            self.assertIsNotNone(state)
            
        finally:
            os.unlink(test_db_path)


if __name__ == "__main__":
    unittest.main()