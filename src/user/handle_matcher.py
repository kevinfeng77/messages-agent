"""Handle matching utilities for user creation from Messages database handles"""

import re
from typing import Optional, Dict, List, Set
from pathlib import Path

from src.database.messages_db import MessagesDatabase
from src.extractors.addressbook_extractor import AddressBookExtractor
from src.user.user import User
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class HandleMatcher:
    """Matches handles from Messages database to existing users or creates new ones"""

    def __init__(self, messages_db_path: str = "./data/messages.db"):
        """
        Initialize HandleMatcher

        Args:
            messages_db_path: Path to the messages database
        """
        self.messages_db = MessagesDatabase(messages_db_path)
        self.addressbook_extractor = AddressBookExtractor()

    def normalize_phone_number(self, phone: str) -> str:
        """
        Normalize a phone number for matching

        This removes country codes and formats consistently with address book entries.
        Based on existing normalization logic from migrator.py.

        Args:
            phone: Raw phone number from handle

        Returns:
            Normalized phone number string
        """
        if not phone:
            return ""

        # Remove all non-digits first
        normalized = "".join(filter(str.isdigit, phone))

        # Remove US country code (1) if present and we have 11 digits
        if normalized.startswith("1") and len(normalized) == 11:
            normalized = normalized[1:]

        # Format as (XXX) XXX-XXXX if we have 10 digits
        if len(normalized) == 10:
            return f"({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}"

        # Return original if we can't normalize to 10 digits
        return phone

    def normalize_email(self, email: str) -> str:
        """
        Normalize an email for matching

        Args:
            email: Raw email address

        Returns:
            Normalized email (lowercase)
        """
        return email.lower().strip() if email else ""

    def extract_phone_from_handle_id(self, handle_id_value: str) -> Optional[str]:
        """
        Extract phone number from handle.id value, removing country code

        According to the ticket: "This is done by removing the country code
        in the handle.ID and then matching these phone numbers against
        the phone numbers in our address book."

        Args:
            handle_id_value: The handle.id value (e.g., "+19495272398")

        Returns:
            Phone number without country code (e.g., "9495272398")
        """
        if not handle_id_value:
            return None

        # Remove + prefix if present
        if handle_id_value.startswith("+"):
            handle_id_value = handle_id_value[1:]

        # Remove all non-digits
        phone_digits = "".join(filter(str.isdigit, handle_id_value))

        # Remove US country code (1) if present
        if phone_digits.startswith("1") and len(phone_digits) == 11:
            phone_digits = phone_digits[1:]

        return phone_digits if len(phone_digits) == 10 else None

    def match_handle_to_user(
        self, handle_id: int, handle_id_value: str
    ) -> Optional[User]:
        """
        Match a handle to an existing user or create a new one

        Args:
            handle_id: The handle ROWID from messages database
            handle_id_value: The handle.id value (phone/email)

        Returns:
            User object (existing or newly created)
        """
        # Check if user already exists with this handle_id
        existing_user = self.messages_db.get_user_by_handle_id(handle_id)
        if existing_user:
            logger.debug(
                f"Found existing user for handle_id {handle_id}: {existing_user}"
            )
            return existing_user

        # Extract all users from address book for matching
        users = self.addressbook_extractor.extract_users()
        contact_lookup = self._build_contact_lookup_from_users(users)

        # Try to match by phone number
        if self._looks_like_phone(handle_id_value):
            phone_without_country = self.extract_phone_from_handle_id(handle_id_value)
            if phone_without_country:
                # Try normalized phone lookup
                normalized_phone = self.normalize_phone_number(phone_without_country)
                if normalized_phone in contact_lookup:
                    contact_info = contact_lookup[normalized_phone]
                    return self._create_user_from_contact(
                        contact_info, phone_without_country, "", handle_id
                    )

                # Try direct phone lookup (various formats)
                for phone_format in self._generate_phone_formats(phone_without_country):
                    if phone_format in contact_lookup:
                        contact_info = contact_lookup[phone_format]
                        return self._create_user_from_contact(
                            contact_info, phone_without_country, "", handle_id
                        )

        # Try to match by email
        if self._looks_like_email(handle_id_value):
            normalized_email = self.normalize_email(handle_id_value)
            if normalized_email in contact_lookup:
                contact_info = contact_lookup[normalized_email]
                return self._create_user_from_contact(
                    contact_info, "", handle_id_value, handle_id
                )

        # No match found - create new user with handle data only
        logger.info(
            f"No contact match for handle_id {handle_id} ({handle_id_value}), creating new user"
        )
        return self._create_fallback_user(handle_id_value, handle_id)

    def _build_contact_lookup_from_users(self, users: List[User]) -> Dict[str, Dict]:
        """
        Build a lookup dictionary from User objects

        Args:
            users: List of User objects from address book

        Returns:
            Dictionary mapping phone/email to contact info
        """
        contact_lookup = {}

        for user in users:
            contact_info = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
            }

            # Add phone numbers in multiple formats
            if user.phone_number:
                for phone_format in self._generate_phone_formats(user.phone_number):
                    contact_lookup[phone_format] = contact_info

            # Add emails
            if user.email:
                normalized_email = self.normalize_email(user.email)
                contact_lookup[normalized_email] = contact_info

        logger.info(f"Built contact lookup with {len(contact_lookup)} entries")
        return contact_lookup

    def _generate_phone_formats(self, phone: str) -> Set[str]:
        """
        Generate various phone number formats for matching

        Args:
            phone: Phone number string

        Returns:
            Set of phone number formats
        """
        if not phone:
            return set()

        # Extract digits only
        digits = "".join(filter(str.isdigit, phone))

        if len(digits) == 10:
            formats = {
                digits,  # Raw digits: "9495272398"
                f"({digits[:3]}) {digits[3:6]}-{digits[6:]}",  # Formatted: "(949) 527-2398"
                f"{digits[:3]}-{digits[3:6]}-{digits[6:]}",  # Dashed: "949-527-2398"
                f"{digits[:3]}.{digits[3:6]}.{digits[6:]}",  # Dotted: "949.527.2398"
                f"+1{digits}",  # With country code: "+19495272398"
                f"1{digits}",  # With country code no plus: "19495272398"
            }
            return formats
        elif len(digits) == 11 and digits.startswith("1"):
            # Remove country code and try again
            return self._generate_phone_formats(digits[1:])

        return {phone}  # Return original if can't process

    def _looks_like_phone(self, value: str) -> bool:
        """Check if a value looks like a phone number"""
        if not value:
            return False

        # Check for phone number patterns
        digits = "".join(filter(str.isdigit, value))
        return len(digits) >= 10 and (
            value.startswith("+") or any(c.isdigit() for c in value)
        )

    def _looks_like_email(self, value: str) -> bool:
        """Check if a value looks like an email"""
        if not value:
            return False

        return "@" in value and "." in value

    def _create_user_from_contact(
        self, contact_info: Dict, phone: str, email: str, handle_id: int
    ) -> User:
        """
        Create a user from contact information

        Args:
            contact_info: Contact information dictionary
            phone: Phone number
            email: Email address
            handle_id: Handle ID from messages database

        Returns:
            User object
        """
        user = User.from_address_book_record(
            first_name=contact_info.get("first_name", ""),
            last_name=contact_info.get("last_name", ""),
            phone_number=phone,
            email=email,
            handle_id=handle_id,
        )

        # Insert into database
        success = self.messages_db.insert_user(user)
        if success:
            logger.info(f"Created user from contact: {user}")
        else:
            logger.error(f"Failed to insert user: {user}")

        return user

    def _create_fallback_user(self, handle_id_value: str, handle_id: int) -> User:
        """
        Create a fallback user when no contact match is found

        Args:
            handle_id_value: The handle.id value
            handle_id: Handle ID from messages database

        Returns:
            User object with minimal information
        """
        # Determine if it's a phone or email
        if self._looks_like_phone(handle_id_value):
            phone = self.extract_phone_from_handle_id(handle_id_value) or ""
            email = ""
        elif self._looks_like_email(handle_id_value):
            phone = ""
            email = handle_id_value
        else:
            # Fallback - treat as phone if it has digits, otherwise email
            if any(c.isdigit() for c in handle_id_value):
                phone = handle_id_value
                email = ""
            else:
                phone = ""
                email = handle_id_value

        user = User.from_address_book_record(
            first_name="",  # Empty as specified in ticket
            last_name="",  # Empty as specified in ticket
            phone_number=phone,
            email=email,
            handle_id=handle_id,
        )

        # Insert into database
        success = self.messages_db.insert_user(user)
        if success:
            logger.info(f"Created fallback user: {user}")
        else:
            logger.error(f"Failed to insert fallback user: {user}")

        return user

    def resolve_user_from_handle_id(self, handle_id: int) -> Optional[User]:
        """
        Resolve a user from just the handle_id by querying the source Messages database

        Args:
            handle_id: Handle ID from Messages database

        Returns:
            User object or None if resolution fails
        """
        try:
            # Import here to avoid circular imports
            from src.database.manager import DatabaseManager

            # Create fresh copy of Messages database
            db_manager = DatabaseManager()
            copy_path = db_manager.create_safe_copy()
            if not copy_path:
                logger.error("Failed to create database copy for handle resolution")
                return None

            # Query the handle table to get the handle.id value
            import sqlite3

            with sqlite3.connect(str(copy_path)) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT id FROM handle WHERE ROWID = ?", (handle_id,))

                row = cursor.fetchone()
                if not row:
                    logger.warning(f"No handle found for handle_id {handle_id}")
                    return None

                handle_id_value = row[0]

            # Use existing matching logic
            return self.match_handle_to_user(handle_id, handle_id_value)

        except Exception as e:
            logger.error(f"Error resolving user from handle_id {handle_id}: {e}")
            return None
