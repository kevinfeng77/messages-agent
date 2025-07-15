"""Tests for HandleMatcher functionality"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.user.handle_matcher import HandleMatcher
from src.user.user import User
from src.database.messages_db import MessagesDatabase


class TestHandleMatcher(unittest.TestCase):
    """Test HandleMatcher functionality"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_messages.db"
        self.handle_matcher = HandleMatcher(str(self.test_db_path))

        # Create test database
        self.handle_matcher.messages_db.create_database()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_normalize_phone_number(self):
        """Test phone number normalization"""
        test_cases = [
            ("5551234567", "(555) 123-4567"),
            ("15551234567", "(555) 123-4567"),  # Remove US country code
            ("(555) 123-4567", "(555) 123-4567"),  # Already formatted
            ("+15551234567", "(555) 123-4567"),  # Should normalize after removing +
            ("", ""),  # Empty string
            ("123", "123"),  # Too short, return original
        ]

        for input_phone, expected in test_cases:
            with self.subTest(input_phone=input_phone):
                result = self.handle_matcher.normalize_phone_number(input_phone)
                self.assertEqual(result, expected)

    def test_normalize_email(self):
        """Test email normalization"""
        test_cases = [
            ("test@example.com", "test@example.com"),
            ("TEST@EXAMPLE.COM", "test@example.com"),
            ("  Test@Example.COM  ", "test@example.com"),
            ("", ""),
        ]

        for input_email, expected in test_cases:
            with self.subTest(input_email=input_email):
                result = self.handle_matcher.normalize_email(input_email)
                self.assertEqual(result, expected)

    def test_extract_phone_from_handle_id(self):
        """Test phone extraction from handle ID values"""
        test_cases = [
            ("+19495272398", "9495272398"),  # Remove country code
            ("+15551234567", "5551234567"),
            ("19495272398", "9495272398"),  # No + prefix
            ("5551234567", "5551234567"),  # Already 10 digits
            ("+44123456789", None),  # Not 11 digits starting with 1
            ("", None),  # Empty
            ("invalid", None),  # No digits
        ]

        for input_handle, expected in test_cases:
            with self.subTest(input_handle=input_handle):
                result = self.handle_matcher.extract_phone_from_handle_id(input_handle)
                self.assertEqual(result, expected)

    def test_looks_like_phone(self):
        """Test phone number detection"""
        test_cases = [
            ("+19495272398", True),
            ("5551234567", True),
            ("(555) 123-4567", True),
            ("test@example.com", False),
            ("", False),
            ("abcdefghij", False),
        ]

        for value, expected in test_cases:
            with self.subTest(value=value):
                result = self.handle_matcher._looks_like_phone(value)
                self.assertEqual(result, expected)

    def test_looks_like_email(self):
        """Test email detection"""
        test_cases = [
            ("test@example.com", True),
            ("user.name@domain.co.uk", True),
            ("+19495272398", False),
            ("5551234567", False),
            ("", False),
            ("no-at-symbol.com", False),
            ("no-dot@symbol", False),
        ]

        for value, expected in test_cases:
            with self.subTest(value=value):
                result = self.handle_matcher._looks_like_email(value)
                self.assertEqual(result, expected)

    def test_generate_phone_formats(self):
        """Test phone format generation"""
        result = self.handle_matcher._generate_phone_formats("5551234567")

        expected_formats = {
            "5551234567",
            "(555) 123-4567",
            "555-123-4567",
            "555.123.4567",
            "+15551234567",
            "15551234567",
        }

        self.assertEqual(result, expected_formats)

    def test_generate_phone_formats_with_country_code(self):
        """Test phone format generation with country code"""
        result = self.handle_matcher._generate_phone_formats("15551234567")

        # Should strip country code and generate formats for 10-digit number
        expected_formats = {
            "5551234567",
            "(555) 123-4567",
            "555-123-4567",
            "555.123.4567",
            "+15551234567",
            "15551234567",
        }

        self.assertEqual(result, expected_formats)

    def test_generate_phone_formats_empty(self):
        """Test phone format generation with empty input"""
        result = self.handle_matcher._generate_phone_formats("")
        self.assertEqual(result, set())

    @patch("src.user.handle_matcher.AddressBookExtractor")
    def test_match_handle_to_user_existing_user(self, mock_extractor):
        """Test matching when user already exists with handle_id"""
        # Create a user with handle_id
        existing_user = User(
            user_id="test-user-1",
            first_name="Test",
            last_name="User",
            phone_number="(555) 123-4567",
            email="test@example.com",
            handle_id=123,
        )
        self.handle_matcher.messages_db.insert_user(existing_user)

        # Test matching
        result = self.handle_matcher.match_handle_to_user(123, "+15551234567")

        self.assertIsNotNone(result)
        self.assertEqual(result.handle_id, 123)
        self.assertEqual(result.user_id, "test-user-1")


    @patch("src.user.handle_matcher.AddressBookExtractor")
    def test_match_handle_to_user_no_match_phone(self, mock_extractor):
        """Test fallback user creation for unmatched phone"""
        # Mock address book extractor with no matches
        mock_instance = Mock()
        mock_instance.extract_users.return_value = []
        mock_extractor.return_value = mock_instance

        # Test matching
        result = self.handle_matcher.match_handle_to_user(999, "+15559999999")

        self.assertIsNotNone(result)
        self.assertEqual(result.first_name, "")  # Empty as specified
        self.assertEqual(result.last_name, "")  # Empty as specified
        self.assertEqual(
            result.phone_number, "5559999999"
        )  # Phone without country code
        self.assertEqual(result.email, "")
        self.assertEqual(result.handle_id, 999)

    @patch("src.user.handle_matcher.AddressBookExtractor")
    def test_match_handle_to_user_no_match_email(self, mock_extractor):
        """Test fallback user creation for unmatched email"""
        # Mock address book extractor with no matches
        mock_instance = Mock()
        mock_instance.extract_users.return_value = []
        mock_extractor.return_value = mock_instance

        # Test matching
        result = self.handle_matcher.match_handle_to_user(998, "unknown@example.com")

        self.assertIsNotNone(result)
        self.assertEqual(result.first_name, "")  # Empty as specified
        self.assertEqual(result.last_name, "")  # Empty as specified
        self.assertEqual(result.phone_number, "")
        self.assertEqual(result.email, "unknown@example.com")
        self.assertEqual(result.handle_id, 998)

    def test_build_contact_lookup_from_users(self):
        """Test contact lookup dictionary building from users"""
        users = [
            User(
                user_id="john-doe",
                first_name="John",
                last_name="Doe",
                phone_number="(555) 123-4567",
                email="john@example.com",
            ),
            User(
                user_id="jane-smith",
                first_name="Jane",
                last_name="Smith",
                phone_number="(555) 555-5555",
                email="jane@example.com",
            ),
        ]

        lookup = self.handle_matcher._build_contact_lookup_from_users(users)

        # Check that various phone formats are included
        self.assertIn("5551234567", lookup)
        self.assertIn("(555) 123-4567", lookup)
        self.assertIn("+15551234567", lookup)

        # Check emails
        self.assertIn("john@example.com", lookup)
        self.assertIn("jane@example.com", lookup)

        # Check contact info is correct
        john_contact = lookup["john@example.com"]
        self.assertEqual(john_contact["first_name"], "John")
        self.assertEqual(john_contact["last_name"], "Doe")


