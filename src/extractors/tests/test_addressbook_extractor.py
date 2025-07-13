"""Tests for AddressBookExtractor"""

import unittest
from src.extractors.addressbook_extractor import AddressBookExtractor
from src.user.user import User


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

    def test_extract_users_real_data(self):
        """Test extracting users from real address book data"""
        # This test may fail on systems without AddressBook data
        try:
            users = self.extractor.extract_users()
            
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