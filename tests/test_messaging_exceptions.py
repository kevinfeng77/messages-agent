"""
Unit tests for messaging exceptions module.

Tests the custom exception hierarchy and error handling.
"""

import pytest

from src.messaging.exceptions import (
    MessagingError,
    MessageValidationError,
    RecipientValidationError,
    MessageSendError,
    NetworkError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    MessageTooLargeError,
    InvalidRecipientFormatError,
)


class TestMessagingExceptions:
    """Test the messaging exception hierarchy."""
    
    def test_base_messaging_error(self):
        """Test the base MessagingError exception."""
        error = MessagingError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_exception_inheritance(self):
        """Test that all exceptions inherit from MessagingError."""
        exceptions = [
            MessageValidationError,
            RecipientValidationError,
            MessageSendError,
            NetworkError,
            AuthenticationError,
            RateLimitError,
            ServiceUnavailableError,
            MessageTooLargeError,
            InvalidRecipientFormatError,
        ]
        
        for exc_class in exceptions:
            error = exc_class("Test error")
            assert isinstance(error, MessagingError)
            assert isinstance(error, Exception)
    
    def test_message_validation_error_hierarchy(self):
        """Test MessageValidationError and its subclasses."""
        # MessageTooLargeError should inherit from MessageValidationError
        error = MessageTooLargeError("Message too large")
        assert isinstance(error, MessageTooLargeError)
        assert isinstance(error, MessageValidationError)
        assert isinstance(error, MessagingError)
    
    def test_recipient_validation_error_hierarchy(self):
        """Test RecipientValidationError and its subclasses."""
        # InvalidRecipientFormatError should inherit from RecipientValidationError
        error = InvalidRecipientFormatError("Invalid format")
        assert isinstance(error, InvalidRecipientFormatError)
        assert isinstance(error, RecipientValidationError)
        assert isinstance(error, MessagingError)
    
    def test_exception_messages(self):
        """Test that exception messages are preserved."""
        test_message = "This is a test error message"
        
        exceptions = [
            MessagingError(test_message),
            MessageValidationError(test_message),
            RecipientValidationError(test_message),
            MessageSendError(test_message),
            NetworkError(test_message),
            AuthenticationError(test_message),
            RateLimitError(test_message),
            ServiceUnavailableError(test_message),
            MessageTooLargeError(test_message),
            InvalidRecipientFormatError(test_message),
        ]
        
        for error in exceptions:
            assert str(error) == test_message
    
    def test_exception_raising_and_catching(self):
        """Test that exceptions can be raised and caught properly."""
        # Test specific exception catching
        with pytest.raises(MessageTooLargeError):
            raise MessageTooLargeError("Message is too large")
        
        # Test base class catching
        with pytest.raises(MessagingError):
            raise InvalidRecipientFormatError("Invalid recipient")
        
        # Test catching by hierarchy
        try:
            raise MessageTooLargeError("Too large")
        except MessageValidationError as e:
            assert isinstance(e, MessageTooLargeError)
        except MessagingError:
            pytest.fail("Should have been caught as MessageValidationError")
        
        try:
            raise InvalidRecipientFormatError("Invalid format")
        except RecipientValidationError as e:
            assert isinstance(e, InvalidRecipientFormatError)
        except MessagingError:
            pytest.fail("Should have been caught as RecipientValidationError")
    
    def test_exception_with_no_message(self):
        """Test that exceptions work without explicit messages."""
        error = MessagingError()
        assert str(error) == ""
        
        # Should still be the correct type
        assert isinstance(error, MessagingError)
    
    def test_exception_with_multiple_args(self):
        """Test exceptions with multiple arguments."""
        error = MessageSendError("Primary message", "Secondary info")
        assert "Primary message" in str(error)
        assert len(error.args) == 2
        assert error.args[0] == "Primary message"
        assert error.args[1] == "Secondary info"