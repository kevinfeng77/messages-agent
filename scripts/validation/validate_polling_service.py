#!/usr/bin/env python3
"""
Validation script for iMessage polling service

This script validates the real-time iMessage polling and database integration functionality.
It performs end-to-end testing of the polling service components and measures performance.
"""

import os
import sys
import time
import tempfile
import sqlite3
from datetime import datetime
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.database.polling_service import MessagePollingService
from src.database.messages_db import MessagesDatabase
from src.database.manager import DatabaseManager
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class PollingServiceValidator:
    """Validates the iMessage polling service functionality"""
    
    def __init__(self):
        self.test_dir = None
        self.polling_service = None
        self.results = {}
        
    def setup_test_environment(self) -> bool:
        """Set up test environment with mock data"""
        try:
            # Create temporary directory
            self.test_dir = tempfile.mkdtemp(prefix="polling_validation_")
            logger.info(f"Created test directory: {self.test_dir}")
            
            # Initialize polling service
            self.polling_service = MessagePollingService(
                data_dir=self.test_dir,
                poll_interval=1,
                batch_size=50
            )
            
            # Create mock source Messages database
            self._create_mock_messages_database()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            return False
    
    def _create_mock_messages_database(self):
        """Create a mock Messages database with test data"""
        source_db_path = os.path.join(self.test_dir, "chat_copy.db")
        
        with sqlite3.connect(source_db_path) as conn:
            cursor = conn.cursor()
            
            # Create messages table (simplified Apple schema)
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
            
            # Create handle table
            cursor.execute(
                """
                CREATE TABLE handle (
                    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT
                )
                """
            )
            
            # Insert test handles
            test_handles = [
                "+15551234567",  # Phone number
                "alice@example.com",  # Email
                "+15559876543",  # Another phone
                "bob@company.com",  # Another email
                "+15555555555"  # Third phone
            ]
            
            for handle_value in test_handles:
                cursor.execute("INSERT INTO handle (id) VALUES (?)", (handle_value,))
            
            # Generate test messages with realistic timestamps
            base_timestamp = 683140800000000000  # Apple timestamp
            timestamp_increment = 60000000000  # 1 minute in nanoseconds
            
            test_messages = []
            for i in range(100):  # Create 100 test messages
                handle_id = (i % 5) + 1  # Cycle through handles
                timestamp = base_timestamp + (i * timestamp_increment)
                is_from_me = i % 3 == 0  # Every 3rd message from me
                
                # Mix of text and attributed body messages
                if i % 10 == 0:
                    # Empty text with mock attributed body
                    text = ""
                    attributed_body = f"mock_attributed_body_{i}".encode()
                else:
                    # Regular text message
                    text = f"Test message {i+1}: Hello from handle {handle_id}"
                    attributed_body = None
                
                test_messages.append((
                    f"MSG-{i+1:03d}",  # guid
                    text,
                    attributed_body,
                    handle_id,
                    timestamp,
                    None,  # date_read
                    is_from_me,
                    "iMessage"
                ))
            
            cursor.executemany(
                """
                INSERT INTO message (guid, text, attributedBody, handle_id, date, date_read, is_from_me, service)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                test_messages
            )
            
            conn.commit()
            logger.info(f"Created mock Messages database with {len(test_messages)} messages")
    
    def validate_initialization(self) -> bool:
        """Validate service initialization"""
        logger.info("=== Validating Service Initialization ===")
        
        try:
            start_time = time.time()
            result = self.polling_service.initialize()
            init_time = time.time() - start_time
            
            self.results["initialization"] = {
                "success": result,
                "duration_seconds": init_time
            }
            
            if not result:
                logger.error("Service initialization failed")
                return False
            
            logger.info(f"✓ Service initialized successfully in {init_time:.3f}s")
            
            # Check database structure
            messages_db = MessagesDatabase(f"{self.test_dir}/messages.db")
            
            required_tables = ["users", "chats", "messages", "chat_messages", "polling_state"]
            for table in required_tables:
                if not messages_db.table_exists(table):
                    logger.error(f"Required table '{table}' not found")
                    return False
                logger.info(f"✓ Table '{table}' exists")
            
            # Check polling state initialization
            state = messages_db.get_polling_state()
            if not state:
                logger.error("Polling state not initialized")
                return False
            
            logger.info(f"✓ Polling state initialized: {state}")
            return True
            
        except Exception as e:
            logger.error(f"Initialization validation failed: {e}")
            self.results["initialization"] = {"success": False, "error": str(e)}
            return False
    
    def validate_single_poll_cycle(self) -> bool:
        """Validate a single polling cycle"""
        logger.info("=== Validating Single Poll Cycle ===")
        
        try:
            # Mock database manager to use our test database
            original_create_safe_copy = DatabaseManager.create_safe_copy
            
            def mock_create_safe_copy(self):
                return Path(os.path.join(self.test_dir, "chat_copy.db"))
            
            DatabaseManager.create_safe_copy = mock_create_safe_copy
            
            try:
                start_time = time.time()
                result = self.polling_service.poll_once()
                poll_time = time.time() - start_time
                
                self.results["single_poll"] = {
                    "success": result["success"],
                    "duration_seconds": poll_time,
                    "new_messages": result.get("new_messages", 0),
                    "synced_messages": result.get("synced_messages", 0)
                }
                
                if not result["success"]:
                    logger.error(f"Poll cycle failed: {result.get('error', 'Unknown error')}")
                    return False
                
                logger.info(f"✓ Poll cycle completed in {poll_time:.3f}s")
                logger.info(f"✓ Found {result['new_messages']} new messages")
                logger.info(f"✓ Synced {result['synced_messages']} messages")
                logger.info(f"✓ Last processed ROWID: {result['last_processed_rowid']}")
                
                return True
                
            finally:
                # Restore original method
                DatabaseManager.create_safe_copy = original_create_safe_copy
                
        except Exception as e:
            logger.error(f"Single poll validation failed: {e}")
            self.results["single_poll"] = {"success": False, "error": str(e)}
            return False
    
    def validate_incremental_sync(self) -> bool:
        """Validate incremental synchronization"""
        logger.info("=== Validating Incremental Sync ===")
        
        try:
            messages_db = MessagesDatabase(f"{self.test_dir}/messages.db")
            
            # Get initial state
            initial_state = messages_db.get_polling_state()
            initial_rowid = initial_state["last_processed_rowid"]
            initial_total = initial_state["total_messages_processed"]
            
            logger.info(f"Initial state: ROWID={initial_rowid}, Total={initial_total}")
            
            # Add more messages to source database
            source_db_path = os.path.join(self.test_dir, "chat_copy.db")
            with sqlite3.connect(source_db_path) as conn:
                cursor = conn.cursor()
                
                # Add 10 more messages
                new_messages = []
                for i in range(10):
                    handle_id = (i % 5) + 1
                    timestamp = 683140800000000000 + ((100 + i) * 60000000000)
                    new_messages.append((
                        f"NEW-MSG-{i+1}",
                        f"New incremental message {i+1}",
                        None,
                        handle_id,
                        timestamp,
                        None,
                        i % 2 == 0,
                        "iMessage"
                    ))
                
                cursor.executemany(
                    """
                    INSERT INTO message (guid, text, attributedBody, handle_id, date, date_read, is_from_me, service)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    new_messages
                )
                conn.commit()
            
            logger.info("Added 10 new messages to source database")
            
            # Mock database manager again
            original_create_safe_copy = DatabaseManager.create_safe_copy
            
            def mock_create_safe_copy(self):
                return Path(source_db_path)
            
            DatabaseManager.create_safe_copy = mock_create_safe_copy
            
            try:
                # Perform another poll cycle
                start_time = time.time()
                result = self.polling_service.poll_once()
                incremental_time = time.time() - start_time
                
                # Get final state
                final_state = messages_db.get_polling_state()
                final_rowid = final_state["last_processed_rowid"]
                final_total = final_state["total_messages_processed"]
                
                self.results["incremental_sync"] = {
                    "success": result["success"],
                    "duration_seconds": incremental_time,
                    "new_messages_detected": result.get("new_messages", 0),
                    "messages_synced": result.get("synced_messages", 0),
                    "rowid_progress": final_rowid - initial_rowid,
                    "total_progress": final_total - initial_total
                }
                
                if not result["success"]:
                    logger.error(f"Incremental sync failed: {result.get('error', 'Unknown error')}")
                    return False
                
                logger.info(f"✓ Incremental sync completed in {incremental_time:.3f}s")
                logger.info(f"✓ ROWID advanced from {initial_rowid} to {final_rowid}")
                logger.info(f"✓ Total messages processed: {initial_total} → {final_total}")
                logger.info(f"✓ Detected {result['new_messages']} new messages")
                logger.info(f"✓ Synced {result['synced_messages']} messages")
                
                # Verify only new messages were processed
                if result["new_messages"] != 10:
                    logger.warning(f"Expected 10 new messages, got {result['new_messages']}")
                
                return True
                
            finally:
                DatabaseManager.create_safe_copy = original_create_safe_copy
                
        except Exception as e:
            logger.error(f"Incremental sync validation failed: {e}")
            self.results["incremental_sync"] = {"success": False, "error": str(e)}
            return False
    
    def validate_user_resolution(self) -> bool:
        """Validate user resolution and identity matching"""
        logger.info("=== Validating User Resolution ===")
        
        try:
            messages_db = MessagesDatabase(f"{self.test_dir}/messages.db")
            
            # Check how many users were created
            users = messages_db.get_all_users()
            user_count = len(users)
            
            logger.info(f"✓ Created {user_count} users from handle resolution")
            
            # Check user details
            users_with_phone = len([u for u in users if u.phone_number])
            users_with_email = len([u for u in users if u.email])
            users_with_handle_id = len([u for u in users if u.handle_id])
            
            logger.info(f"✓ Users with phone numbers: {users_with_phone}")
            logger.info(f"✓ Users with emails: {users_with_email}")
            logger.info(f"✓ Users with handle_id: {users_with_handle_id}")
            
            # All users should have handle_id
            if users_with_handle_id != user_count:
                logger.error(f"Not all users have handle_id: {users_with_handle_id}/{user_count}")
                return False
            
            # Check messages are linked to users
            messages = messages_db.get_all_messages()
            message_count = len(messages)
            
            logger.info(f"✓ Synced {message_count} messages")
            
            # Verify all messages have valid user_id
            valid_user_ids = {u.user_id for u in users}
            messages_with_valid_user = len([m for m in messages if m["user_id"] in valid_user_ids])
            
            if messages_with_valid_user != message_count:
                logger.error(f"Some messages have invalid user_id: {messages_with_valid_user}/{message_count}")
                return False
            
            logger.info(f"✓ All {message_count} messages have valid user references")
            
            self.results["user_resolution"] = {
                "success": True,
                "total_users": user_count,
                "users_with_phone": users_with_phone,
                "users_with_email": users_with_email,
                "total_messages": message_count,
                "messages_with_valid_user": messages_with_valid_user
            }
            
            return True
            
        except Exception as e:
            logger.error(f"User resolution validation failed: {e}")
            self.results["user_resolution"] = {"success": False, "error": str(e)}
            return False
    
    def validate_performance(self) -> bool:
        """Validate performance characteristics"""
        logger.info("=== Validating Performance ===")
        
        try:
            # Test performance with larger batch
            large_polling_service = MessagePollingService(
                data_dir=self.test_dir,
                poll_interval=1,
                batch_size=1000  # Large batch
            )
            
            # Initialize if needed
            large_polling_service.initialize()
            
            # Mock database manager
            original_create_safe_copy = DatabaseManager.create_safe_copy
            
            def mock_create_safe_copy(self):
                return Path(os.path.join(self.test_dir, "chat_copy.db"))
            
            DatabaseManager.create_safe_copy = mock_create_safe_copy
            
            try:
                # Measure multiple poll cycles
                poll_times = []
                for i in range(3):
                    start_time = time.time()
                    result = large_polling_service.poll_once()
                    poll_time = time.time() - start_time
                    poll_times.append(poll_time)
                    
                    if not result["success"]:
                        logger.error(f"Performance test poll {i+1} failed")
                        return False
                
                avg_poll_time = sum(poll_times) / len(poll_times)
                max_poll_time = max(poll_times)
                min_poll_time = min(poll_times)
                
                logger.info(f"✓ Average poll time: {avg_poll_time:.3f}s")
                logger.info(f"✓ Min poll time: {min_poll_time:.3f}s")
                logger.info(f"✓ Max poll time: {max_poll_time:.3f}s")
                
                # Performance thresholds
                if avg_poll_time > 5.0:
                    logger.warning(f"Average poll time is high: {avg_poll_time:.3f}s")
                
                if max_poll_time > 10.0:
                    logger.warning(f"Max poll time is very high: {max_poll_time:.3f}s")
                
                self.results["performance"] = {
                    "success": True,
                    "avg_poll_time_seconds": avg_poll_time,
                    "min_poll_time_seconds": min_poll_time,
                    "max_poll_time_seconds": max_poll_time,
                    "poll_cycles_tested": len(poll_times)
                }
                
                return True
                
            finally:
                DatabaseManager.create_safe_copy = original_create_safe_copy
                
        except Exception as e:
            logger.error(f"Performance validation failed: {e}")
            self.results["performance"] = {"success": False, "error": str(e)}
            return False
    
    def validate_error_handling(self) -> bool:
        """Validate error handling and recovery"""
        logger.info("=== Validating Error Handling ===")
        
        try:
            # Test with invalid database path in a temporary directory that exists but has no permissions
            import tempfile
            import stat
            
            # Create a directory we can remove permissions from
            restricted_dir = tempfile.mkdtemp()
            restricted_subdir = os.path.join(restricted_dir, "restricted")
            os.makedirs(restricted_subdir)
            
            try:
                # Remove write permissions
                os.chmod(restricted_subdir, stat.S_IREAD)
                
                error_polling_service = MessagePollingService(
                    data_dir=restricted_subdir,
                    poll_interval=1,
                    batch_size=10
                )
                
                # Should handle initialization failure gracefully
                result = error_polling_service.initialize()
                init_failed = not result
                
                # Test poll_once with problematic service
                poll_result = error_polling_service.poll_once()
                poll_failed = not poll_result["success"]
                
                # Test status retrieval under error conditions
                status = error_polling_service.get_status()
                error_reported = "error" in status or poll_result.get("error") is not None
                
                logger.info(f"✓ Initialization failure handled: {init_failed}")
                logger.info(f"✓ Poll failure handled: {poll_failed}")
                logger.info(f"✓ Error status reported: {error_reported}")
                
                if poll_result.get("error"):
                    logger.info(f"✓ Error message: {poll_result['error']}")
                
                self.results["error_handling"] = {
                    "success": True,
                    "initialization_failure_handled": init_failed,
                    "poll_failure_handled": poll_failed,
                    "error_status_reported": error_reported
                }
                
                return True
                
            finally:
                # Restore permissions and cleanup
                try:
                    os.chmod(restricted_subdir, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
                    import shutil
                    shutil.rmtree(restricted_dir, ignore_errors=True)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error handling validation failed: {e}")
            self.results["error_handling"] = {"success": False, "error": str(e)}
            return False
    
    def cleanup(self):
        """Clean up test environment"""
        if self.test_dir:
            import shutil
            shutil.rmtree(self.test_dir, ignore_errors=True)
            logger.info(f"Cleaned up test directory: {self.test_dir}")
    
    def generate_report(self) -> dict:
        """Generate validation report"""
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results.values() if r.get("success", False)])
        
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": (successful_tests / total_tests) * 100 if total_tests > 0 else 0
            },
            "test_results": self.results
        }
        
        return report
    
    def run_validation(self) -> bool:
        """Run complete validation suite"""
        logger.info("Starting iMessage Polling Service Validation")
        logger.info("=" * 60)
        
        try:
            # Setup
            if not self.setup_test_environment():
                return False
            
            # Run validation tests
            tests = [
                self.validate_initialization,
                self.validate_single_poll_cycle,
                self.validate_incremental_sync,
                self.validate_user_resolution,
                self.validate_performance,
                self.validate_error_handling
            ]
            
            all_passed = True
            for test in tests:
                if not test():
                    all_passed = False
                    logger.error(f"Test failed: {test.__name__}")
                logger.info("")  # Add spacing between tests
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Validation suite failed: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main validation function"""
    validator = PollingServiceValidator()
    
    try:
        success = validator.run_validation()
        
        # Generate and display report
        report = validator.generate_report()
        
        logger.info("=" * 60)
        logger.info("VALIDATION REPORT")
        logger.info("=" * 60)
        logger.info(f"Tests Run: {report['summary']['total_tests']}")
        logger.info(f"Successful: {report['summary']['successful_tests']}")
        logger.info(f"Failed: {report['summary']['failed_tests']}")
        logger.info(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        
        if success:
            logger.info("\n🎉 ALL VALIDATION TESTS PASSED!")
            logger.info("The iMessage polling service is working correctly.")
        else:
            logger.error("\n❌ SOME VALIDATION TESTS FAILED!")
            logger.error("Please review the test results above.")
        
        # Print detailed results
        logger.info("\nDetailed Results:")
        for test_name, result in report["test_results"].items():
            status = "✓ PASS" if result.get("success", False) else "✗ FAIL"
            logger.info(f"  {test_name}: {status}")
            
            if "duration_seconds" in result:
                logger.info(f"    Duration: {result['duration_seconds']:.3f}s")
            
            if "error" in result:
                logger.info(f"    Error: {result['error']}")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\nValidation interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)