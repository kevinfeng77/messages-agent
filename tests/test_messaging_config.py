"""
Unit tests for messaging configuration module.

Tests the MessageConfig class, validation, and environment variable loading.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from src.messaging.config import MessageConfig, load_config


class TestMessageConfig:
    """Test the MessageConfig model and validation."""
    
    def test_default_config_values(self):
        """Test default configuration values."""
        config = MessageConfig()
        
        assert config.max_message_length == 1000
        assert config.send_timeout_seconds == 30
        assert config.max_retry_attempts == 3
        assert config.retry_backoff_factor == 2.0
        assert config.initial_retry_delay == 1.0
        assert config.rate_limit_messages_per_minute == 60
        assert config.require_imessage_enabled is True
        assert config.validate_recipients is True
        assert config.log_message_content is False
        assert config.log_recipients is False
    
    def test_custom_config_values(self):
        """Test custom configuration values."""
        config = MessageConfig(
            max_message_length=500,
            send_timeout_seconds=60,
            max_retry_attempts=5,
            retry_backoff_factor=3.0,
            initial_retry_delay=2.0,
            rate_limit_messages_per_minute=30,
            require_imessage_enabled=False,
            validate_recipients=False,
            log_message_content=True,
            log_recipients=True
        )
        
        assert config.max_message_length == 500
        assert config.send_timeout_seconds == 60
        assert config.max_retry_attempts == 5
        assert config.retry_backoff_factor == 3.0
        assert config.initial_retry_delay == 2.0
        assert config.rate_limit_messages_per_minute == 30
        assert config.require_imessage_enabled is False
        assert config.validate_recipients is False
        assert config.log_message_content is True
        assert config.log_recipients is True
    
    def test_max_message_length_validation(self):
        """Test validation for max_message_length."""
        # Valid values
        MessageConfig(max_message_length=1)
        MessageConfig(max_message_length=5000)
        MessageConfig(max_message_length=10000)
        
        # Invalid values
        with pytest.raises(ValidationError, match="max_message_length must be positive"):
            MessageConfig(max_message_length=0)
        
        with pytest.raises(ValidationError, match="max_message_length must be positive"):
            MessageConfig(max_message_length=-1)
        
        with pytest.raises(ValidationError, match="max_message_length cannot exceed 10000"):
            MessageConfig(max_message_length=10001)
    
    def test_send_timeout_validation(self):
        """Test validation for send_timeout_seconds."""
        # Valid values
        MessageConfig(send_timeout_seconds=1)
        MessageConfig(send_timeout_seconds=300)
        
        # Invalid values
        with pytest.raises(ValidationError, match="send_timeout_seconds must be positive"):
            MessageConfig(send_timeout_seconds=0)
        
        with pytest.raises(ValidationError, match="send_timeout_seconds must be positive"):
            MessageConfig(send_timeout_seconds=-1)
        
        with pytest.raises(ValidationError, match="send_timeout_seconds cannot exceed 300"):
            MessageConfig(send_timeout_seconds=301)
    
    def test_max_retry_attempts_validation(self):
        """Test validation for max_retry_attempts."""
        # Valid values
        MessageConfig(max_retry_attempts=0)
        MessageConfig(max_retry_attempts=10)
        
        # Invalid values
        with pytest.raises(ValidationError, match="max_retry_attempts must be non-negative"):
            MessageConfig(max_retry_attempts=-1)
        
        with pytest.raises(ValidationError, match="max_retry_attempts cannot exceed 10"):
            MessageConfig(max_retry_attempts=11)


class TestLoadConfig:
    """Test the load_config function and environment variable handling."""
    
    def test_load_config_defaults(self):
        """Test loading configuration with no environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
            
            # Should match default values
            assert config.max_message_length == 1000
            assert config.send_timeout_seconds == 30
            assert config.max_retry_attempts == 3
    
    def test_load_config_with_env_vars(self):
        """Test loading configuration with environment variables."""
        env_vars = {
            'MESSAGE_MAX_LENGTH': '2000',
            'MESSAGE_SEND_TIMEOUT': '45',
            'MESSAGE_MAX_RETRIES': '5',
            'MESSAGE_RETRY_BACKOFF': '1.5',
            'MESSAGE_INITIAL_DELAY': '0.5',
            'MESSAGE_RATE_LIMIT': '120',
            'MESSAGE_REQUIRE_IMESSAGE': 'false',
            'MESSAGE_VALIDATE_RECIPIENTS': 'false',
            'MESSAGE_LOG_CONTENT': 'true',
            'MESSAGE_LOG_RECIPIENTS': 'true'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()
            
            assert config.max_message_length == 2000
            assert config.send_timeout_seconds == 45
            assert config.max_retry_attempts == 5
            assert config.retry_backoff_factor == 1.5
            assert config.initial_retry_delay == 0.5
            assert config.rate_limit_messages_per_minute == 120
            assert config.require_imessage_enabled is False
            assert config.validate_recipients is False
            assert config.log_message_content is True
            assert config.log_recipients is True
    
    def test_load_config_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        # Test 'true' variations
        for true_val in ['true', 'True', 'TRUE']:
            with patch.dict(os.environ, {'MESSAGE_REQUIRE_IMESSAGE': true_val}, clear=True):
                config = load_config()
                assert config.require_imessage_enabled is True
        
        # Test 'false' variations
        for false_val in ['false', 'False', 'FALSE', 'no', 'off', '0']:
            with patch.dict(os.environ, {'MESSAGE_REQUIRE_IMESSAGE': false_val}, clear=True):
                config = load_config()
                assert config.require_imessage_enabled is False
    
    def test_load_config_invalid_env_vars(self):
        """Test handling of invalid environment variable values."""
        # Invalid integer
        with patch.dict(os.environ, {'MESSAGE_MAX_LENGTH': 'invalid'}, clear=True):
            with pytest.raises(ValueError):
                load_config()
        
        # Invalid float
        with patch.dict(os.environ, {'MESSAGE_RETRY_BACKOFF': 'invalid'}, clear=True):
            with pytest.raises(ValueError):
                load_config()
        
        # Values that fail validation
        with patch.dict(os.environ, {'MESSAGE_MAX_LENGTH': '-1'}, clear=True):
            with pytest.raises(ValidationError):
                load_config()
    
    def test_load_config_partial_env_vars(self):
        """Test loading with only some environment variables set."""
        env_vars = {
            'MESSAGE_MAX_LENGTH': '1500',
            'MESSAGE_LOG_CONTENT': 'true'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = load_config()
            
            # Overridden values
            assert config.max_message_length == 1500
            assert config.log_message_content is True
            
            # Default values
            assert config.send_timeout_seconds == 30
            assert config.max_retry_attempts == 3
            assert config.log_recipients is False