#!/usr/bin/env python3
"""
Test py-imessage send functionality.
This script tests if py-imessage can send a test message.
"""

import sys
import traceback
from py_imessage import imessage


def test_py_imessage_send():
    """Test py-imessage send functionality."""
    print("Testing py-imessage send functionality...")
    
    # Use your own phone number for testing
    test_recipient = input("Enter your phone number for testing (or press Enter to skip): ").strip()
    
    if not test_recipient:
        print("No recipient provided, skipping send test")
        return True
    
    try:
        print(f"Attempting to send test message to: {test_recipient}")
        
        # Test sending a message
        result = imessage.send(test_recipient, "Test message from py-imessage")
        print(f"Send result: {result}")
        
        print("✓ py-imessage send test completed")
        return True
        
    except Exception as e:
        print(f"✗ py-imessage send failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_py_imessage_send()
    sys.exit(0 if success else 1)