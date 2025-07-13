#!/usr/bin/env python3
"""
Quick test of real message sending.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.messaging import MessageService, MessageConfig


async def test_send():
    """Test sending a real message."""
    # Configure for real sending
    config = MessageConfig(
        require_imessage_enabled=True,
        max_message_length=500,
        rate_limit_messages_per_minute=5,
        log_message_content=True,   # Enable logging to see what happens
        log_recipients=True
    )
    
    try:
        service = MessageService(config)
        print(f"✅ Service initialized! Available: {service.is_available()}")
        
        # Test with your phone number
        recipient = input("Enter your phone number (e.g., +1234567890): ").strip()
        if not recipient:
            print("No recipient provided")
            return
            
        message = "🤖 Test message from Message Agent! This is a real iMessage."
        
        print(f"\nSending to: {recipient}")
        print(f"Message: {message}")
        print("Sending...")
        
        result = await service.send_message(recipient, message)
        
        if result.success:
            print("✅ SUCCESS!")
            print(f"Message ID: {result.message_id}")
            print(f"Duration: {result.duration_seconds:.3f}s")
            print("\nCheck your phone - message should arrive shortly!")
        else:
            print("❌ FAILED!")
            print(f"Error: {result.error}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_send())