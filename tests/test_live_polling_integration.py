#!/usr/bin/env python3
"""
Integration tests for live polling functionality

These tests validate the complete polling system including real Messages database
interaction, copy freshness, and smart database management.

Note: These integration tests are skipped in CI environments (like CircleCI)
because they require macOS Messages database access and file system operations
that may not be available or appropriate in CI contexts.
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Skip all tests in this module if running in CI environment
SKIP_INTEGRATION_TESTS = os.getenv('CI') == 'true' or os.getenv('CIRCLECI') == 'true'
SKIP_REASON = "Integration tests skipped in CI environment"

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.smart_manager import SmartDatabaseManager
from src.database.polling_service import MessagePollingService
from scripts.validation.copy_freshness_checker import CopyFreshnessChecker
from scripts.validation.validate_live_polling import LivePollingValidator


@unittest.skipIf(SKIP_INTEGRATION_TESTS, SKIP_REASON)
class TestSmartDatabaseManager(unittest.TestCase):
    """Test the smart database manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_smart_manager_")
        self.smart_manager = SmartDatabaseManager(self.test_dir, copy_cache_ttl_seconds=30)
        
        # Create mock source database
        self.mock_source_path = Path(self.test_dir) / "mock_chat.db"
        self.create_mock_source_database()
        
        # Override source path for testing
        self.smart_manager.source_path = str(self.mock_source_path)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_mock_source_database(self):
        """Create a mock source Messages database"""
        with sqlite3.connect(str(self.mock_source_path)) as conn:
            cursor = conn.cursor()
            
            # Create basic message table
            cursor.execute(
                """
                CREATE TABLE message (
                    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT,
                    date INTEGER,
                    is_from_me INTEGER,
                    handle_id INTEGER
                )
                """
            )
            
            # Insert test messages
            base_timestamp = 683140800000000000  # Apple timestamp
            for i in range(50):
                cursor.execute(
                    """
                    INSERT INTO message (text, date, is_from_me, handle_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (f"Test message {i+1}", base_timestamp + i * 60000000000, i % 2, 1)
                )
            
            conn.commit()
    
    def add_messages_to_source(self, count: int = 5):
        """Add new messages to source database"""
        with sqlite3.connect(str(self.mock_source_path)) as conn:
            cursor = conn.cursor()
            
            # Get current max ROWID
            cursor.execute("SELECT MAX(ROWID) FROM message")
            max_rowid = cursor.fetchone()[0] or 0
            
            base_timestamp = 683140800000000000 + max_rowid * 60000000000
            for i in range(count):
                cursor.execute(
                    """
                    INSERT INTO message (text, date, is_from_me, handle_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (f"New message {max_rowid + i + 1}", base_timestamp + i * 60000000000, i % 2, 1)
                )
            
            conn.commit()
    
    def test_get_source_wal_state(self):
        """Test WAL state detection"""
        wal_state = self.smart_manager.get_source_wal_state()
        
        self.assertIsInstance(wal_state, dict)
        self.assertIn("main_db_exists", wal_state)
        self.assertTrue(wal_state["main_db_exists"])
        self.assertIn("state_timestamp", wal_state)
    
    def test_fresh_copy_creation(self):
        """Test creating fresh database copy"""
        copy_path = self.smart_manager.get_fresh_copy_if_needed()
        
        self.assertIsNotNone(copy_path)
        self.assertTrue(copy_path.exists())
        self.assertIsNotNone(self.smart_manager.last_copy_info)
        
        # Verify copy contents
        with sqlite3.connect(str(copy_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM message")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 50)  # Should have all original messages
    
    def test_copy_reuse(self):
        """Test that fresh copies are reused when appropriate"""
        # Create first copy
        copy_path1 = self.smart_manager.get_fresh_copy_if_needed()
        creation_time1 = self.smart_manager.last_copy_info["creation_time"]
        
        # Request another copy immediately - should reuse
        copy_path2 = self.smart_manager.get_fresh_copy_if_needed()
        
        self.assertEqual(str(copy_path1), str(copy_path2))
        self.assertEqual(creation_time1, self.smart_manager.last_copy_info["creation_time"])
    
    def test_copy_refresh_after_source_change(self):
        """Test that copy is refreshed when source changes"""
        # Create initial copy
        copy_path1 = self.smart_manager.get_fresh_copy_if_needed()
        creation_time1 = self.smart_manager.last_copy_info["creation_time"]
        
        # Wait a bit then modify source
        time.sleep(0.1)
        self.add_messages_to_source(3)
        
        # Request new copy - should detect source change and refresh
        copy_path2 = self.smart_manager.get_fresh_copy_if_needed()
        creation_time2 = self.smart_manager.last_copy_info["creation_time"]
        
        self.assertNotEqual(creation_time1, creation_time2)
        
        # Verify new copy has updated content
        with sqlite3.connect(str(copy_path2)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM message")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 53)  # Original 50 + 3 new
    
    def test_copy_expiration(self):
        """Test that copies expire after TTL"""
        # Create manager with very short TTL
        short_ttl_manager = SmartDatabaseManager(self.test_dir, copy_cache_ttl_seconds=1)
        short_ttl_manager.source_path = str(self.mock_source_path)
        
        # Create copy
        copy_path1 = short_ttl_manager.get_fresh_copy_if_needed()
        creation_time1 = short_ttl_manager.last_copy_info["creation_time"]
        
        # Wait for TTL to expire
        time.sleep(1.5)
        
        # Request new copy - should create fresh one due to expiration
        copy_path2 = short_ttl_manager.get_fresh_copy_if_needed()
        creation_time2 = short_ttl_manager.last_copy_info["creation_time"]
        
        self.assertNotEqual(creation_time1, creation_time2)
    
    def test_copy_validation(self):
        """Test copy content validation"""
        copy_path = self.smart_manager.get_fresh_copy_if_needed()
        
        # Test validation with no minimum ROWID
        self.assertTrue(self.smart_manager.validate_copy_contents(copy_path))
        
        # Test validation with minimum ROWID
        self.assertTrue(self.smart_manager.validate_copy_contents(copy_path, expected_min_rowid=40))
        
        # Test validation with too high minimum ROWID
        self.assertFalse(self.smart_manager.validate_copy_contents(copy_path, expected_min_rowid=100))
    
    def test_efficiency_stats(self):
        """Test copy efficiency statistics"""
        # Initially no stats
        stats = self.smart_manager.get_copy_efficiency_stats()
        self.assertIn("no_copy_info", stats)
        
        # Create copy and check stats
        self.smart_manager.get_fresh_copy_if_needed()
        stats = self.smart_manager.get_copy_efficiency_stats()
        
        self.assertIn("last_copy_age_seconds", stats)
        self.assertIn("copy_cache_ttl_seconds", stats)
        self.assertIn("copy_utilization", stats)
        self.assertIn("copy_is_reusable", stats)


@unittest.skipIf(SKIP_INTEGRATION_TESTS, SKIP_REASON)
class TestCopyFreshnessChecker(unittest.TestCase):
    """Test the copy freshness checker functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_freshness_")
        
        # Create mock Messages database structure
        self.mock_messages_dir = Path(self.test_dir) / "Messages"
        self.mock_messages_dir.mkdir()
        self.mock_chat_db = self.mock_messages_dir / "chat.db"
        
        self.create_mock_messages_database()
        
        # Create checker with mock path
        self.checker = CopyFreshnessChecker(self.test_dir)
        self.checker.messages_db_path = self.mock_chat_db
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_mock_messages_database(self):
        """Create mock Messages database"""
        with sqlite3.connect(str(self.mock_chat_db)) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                CREATE TABLE message (
                    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT,
                    date INTEGER,
                    is_from_me INTEGER,
                    handle_id INTEGER
                )
                """
            )
            
            # Add messages with recent timestamps
            apple_epoch = datetime(2001, 1, 1)
            now = datetime.now()
            recent_timestamp = int((now - apple_epoch).total_seconds() * 1_000_000_000)
            
            for i in range(20):
                timestamp = recent_timestamp - ((20 - i) * 60 * 1_000_000_000)  # Every minute going back
                cursor.execute(
                    """
                    INSERT INTO message (text, date, is_from_me, handle_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (f"Recent message {i+1}", timestamp, i % 2, 1)
                )
            
            conn.commit()
    
    def test_get_source_wal_info(self):
        """Test WAL file information gathering"""
        wal_info = self.checker.get_source_wal_info()
        
        self.assertIsInstance(wal_info, dict)
        self.assertIn("main_db_exists", wal_info)
        self.assertTrue(wal_info["main_db_exists"])
    
    def test_get_max_rowid_from_source(self):
        """Test getting max ROWID from source"""
        max_rowid = self.checker.get_max_rowid_from_source()
        
        self.assertIsNotNone(max_rowid)
        self.assertEqual(max_rowid, 20)  # Should be 20 from our test data
    
    def test_get_recent_messages(self):
        """Test getting recent messages from source"""
        recent_messages = self.checker.get_recent_messages_from_source(minutes_back=30)
        
        self.assertIsInstance(recent_messages, list)
        self.assertGreater(len(recent_messages), 0)
        
        # All messages should have required fields
        for msg in recent_messages:
            self.assertIn("rowid", msg)
            self.assertIn("timestamp", msg)
            self.assertIn("text", msg)
    
    def test_validate_copy_freshness(self):
        """Test copy freshness validation"""
        result = self.checker.validate_copy_freshness(freshness_threshold_seconds=60)
        
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        
        if result["success"]:
            self.assertIn("source_max_rowid", result)
            self.assertIn("copy_max_rowid", result)
            self.assertIn("is_fresh", result)
            self.assertIn("copy_creation_time_seconds", result)


@unittest.skipIf(SKIP_INTEGRATION_TESTS, SKIP_REASON)
class TestLivePollingValidator(unittest.TestCase):
    """Test the live polling validator functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_live_polling_")
        
        # Create mock Messages database
        self.mock_messages_dir = Path(self.test_dir) / "Messages"
        self.mock_messages_dir.mkdir()
        self.mock_chat_db = self.mock_messages_dir / "chat.db"
        
        self.create_mock_messages_database()
        
        # Create validator with mock path
        self.validator = LivePollingValidator(self.test_dir)
        self.validator.messages_db_path = str(self.mock_chat_db)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_mock_messages_database(self):
        """Create mock Messages database"""
        with sqlite3.connect(str(self.mock_chat_db)) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                CREATE TABLE message (
                    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT,
                    attributedBody BLOB,
                    date INTEGER,
                    is_from_me INTEGER,
                    handle_id INTEGER,
                    service TEXT,
                    guid TEXT
                )
                """
            )
            
            # Add test messages
            base_timestamp = 683140800000000000
            for i in range(30):
                cursor.execute(
                    """
                    INSERT INTO message (text, date, is_from_me, handle_id, service, guid)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (f"Test message {i+1}", base_timestamp + i * 60000000000, i % 2, 1, "iMessage", f"msg-{i+1}")
                )
            
            conn.commit()
    
    def test_check_prerequisites(self):
        """Test prerequisite checking"""
        # This should pass with our mock database
        result = self.validator.check_prerequisites()
        self.assertTrue(result)
    
    def test_get_current_max_rowid(self):
        """Test getting current max ROWID"""
        max_rowid = self.validator.get_current_max_rowid()
        
        self.assertIsNotNone(max_rowid)
        self.assertEqual(max_rowid, 30)  # From our test data
    
    def test_validate_copy_freshness(self):
        """Test copy freshness validation"""
        result = self.validator.validate_copy_freshness()
        self.assertTrue(result)  # Should pass with mock data
    
    def test_validate_performance_metrics(self):
        """Test performance metrics validation"""
        result = self.validator.validate_performance_metrics()
        self.assertTrue(result)  # Should pass with mock data
    
    @patch('time.sleep')  # Speed up the test  
    @patch('builtins.input', return_value='')  # Mock user input
    def test_generate_validation_report(self, mock_input, mock_sleep):
        """Test validation report generation"""
        # Set up some test data
        self.validator.baseline_rowid = 25
        self.validator.messages_detected = [
            {"rowid": 26, "contents": "Test message", "detection_time": datetime.now().isoformat()},
            {"rowid": 27, "contents": "Another test", "detection_time": datetime.now().isoformat()}
        ]
        
        report = self.validator.generate_validation_report()
        
        self.assertIsInstance(report, dict)
        self.assertIn("validation_timestamp", report)
        self.assertIn("baseline_rowid", report)
        self.assertIn("messages_detected", report)
        self.assertEqual(report["messages_detected"], 2)


@unittest.skipIf(SKIP_INTEGRATION_TESTS, SKIP_REASON)
class TestIntegrationScenarios(unittest.TestCase):
    """Test complete integration scenarios"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_integration_")
        
        # Create complete mock environment
        self.setup_mock_environment()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def setup_mock_environment(self):
        """Set up complete mock Messages environment"""
        # Create mock Messages database
        self.mock_messages_dir = Path(self.test_dir) / "Messages"
        self.mock_messages_dir.mkdir()
        self.mock_chat_db = self.mock_messages_dir / "chat.db"
        
        with sqlite3.connect(str(self.mock_chat_db)) as conn:
            cursor = conn.cursor()
            
            # Create full Messages database schema
            cursor.execute(
                """
                CREATE TABLE message (
                    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
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
            
            cursor.execute(
                """
                CREATE TABLE handle (
                    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT
                )
                """
            )
            
            # Add test handles
            cursor.execute("INSERT INTO handle (id) VALUES (?)", ("+15551234567",))
            cursor.execute("INSERT INTO handle (id) VALUES (?)", ("test@example.com",))
            
            # Add test messages
            base_timestamp = 683140800000000000
            for i in range(50):
                cursor.execute(
                    """
                    INSERT INTO message (guid, text, handle_id, date, is_from_me, service)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (f"msg-{i+1}", f"Integration test message {i+1}", 
                     (i % 2) + 1, base_timestamp + i * 60000000000, i % 3 == 0, "iMessage")
                )
            
            conn.commit()
    
    def test_end_to_end_polling_with_smart_manager(self):
        """Test complete polling flow with smart database manager"""
        # Create smart manager
        smart_manager = SmartDatabaseManager(self.test_dir, copy_cache_ttl_seconds=60)
        smart_manager.source_path = str(self.mock_chat_db)
        
        # Test copy creation and reuse
        copy1 = smart_manager.get_fresh_copy_if_needed()
        self.assertIsNotNone(copy1)
        
        copy2 = smart_manager.get_fresh_copy_if_needed()
        self.assertEqual(str(copy1), str(copy2))  # Should reuse
        
        # Test copy refresh after forced refresh
        copy3 = smart_manager.force_refresh_copy()
        self.assertNotEqual(smart_manager.last_copy_info["creation_time"], 
                          smart_manager.last_copy_info["creation_time"])  # Times should differ
    
    def test_polling_service_with_smart_manager(self):
        """Test polling service integration with smart manager"""
        # Mock the polling service to use smart manager
        with patch('src.database.polling_service.DatabaseManager', SmartDatabaseManager):
            polling_service = MessagePollingService(self.test_dir, poll_interval=1)
            
            # Override the database manager's source path
            polling_service.db_manager.source_path = str(self.mock_chat_db)
            
            self.assertTrue(polling_service.initialize())
            
            # Test single poll cycle
            result = polling_service.poll_once()
            self.assertTrue(result["success"])
            self.assertGreaterEqual(result["new_messages"], 0)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)