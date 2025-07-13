"""
Custom exceptions for the messaging module.

This module defines all custom exceptions used throughout the messaging system,
providing clear error types for different failure scenarios.
"""


class MessagingError(Exception):
    """Base exception for all messaging-related errors."""
    pass


class MessageValidationError(MessagingError):
    """Raised when message content or recipient validation fails."""
    pass


class RecipientValidationError(MessagingError):
    """Raised when recipient format or validation fails."""
    pass


class MessageSendError(MessagingError):
    """Raised when message sending fails."""
    pass


class NetworkError(MessagingError):
    """Raised when network connectivity issues occur."""
    pass


class AuthenticationError(MessagingError):
    """Raised when authentication or permission errors occur."""
    pass


class RateLimitError(MessagingError):
    """Raised when rate limiting is triggered."""
    pass


class ServiceUnavailableError(MessagingError):
    """Raised when the iMessage service is unavailable."""
    pass


class MessageTooLargeError(MessageValidationError):
    """Raised when message content exceeds size limits."""
    pass


class InvalidRecipientFormatError(RecipientValidationError):
    """Raised when recipient format is invalid (phone/email)."""
    pass