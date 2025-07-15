"""
Unit tests for messaging service module.

Simplified tests focusing only on core message sending functionality.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.messaging.service import (
    MessageService, 
    MessageResult, 
    MessageMetrics, 
    RateLimiter
)
from src.messaging.config import MessageConfig
from src.messaging.exceptions import (
    MessageValidationError,
    InvalidRecipientFormatError,
    ServiceUnavailableError,
)


class TestMessageResult:
    """Test the MessageResult dataclass."""
    
    def test_message_result_creation(self):
        """Test creating a MessageResult."""
        timestamp = datetime.now()
        result = MessageResult(
            success=True,
            message_id="test_123",
            timestamp=timestamp,
            retry_count=0,
            duration_seconds=1.5
        )
        
        assert result.success is True
        assert result.message_id == "test_123"
        assert result.error is None
        assert result.timestamp == timestamp
        assert result.retry_count == 0
        assert result.duration_seconds == 1.5


class TestMessageService:
    """Test the MessageService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = MessageConfig(
            max_message_length=100,
            require_imessage_enabled=False,
            validate_recipients=True
        )
    
    @patch('src.messaging.service.AppleScriptMessageService')
    def test_service_creation(self, mock_applescript):
        """Test creating service with AppleScript."""
        mock_applescript.return_value.is_available.return_value = True
        service = MessageService(self.config)
        assert service.config == self.config
        assert service.is_available() is True
    
    def test_validate_recipient_valid_email(self):
        """Test validating valid email addresses."""
        service = MessageService(self.config)
        
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@domain.co.uk"
        ]
        
        for email in valid_emails:
            assert service.validate_recipient(email) is True
    
    def test_validate_recipient_valid_phone(self):
        """Test validating valid phone numbers."""
        service = MessageService(self.config)
        
        valid_phones = [
            "+1234567890",
            "1234567890",
            "+15551234567",
            "555-123-4567"
        ]
        
        for phone in valid_phones:
            assert service.validate_recipient(phone) is True
    
    def test_validate_recipient_invalid(self):
        """Test validating invalid recipients."""
        service = MessageService(self.config)
        
        invalid_recipients = [
            "",
            "   ",
            "invalid-email",
            "@domain.com",
            "123",
            None
        ]
        
        for recipient in invalid_recipients:
            with pytest.raises(InvalidRecipientFormatError):
                service.validate_recipient(recipient)
    
    def test_validate_message_content_valid(self):
        """Test validating valid message content."""
        service = MessageService(self.config)
        
        valid_messages = [
            "Hello world",
            "A" * 100,  # At the limit
            "Test message with numbers 123"
        ]
        
        for message in valid_messages:
            assert service.validate_message_content(message) is True
    
    def test_validate_message_content_invalid(self):
        """Test validating invalid message content."""
        service = MessageService(self.config)
        
        # Empty content
        with pytest.raises(MessageValidationError):
            service.validate_message_content("")
        
        with pytest.raises(MessageValidationError):
            service.validate_message_content("   ")
        
        with pytest.raises(MessageValidationError):
            service.validate_message_content(None)
    
    
    def test_get_metrics_initial(self):
        """Test getting initial metrics."""
        service = MessageService(self.config)
        metrics = service.get_metrics()
        
        assert metrics['total_attempts'] == 0
        assert metrics['successful_sends'] == 0
        assert metrics['failed_sends'] == 0
        assert metrics['success_rate'] == 0.0
    
    def test_is_available(self):
        """Test service availability."""
        config = MessageConfig(require_imessage_enabled=False)
        service = MessageService(config)
        assert service.is_available() is True