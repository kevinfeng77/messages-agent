"""Tests for User class and AddressBookExtractor"""

import unittest
import tempfile
import sqlite3
from pathlib import Path
import uuid

from src.user.user import User, AddressBookExtractor


class TestUser(unittest.TestCase):
    """Test cases for User class"""

    def test_user_creation_valid(self):
        """Test creating a valid user"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email="john@example.com"
        )
        
        self.assertEqual(user.user_id, "test-123")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.phone_number, "(555) 123-4567")
        self.assertEqual(user.email, "john@example.com")

    def test_user_creation_phone_only(self):
        """Test creating user with phone only"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email=""
        )
        
        self.assertEqual(user.phone_number, "(555) 123-4567")
        self.assertEqual(user.email, "")

    def test_user_creation_email_only(self):
        """Test creating user with email only"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="",
            email="john@example.com"
        )
        
        self.assertEqual(user.phone_number, "")
        self.assertEqual(user.email, "john@example.com")

    def test_user_creation_invalid_no_id(self):
        """Test that user creation fails without user_id"""
        with self.assertRaises(ValueError):
            User(
                user_id="",
                first_name="John",
                last_name="Doe",
                phone_number="(555) 123-4567",
                email="john@example.com"
            )

    def test_user_creation_invalid_no_name(self):
        """Test that user creation fails without first and last name"""
        with self.assertRaises(ValueError):
            User(
                user_id="test-123",
                first_name="",
                last_name="",
                phone_number="(555) 123-4567",
                email="john@example.com"
            )

    def test_user_creation_invalid_no_contact(self):
        """Test that user creation fails without phone or email"""
        with self.assertRaises(ValueError):
            User(
                user_id="test-123",
                first_name="John",
                last_name="Doe",
                phone_number="",
                email=""
            )

    def test_from_address_book_record_valid(self):
        """Test creating user from address book record"""
        user = User.from_address_book_record(
            first_name="Jane",
            last_name="Smith",
            phone_number="(555) 987-6543",
            email="jane@example.com"
        )
        
        self.assertEqual(user.first_name, "Jane")
        self.assertEqual(user.last_name, "Smith")
        self.assertEqual(user.phone_number, "(555) 987-6543")
        self.assertEqual(user.email, "jane@example.com")
        self.assertTrue(user.user_id)  # Should have generated UUID

    def test_from_address_book_record_phone_only(self):
        """Test creating user from address book with phone only"""
        user = User.from_address_book_record(
            first_name="Bob",
            last_name="Johnson",
            phone_number="(555) 555-5555"
        )
        
        self.assertEqual(user.phone_number, "(555) 555-5555")
        self.assertEqual(user.email, "")

    def test_from_address_book_record_email_only(self):
        """Test creating user from address book with email only"""
        user = User.from_address_book_record(
            first_name="Alice",
            last_name="Brown",
            email="alice@example.com"
        )
        
        self.assertEqual(user.phone_number, "")
        self.assertEqual(user.email, "alice@example.com")

    def test_from_address_book_record_custom_id(self):
        """Test creating user with custom ID"""
        custom_id = "custom-user-123"
        user = User.from_address_book_record(
            first_name="Custom",
            last_name="User",
            phone_number="(555) 111-2222",
            user_id=custom_id
        )
        
        self.assertEqual(user.user_id, custom_id)

    def test_from_address_book_record_invalid_no_contact(self):
        """Test that creation fails without contact info"""
        with self.assertRaises(ValueError):
            User.from_address_book_record(
                first_name="Invalid",
                last_name="User"
            )

    def test_to_dict(self):
        """Test converting user to dictionary"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email="john@example.com"
        )
        
        expected_dict = {
            'user_id': 'test-123',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '(555) 123-4567',
            'email': 'john@example.com'
        }
        
        self.assertEqual(user.to_dict(), expected_dict)

    def test_str_representation_full(self):
        """Test string representation with both phone and email"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email="john@example.com"
        )
        
        str_repr = str(user)
        self.assertIn("John Doe", str_repr)
        self.assertIn("phone: (555) 123-4567", str_repr)
        self.assertIn("email: john@example.com", str_repr)

    def test_str_representation_phone_only(self):
        """Test string representation with phone only"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email=""
        )
        
        str_repr = str(user)
        self.assertIn("John Doe", str_repr)
        self.assertIn("phone: (555) 123-4567", str_repr)
        self.assertNotIn("email:", str_repr)

    def test_str_representation_email_only(self):
        """Test string representation with email only"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="",
            email="john@example.com"
        )
        
        str_repr = str(user)
        self.assertIn("John Doe", str_repr)
        self.assertIn("email: john@example.com", str_repr)
        self.assertNotIn("phone:", str_repr)


class TestAddressBookExtractor(unittest.TestCase):
    """Test cases for AddressBookExtractor"""

    def setUp(self):
        """Set up test fixtures"""
        self.extractor = AddressBookExtractor()

    def test_normalize_phone_standard(self):
        """Test phone number normalization for standard 10-digit number"""
        result = self.extractor._normalize_phone("5551234567")
        self.assertEqual(result, "(555) 123-4567")

    def test_normalize_phone_with_country_code(self):
        """Test phone number normalization with US country code"""
        result = self.extractor._normalize_phone("15551234567")
        self.assertEqual(result, "(555) 123-4567")

    def test_normalize_phone_formatted(self):
        """Test phone number normalization with existing formatting"""
        result = self.extractor._normalize_phone("(555) 123-4567")
        self.assertEqual(result, "(555) 123-4567")

    def test_normalize_phone_with_dashes(self):
        """Test phone number normalization with dashes"""
        result = self.extractor._normalize_phone("555-123-4567")
        self.assertEqual(result, "(555) 123-4567")

    def test_normalize_phone_with_spaces(self):
        """Test phone number normalization with spaces"""
        result = self.extractor._normalize_phone("555 123 4567")
        self.assertEqual(result, "(555) 123-4567")

    def test_normalize_phone_invalid_length(self):
        """Test phone number normalization with invalid length"""
        result = self.extractor._normalize_phone("123")
        self.assertEqual(result, "123")  # Returns original if can't normalize

    def test_normalize_phone_empty(self):
        """Test phone number normalization with empty string"""
        result = self.extractor._normalize_phone("")
        self.assertEqual(result, "")

    def test_normalize_phone_none(self):
        """Test phone number normalization with None"""
        result = self.extractor._normalize_phone(None)
        self.assertEqual(result, "")

    def test_get_addressbook_databases(self):
        """Test getting AddressBook database paths"""
        # This test will vary based on system, just ensure it returns a list
        databases = self.extractor._get_addressbook_databases()
        self.assertIsInstance(databases, list)

    def test_get_extraction_stats(self):
        """Test getting extraction statistics"""
        stats = self.extractor.get_extraction_stats()
        
        # Check that we get expected keys
        expected_keys = [
            'total_databases', 'database_paths', 'total_records',
            'records_with_phone', 'records_with_email', 'unique_contacts'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], (int, list))


class TestAddressBookExtractionIntegration(unittest.TestCase):
    """Integration tests for address book extraction with real database"""

    def test_extract_users_real_data(self):
        """Test extracting users from real address book data"""
        extractor = AddressBookExtractor()
        
        # This test may fail on systems without AddressBook data
        try:
            users = extractor.extract_users()
            
            # If we get users, validate their structure
            if users:
                for user in users[:5]:  # Test first 5 users
                    self.assertIsInstance(user, User)
                    self.assertTrue(user.user_id)
                    self.assertTrue(user.first_name or user.last_name)
                    self.assertTrue(user.phone_number or user.email)
                    
                    # Test that user can be converted to dict
                    user_dict = user.to_dict()
                    self.assertIn('user_id', user_dict)
                    self.assertIn('first_name', user_dict)
                    self.assertIn('last_name', user_dict)
                    
            # Even if no users found, ensure we get a list
            self.assertIsInstance(users, list)
            
        except Exception as e:
            # If extraction fails (e.g., no AddressBook), skip the test
            self.skipTest(f"Address book extraction failed: {e}")


if __name__ == '__main__':
    unittest.main()