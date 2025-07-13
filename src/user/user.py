"""User class for managing user data"""

import uuid
from dataclasses import dataclass
from typing import Optional, Dict

from utils.logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class User:
    """User data class for managing user information"""

    user_id: str
    first_name: str
    last_name: str
    phone_number: str
    email: str
    handle_id: Optional[int] = None

    def __post_init__(self):
        """Validate user data after initialization"""
        if not self.user_id:
            raise ValueError("user_id is required")

        # At least one name component must be present, unless this is a handle-only user
        # Handle-only users (with handle_id but no contact info) can have empty names
        if not (self.first_name or self.last_name) and self.handle_id is None:
            raise ValueError("At least one of first_name or last_name must be provided")

        if not (self.phone_number or self.email):
            raise ValueError("At least one of phone_number or email must be provided")

    @classmethod
    def from_address_book_record(
        cls,
        first_name: str,
        last_name: str,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        user_id: Optional[str] = None,
        handle_id: Optional[int] = None,
    ) -> "User":
        """
        Create a User instance from address book data

        Args:
            first_name: First name from address book
            last_name: Last name from address book
            phone_number: Phone number from address book
            email: Email from address book
            user_id: Optional custom user ID (generates UUID if not provided)
            handle_id: Optional handle ID from messages database

        Returns:
            User instance
        """
        if user_id is None:
            user_id = str(uuid.uuid4())

        # Ensure we have at least one contact method
        if not phone_number and not email:
            raise ValueError("Must provide either phone_number or email")

        # Provide empty string if one is missing (to satisfy table constraints)
        phone_number = phone_number or ""
        email = email or ""

        return cls(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            email=email,
            handle_id=handle_id,
        )

    def to_dict(self) -> Dict[str, str]:
        """Convert user to dictionary for database operations"""
        return {
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "email": self.email,
            "handle_id": self.handle_id,
        }

    def __str__(self) -> str:
        """String representation of user"""
        contact_info = []
        if self.phone_number:
            contact_info.append(f"phone: {self.phone_number}")
        if self.email:
            contact_info.append(f"email: {self.email}")

        contact_str = " (" + ", ".join(contact_info) + ")" if contact_info else ""
        return f"{self.first_name} {self.last_name}{contact_str}"
