"""Tests for User class and AddressBookExtractor"""

import unittest
import tempfile
import sqlite3
from pathlib import Path
import uuid

from src.user.user import User


class TestUser(unittest.TestCase):
    """Test cases for User class"""

    def test_user_creation_valid(self):
        """Test creating a valid user"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email="john@example.com",
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
            email="",
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
            email="john@example.com",
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
                email="john@example.com",
            )

    def test_user_creation_invalid_no_name(self):
        """Test that user creation fails without any name"""
        with self.assertRaises(ValueError):
            User(
                user_id="test-123",
                first_name="",
                last_name="",
                phone_number="(555) 123-4567",
                email="john@example.com",
            )

    def test_user_creation_first_name_only(self):
        """Test creating user with only first name"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="",
            phone_number="(555) 123-4567",
            email="john@example.com",
        )

        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "")

    def test_user_creation_last_name_only(self):
        """Test creating user with only last name"""
        user = User(
            user_id="test-123",
            first_name="",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email="john@example.com",
        )

        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "Doe")

    def test_user_creation_invalid_no_contact(self):
        """Test that user creation fails without phone or email"""
        with self.assertRaises(ValueError):
            User(
                user_id="test-123",
                first_name="John",
                last_name="Doe",
                phone_number="",
                email="",
            )

    def test_from_address_book_record_valid(self):
        """Test creating user from address book record"""
        user = User.from_address_book_record(
            first_name="Jane",
            last_name="Smith",
            phone_number="(555) 987-6543",
            email="jane@example.com",
        )

        self.assertEqual(user.first_name, "Jane")
        self.assertEqual(user.last_name, "Smith")
        self.assertEqual(user.phone_number, "(555) 987-6543")
        self.assertEqual(user.email, "jane@example.com")
        self.assertTrue(user.user_id)  # Should have generated UUID

    def test_from_address_book_record_phone_only(self):
        """Test creating user from address book with phone only"""
        user = User.from_address_book_record(
            first_name="Bob", last_name="Johnson", phone_number="(555) 555-5555"
        )

        self.assertEqual(user.phone_number, "(555) 555-5555")
        self.assertEqual(user.email, "")

    def test_from_address_book_record_email_only(self):
        """Test creating user from address book with email only"""
        user = User.from_address_book_record(
            first_name="Alice", last_name="Brown", email="alice@example.com"
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
            user_id=custom_id,
        )

        self.assertEqual(user.user_id, custom_id)

    def test_from_address_book_record_invalid_no_contact(self):
        """Test that creation fails without contact info"""
        with self.assertRaises(ValueError):
            User.from_address_book_record(first_name="Invalid", last_name="User")

    def test_to_dict(self):
        """Test converting user to dictionary"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email="john@example.com",
        )

        expected_dict = {
            "user_id": "test-123",
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "(555) 123-4567",
            "email": "john@example.com",
            "handle_id": None,
        }

        self.assertEqual(user.to_dict(), expected_dict)

    def test_str_representation_full(self):
        """Test string representation with both phone and email"""
        user = User(
            user_id="test-123",
            first_name="John",
            last_name="Doe",
            phone_number="(555) 123-4567",
            email="john@example.com",
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
            email="",
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
            email="john@example.com",
        )

        str_repr = str(user)
        self.assertIn("John Doe", str_repr)
        self.assertIn("email: john@example.com", str_repr)
        self.assertNotIn("phone:", str_repr)


if __name__ == "__main__":
    unittest.main()
