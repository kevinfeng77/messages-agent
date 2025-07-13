#!/usr/bin/env python3
"""
Test quiet messaging without opening Messages UI.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.messaging import MessageService, MessageConfig


async def test_quiet_message():
    """Test sending a message without opening UI."""
    print("🔧 Testing quiet message sending...")
    
    # Configure for real sending but minimal UI
    config = MessageConfig(
        require_imessage_enabled=True,
        log_message_content=False,
        log_recipients=False
    )
    
    try:
        service = MessageService(config)
        print("✅ Service initialized")
        
        # Send test message to yourself
        recipient = input("Enter YOUR phone number (+1234567890): ").strip()
        if not recipient:
            print("❌ No recipient provided")
            return
        
        message = "🤖 Quiet test message"
        print(f"📤 Sending quiet message to {recipient}...")
        
        result = await service.send_message(recipient, message)
        
        if result.success:
            print("✅ Message sent quietly!")
            print(f"   Duration: {result.duration_seconds:.3f}s")
        else:
            print(f"❌ Send failed: {result.error}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_quiet_message())