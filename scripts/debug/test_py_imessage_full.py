#!/usr/bin/env python3
"""
Test full py-imessage functionality - both sending and receiving.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import py_imessage.imessage as py_imessage_lib
    from src.messaging.py_imessage_extended import PyiMessageReader
    print("✅ py-imessage modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import py-imessage modules: {e}")
    sys.exit(1)


def test_reading_messages():
    """Test reading messages from database."""
    print("\n📖 Testing Message Reading")
    print("=" * 40)
    
    try:
        with PyiMessageReader() as reader:
            print("✅ Database connection established")
            
            # Get recent messages
            print("\n📄 Recent Messages (last 5):")
            recent = reader.get_recent_messages(limit=5)
            for i, msg in enumerate(recent, 1):
                direction = "→" if msg['is_from_me'] else "←"
                handle = msg['handle'] or 'Unknown'
                text = msg['text'] or '[No text]'
                date = msg['date'].strftime('%Y-%m-%d %H:%M:%S') if msg['date'] else 'Unknown'
                print(f"  {i}. {direction} {handle}: {text[:50]}... ({date})")
            
            if not recent:
                print("  No recent messages found")
            
            # Get contacts
            print(f"\n📞 Contacts:")
            contacts = reader.get_contacts()
            print(f"  Found {len(contacts)} contacts")
            for contact in contacts[:5]:  # Show first 5
                print(f"    • {contact}")
            
            if len(contacts) > 5:
                print(f"    ... and {len(contacts) - 5} more")
            
            return True
            
    except Exception as e:
        print(f"❌ Database reading failed: {e}")
        if "authorization denied" in str(e).lower():
            print("💡 Need Full Disk Access - see System Preferences > Security & Privacy")
        return False


def test_sending_message():
    """Test sending a message."""
    print("\n📤 Testing Message Sending")
    print("=" * 40)
    
    test_number = "+12538861994"
    test_message = "🤖 py-imessage full test"
    
    print(f"Sending to: {test_number}")
    print(f"Message: {test_message}")
    
    try:
        print("\n🚀 Sending message...")
        result = py_imessage_lib.send(test_number, test_message)
        print(f"✅ Message sent! GUID: {result}")
        
        # Test message status
        print(f"\n📊 Checking message status...")
        try:
            status = py_imessage_lib.status(result)
            print(f"✅ Message status: {status}")
        except Exception as e:
            print(f"⚠️  Status check failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Message sending failed: {e}")
        return False


def test_conversation():
    """Test getting conversation history."""
    print("\n💬 Testing Conversation History")
    print("=" * 40)
    
    test_number = "+12538861994"
    
    try:
        with PyiMessageReader() as reader:
            conversation = reader.get_conversation(test_number, limit=10)
            
            if conversation:
                print(f"📱 Conversation with {test_number} (last {len(conversation)} messages):")
                for i, msg in enumerate(conversation, 1):
                    direction = "You" if msg['is_from_me'] else test_number
                    text = msg['text'] or '[No text]'
                    date = msg['date'].strftime('%H:%M:%S') if msg['date'] else 'Unknown'
                    print(f"  {i}. [{date}] {direction}: {text}")
            else:
                print(f"📭 No conversation found with {test_number}")
            
            return True
            
    except Exception as e:
        print(f"❌ Conversation reading failed: {e}")
        return False


def main():
    """Run comprehensive py-imessage tests."""
    print("🧪 Comprehensive py-imessage Test")
    print("=" * 50)
    print()
    
    # Test reading first (safer)
    reading_ok = test_reading_messages()
    
    # Test sending
    sending_ok = test_sending_message()
    
    # Test conversation (if reading works)
    conversation_ok = False
    if reading_ok:
        conversation_ok = test_conversation()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  📖 Reading: {'✅ Working' if reading_ok else '❌ Failed'}")
    print(f"  📤 Sending: {'✅ Working' if sending_ok else '❌ Failed'}")
    print(f"  💬 Conversations: {'✅ Working' if conversation_ok else '❌ Failed'}")
    
    if reading_ok and sending_ok:
        print("\n🎉 py-imessage is fully functional!")
        print("You can use it for both sending and receiving messages.")
    elif sending_ok:
        print("\n⚠️  py-imessage sending works, but reading needs Full Disk Access")
        print("Grant Full Disk Access to Terminal in System Preferences")
    else:
        print("\n❌ py-imessage has issues that need to be resolved")
        print("Check the error messages above for troubleshooting")


if __name__ == "__main__":
    main()