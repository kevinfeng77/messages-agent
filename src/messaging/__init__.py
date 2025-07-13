"""
Messaging module for the Messages Agent system.

This module provides functionality for message processing, decoding, and sending.
It includes message text decoding from binary formats and iMessage sending capabilities.
"""

from .decoder import MessageDecoder
from .service import MessageService, MessageResult, MessageMetrics
from .config import MessageConfig, load_config
from .exceptions import (
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

__all__ = [
    # Message decoding
    'MessageDecoder',
    
    # Message sending
    'MessageService',
    'MessageResult',
    'MessageMetrics',
    
    # Configuration
    'MessageConfig',
    'load_config',
    
    # Exceptions
    'MessagingError',
    'MessageValidationError',
    'RecipientValidationError',
    'MessageSendError',
    'NetworkError',
    'AuthenticationError',
    'RateLimitError',
    'ServiceUnavailableError',
    'MessageTooLargeError',
    'InvalidRecipientFormatError',
]