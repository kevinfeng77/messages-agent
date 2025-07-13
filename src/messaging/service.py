"""
Message sending service using py-imessage.

This module provides the main MessageService class for sending text messages
via iMessage on macOS systems. It includes comprehensive error handling,
validation, retry logic, and monitoring capabilities.
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from .config import MessageConfig, config
from .applescript_service import AppleScriptMessageService
from .exceptions import (
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

logger = logging.getLogger(__name__)


@dataclass
class MessageResult:
    """Result of a message sending operation."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None
    retry_count: int = 0
    duration_seconds: float = 0.0


@dataclass
class MessageMetrics:
    """Metrics for message sending operations."""
    total_attempts: int = 0
    successful_sends: int = 0
    failed_sends: int = 0
    total_retries: int = 0
    average_duration: float = 0.0
    last_send_time: Optional[datetime] = None


class RateLimiter:
    """Simple rate limiter for message sending."""
    
    def __init__(self, messages_per_minute: int):
        self.messages_per_minute = messages_per_minute
        self.send_times: List[datetime] = []
    
    def check_rate_limit(self) -> bool:
        """Check if we can send a message without exceeding rate limits."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Remove old entries
        self.send_times = [t for t in self.send_times if t > cutoff]
        
        return len(self.send_times) < self.messages_per_minute
    
    def record_send(self):
        """Record a message send for rate limiting."""
        self.send_times.append(datetime.now())


class MessageService:
    """
    Service for sending text messages via iMessage.
    
    This service provides a high-level interface for sending messages with
    comprehensive error handling, validation, retry logic, and monitoring.
    """
    
    def __init__(self, config_override: Optional[MessageConfig] = None):
        """
        Initialize the message service.
        
        Args:
            config_override: Optional configuration override
        """
        self.config = config_override or config
        self.rate_limiter = RateLimiter(self.config.rate_limit_messages_per_minute)
        self.metrics = MessageMetrics()
        self._applescript_service: Optional[AppleScriptMessageService] = None
        self._imessage_client = None
        
        # Initialize messaging services
        self._init_messaging_services()
    
    def _init_messaging_services(self):
        """Initialize AppleScript messaging service (py-imessage has bugs)."""
        # py-imessage has bugs - concatenates phone number and message
        self._imessage_client = None
        logger.info("py-imessage disabled due to JavaScript bugs")
        
        # Initialize AppleScript messaging service as primary
        try:
            self._applescript_service = AppleScriptMessageService(self.config)
            if self._applescript_service.is_available():
                logger.info("AppleScript messaging service initialized successfully")
            else:
                logger.warning("AppleScript messaging service not available")
                if self.config.require_imessage_enabled:
                    raise ServiceUnavailableError("AppleScript messaging service not available")
                self._applescript_service = None
        except Exception as e:
            logger.error(f"AppleScript service failed to initialize: {e}")
            if self.config.require_imessage_enabled:
                raise ServiceUnavailableError(f"AppleScript messaging service unavailable: {e}")
            self._applescript_service = None
    
    def validate_recipient(self, recipient: str) -> bool:
        """
        Validate recipient format (phone number or email).
        
        Args:
            recipient: Phone number or email address
            
        Returns:
            bool: True if valid format
            
        Raises:
            InvalidRecipientFormatError: If format is invalid
        """
        if not recipient or not isinstance(recipient, str):
            raise InvalidRecipientFormatError("Recipient must be a non-empty string")
        
        recipient = recipient.strip()
        
        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if '@' in recipient and re.match(email_pattern, recipient):
            return True
        
        # Phone number validation (E.164 format or similar)
        # Remove common formatting characters
        phone = re.sub(r'[^\d+]', '', recipient)
        
        # Check for valid phone number patterns
        if re.match(r'^\+?1?[0-9]{10,15}$', phone):
            return True
        
        raise InvalidRecipientFormatError(f"Invalid recipient format: {recipient}")
    
    def validate_message_content(self, content: str) -> bool:
        """
        Validate message content.
        
        Args:
            content: Message content to validate
            
        Returns:
            bool: True if valid
            
        Raises:
            MessageTooLargeError: If content exceeds size limits
            MessageValidationError: If content is invalid
        """
        if not content or not isinstance(content, str):
            raise MessageValidationError("Message content must be a non-empty string")
        
        if len(content) > self.config.max_message_length:
            raise MessageTooLargeError(
                f"Message length {len(content)} exceeds limit of {self.config.max_message_length}"
            )
        
        # Check for potentially problematic content
        if content.strip() == "":
            raise MessageValidationError("Message content cannot be empty or whitespace only")
        
        return True
    
    async def _send_message_impl(self, recipient: str, content: str) -> MessageResult:
        """
        Internal implementation of message sending with py-imessage first, AppleScript fallback.
        
        Args:
            recipient: Validated recipient
            content: Validated message content
            
        Returns:
            MessageResult: Result of the send operation
        """
        start_time = time.time()
        
        try:
            # Use AppleScript service (py-imessage has bugs)
            if self._applescript_service is not None:
                message_id = await self._applescript_service.send_message(recipient, content)
                logger.info(f"Message sent via AppleScript: {message_id}")
                
                duration = time.time() - start_time
                
                return MessageResult(
                    success=True,
                    message_id=message_id,
                    timestamp=datetime.now(),
                    duration_seconds=duration
                )
            else:
                raise ServiceUnavailableError("AppleScript service not available")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            # Classify error types for better handling
            if "network" in error_msg.lower() or "connection" in error_msg.lower():
                raise NetworkError(f"Network error: {error_msg}")
            elif "auth" in error_msg.lower() or "permission" in error_msg.lower():
                raise AuthenticationError(f"Authentication error: {error_msg}")
            elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
                raise RateLimitError(f"Rate limit error: {error_msg}")
            else:
                raise MessageSendError(f"Send failed: {error_msg}")
    
    async def send_message(
        self,
        recipient: str,
        content: str,
        retry_on_failure: bool = True,
    ) -> MessageResult:
        """
        Send a text message to a recipient.
        
        Args:
            recipient: Phone number (E.164 format) or email address
            content: Message content to send
            retry_on_failure: Whether to retry on failure
            
        Returns:
            MessageResult: Result of the send operation
            
        Raises:
            MessagingError: Various messaging-related errors
        """
        # Update metrics
        self.metrics.total_attempts += 1
        
        # Validate inputs
        if self.config.validate_recipients:
            self.validate_recipient(recipient)
        self.validate_message_content(content)
        
        # Check rate limiting
        if not self.rate_limiter.check_rate_limit():
            raise RateLimitError("Rate limit exceeded - too many messages sent recently")
        
        # Log send attempt (respecting privacy settings)
        if self.config.log_recipients and self.config.log_message_content:
            logger.info(f"Sending message to {recipient}: {content[:50]}...")
        elif self.config.log_recipients:
            logger.info(f"Sending message to {recipient}")
        elif self.config.log_message_content:
            logger.info(f"Sending message: {content[:50]}...")
        else:
            logger.info("Sending message")
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retry_attempts:
            try:
                result = await self._send_message_impl(recipient, content)
                result.retry_count = retry_count
                
                # Record successful send
                self.rate_limiter.record_send()
                self.metrics.successful_sends += 1
                self.metrics.last_send_time = datetime.now()
                
                # Update average duration
                total_duration = (self.metrics.average_duration * (self.metrics.successful_sends - 1) + 
                                result.duration_seconds)
                self.metrics.average_duration = total_duration / self.metrics.successful_sends
                
                logger.info(f"Message sent successfully (retry count: {retry_count})")
                return result
                
            except (NetworkError, MessageSendError) as e:
                last_error = e
                retry_count += 1
                self.metrics.total_retries += 1
                
                if retry_count <= self.config.max_retry_attempts and retry_on_failure:
                    delay = self.config.initial_retry_delay * (
                        self.config.retry_backoff_factor ** (retry_count - 1)
                    )
                    logger.warning(
                        f"Message send failed (attempt {retry_count}), retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    break
            
            except (AuthenticationError, RateLimitError, ServiceUnavailableError,
                   MessageValidationError, RecipientValidationError) as e:
                # Don't retry these types of errors
                last_error = e
                break
        
        # All retries exhausted or non-retryable error
        self.metrics.failed_sends += 1
        error_msg = f"Message send failed after {retry_count} attempts: {last_error}"
        logger.error(error_msg)
        
        return MessageResult(
            success=False,
            error=str(last_error),
            timestamp=datetime.now(),
            retry_count=retry_count
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current service metrics.
        
        Returns:
            Dict containing performance and usage metrics
        """
        success_rate = 0.0
        if self.metrics.total_attempts > 0:
            success_rate = self.metrics.successful_sends / self.metrics.total_attempts
        
        return {
            'total_attempts': self.metrics.total_attempts,
            'successful_sends': self.metrics.successful_sends,
            'failed_sends': self.metrics.failed_sends,
            'success_rate': success_rate,
            'total_retries': self.metrics.total_retries,
            'average_duration_seconds': self.metrics.average_duration,
            'last_send_time': self.metrics.last_send_time.isoformat() if self.metrics.last_send_time else None,
            'rate_limit_messages_per_minute': self.config.rate_limit_messages_per_minute,
            'current_rate_limit_usage': len(self.rate_limiter.send_times)
        }
    
    def reset_metrics(self):
        """Reset all metrics counters."""
        self.metrics = MessageMetrics()
        logger.info("Service metrics reset")
    
    def is_available(self) -> bool:
        """
        Check if the message service is available.
        
        Returns:
            bool: True if service is ready to send messages
        """
        if self.config.require_imessage_enabled:
            return self._applescript_service is not None and self._applescript_service.is_available()
        return True  # Mock mode is always available