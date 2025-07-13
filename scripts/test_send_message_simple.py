#!/usr/bin/env python3
"""
Simple message sending test script using AppleScript (py-imessage has bugs).
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from messaging.service import MessageService
from messaging.config import MessageConfig


async def main():
    """Main function to test message sending."""
    print("📱 Message Agent - Send Test Message (AppleScript)")
    print("=" * 50)
    
    try:
        # Get recipient from user
        recipient = input("Enter phone number (e.g., +1234567890): ").strip()
        if not recipient:
            print("❌ No recipient provided. Exiting.")
            return
        
        # Get message from user
        message = input("Enter message to send: ").strip()
        if not message:
            print("❌ No message provided. Exiting.")
            return
        
        print(f"\n📤 Sending message to: {recipient}")
        print(f"💬 Message: {message}")
        print("\n⏳ Sending...")
        
        # Create service (uses AppleScript, not py-imessage)
        config = MessageConfig(
            require_imessage_enabled=False,  # Use AppleScript (py-imessage has bugs)
            log_message_content=True,
            log_recipients=True
        )
        
        service = MessageService(config)
        result = await service.send_message(recipient, message)
        
        if result.success:
            print(f"✅ Message sent successfully!")
            print(f"   📨 Message ID: {result.message_id}")
            print(f"   ⏱️  Duration: {result.duration_seconds:.2f}s")
            if result.retry_count > 0:
                print(f"   🔄 Retries: {result.retry_count}")
        else:
            print(f"❌ Failed to send message: {result.error}")
            
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)