"""Test suite for MessagePollingService"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.database.polling_service import MessagePollingService
from src.database.messages_db import MessagesDatabase
from src.user.user import User


class TestMessagePollingService(unittest.TestCase):
    """Test cases for MessagePollingService"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test databases
        self.test_dir = tempfile.mkdtemp()
        self.messages_db_path = os.path.join(self.test_dir, "messages.db")
        self.source_db_path = os.path.join(self.test_dir, "chat_copy.db")
        
        # Initialize polling service with test directory
        self.polling_service = MessagePollingService(
            data_dir=self.test_dir,
            poll_interval=1,  # Short interval for testing
            batch_size=10
        )
        
        # Create test databases
        self.messages_db = MessagesDatabase(self.messages_db_path)
        self.messages_db.create_database()
        
        # Create mock source database with messages
        self._create_mock_source_database()
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_mock_source_database(self):
        """Create a mock source Messages database for testing"""
        with sqlite3.connect(self.source_db_path) as conn:
            cursor = conn.cursor()
            
            # Create messages table
            cursor.execute(
                """
                CREATE TABLE message (
                    ROWID INTEGER PRIMARY KEY,
                    guid TEXT,
                    text TEXT,
                    attributedBody BLOB,
                    handle_id INTEGER,
                    date INTEGER,
                    date_read INTEGER,
                    is_from_me INTEGER,
                    service TEXT
                )
                """
            )
            
            # Create handle table
            cursor.execute(
                """
                CREATE TABLE handle (
                    ROWID INTEGER PRIMARY KEY,
                    id TEXT
                )
                """
            )
            
            # Insert test handles
            test_handles = [
                (1, "+15551234567"),
                (2, "test@example.com"),
                (3, "+15559876543")
            ]
            cursor.executemany("INSERT INTO handle (ROWID, id) VALUES (?, ?)", test_handles)
            
            # Insert test messages
            test_messages = [
                (1, "MSG-001", "Hello world", None, 1, 683140800000000000, None, 0, "iMessage"),
                (2, "MSG-002", "How are you?", None, 2, 683140860000000000, None, 1, "iMessage"),
                (3, "MSG-003", "Good thanks!", None, 1, 683140920000000000, None, 0, "iMessage"),
                (4, "MSG-004", "", b"mock_attributed_body", 3, 683140980000000000, None, 0, "iMessage"),
            ]
            cursor.executemany(
                "INSERT INTO message (ROWID, guid, text, attributedBody, handle_id, date, date_read, is_from_me, service) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                test_messages
            )
            
            conn.commit()
    
    def test_initialize(self):
        """Test service initialization"""
        result = self.polling_service.initialize()
        self.assertTrue(result)
        
        # Check that polling state was created
        state = self.messages_db.get_polling_state()
        self.assertIsNotNone(state)
        self.assertEqual(state["last_processed_rowid"], 0)
        self.assertEqual(state["sync_status"], "initialized")
    
    def test_convert_apple_timestamp(self):
        """Test Apple timestamp conversion"""
        # Apple timestamp for 2022-09-01 12:00:00 UTC
        apple_timestamp = 683140800000000000
        
        iso_timestamp = self.polling_service.convert_apple_timestamp(apple_timestamp)
        
        # Should be a valid ISO format
        self.assertIsInstance(iso_timestamp, str)
        datetime.fromisoformat(iso_timestamp)  # Should not raise
    
    @patch('src.database.polling_service.DatabaseManager')
    def test_get_new_messages_from_source(self, mock_db_manager):
        """Test getting new messages from source database"""
        # Mock DatabaseManager to return our test database
        mock_manager = Mock()
        mock_manager.create_safe_copy.return_value = Path(self.source_db_path)
        mock_db_manager.return_value = mock_manager
        
        # Get messages since ROWID 0 (should get all)
        new_messages = self.polling_service.get_new_messages_from_source(0)
        
        self.assertEqual(len(new_messages), 4)
        self.assertEqual(new_messages[0]["rowid"], 1)
        self.assertEqual(new_messages[0]["text"], "Hello world")
        self.assertEqual(new_messages[0]["handle_id"], 1)
        
        # Get messages since ROWID 2 (should get last 2)
        new_messages = self.polling_service.get_new_messages_from_source(2)
        
        self.assertEqual(len(new_messages), 2)
        self.assertEqual(new_messages[0]["rowid"], 3)
        self.assertEqual(new_messages[1]["rowid"], 4)
    
    @patch('src.database.polling_service.extract_message_text')
    @patch('src.database.polling_service.DatabaseManager')
    def test_get_new_messages_text_extraction(self, mock_db_manager, mock_extract_text):
        """Test text extraction in get_new_messages_from_source"""
        # Mock dependencies
        mock_manager = Mock()
        mock_manager.create_safe_copy.return_value = Path(self.source_db_path)
        mock_db_manager.return_value = mock_manager
        
        mock_extract_text.side_effect = lambda text, blob: text or "extracted_text"
        
        new_messages = self.polling_service.get_new_messages_from_source(0)
        
        # Should have called extract_message_text for each message
        self.assertEqual(mock_extract_text.call_count, 4)
        
        # Check that extracted text is included
        for msg in new_messages:
            self.assertIn("extracted_text", msg)
    
    @patch('src.user.handle_matcher.HandleMatcher.resolve_user_from_handle_id')
    def test_resolve_user_from_handle(self, mock_resolve_user):
        """Test user resolution from handle_id"""
        # Mock a user being resolved
        test_user = User.from_address_book_record(
            first_name="John",
            last_name="Doe", 
            phone_number="5551234567",
            email="john@example.com",
            handle_id=1
        )
        mock_resolve_user.return_value = test_user
        
        # Test resolving a new handle_id
        result = self.polling_service.resolve_user_from_handle(1)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.first_name, "John")
        self.assertEqual(result.handle_id, 1)
        
        # Should have called the handle matcher
        mock_resolve_user.assert_called_once_with(1)
    
    def test_resolve_user_from_handle_existing(self):
        """Test resolving user that already exists in database"""
        # Create and insert a test user
        test_user = User.from_address_book_record(
            first_name="Jane",
            last_name="Smith",
            phone_number="5559876543", 
            email="jane@example.com",
            handle_id=2
        )
        self.messages_db.insert_user(test_user)
        
        # Should return existing user without calling handle matcher
        result = self.polling_service.resolve_user_from_handle(2)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.first_name, "Jane")
        self.assertEqual(result.handle_id, 2)
    
    @patch('src.database.polling_service.MessagePollingService.resolve_user_from_handle')
    def test_sync_new_messages(self, mock_resolve_user):
        """Test syncing new messages to normalized database"""
        # Mock user resolution
        test_user = User.from_address_book_record(
            first_name="Test",
            last_name="User",
            phone_number="5551234567",
            email="test@example.com",
            handle_id=1
        )
        mock_resolve_user.return_value = test_user
        
        # Test messages to sync
        new_messages = [
            {
                "rowid": 1,
                "text": "Hello",
                "extracted_text": "Hello", 
                "handle_id": 1,
                "date": 683140800000000000,
                "is_from_me": False
            },
            {
                "rowid": 2,
                "text": "Hi there",
                "extracted_text": "Hi there",
                "handle_id": 1, 
                "date": 683140860000000000,
                "is_from_me": True
            }
        ]
        
        synced_count = self.polling_service.sync_new_messages(new_messages)
        
        self.assertEqual(synced_count, 2)
        
        # Check messages were inserted into database
        messages = self.messages_db.get_all_messages()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["contents"], "Hi there")  # Latest first
        self.assertEqual(messages[1]["contents"], "Hello")
    
    def test_sync_new_messages_no_user_resolution(self):
        """Test sync when user resolution fails"""
        # Test messages but no user resolution
        new_messages = [
            {
                "rowid": 1,
                "text": "Hello",
                "extracted_text": "Hello",
                "handle_id": 99,  # Non-existent handle
                "date": 683140800000000000,
                "is_from_me": False
            }
        ]
        
        # Mock resolve_user_from_handle to return None
        with patch.object(self.polling_service, 'resolve_user_from_handle', return_value=None):
            synced_count = self.polling_service.sync_new_messages(new_messages)
        
        self.assertEqual(synced_count, 0)
        
        # No messages should be in database
        messages = self.messages_db.get_all_messages()
        self.assertEqual(len(messages), 0)
    
    def test_sync_new_messages_empty_content(self):
        """Test sync skips messages with no content"""
        # Mock user resolution
        test_user = User.from_address_book_record(
            first_name="Test",
            last_name="User", 
            phone_number="5551234567",
            email="test@example.com",
            handle_id=1
        )
        
        with patch.object(self.polling_service, 'resolve_user_from_handle', return_value=test_user):
            new_messages = [
                {
                    "rowid": 1,
                    "text": "",
                    "extracted_text": "",
                    "handle_id": 1,
                    "date": 683140800000000000,
                    "is_from_me": False
                }
            ]
            
            synced_count = self.polling_service.sync_new_messages(new_messages)
        
        self.assertEqual(synced_count, 0)
    
    @patch('src.database.polling_service.MessagePollingService.get_new_messages_from_source')
    @patch('src.database.polling_service.MessagePollingService.sync_new_messages')
    def test_poll_once_no_new_messages(self, mock_sync, mock_get_messages):
        """Test polling cycle with no new messages"""
        # Initialize polling state
        self.polling_service.initialize()
        
        # Mock no new messages
        mock_get_messages.return_value = []
        
        result = self.polling_service.poll_once()
        
        self.assertTrue(result["success"])
        self.assertEqual(result["new_messages"], 0)
        self.assertEqual(result["synced_messages"], 0)
        
        # sync_new_messages should not be called
        mock_sync.assert_not_called()
    
    @patch('src.database.polling_service.MessagePollingService.get_new_messages_from_source')
    @patch('src.database.polling_service.MessagePollingService.sync_new_messages')
    def test_poll_once_with_new_messages(self, mock_sync, mock_get_messages):
        """Test polling cycle with new messages"""
        # Initialize polling state
        self.polling_service.initialize()
        
        # Mock new messages
        test_messages = [
            {"rowid": 1, "text": "Hello"},
            {"rowid": 2, "text": "World"}
        ]
        mock_get_messages.return_value = test_messages
        mock_sync.return_value = 2
        
        result = self.polling_service.poll_once()
        
        self.assertTrue(result["success"])
        self.assertEqual(result["new_messages"], 2)
        self.assertEqual(result["synced_messages"], 2)
        self.assertEqual(result["last_processed_rowid"], 2)
        
        # Check that polling state was updated
        state = self.messages_db.get_polling_state()
        self.assertEqual(state["last_processed_rowid"], 2)
        self.assertEqual(state["total_messages_processed"], 2)
        self.assertEqual(state["sync_status"], "idle")
    
    @patch('src.database.polling_service.MessagePollingService.get_new_messages_from_source')
    def test_poll_once_with_error(self, mock_get_messages):
        """Test polling cycle with error"""
        # Initialize polling state
        self.polling_service.initialize()
        
        # Mock error in getting messages
        mock_get_messages.side_effect = Exception("Test error")
        
        result = self.polling_service.poll_once()
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Test error")
        
        # Check that polling state shows error
        state = self.messages_db.get_polling_state()
        self.assertEqual(state["sync_status"], "error")
    
    def test_get_status(self):
        """Test getting service status"""
        # Initialize service
        self.polling_service.initialize()
        
        status = self.polling_service.get_status()
        
        self.assertIn("is_running", status)
        self.assertIn("polling_state", status)
        self.assertIn("poll_interval", status)
        self.assertIn("batch_size", status)
        
        self.assertFalse(status["is_running"])
        self.assertEqual(status["poll_interval"], 1)
        self.assertEqual(status["batch_size"], 10)
    
    def test_start_stop_polling(self):
        """Test starting and stopping polling"""
        # Test starting when not running
        self.assertFalse(self.polling_service.is_running)
        
        # Test stopping when not running
        self.polling_service.stop_polling()  # Should not raise
        
        # Test setting running state
        self.polling_service.is_running = True
        self.assertTrue(self.polling_service.is_running)
        
        self.polling_service.stop_polling()
        self.assertFalse(self.polling_service.is_running)


class TestPollingServiceIntegration(unittest.TestCase):
    """Integration tests for polling service with real database operations"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.polling_service = MessagePollingService(
            data_dir=self.test_dir,
            poll_interval=1,
            batch_size=5
        )
    
    def tearDown(self):
        """Clean up integration test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_end_to_end_initialization(self):
        """Test complete initialization flow"""
        result = self.polling_service.initialize()
        self.assertTrue(result)
        
        # Check database was created with all tables
        messages_db = MessagesDatabase(f"{self.test_dir}/messages.db")
        
        # Check tables exist
        self.assertTrue(messages_db.table_exists("users"))
        self.assertTrue(messages_db.table_exists("chats"))
        self.assertTrue(messages_db.table_exists("messages"))
        self.assertTrue(messages_db.table_exists("chat_messages"))
        self.assertTrue(messages_db.table_exists("polling_state"))
        
        # Check polling state was initialized
        state = messages_db.get_polling_state()
        self.assertIsNotNone(state)
        self.assertEqual(state["last_processed_rowid"], 0)


if __name__ == "__main__":
    unittest.main()