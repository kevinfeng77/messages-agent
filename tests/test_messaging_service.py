"""
Unit tests for messaging service module.

Tests the MessageService class, validation, sending logic, and error handling.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.messaging.service import (
    MessageService, 
    MessageResult, 
    MessageMetrics, 
    RateLimiter
)
from src.messaging.config import MessageConfig
from src.messaging.exceptions import (
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


class TestMessageResult:
    """Test the MessageResult dataclass."""
    
    def test_message_result_creation(self):
        """Test creating a MessageResult."""
        timestamp = datetime.now()
        result = MessageResult(
            success=True,
            message_id="test_123",
            timestamp=timestamp,
            retry_count=2,
            duration_seconds=1.5
        )
        
        assert result.success is True
        assert result.message_id == "test_123"
        assert result.error is None
        assert result.timestamp == timestamp
        assert result.retry_count == 2
        assert result.duration_seconds == 1.5
    
    def test_message_result_failure(self):
        """Test creating a failed MessageResult."""
        result = MessageResult(
            success=False,
            error="Network timeout"
        )
        
        assert result.success is False
        assert result.message_id is None
        assert result.error == "Network timeout"


class TestMessageMetrics:
    """Test the MessageMetrics dataclass."""
    
    def test_metrics_defaults(self):
        """Test default metrics values."""
        metrics = MessageMetrics()
        
        assert metrics.total_attempts == 0
        assert metrics.successful_sends == 0
        assert metrics.failed_sends == 0
        assert metrics.total_retries == 0
        assert metrics.average_duration == 0.0
        assert metrics.last_send_time is None


class TestRateLimiter:
    """Test the RateLimiter class."""
    
    def test_rate_limiter_creation(self):
        """Test creating a rate limiter."""
        limiter = RateLimiter(messages_per_minute=60)
        assert limiter.messages_per_minute == 60
        assert len(limiter.send_times) == 0
    
    def test_rate_limit_check_empty(self):
        """Test rate limit check with no previous sends."""
        limiter = RateLimiter(messages_per_minute=60)
        assert limiter.check_rate_limit() is True
    
    def test_rate_limit_check_under_limit(self):
        """Test rate limit check under the limit."""
        limiter = RateLimiter(messages_per_minute=60)
        
        # Add some sends within the limit
        for _ in range(30):
            limiter.record_send()
        
        assert limiter.check_rate_limit() is True
    
    def test_rate_limit_check_at_limit(self):
        """Test rate limit check at the limit."""
        limiter = RateLimiter(messages_per_minute=60)
        
        # Add sends up to the limit
        for _ in range(60):
            limiter.record_send()
        
        assert limiter.check_rate_limit() is False
    
    def test_rate_limit_cleanup_old_entries(self):
        """Test that old rate limit entries are cleaned up."""
        limiter = RateLimiter(messages_per_minute=60)
        
        # Add old entries (more than 1 minute ago)
        old_time = datetime.now() - timedelta(minutes=2)
        limiter.send_times = [old_time] * 100
        
        # Should allow new sends after cleanup
        assert limiter.check_rate_limit() is True
        assert len(limiter.send_times) == 0


class TestMessageService:
    """Test the MessageService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = MessageConfig(
            max_message_length=100,
            send_timeout_seconds=10,
            max_retry_attempts=2,
            rate_limit_messages_per_minute=60,
            require_imessage_enabled=False,
            validate_recipients=True
        )
    
    def test_service_creation_no_imessage(self):
        """Test creating service without iMessage client."""
        with patch('src.messaging.service.iMessage', None):
            service = MessageService(self.config)
            assert service.config == self.config
            assert service._imessage_client is None
            assert service.is_available() is True  # Mock mode
    
    def test_service_creation_with_imessage_required(self):
        """Test creating service with iMessage required but unavailable."""
        config = MessageConfig(require_imessage_enabled=True)
        
        with patch('src.messaging.service.iMessage', None):
            with pytest.raises(ServiceUnavailableError):
                MessageService(config)
    
    @patch('src.messaging.service.iMessage')
    def test_service_creation_with_imessage(self, mock_imessage_class):
        """Test creating service with iMessage client."""
        mock_client = Mock()
        mock_imessage_class.return_value = mock_client
        
        service = MessageService(self.config)
        assert service._imessage_client == mock_client
        assert service.is_available() is True
    
    def test_validate_recipient_valid_email(self):
        """Test validating valid email addresses."""
        service = MessageService(self.config)
        
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@domain.co.uk",
            "123@test.com"
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
            "555-123-4567",
            "(555) 123-4567"
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
            "email@",
            "123",
            "abc",
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
            "Test message with numbers 123 and symbols !@#"
        ]
        
        for message in valid_messages:
            assert service.validate_message_content(message) is True
    
    def test_validate_message_content_invalid(self):
        """Test validating invalid message content."""
        service = MessageService(self.config)
        
        # Empty or None content
        with pytest.raises(MessageValidationError):
            service.validate_message_content("")
        
        with pytest.raises(MessageValidationError):
            service.validate_message_content("   ")
        
        with pytest.raises(MessageValidationError):
            service.validate_message_content(None)
        
        # Too large content
        with pytest.raises(MessageTooLargeError):
            service.validate_message_content("A" * 101)
    
    @pytest.mark.asyncio
    async def test_send_message_success_mock_mode(self):
        """Test successful message sending in mock mode."""
        service = MessageService(self.config)
        
        result = await service.send_message(
            recipient="test@example.com",
            content="Test message"
        )
        
        assert result.success is True
        assert result.message_id.startswith("mock_")
        assert result.error is None
        assert result.retry_count == 0
        assert result.duration_seconds > 0
        assert isinstance(result.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_send_message_validation_error(self):
        """Test message sending with validation errors."""
        service = MessageService(self.config)
        
        # Invalid recipient should raise exception
        with pytest.raises(InvalidRecipientFormatError):
            await service.send_message(
                recipient="invalid",
                content="Test message"
            )
    
    @pytest.mark.asyncio
    async def test_send_message_rate_limit(self):
        """Test message sending with rate limiting."""
        config = MessageConfig(
            rate_limit_messages_per_minute=1,
            require_imessage_enabled=False
        )
        service = MessageService(config)
        
        # First message should succeed
        result1 = await service.send_message(
            recipient="test@example.com",
            content="Test message 1"
        )
        assert result1.success is True
        
        # Second message should hit rate limit (throws exception)
        with pytest.raises(RateLimitError):
            await service.send_message(
                recipient="test@example.com",
                content="Test message 2"
            )
    
    @pytest.mark.asyncio
    async def test_send_message_with_retries(self):
        """Test message sending with retry logic."""
        service = MessageService(self.config)
        
        # Mock the internal send method to fail first, then succeed
        call_count = 0
        original_send = service._send_message_impl
        
        def mock_send(recipient, content):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("Network failure")
            return original_send(recipient, content)
        
        service._send_message_impl = mock_send
        
        result = await service.send_message(
            recipient="test@example.com",
            content="Test message"
        )
        
        assert result.success is True
        assert result.retry_count == 1
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_message_max_retries_exceeded(self):
        """Test message sending when max retries are exceeded."""
        service = MessageService(self.config)
        
        # Mock the internal send method to always fail
        def mock_send(recipient, content):
            raise NetworkError("Persistent network failure")
        
        service._send_message_impl = mock_send
        
        result = await service.send_message(
            recipient="test@example.com",
            content="Test message"
        )
        
        assert result.success is False
        assert result.retry_count == self.config.max_retry_attempts + 1
        assert "Persistent network failure" in result.error
    
    @pytest.mark.asyncio
    async def test_send_message_non_retryable_error(self):
        """Test message sending with non-retryable errors."""
        service = MessageService(self.config)
        
        # Mock the internal send method to raise non-retryable error
        def mock_send(recipient, content):
            raise AuthenticationError("Authentication failed")
        
        service._send_message_impl = mock_send
        
        result = await service.send_message(
            recipient="test@example.com",
            content="Test message"
        )
        
        assert result.success is False
        assert result.retry_count == 0  # No retries for auth errors
        assert "Authentication failed" in result.error
    
    def test_get_metrics_initial(self):
        """Test getting initial metrics."""
        service = MessageService(self.config)
        metrics = service.get_metrics()
        
        assert metrics['total_attempts'] == 0
        assert metrics['successful_sends'] == 0
        assert metrics['failed_sends'] == 0
        assert metrics['success_rate'] == 0.0
        assert metrics['total_retries'] == 0
        assert metrics['average_duration_seconds'] == 0.0
        assert metrics['last_send_time'] is None
    
    @pytest.mark.asyncio
    async def test_get_metrics_after_sends(self):
        """Test getting metrics after some message sends."""
        service = MessageService(self.config)
        
        # Send some messages
        await service.send_message("test1@example.com", "Message 1")
        await service.send_message("test2@example.com", "Message 2")
        
        metrics = service.get_metrics()
        
        assert metrics['total_attempts'] == 2
        assert metrics['successful_sends'] == 2
        assert metrics['failed_sends'] == 0
        assert metrics['success_rate'] == 1.0
        assert metrics['average_duration_seconds'] > 0
        assert metrics['last_send_time'] is not None
    
    def test_reset_metrics(self):
        """Test resetting service metrics."""
        service = MessageService(self.config)
        
        # Modify metrics manually
        service.metrics.total_attempts = 10
        service.metrics.successful_sends = 8
        service.metrics.failed_sends = 2
        
        # Reset and verify
        service.reset_metrics()
        metrics = service.get_metrics()
        
        assert metrics['total_attempts'] == 0
        assert metrics['successful_sends'] == 0
        assert metrics['failed_sends'] == 0
    
    def test_is_available_mock_mode(self):
        """Test service availability in mock mode."""
        config = MessageConfig(require_imessage_enabled=False)
        service = MessageService(config)
        assert service.is_available() is True
    
    @patch('src.messaging.service.iMessage')
    def test_is_available_with_imessage(self, mock_imessage_class):
        """Test service availability with iMessage client."""
        mock_client = Mock()
        mock_imessage_class.return_value = mock_client
        
        config = MessageConfig(require_imessage_enabled=True)
        service = MessageService(config)
        assert service.is_available() is True
    
    def test_is_available_no_imessage_required(self):
        """Test service availability when iMessage is required but not available."""
        config = MessageConfig(require_imessage_enabled=True)
        
        with patch('src.messaging.service.iMessage', None):
            with pytest.raises(ServiceUnavailableError):
                MessageService(config)