#!/usr/bin/env python3
"""
Test py-imessage directly to diagnose authorization issues.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import py_imessage.imessage as py_imessage_lib
    print("✅ py-imessage imported successfully")
except ImportError as e:
    print(f"❌ Failed to import py-imessage: {e}")
    sys.exit(1)


def test_py_imessage_send():
    """Test py-imessage send function directly."""
    print("\n🧪 Testing py-imessage send function")
    print("=" * 40)
    
    # Test recipient
    recipient = "+12538861994"
    print(f"Using test number: {recipient}")
    
    message = "🤖 Direct py-imessage test"
    
    print(f"\n📤 Attempting to send via py-imessage...")
    print(f"To: {recipient}")
    print(f"Message: {message}")
    print("⚠️  This will try to send a REAL message to the test number!")
    
    try:
        print("\n🚀 Calling py_imessage_lib.send()...")
        result = py_imessage_lib.send(recipient, message)
        print(f"✅ py-imessage send returned: {result}")
        print("🎉 py-imessage is working!")
        
    except Exception as e:
        print(f"❌ py-imessage send failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Check for specific error types
        error_str = str(e).lower()
        if "authorization" in error_str or "permission" in error_str:
            print("\n💡 This looks like a permissions issue.")
            print("Solutions:")
            print("1. System Preferences > Security & Privacy > Privacy > Automation")
            print("2. Make sure Python/Terminal has permission to control Messages")
            print("3. Try running from a different terminal or application")
        elif "javascript" in error_str:
            print("\n💡 This looks like a JavaScript API issue.")
            print("The patch may not have fully resolved the problem.")
        else:
            print("\n💡 This might be a different issue.")
            print("Check the full error message above for clues.")


if __name__ == "__main__":
    test_py_imessage_send()