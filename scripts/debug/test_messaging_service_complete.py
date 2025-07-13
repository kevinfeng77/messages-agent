#!/usr/bin/env python3
"""
Complete test of the messaging service functionality.
This script tests both py-imessage and AppleScript fallback.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from messaging.service import MessageService
from messaging.config import MessageConfig


async def test_messaging_service():
    """Test the complete messaging service functionality."""
    print("Testing complete messaging service functionality...")
    
    try:
        # Create service with test configuration
        test_config = MessageConfig(
            max_message_length=1000,
            send_timeout_seconds=30,
            max_retry_attempts=1,
            require_imessage_enabled=False,  # Allow fallback to mock
            log_message_content=True,
            log_recipients=True
        )
        
        service = MessageService(test_config)
        print("✓ MessageService initialized successfully")
        
        # Test validation
        print("\n1. Testing validation...")
        
        # Valid recipients
        valid_recipients = ["+15551234567", "test@example.com", "555-123-4567"]
        for recipient in valid_recipients:
            try:
                service.validate_recipient(recipient)
                print(f"   ✓ Valid recipient: {recipient}")
            except Exception as e:
                print(f"   ✗ Unexpected validation failure for {recipient}: {e}")
        
        # Valid message content
        try:
            service.validate_message_content("Test message")
            print("   ✓ Valid message content accepted")
        except Exception as e:
            print(f"   ✗ Unexpected validation failure for valid content: {e}")
        
        # Test sending (will use mock if no real services available)
        print("\n2. Testing message sending...")
        
        # Use test recipient
        test_recipient = "+12538861994"
        print(f"Using test recipient: {test_recipient}")
        
        test_message = "Test message from Messages Agent"
        
        try:
            result = await service.send_message(test_recipient, test_message)
            
            if result.success:
                print(f"   ✓ Message sent successfully!")
                print(f"     Message ID: {result.message_id}")
                print(f"     Duration: {result.duration_seconds:.2f}s")
                print(f"     Timestamp: {result.timestamp}")
                print(f"     Retry count: {result.retry_count}")
            else:
                print(f"   ✗ Message send failed: {result.error}")
                return False
        except Exception as e:
            print(f"   ✗ Message send threw exception: {e}")
            traceback.print_exc()
            return False
        
        # Test metrics
        print("\n3. Testing metrics...")
        metrics = service.get_metrics()
        print(f"   Total attempts: {metrics['total_attempts']}")
        print(f"   Successful sends: {metrics['successful_sends']}")
        print(f"   Failed sends: {metrics['failed_sends']}")
        print(f"   Average duration: {metrics['average_duration_seconds']:.2f}s")
        print(f"   Success rate: {metrics['success_rate']:.1%}")
        
        print("\n✓ Complete messaging service test passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Messaging service test failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_messaging_service())
    sys.exit(0 if success else 1)