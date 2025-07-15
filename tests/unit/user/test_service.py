#!/usr/bin/env python3
"""
Unit tests for UserService
"""

import unittest
from unittest.mock import Mock, patch

from src.user.service import UserService
from src.user.user import User


class TestUserService(unittest.TestCase):
    """Test UserService functionality."""

    def setUp(self):
        """Set up test environment."""
        self.mock_db = Mock()
        self.service = UserService(db=self.mock_db)

    def test_get_user_by_id_success(self):
        """Test successful user lookup by ID."""
        # Create mock user
        mock_user = User(
            user_id="test-user-123",
            first_name="John",
            last_name="Doe",
            phone_number="+15551234567",
            email="john.doe@example.com"
        )
        
        # Mock database response
        self.mock_db.get_user_by_id.return_value = mock_user
        
        # Test the service
        result = self.service.get_user_by_id("test-user-123")
        
        # Verify
        self.assertEqual(result, mock_user)
        self.mock_db.get_user_by_id.assert_called_once_with("test-user-123")

    def test_get_user_by_id_not_found(self):
        """Test user lookup when user not found."""
        # Mock database response
        self.mock_db.get_user_by_id.return_value = None
        
        # Test the service
        result = self.service.get_user_by_id("nonexistent-user")
        
        # Verify
        self.assertIsNone(result)
        self.mock_db.get_user_by_id.assert_called_once_with("nonexistent-user")

    def test_get_user_by_id_database_error(self):
        """Test user lookup when database raises exception."""
        # Mock database to raise exception
        self.mock_db.get_user_by_id.side_effect = Exception("Database error")
        
        # Test that exception is re-raised
        with self.assertRaises(Exception):
            self.service.get_user_by_id("test-user")

    def test_get_user_phone_number_success(self):
        """Test successful phone number retrieval."""
        # Create mock user with phone number
        mock_user = User(
            user_id="test-user-123",
            first_name="John",
            last_name="Doe",
            phone_number="555-123-4567",  # Unformatted phone
            email="john.doe@example.com"
        )
        
        self.mock_db.get_user_by_id.return_value = mock_user
        
        # Test the service
        result = self.service.get_user_phone_number("test-user-123")
        
        # Verify formatted phone number is returned
        self.assertEqual(result, "+15551234567")

    def test_get_user_phone_number_user_not_found(self):
        """Test phone number retrieval when user not found."""
        self.mock_db.get_user_by_id.return_value = None
        
        result = self.service.get_user_phone_number("nonexistent-user")
        
        self.assertIsNone(result)

    def test_get_user_phone_number_no_phone(self):
        """Test phone number retrieval when user has no phone number."""
        # Create mock user without phone number
        mock_user = User(
            user_id="test-user-123",
            first_name="John",
            last_name="Doe",
            phone_number="",  # Empty phone number
            email="john.doe@example.com"
        )
        
        self.mock_db.get_user_by_id.return_value = mock_user
        
        result = self.service.get_user_phone_number("test-user-123")
        
        self.assertIsNone(result)

    def test_format_phone_number_us_10_digit(self):
        """Test formatting 10-digit US phone number."""
        test_cases = [
            ("5551234567", "+15551234567"),
            ("(555) 123-4567", "+15551234567"),
            ("555-123-4567", "+15551234567"),
            ("555.123.4567", "+15551234567"),
            ("555 123 4567", "+15551234567"),
        ]
        
        for input_phone, expected in test_cases:
            with self.subTest(input_phone=input_phone):
                result = self.service.format_phone_number(input_phone)
                self.assertEqual(result, expected)

    def test_format_phone_number_us_11_digit(self):
        """Test formatting 11-digit US phone number."""
        test_cases = [
            ("15551234567", "+15551234567"),
            ("1-555-123-4567", "+15551234567"),
            ("1 (555) 123-4567", "+15551234567"),
        ]
        
        for input_phone, expected in test_cases:
            with self.subTest(input_phone=input_phone):
                result = self.service.format_phone_number(input_phone)
                self.assertEqual(result, expected)

    def test_format_phone_number_international(self):
        """Test formatting international phone numbers."""
        test_cases = [
            ("+15551234567", "+15551234567"),  # Already formatted
            ("+44 20 7946 0958", "+442079460958"),  # UK number
            ("+33 1 42 86 83 26", "+33142868326"),  # French number
        ]
        
        for input_phone, expected in test_cases:
            with self.subTest(input_phone=input_phone):
                result = self.service.format_phone_number(input_phone)
                self.assertEqual(result, expected)

    def test_format_phone_number_edge_cases(self):
        """Test formatting edge cases."""
        # Empty or None
        self.assertEqual(self.service.format_phone_number(""), "")
        self.assertEqual(self.service.format_phone_number(None), None)
        
        # Invalid lengths (should return as-is with warning)
        invalid_numbers = ["123", "12345678901234567890"]
        for phone in invalid_numbers:
            result = self.service.format_phone_number(phone)
            self.assertEqual(result, phone)

    def test_get_user_for_messaging_success(self):
        """Test successful user and phone retrieval for messaging."""
        mock_user = User(
            user_id="test-user-123",
            first_name="John",
            last_name="Doe",
            phone_number="555-123-4567",
            email="john.doe@example.com"
        )
        
        self.mock_db.get_user_by_id.return_value = mock_user
        
        user, phone = self.service.get_user_for_messaging("test-user-123")
        
        self.assertEqual(user, mock_user)
        self.assertEqual(phone, "+15551234567")

    def test_get_user_for_messaging_not_found(self):
        """Test user and phone retrieval when user not found."""
        self.mock_db.get_user_by_id.return_value = None
        
        user, phone = self.service.get_user_for_messaging("nonexistent-user")
        
        self.assertIsNone(user)
        self.assertIsNone(phone)

    def test_validate_phone_number(self):
        """Test phone number validation."""
        # Valid phone numbers
        valid_numbers = [
            "+15551234567",
            "+442079460958",
            "5551234567",
            "15551234567",
            "(555) 123-4567",
            "555-123-4567",
        ]
        
        for phone in valid_numbers:
            with self.subTest(phone=phone):
                self.assertTrue(self.service.validate_phone_number(phone))
        
        # Invalid phone numbers
        invalid_numbers = [
            "",
            None,
            "123",
            "12345678901234567890",
            "abc-def-ghij",
            "+1234",  # Too short international
        ]
        
        for phone in invalid_numbers:
            with self.subTest(phone=phone):
                self.assertFalse(self.service.validate_phone_number(phone))

    def test_service_without_db_parameter(self):
        """Test service creation without providing database parameter."""
        # This should create its own MessagesDatabase instance
        with patch('src.user.service.MessagesDatabase') as mock_db_class:
            service = UserService()
            mock_db_class.assert_called_once()


if __name__ == "__main__":
    unittest.main()