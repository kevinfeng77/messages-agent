"""
Configuration management for the messaging module.

This module handles all configuration settings for message sending,
including validation, timeouts, and service settings.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field, validator


class MessageConfig(BaseModel):
    """Configuration model for message sending settings."""
    
    # Message limits
    max_message_length: int = Field(
        default=1000,
        description="Maximum allowed message length in characters"
    )
    
    # Timeout settings
    send_timeout_seconds: int = Field(
        default=30,
        description="Timeout for message sending operations in seconds"
    )
    
    # Retry settings
    max_retry_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed sends"
    )
    
    retry_backoff_factor: float = Field(
        default=2.0,
        description="Exponential backoff factor for retries"
    )
    
    initial_retry_delay: float = Field(
        default=1.0,
        description="Initial delay before first retry in seconds"
    )
    
    # Rate limiting
    rate_limit_messages_per_minute: int = Field(
        default=60,
        description="Maximum messages per minute (rate limiting)"
    )
    
    # Service settings
    require_imessage_enabled: bool = Field(
        default=True,
        description="Whether to require iMessage service to be enabled"
    )
    
    validate_recipients: bool = Field(
        default=True,
        description="Whether to validate recipient formats"
    )
    
    # Logging settings
    log_message_content: bool = Field(
        default=False,
        description="Whether to log message content (privacy consideration)"
    )
    
    log_recipients: bool = Field(
        default=False,
        description="Whether to log recipient info (privacy consideration)"
    )
    
    @validator('max_message_length')
    def validate_max_message_length(cls, v):
        if v <= 0:
            raise ValueError("max_message_length must be positive")
        if v > 10000:
            raise ValueError("max_message_length cannot exceed 10000 characters")
        return v
    
    @validator('send_timeout_seconds')
    def validate_send_timeout(cls, v):
        if v <= 0:
            raise ValueError("send_timeout_seconds must be positive")
        if v > 300:  # 5 minutes max
            raise ValueError("send_timeout_seconds cannot exceed 300 seconds")
        return v
    
    @validator('max_retry_attempts')
    def validate_max_retry_attempts(cls, v):
        if v < 0:
            raise ValueError("max_retry_attempts must be non-negative")
        if v > 10:
            raise ValueError("max_retry_attempts cannot exceed 10")
        return v


def load_config() -> MessageConfig:
    """
    Load configuration from environment variables or defaults.
    
    Environment variables supported:
    - MESSAGE_MAX_LENGTH: Maximum message length
    - MESSAGE_SEND_TIMEOUT: Send timeout in seconds
    - MESSAGE_MAX_RETRIES: Maximum retry attempts
    - MESSAGE_RETRY_BACKOFF: Retry backoff factor
    - MESSAGE_INITIAL_DELAY: Initial retry delay
    - MESSAGE_RATE_LIMIT: Messages per minute limit
    - MESSAGE_REQUIRE_IMESSAGE: Require iMessage enabled (true/false)
    - MESSAGE_VALIDATE_RECIPIENTS: Validate recipient formats (true/false)
    - MESSAGE_LOG_CONTENT: Log message content (true/false)
    - MESSAGE_LOG_RECIPIENTS: Log recipient info (true/false)
    
    Returns:
        MessageConfig: Configured settings instance
    """
    config_data = {}
    
    # Load environment variables with fallbacks
    if max_length := os.getenv('MESSAGE_MAX_LENGTH'):
        config_data['max_message_length'] = int(max_length)
    
    if timeout := os.getenv('MESSAGE_SEND_TIMEOUT'):
        config_data['send_timeout_seconds'] = int(timeout)
    
    if max_retries := os.getenv('MESSAGE_MAX_RETRIES'):
        config_data['max_retry_attempts'] = int(max_retries)
    
    if backoff := os.getenv('MESSAGE_RETRY_BACKOFF'):
        config_data['retry_backoff_factor'] = float(backoff)
    
    if initial_delay := os.getenv('MESSAGE_INITIAL_DELAY'):
        config_data['initial_retry_delay'] = float(initial_delay)
    
    if rate_limit := os.getenv('MESSAGE_RATE_LIMIT'):
        config_data['rate_limit_messages_per_minute'] = int(rate_limit)
    
    if require_imessage := os.getenv('MESSAGE_REQUIRE_IMESSAGE'):
        config_data['require_imessage_enabled'] = require_imessage.lower() == 'true'
    
    if validate_recipients := os.getenv('MESSAGE_VALIDATE_RECIPIENTS'):
        config_data['validate_recipients'] = validate_recipients.lower() == 'true'
    
    if log_content := os.getenv('MESSAGE_LOG_CONTENT'):
        config_data['log_message_content'] = log_content.lower() == 'true'
    
    if log_recipients := os.getenv('MESSAGE_LOG_RECIPIENTS'):
        config_data['log_recipients'] = log_recipients.lower() == 'true'
    
    return MessageConfig(**config_data)


# Global configuration instance
config = load_config()