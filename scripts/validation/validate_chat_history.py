#!/usr/bin/env python3
"""
End-to-end validation script for chat history retrieval functionality.

This script validates the complete chat history retrieval system including:
- Database setup and data integrity
- Chat history service functionality
- Performance characteristics with realistic data volumes
- Edge case handling and error scenarios
"""

import os
import sys
import time
import tempfile
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.database.messages_db import MessagesDatabase
from src.message_maker.chat_history import ChatHistoryService
from src.message_maker.types import ChatMessage
from src.user.user import User
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class ChatHistoryValidator:
    """Validator for chat history retrieval functionality."""

    def __init__(self):
        """Initialize validator with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.messages_db = MessagesDatabase(self.db_path)
        self.chat_service = ChatHistoryService(self.db_path)
        
        self.validation_results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "performance_metrics": {},
            "errors": []
        }

    def cleanup(self):
        """Clean up temporary resources."""
        try:
            Path(self.db_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup database: {e}")

    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result and update counters."""
        if passed:
            self.validation_results["tests_passed"] += 1
            logger.info(f"✅ {test_name}: PASSED {details}")
        else:
            self.validation_results["tests_failed"] += 1
            error_msg = f"❌ {test_name}: FAILED {details}"
            logger.error(error_msg)
            self.validation_results["errors"].append(error_msg)

    def setup_test_database(self) -> bool:
        """Set up test database with realistic data."""
        try:
            logger.info("Setting up test database...")
            
            # Create database
            if not self.messages_db.create_database():
                raise Exception("Failed to create database")

            # Create test users
            test_users = [
                User("alice123", "Alice", "Johnson", "+1234567890", "alice@example.com", 1),
                User("bob456", "Bob", "Smith", "+1987654321", "bob@example.com", 2),
                User("charlie789", "Charlie", "Brown", "+1555666777", "charlie@example.com", 3),
                User("diana101", "Diana", "Wilson", "+1444555666", "diana@example.com", 4)
            ]

            for user in test_users:
                if not self.messages_db.insert_user(user):
                    raise Exception(f"Failed to insert user {user.user_id}")

            # Create test chats
            test_chats = [
                {
                    "chat_id": 1001,
                    "display_name": "Alice & Bob",
                    "user_ids": ["alice123", "bob456"]
                },
                {
                    "chat_id": 1002,
                    "display_name": "Group Chat",
                    "user_ids": ["alice123", "bob456", "charlie789", "diana101"]
                },
                {
                    "chat_id": 1003,
                    "display_name": "Empty Chat",
                    "user_ids": ["alice123"]
                }
            ]

            for chat in test_chats:
                if not self.messages_db.insert_chat(**chat):
                    raise Exception(f"Failed to insert chat {chat['chat_id']}")

            # Create realistic message data
            self._create_realistic_message_data()

            logger.info("Test database setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to setup test database: {e}")
            return False

    def _create_realistic_message_data(self):
        """Create realistic message data for testing."""
        base_time = datetime(2023, 1, 1, 10, 0, 0)
        
        # Chat 1001: Alice & Bob conversation (50 messages)
        messages_1001 = []
        chat_messages_1001 = []
        
        conversation_patterns = [
            ("alice123", "Hey Bob! How's your day going?"),
            ("bob456", "Hi Alice! It's going well, thanks for asking. How about yours?"),
            ("alice123", "Pretty good! Just finished that project I was working on."),
            ("bob456", "That's awesome! The one you mentioned last week?"),
            ("alice123", "Yes, exactly! It took longer than expected but I'm happy with the result."),
            ("bob456", "I'd love to hear more about it sometime."),
            ("alice123", "Sure! Maybe we can grab coffee and I can show you."),
            ("bob456", "Sounds great! How about tomorrow afternoon?"),
            ("alice123", "Perfect! Let's meet at the usual place around 3 PM."),
            ("bob456", "It's a date! See you tomorrow 😊"),
        ]

        for i, (user_id, content) in enumerate(conversation_patterns * 5):  # Repeat 5 times for 50 messages
            message_id = 1000 + i
            timestamp = base_time + timedelta(minutes=i * 2)
            timestamp_str = timestamp.isoformat() + "Z"
            
            messages_1001.append({
                "message_id": message_id,
                "user_id": user_id,
                "contents": f"{content} (msg {i+1})",
                "is_from_me": user_id == "alice123",  # From Alice's perspective
                "created_at": timestamp_str
            })
            
            chat_messages_1001.append({
                "chat_id": 1001,
                "message_id": message_id,
                "message_date": timestamp_str
            })

        # Insert messages for chat 1001
        for msg in messages_1001:
            if not self.messages_db.insert_message(**msg):
                raise Exception(f"Failed to insert message {msg['message_id']}")

        for cm in chat_messages_1001:
            if not self.messages_db.insert_chat_message(**cm):
                raise Exception(f"Failed to insert chat_message {cm['message_id']}")

        # Chat 1002: Group chat (100 messages for performance testing)
        messages_1002 = []
        chat_messages_1002 = []
        users = ["alice123", "bob456", "charlie789", "diana101"]
        
        for i in range(100):
            user_id = users[i % len(users)]
            message_id = 2000 + i
            timestamp = base_time + timedelta(hours=1, minutes=i)
            timestamp_str = timestamp.isoformat() + "Z"
            
            content = f"Group message {i+1} from {user_id.split('123')[0] if '123' in user_id else user_id.split('456')[0] if '456' in user_id else user_id.split('789')[0] if '789' in user_id else user_id.split('101')[0]}"
            
            messages_1002.append({
                "message_id": message_id,
                "user_id": user_id,
                "contents": content,
                "is_from_me": user_id == "alice123",
                "created_at": timestamp_str
            })
            
            chat_messages_1002.append({
                "chat_id": 1002,
                "message_id": message_id,
                "message_date": timestamp_str
            })

        # Insert messages for chat 1002
        for msg in messages_1002:
            if not self.messages_db.insert_message(**msg):
                raise Exception(f"Failed to insert message {msg['message_id']}")

        for cm in chat_messages_1002:
            if not self.messages_db.insert_chat_message(**cm):
                raise Exception(f"Failed to insert chat_message {cm['message_id']}")

    def test_basic_functionality(self) -> bool:
        """Test basic chat history retrieval functionality."""
        logger.info("Testing basic functionality...")
        
        try:
            # Test 1: Retrieve chat history for existing chat
            messages = self.chat_service.get_chat_history_for_message_generation("1001", "alice123")
            self.log_test_result(
                "Basic retrieval", 
                len(messages) == 50,
                f"Retrieved {len(messages)} messages"
            )

            # Test 2: Verify chronological order
            is_chronological = all(
                messages[i].created_at <= messages[i+1].created_at 
                for i in range(len(messages)-1)
            )
            self.log_test_result("Chronological order", is_chronological)

            # Test 3: Verify is_from_me logic
            alice_messages = [msg for msg in messages if msg.is_from_me]
            bob_messages = [msg for msg in messages if not msg.is_from_me]
            
            # Should have roughly equal numbers (given our test data pattern)
            ratio_valid = 0.4 <= len(alice_messages) / len(messages) <= 0.6
            self.log_test_result(
                "is_from_me logic", 
                ratio_valid,
                f"Alice: {len(alice_messages)}, Bob: {len(bob_messages)}"
            )

            # Test 4: Empty chat handling
            empty_messages = self.chat_service.get_chat_history_for_message_generation("1003", "alice123")
            self.log_test_result("Empty chat handling", len(empty_messages) == 0)

            return True

        except Exception as e:
            self.log_test_result("Basic functionality", False, str(e))
            return False

    def test_error_handling(self) -> bool:
        """Test error handling and edge cases."""
        logger.info("Testing error handling...")
        
        try:
            # Test 1: Invalid chat_id format
            try:
                self.chat_service.get_chat_history_for_message_generation("invalid", "alice123")
                self.log_test_result("Invalid chat_id handling", False, "Should have raised ValueError")
            except ValueError:
                self.log_test_result("Invalid chat_id handling", True)

            # Test 2: Nonexistent chat
            messages = self.chat_service.get_chat_history_for_message_generation("99999", "alice123")
            self.log_test_result("Nonexistent chat handling", len(messages) == 0)

            # Test 3: Chat existence check
            exists = self.chat_service.chat_exists("1001")
            not_exists = not self.chat_service.chat_exists("99999")
            self.log_test_result("Chat existence check", exists and not_exists)

            # Test 4: Message count
            count = self.chat_service.get_message_count("1001")
            self.log_test_result("Message count", count == 50)

            # Test 5: Chat participants
            participants = self.chat_service.get_chat_participants("1001")
            expected_participants = {"alice123", "bob456"}
            actual_participants = set(participants)
            self.log_test_result(
                "Chat participants", 
                actual_participants == expected_participants,
                f"Expected: {expected_participants}, Got: {actual_participants}"
            )

            return True

        except Exception as e:
            self.log_test_result("Error handling", False, str(e))
            return False

    def test_performance(self) -> bool:
        """Test performance with realistic data volumes."""
        logger.info("Testing performance...")
        
        try:
            # Test 1: Full chat retrieval performance (100 messages)
            start_time = time.time()
            messages = self.chat_service.get_chat_history_for_message_generation("1002", "alice123")
            full_retrieval_time = time.time() - start_time
            
            self.validation_results["performance_metrics"]["full_retrieval_100_messages"] = full_retrieval_time
            
            performance_ok = full_retrieval_time < 1.0  # Should be under 1 second
            self.log_test_result(
                "Full retrieval performance",
                performance_ok,
                f"{full_retrieval_time:.3f}s for {len(messages)} messages"
            )

            # Test 2: Recent messages retrieval performance
            start_time = time.time()
            recent_messages = self.chat_service.get_recent_chat_history("1002", "alice123", 20)
            recent_retrieval_time = time.time() - start_time
            
            self.validation_results["performance_metrics"]["recent_retrieval_20_messages"] = recent_retrieval_time
            
            recent_performance_ok = recent_retrieval_time < 0.5  # Should be under 0.5 seconds
            self.log_test_result(
                "Recent retrieval performance",
                recent_performance_ok,
                f"{recent_retrieval_time:.3f}s for {len(recent_messages)} messages"
            )

            # Test 3: Multiple consecutive calls (caching behavior)
            start_time = time.time()
            for _ in range(10):
                self.chat_service.get_chat_history_for_message_generation("1001", "alice123")
            multiple_calls_time = time.time() - start_time
            
            self.validation_results["performance_metrics"]["10_consecutive_calls"] = multiple_calls_time
            
            avg_call_time = multiple_calls_time / 10
            consistency_ok = avg_call_time < 0.1  # Average should be under 0.1 seconds
            self.log_test_result(
                "Consecutive calls performance",
                consistency_ok,
                f"Average: {avg_call_time:.3f}s per call"
            )

            return True

        except Exception as e:
            self.log_test_result("Performance testing", False, str(e))
            return False

    def test_data_integrity(self) -> bool:
        """Test data integrity and validation."""
        logger.info("Testing data integrity...")
        
        try:
            # Get messages for validation
            messages = self.chat_service.get_chat_history_for_message_generation("1001", "alice123")
            
            # Test 1: All messages have valid structure
            all_valid = True
            for i, msg in enumerate(messages):
                try:
                    msg.validate()
                except Exception as e:
                    self.log_test_result(f"Message {i} validation", False, str(e))
                    all_valid = False
                    break
            
            if all_valid:
                self.log_test_result("Message validation", True, f"All {len(messages)} messages valid")

            # Test 2: No duplicate messages
            contents = [msg.contents for msg in messages]
            unique_contents = set(contents)
            no_duplicates = len(contents) == len(unique_contents)
            self.log_test_result("No duplicate messages", no_duplicates)

            # Test 3: Consistent user perspective
            alice_perspective = self.chat_service.get_chat_history_for_message_generation("1001", "alice123")
            bob_perspective = self.chat_service.get_chat_history_for_message_generation("1001", "bob456")
            
            # Should have same number of messages
            same_count = len(alice_perspective) == len(bob_perspective)
            
            # is_from_me should be inverted between perspectives
            perspective_consistent = True
            for a_msg, b_msg in zip(alice_perspective, bob_perspective):
                if a_msg.contents == b_msg.contents and a_msg.is_from_me == b_msg.is_from_me:
                    perspective_consistent = False
                    break
            
            self.log_test_result(
                "User perspective consistency",
                same_count and perspective_consistent,
                f"Alice: {len(alice_perspective)}, Bob: {len(bob_perspective)}"
            )

            return True

        except Exception as e:
            self.log_test_result("Data integrity", False, str(e))
            return False

    def test_recent_messages_functionality(self) -> bool:
        """Test recent messages with various limits."""
        logger.info("Testing recent messages functionality...")
        
        try:
            # Test various limits
            limits_to_test = [1, 5, 10, 25, 50, 100, 1000]
            
            for limit in limits_to_test:
                messages = self.chat_service.get_recent_chat_history("1002", "alice123", limit)
                expected_count = min(limit, 100)  # Chat 1002 has 100 messages
                
                self.log_test_result(
                    f"Recent messages limit {limit}",
                    len(messages) == expected_count,
                    f"Got {len(messages)}, expected {expected_count}"
                )

            # Test that recent messages are in chronological order
            recent_20 = self.chat_service.get_recent_chat_history("1002", "alice123", 20)
            is_chronological = all(
                recent_20[i].created_at <= recent_20[i+1].created_at 
                for i in range(len(recent_20)-1)
            )
            self.log_test_result("Recent messages chronological order", is_chronological)

            return True

        except Exception as e:
            self.log_test_result("Recent messages functionality", False, str(e))
            return False

    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        logger.info("Starting chat history validation...")
        start_time = time.time()
        
        try:
            # Setup
            if not self.setup_test_database():
                return self.validation_results

            # Run test suites
            test_suites = [
                self.test_basic_functionality,
                self.test_error_handling,
                self.test_performance,
                self.test_data_integrity,
                self.test_recent_messages_functionality
            ]

            for test_suite in test_suites:
                try:
                    test_suite()
                except Exception as e:
                    logger.error(f"Test suite {test_suite.__name__} failed: {e}")
                    self.validation_results["errors"].append(f"{test_suite.__name__}: {e}")

            # Calculate overall results
            total_time = time.time() - start_time
            self.validation_results["total_execution_time"] = total_time
            self.validation_results["success_rate"] = (
                self.validation_results["tests_passed"] / 
                (self.validation_results["tests_passed"] + self.validation_results["tests_failed"])
                if (self.validation_results["tests_passed"] + self.validation_results["tests_failed"]) > 0
                else 0
            )

            return self.validation_results

        finally:
            self.cleanup()

    def print_summary(self, results: Dict[str, Any]):
        """Print validation summary."""
        print("\n" + "="*60)
        print("CHAT HISTORY VALIDATION SUMMARY")
        print("="*60)
        
        print(f"✅ Tests Passed: {results['tests_passed']}")
        print(f"❌ Tests Failed: {results['tests_failed']}")
        print(f"📊 Success Rate: {results['success_rate']:.1%}")
        print(f"⏱️  Total Time: {results['total_execution_time']:.2f}s")
        
        if results['performance_metrics']:
            print("\n📈 PERFORMANCE METRICS:")
            for metric, value in results['performance_metrics'].items():
                print(f"   {metric}: {value:.3f}s")
        
        if results['errors']:
            print("\n❌ ERRORS:")
            for error in results['errors']:
                print(f"   {error}")
        
        overall_status = "✅ PASSED" if results['success_rate'] >= 0.9 else "❌ FAILED"
        print(f"\n🎯 OVERALL STATUS: {overall_status}")
        print("="*60)


def main():
    """Main validation function."""
    print("Chat History Retrieval Validation Script")
    print("=" * 50)
    
    validator = ChatHistoryValidator()
    
    try:
        results = validator.run_validation()
        validator.print_summary(results)
        
        # Exit with error code if validation failed
        if results['success_rate'] < 0.9:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Validation script failed: {e}")
        print(f"\n❌ VALIDATION SCRIPT FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()