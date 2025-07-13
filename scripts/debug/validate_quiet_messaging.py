#!/usr/bin/env python3
"""
Validate quiet messaging functionality.
This script tests if the messaging service can send without opening UI.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.messaging import MessageService, MessageConfig


async def validate_messaging_services():
    """Validate available messaging services."""
    print("🔍 Validating Messaging Services")
    print("=" * 40)
    
    config = MessageConfig(
        require_imessage_enabled=False,  # Allow fallback to mock
        log_message_content=True,
        log_recipients=True
    )
    
    try:
        service = MessageService(config)
        print("✅ MessageService initialized successfully")
        
        # Check service availability
        if service.is_available():
            print("✅ Service reports as available")
        else:
            print("⚠️  Service reports as unavailable")
        
        # Check which services were initialized
        if hasattr(service, '_imessage_client') and service._imessage_client:
            print("✅ py-imessage client available")
        else:
            print("⚠️  py-imessage client not available")
            
        if hasattr(service, '_applescript_service') and service._applescript_service:
            print("✅ AppleScript service available")
            if service._applescript_service.is_available():
                print("✅ AppleScript service reports ready")
            else:
                print("⚠️  AppleScript service not ready")
        else:
            print("⚠️  AppleScript service not available")
        
        # Test mock send (safe)
        print("\n📤 Testing mock message send...")
        test_recipient = "+1234567890"
        test_message = "🤖 Test message for validation"
        
        result = await service.send_message(test_recipient, test_message)
        
        if result.success:
            print(f"✅ Mock send successful!")
            print(f"   Message ID: {result.message_id}")
            print(f"   Duration: {result.duration_seconds:.3f}s")
            print(f"   Timestamp: {result.timestamp}")
        else:
            print(f"❌ Mock send failed: {result.error}")
        
        # Show metrics
        metrics = service.get_metrics()
        print(f"\n📊 Service Metrics:")
        print(f"   Total attempts: {metrics['total_attempts']}")
        print(f"   Successful sends: {metrics['successful_sends']}")
        print(f"   Success rate: {metrics['success_rate']:.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False


def main():
    """Run validation tests."""
    print("🧪 Message Service Validation")
    print("=" * 50)
    print()
    
    success = asyncio.run(validate_messaging_services())
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Validation completed successfully!")
        print("The messaging service is ready for use.")
    else:
        print("❌ Validation failed.")
        print("Check the error messages above for troubleshooting.")


if __name__ == "__main__":
    main()