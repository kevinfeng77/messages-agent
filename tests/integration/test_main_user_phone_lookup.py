#!/usr/bin/env python3
"""
Integration tests for get_user_phone_number function in main.py
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, call

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import main module functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from main import get_user_phone_number

from src.user.user import User


class TestMainUserPhoneLookup(unittest.TestCase):
    """Integration tests for main.py user phone lookup functionality."""

    @patch('main.MessagesDatabase')
    def test_get_user_phone_number_success(self, mock_db_class):
        """Test successful phone number lookup from database."""
        # Create mock user
        mock_user = User(
            user_id="test-user-123",
            first_name="John",
            last_name="Doe",
            phone_number="+15551234567",
            email="john.doe@example.com"
        )
        
        # Mock database instance and method
        mock_db = Mock()
        mock_db.get_user_by_id.return_value = mock_user
        mock_db_class.return_value = mock_db
        
        # Test the function
        result = get_user_phone_number("test-user-123")
        
        # Verify
        self.assertEqual(result, "+15551234567")
        mock_db.get_user_by_id.assert_called_once_with("test-user-123")

    @patch('main.MessagesDatabase')
    @patch('builtins.input', return_value="+15551234567")
    def test_get_user_phone_number_user_not_found_fallback(self, mock_input, mock_db_class):
        """Test fallback to manual input when user not found."""
        # Mock database to return None (user not found)
        mock_db = Mock()
        mock_db.get_user_by_id.return_value = None
        mock_db_class.return_value = mock_db
        
        # Test the function
        result = get_user_phone_number("nonexistent-user")
        
        # Verify
        self.assertEqual(result, "+15551234567")
        mock_db.get_user_by_id.assert_called_once_with("nonexistent-user")
        mock_input.assert_called_once_with("Please enter the recipient's phone number (e.g., +1234567890): ")

    @patch('main.MessagesDatabase')
    @patch('builtins.input', return_value="+15559876543")
    def test_get_user_phone_number_no_phone_fallback(self, mock_input, mock_db_class):
        """Test fallback to manual input when user has no phone number."""
        # Create mock user without phone number
        mock_user = User(
            user_id="test-user-123",
            first_name="Jane",
            last_name="Smith",
            phone_number="",  # Empty phone number
            email="jane.smith@example.com"
        )
        
        mock_db = Mock()
        mock_db.get_user_by_id.return_value = mock_user
        mock_db_class.return_value = mock_db
        
        # Test the function
        result = get_user_phone_number("test-user-123")
        
        # Verify
        self.assertEqual(result, "+15559876543")
        mock_input.assert_called_once_with("Please enter phone number for Jane Smith (e.g., +1234567890): ")

    @patch('main.MessagesDatabase')
    @patch('builtins.input', return_value="")
    def test_get_user_phone_number_empty_input_raises_error(self, mock_input, mock_db_class):
        """Test that empty manual input raises ValueError."""
        mock_db = Mock()
        mock_db.get_user_by_id.return_value = None
        mock_db_class.return_value = mock_db
        
        # Test that ValueError is raised
        with self.assertRaises(ValueError) as cm:
            get_user_phone_number("test-user")
        
        self.assertEqual(str(cm.exception), "No phone number provided")

    @patch('main.MessagesDatabase')
    @patch('builtins.input', return_value="+15555551234")
    def test_get_user_phone_number_database_exception_fallback(self, mock_input, mock_db_class):
        """Test fallback to manual input when database raises exception."""
        # Mock database to raise exception
        mock_db = Mock()
        mock_db.get_user_by_id.side_effect = Exception("Database connection error")
        mock_db_class.return_value = mock_db
        
        # Test the function
        result = get_user_phone_number("test-user")
        
        # Verify
        self.assertEqual(result, "+15555551234")
        mock_input.assert_called_once_with("Please enter the recipient's phone number (e.g., +1234567890): ")

    @patch('main.MessagesDatabase')
    @patch('builtins.print')  # Mock print to capture output
    def test_get_user_phone_number_success_output(self, mock_print, mock_db_class):
        """Test that successful lookup prints appropriate message."""
        mock_user = User(
            user_id="test-user-123",
            first_name="Alice",
            last_name="Johnson",
            phone_number="+15551112222",
            email="alice.johnson@example.com"
        )
        
        mock_db = Mock()
        mock_db.get_user_by_id.return_value = mock_user
        mock_db_class.return_value = mock_db
        
        # Test the function
        result = get_user_phone_number("test-user-123")
        
        # Verify result and print output
        self.assertEqual(result, "+15551112222")
        mock_print.assert_called_with("📞 Found phone number for Alice Johnson: +15551112222")

    @patch('main.MessagesDatabase')
    @patch('builtins.print')
    @patch('builtins.input', return_value="+15551234567")
    def test_get_user_phone_number_not_found_output(self, mock_input, mock_print, mock_db_class):
        """Test that user not found prints appropriate warning."""
        mock_db = Mock()
        mock_db.get_user_by_id.return_value = None
        mock_db_class.return_value = mock_db
        
        # Test the function
        get_user_phone_number("missing-user")
        
        # Verify warning message is printed
        mock_print.assert_called_with("⚠️  User not found in database for user_id: missing-user")

    @patch('main.MessagesDatabase')
    @patch('builtins.print')
    @patch('builtins.input', return_value="+15551234567")
    def test_get_user_phone_number_error_output(self, mock_input, mock_print, mock_db_class):
        """Test that database error prints appropriate error message."""
        mock_db = Mock()
        mock_db.get_user_by_id.side_effect = Exception("Connection timeout")
        mock_db_class.return_value = mock_db
        
        # Test the function
        get_user_phone_number("test-user")
        
        # Verify error message is printed
        mock_print.assert_called_with("❌ Error looking up user: Connection timeout")


if __name__ == "__main__":
    unittest.main()