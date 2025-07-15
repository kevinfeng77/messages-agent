#!/usr/bin/env python3
"""
User Service Module

Provides service layer for user operations including database lookups,
phone number retrieval, and user management functionality.
"""

import re
from typing import Optional

from src.database.messages_db import MessagesDatabase
from src.user.user import User
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class UserService:
    """Service class for user-related operations."""

    def __init__(self, db: Optional[MessagesDatabase] = None):
        """
        Initialize UserService.
        
        Args:
            db: Optional MessagesDatabase instance. If None, creates a new instance.
        """
        self.db = db or MessagesDatabase()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID from database.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            User object if found, None otherwise
        """
        try:
            logger.info(f"Looking up user with ID: {user_id}")
            user = self.db.get_user_by_id(user_id)
            if user:
                logger.info(f"Found user: {user.first_name} {user.last_name}")
            else:
                logger.warning(f"User not found for ID: {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error looking up user {user_id}: {e}")
            raise

    def get_user_phone_number(self, user_id: str) -> Optional[str]:
        """
        Get phone number for a user.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            Phone number string if found, None otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        if not user.phone_number:
            logger.warning(f"No phone number for user: {user.first_name} {user.last_name}")
            return None
        
        # Format phone number for consistency
        formatted_phone = self.format_phone_number(user.phone_number)
        logger.info(f"Retrieved phone number for {user.first_name} {user.last_name}: {formatted_phone}")
        return formatted_phone

    def format_phone_number(self, phone: str) -> str:
        """
        Format phone number for text messaging.
        
        This function cleans and formats phone numbers to ensure compatibility
        with messaging services. It handles various input formats and normalizes
        them to a consistent format.
        
        Args:
            phone: Raw phone number string
            
        Returns:
            Formatted phone number string
            
        Examples:
            format_phone_number("(555) 123-4567") -> "+15551234567"
            format_phone_number("555-123-4567") -> "+15551234567"
            format_phone_number("+1 555 123 4567") -> "+15551234567"
        """
        if not phone:
            return phone
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # If it starts with +, keep it as is
        if cleaned.startswith('+'):
            return cleaned
        
        # If it's 10 digits, assume US number and add +1
        if len(cleaned) == 10:
            return f"+1{cleaned}"
        
        # If it's 11 digits and starts with 1, add +
        if len(cleaned) == 11 and cleaned.startswith('1'):
            return f"+{cleaned}"
        
        # Return as-is if we can't determine format
        logger.warning(f"Unable to format phone number: {phone}")
        return phone

    def get_user_for_messaging(self, user_id: str) -> tuple[Optional[User], Optional[str]]:
        """
        Get user and formatted phone number for messaging purposes.
        
        This is a convenience method that combines user lookup and phone
        number formatting for messaging workflows.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            Tuple of (User object, formatted phone number) or (None, None) if not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None, None
        
        phone = self.get_user_phone_number(user_id)
        return user, phone

    def validate_phone_number(self, phone: str) -> bool:
        """
        Validate if a phone number is in a reasonable format.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            True if phone number appears valid, False otherwise
        """
        if not phone:
            return False
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Check for valid formats:
        # +1xxxxxxxxxx (US/Canada with country code)
        # +xxxxxxxxxxx (International with country code)
        # xxxxxxxxxx (10 digit US)
        # 1xxxxxxxxxx (11 digit US with 1)
        
        if cleaned.startswith('+'):
            # International format - should have at least 10 digits after +
            return len(cleaned) >= 11 and cleaned[1:].isdigit()
        else:
            # Domestic format - 10 or 11 digits
            return len(cleaned) in [10, 11] and cleaned.isdigit()