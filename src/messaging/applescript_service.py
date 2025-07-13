"""
AppleScript-based message service as fallback for py-imessage.

This module provides a more reliable alternative to py-imessage using
direct AppleScript automation, which tends to be more stable across
macOS versions.
"""

import asyncio
import logging
import subprocess
import time
from typing import Optional
from datetime import datetime

from .config import MessageConfig
from .exceptions import MessageSendError, AuthenticationError

logger = logging.getLogger(__name__)


class AppleScriptMessageService:
    """Message service using AppleScript automation."""
    
    def __init__(self, config: MessageConfig):
        self.config = config
    
    def _escape_applescript_string(self, text: str) -> str:
        """Escape quotes and special characters for AppleScript."""
        return text.replace('"', '\\"').replace('\\', '\\\\')
    
    def _send_message_applescript(self, recipient: str, message: str) -> str:
        """
        Send message using AppleScript.
        
        Args:
            recipient: Phone number or email
            message: Message content
            
        Returns:
            str: Message ID (timestamp-based)
            
        Raises:
            MessageSendError: If send fails
        """
        escaped_recipient = self._escape_applescript_string(recipient)
        escaped_message = self._escape_applescript_string(message)
        
        applescript = f'''
        tell application "Messages"
            -- Prevent Messages from coming to front
            set wasRunning to (application "Messages" is running)
            if not wasRunning then
                launch application "Messages"
            end if
            
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{escaped_recipient}" of targetService
            send "{escaped_message}" to targetBuddy
            
            -- Hide Messages if it wasn't running before
            if not wasRunning then
                tell application "System Events"
                    set visible of process "Messages" to false
                end tell
            end if
            
            return "sent"
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Generate a simple message ID
                message_id = f"applescript_{int(time.time())}"
                logger.info(f"AppleScript message sent successfully: {message_id}")
                return message_id
            else:
                error_msg = result.stderr.strip()
                if "AppleEvent handler failed" in error_msg:
                    raise AuthenticationError(
                        "AppleScript automation not permitted. "
                        "Grant Terminal permission in System Preferences > Security & Privacy > Privacy > Automation"
                    )
                else:
                    raise MessageSendError(f"AppleScript failed: {error_msg}")
                    
        except subprocess.TimeoutExpired:
            raise MessageSendError("AppleScript message send timed out")
        except Exception as e:
            raise MessageSendError(f"AppleScript error: {e}")
    
    async def send_message(self, recipient: str, message: str) -> str:
        """
        Send message asynchronously.
        
        Args:
            recipient: Phone number or email
            message: Message content
            
        Returns:
            str: Message ID
        """
        # Run AppleScript in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._send_message_applescript, 
            recipient, 
            message
        )
    
    def is_available(self) -> bool:
        """Check if AppleScript messaging is available."""
        try:
            result = subprocess.run(
                ['osascript', '-e', 'tell application "Messages" to return name'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False