class TestHandleMatcherIntegration(unittest.TestCase):
    """Integration tests for HandleMatcher with real database operations"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_messages.db"
        self.handle_matcher = HandleMatcher(str(self.test_db_path))

        # Create test database
        self.handle_matcher.messages_db.create_database()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_database_operations(self):
        """Test database operations work correctly"""
        # Insert a test user
        user = User(
            user_id="test-1",
            first_name="Test",
            last_name="User",
            phone_number="(555) 123-4567",
            email="test@example.com",
            handle_id=42,
        )

        success = self.handle_matcher.messages_db.insert_user(user)
        self.assertTrue(success)

        # Retrieve by handle_id
        retrieved = self.handle_matcher.messages_db.get_user_by_handle_id(42)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.user_id, "test-1")
        self.assertEqual(retrieved.handle_id, 42)

        # Update handle_id
        success = self.handle_matcher.messages_db.update_user_handle_id("test-1", 99)
        self.assertTrue(success)

        # Verify update
        updated = self.handle_matcher.messages_db.get_user_by_handle_id(99)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.user_id, "test-1")

        # Old handle_id should not exist
        old = self.handle_matcher.messages_db.get_user_by_handle_id(42)
        self.assertIsNone(old)


if __name__ == "__main__":
    unittest.main()
