#!/usr/bin/env python3
"""
Test AppleScript-based messaging as alternative to py-imessage.

This script tests if we can send messages using direct AppleScript,
which might be more reliable than py-imessage's JavaScript approach.
"""

import subprocess
import sys
from pathlib import Path


def test_applescript_message(recipient: str, message: str) -> bool:
    """
    Test sending a message using AppleScript.
    
    Args:
        recipient: Phone number or email
        message: Message content
        
    Returns:
        bool: True if successful
    """
    applescript = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{recipient}" of targetService
        send "{message}" to targetBuddy
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
            print(f"✅ Message sent successfully via AppleScript")
            print(f"Output: {result.stdout}")
            return True
        else:
            print(f"❌ AppleScript failed:")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ AppleScript timed out")
        return False
    except Exception as e:
        print(f"❌ Error running AppleScript: {e}")
        return False


def test_get_buddies():
    """Test getting list of available buddies/contacts."""
    applescript = '''
    tell application "Messages"
        return name of every buddy of (1st service whose service type = iMessage)
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ Available buddies: {result.stdout}")
            return True
        else:
            print(f"❌ Failed to get buddies: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting buddies: {e}")
        return False


def test_messages_permissions():
    """Test various Messages app permission levels."""
    print("🔍 Testing Messages App Permissions")
    print("=" * 40)
    
    # Test 1: Basic app access
    try:
        result = subprocess.run(
            ['osascript', '-e', 'tell application "Messages" to return name'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✅ Basic Messages app access")
        else:
            print(f"❌ No basic access: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Exception in basic access: {e}")
        return False
    
    # Test 2: Get services
    try:
        result = subprocess.run(
            ['osascript', '-e', 'tell application "Messages" to return service type of every service'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Can access services: {result.stdout.strip()}")
        else:
            print(f"❌ Cannot access services: {result.stderr}")
    except Exception as e:
        print(f"❌ Exception accessing services: {e}")
    
    # Test 3: Get buddies (this often requires additional permissions)
    print("\n⚠️  Testing buddy access (may require permissions)...")
    return test_get_buddies()


def main():
    """Run AppleScript messaging tests."""
    print("📱 AppleScript Messaging Test")
    print("=" * 40)
    
    # First test permissions
    if not test_messages_permissions():
        print("\n❌ Messages permissions not properly configured")
        print("Solutions:")
        print("1. System Preferences > Security & Privacy > Privacy > Automation")
        print("2. Grant Terminal access to control Messages")
        print("3. Or try running from different terminal/IDE")
        return
    
    print("\n📤 Ready to test message sending")
    print("⚠️  WARNING: This will send a REAL message!")
    
    recipient = input("Enter YOUR phone number for testing (+1234567890): ").strip()
    if not recipient:
        print("❌ No recipient provided")
        return
    
    confirm = input(f"Send test message to {recipient}? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Cancelled")
        return
    
    message = "🤖 AppleScript test message"
    print(f"\n🚀 Sending message...")
    print(f"To: {recipient}")
    print(f"Message: {message}")
    
    success = test_applescript_message(recipient, message)
    
    if success:
        print("\n🎉 AppleScript messaging works!")
        print("Consider implementing AppleScript-based message service as fallback")
    else:
        print("\n❌ AppleScript messaging failed")
        print("Check Messages app configuration and permissions")


if __name__ == "__main__":
    main()