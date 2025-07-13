"""
Integration tests for messaging module.

Tests the complete messaging system integration including configuration,
service initialization, and end-to-end message sending flows.
"""

import asyncio
import os
import pytest
from unittest.mock import patch, Mock

from src.messaging import (
    MessageService, 
    MessageConfig, 
    load_config,
    MessagingError,
    ServiceUnavailableError,
    InvalidRecipientFormatError,
    MessageTooLargeError,
    RateLimitError
)


class TestMessagingIntegration:
    """Integration tests for the complete messaging system."""
    
    def test_module_imports(self):
        """Test that all messaging module components can be imported."""
        from src.messaging import (
            MessageService,
            MessageResult,
            MessageMetrics,
            MessageConfig,
            load_config,
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
        
        # Verify all imports are available
        assert MessageService is not None
        assert MessageResult is not None
        assert MessageMetrics is not None
        assert MessageConfig is not None
        assert load_config is not None
        
        # Verify exception hierarchy
        assert issubclass(MessageValidationError, MessagingError)
        assert issubclass(MessageTooLargeError, MessageValidationError)
        assert issubclass(InvalidRecipientFormatError, RecipientValidationError)
    
    def test_config_integration_with_service(self):
        """Test configuration integration with message service."""
        # Create custom config
        config = MessageConfig(
            max_message_length=50,
            max_retry_attempts=1,
            rate_limit_messages_per_minute=10,
            require_imessage_enabled=False
        )
        
        # Create service with custom config
        service = MessageService(config)
        
        # Verify config is applied
        assert service.config.max_message_length == 50
        assert service.config.max_retry_attempts == 1
        assert service.config.rate_limit_messages_per_minute == 10
        assert service.rate_limiter.messages_per_minute == 10
    
    def test_environment_config_integration(self):
        """Test environment variable configuration integration."""
        env_vars = {
            'MESSAGE_MAX_LENGTH': '200',
            'MESSAGE_MAX_RETRIES': '5',
            'MESSAGE_REQUIRE_IMESSAGE': 'false'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()
            service = MessageService(config)
            
            assert service.config.max_message_length == 200
            assert service.config.max_retry_attempts == 5
            assert service.config.require_imessage_enabled is False
    
    @pytest.mark.asyncio
    async def test_end_to_end_message_flow_mock_mode(self):
        """Test complete end-to-end message sending flow in mock mode."""
        config = MessageConfig(
            max_message_length=100,
            max_retry_attempts=2,
            require_imessage_enabled=False,
            validate_recipients=True
        )
        
        service = MessageService(config)
        
        # Test successful send
        result = await service.send_message(
            recipient="test@example.com",
            content="Integration test message"
        )
        
        assert result.success is True
        assert result.message_id is not None
        assert result.error is None
        assert result.timestamp is not None
        
        # Verify metrics are updated
        metrics = service.get_metrics()
        assert metrics['total_attempts'] == 1
        assert metrics['successful_sends'] == 1
        assert metrics['success_rate'] == 1.0
    
    @pytest.mark.asyncio
    async def test_validation_integration(self):
        """Test validation integration across all components."""
        service = MessageService(MessageConfig(
            max_message_length=20,
            validate_recipients=True,
            require_imessage_enabled=False
        ))
        
        # Test recipient validation (should raise exception)
        with pytest.raises(InvalidRecipientFormatError):
            await service.send_message(
                recipient="invalid-recipient",
                content="Test"
            )
        
        # Test message length validation (should raise exception)
        with pytest.raises(MessageTooLargeError):
            await service.send_message(
                recipient="test@example.com",
                content="A" * 21  # Exceeds limit
            )
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test rate limiting integration."""
        config = MessageConfig(
            rate_limit_messages_per_minute=2,
            require_imessage_enabled=False
        )
        service = MessageService(config)
        
        # Send messages up to the limit
        result1 = await service.send_message("test1@example.com", "Message 1")
        result2 = await service.send_message("test2@example.com", "Message 2")
        
        assert result1.success is True
        assert result2.success is True
        
        # Next message should hit rate limit (raises exception)
        with pytest.raises(RateLimitError):
            await service.send_message("test3@example.com", "Message 3")
        
        # Verify metrics (rate limit error increments attempts but doesn't complete)
        metrics = service.get_metrics()
        assert metrics['total_attempts'] == 3  # All attempts counted including rate limited one
        assert metrics['successful_sends'] == 2
        assert metrics['failed_sends'] == 0  # Rate limit error doesn't get counted as failed send
    
    @pytest.mark.asyncio
    async def test_retry_logic_integration(self):
        """Test retry logic integration with error handling."""
        config = MessageConfig(
            max_retry_attempts=2,
            initial_retry_delay=0.1,  # Fast retries for testing
            retry_backoff_factor=1.0,
            require_imessage_enabled=False
        )
        service = MessageService(config)
        
        # Mock the implementation to fail first time, succeed second time
        call_count = 0
        original_impl = service._send_message_impl
        
        def mock_impl(recipient, content):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from src.messaging.exceptions import NetworkError
                raise NetworkError("Temporary network failure")
            return original_impl(recipient, content)
        
        service._send_message_impl = mock_impl
        
        result = await service.send_message(
            recipient="test@example.com",
            content="Retry test message"
        )
        
        assert result.success is True
        assert result.retry_count == 1
        assert call_count == 2
        
        # Verify metrics include retry count
        metrics = service.get_metrics()
        assert metrics['total_retries'] == 1
    
    @pytest.mark.asyncio
    async def test_multiple_service_instances(self):
        """Test multiple service instances with different configurations."""
        config1 = MessageConfig(
            max_message_length=100,
            rate_limit_messages_per_minute=60,
            require_imessage_enabled=False
        )
        
        config2 = MessageConfig(
            max_message_length=200,
            rate_limit_messages_per_minute=120,
            require_imessage_enabled=False
        )
        
        service1 = MessageService(config1)
        service2 = MessageService(config2)
        
        # Verify different configurations
        assert service1.config.max_message_length == 100
        assert service2.config.max_message_length == 200
        
        assert service1.rate_limiter.messages_per_minute == 60
        assert service2.rate_limiter.messages_per_minute == 120
        
        # Verify independent metrics
        await service1.send_message("test1@example.com", "Message 1")
        await service2.send_message("test2@example.com", "Message 2")
        
        metrics1 = service1.get_metrics()
        metrics2 = service2.get_metrics()
        
        assert metrics1['successful_sends'] == 1
        assert metrics2['successful_sends'] == 1
        
        # Metrics should be independent
        service1.reset_metrics()
        assert service1.get_metrics()['successful_sends'] == 0
        assert service2.get_metrics()['successful_sends'] == 1
    
    @patch('src.messaging.service.iMessage')
    def test_imessage_client_integration(self, mock_imessage_class):
        """Test integration with actual iMessage client (mocked)."""
        # Mock successful iMessage client
        mock_client = Mock()
        mock_send_result = Mock()
        mock_send_result.success = True
        mock_send_result.message_id = "imessage_123"
        mock_client.send.return_value = mock_send_result
        mock_imessage_class.return_value = mock_client
        
        config = MessageConfig(require_imessage_enabled=True)
        service = MessageService(config)
        
        # Verify client was initialized
        assert service._imessage_client == mock_client
        assert service.is_available() is True
        
        # Note: Can't easily test async send_message with mocked iMessage
        # because it would need proper async mocking setup
    
    def test_error_handling_integration(self):
        """Test error handling integration across components."""
        # Test service unavailable error
        config = MessageConfig(require_imessage_enabled=True)
        
        with patch('src.messaging.service.iMessage', None):
            with pytest.raises(ServiceUnavailableError):
                MessageService(config)
        
        # Test configuration validation errors
        with pytest.raises(Exception):  # Pydantic ValidationError
            MessageConfig(max_message_length=-1)
    
    @pytest.mark.asyncio
    async def test_logging_integration(self):
        """Test logging integration (basic verification)."""
        import logging
        
        # Capture log messages
        logger = logging.getLogger('src.messaging.service')
        
        # Create service and send message
        service = MessageService(MessageConfig(
            require_imessage_enabled=False,
            log_message_content=False,
            log_recipients=False
        ))
        
        with patch.object(logger, 'info') as mock_log:
            await service.send_message(
                recipient="test@example.com",
                content="Test message"
            )
            
            # Verify logging was called
            mock_log.assert_called()
            
            # Check that privacy settings are respected
            log_calls = [call.args[0] for call in mock_log.call_args_list]
            log_text = ' '.join(log_calls)
            
            # Should not contain recipient or content due to privacy settings
            assert "test@example.com" not in log_text
            assert "Test message" not in log_text