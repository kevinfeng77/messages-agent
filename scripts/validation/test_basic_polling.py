#!/usr/bin/env python3
"""
Manual Polling Test - Simple script to test live message detection

Usage:
    python3 scripts/validation/test_basic_polling.py

This script will:
1. Test basic polling functionality
2. Monitor for new messages for 30 seconds
3. Display any detected messages in real-time
"""

import os
import sys
import time
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.database.polling_service import MessagePollingService
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def test_basic_polling():
    """Test basic polling functionality"""
    print("🔍 Testing Basic Polling Functionality")
    print("=" * 50)
    
    try:
        # Initialize service
        service = MessagePollingService("./data", poll_interval=2)
        
        if not service.initialize():
            print("❌ Failed to initialize polling service")
            return False
        
        print("✅ Polling service initialized")
        
        # Test single poll
        result = service.poll_once()
        
        if result.get("success"):
            print(f"✅ Poll successful:")
            print(f"  - New messages: {result.get('new_messages', 0)}")
            print(f"  - Synced messages: {result.get('synced_messages', 0)}")
            print(f"  - Last ROWID: {result.get('last_processed_rowid', 'Unknown')}")
            print(f"  - Duration: {result.get('duration_seconds', 0):.3f}s")
            return True
        else:
            print(f"❌ Poll failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_live_detection():
    """Test live message detection for a short period"""
    print("\n🚨 Testing Live Message Detection")
    print("=" * 50)
    print("The system will monitor for new messages for 30 seconds.")
    print("Send an iMessage during this time to test detection.")
    print("Press Ctrl+C to stop early.")
    
    detected_messages = []
    
    def on_new_messages(new_messages, synced_count):
        """Callback for new message detection"""
        for msg in new_messages:
            content = (msg.get("extracted_text") or 
                      msg.get("text") or 
                      "[No content]")[:50]
            sender = "You" if msg.get("is_from_me") else "Contact"
            detected_messages.append({
                "rowid": msg.get("rowid", 0),
                "sender": sender,
                "content": content
            })
            print(f"🚨 NEW MESSAGE: {sender} - {content}... (ROWID: {msg.get('rowid')})")
    
    try:
        service = MessagePollingService("./data", poll_interval=2)
        service.initialize()
        service.set_new_message_callback(on_new_messages)
        
        print("🔄 Monitoring started... (30 seconds)")
        
        # Monitor for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            result = service.poll_once()
            if not result.get("success"):
                print(f"⚠️  Poll error: {result.get('error')}")
            time.sleep(2)
        
        print(f"\n✅ Monitoring complete. Detected {len(detected_messages)} messages.")
        
        if detected_messages:
            print("📋 Detected messages:")
            for i, msg in enumerate(detected_messages[:5], 1):
                print(f"  {i}. {msg['sender']}: {msg['content']}... (ROWID: {msg['rowid']})")
        
        return len(detected_messages) > 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        return len(detected_messages) > 0
    except Exception as e:
        print(f"❌ Live detection test failed: {e}")
        return False


if __name__ == "__main__":
    print("🔬 Messages Agent - Basic Polling Test")
    print("=" * 50)
    
    # Test basic functionality
    basic_success = test_basic_polling()
    
    if not basic_success:
        print("\n❌ Basic polling test failed. Live detection skipped.")
        sys.exit(1)
    
    # Test live detection
    try:
        live_success = test_live_detection()
        
        if live_success:
            print("\n🎉 LIVE POLLING TEST PASSED!")
            print("The system successfully detected new messages.")
        else:
            print("\n⚠️  No messages detected during test period.")
            print("This is normal if no messages were sent during the test.")
            print("Basic polling functionality is working correctly.")
        
        print("\n✅ Message Agent polling system is operational!")
        
    except Exception as e:
        print(f"\n❌ Live detection test failed: {e}")
        sys.exit(1)