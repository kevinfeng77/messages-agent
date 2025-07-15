#!/usr/bin/env python3
"""
Real-time iMessage Polling with Notifications

This script demonstrates the real-time iMessage polling service with 
live notifications when new messages arrive.
"""

import os
import sys
import signal
import time
from datetime import datetime
from typing import List, Dict, Any

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from src.database.polling_service import MessagePollingService
from src.database.messages_db import MessagesDatabase
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def format_message_content(content: str, max_length: int = 100) -> str:
    """Format message content for display"""
    if not content:
        return "[No text content]"
    
    # Clean up the content
    content = content.strip()
    
    # Truncate if too long
    if len(content) > max_length:
        content = content[:max_length-3] + "..."
    
    return content


def on_new_messages_received(new_messages: List[Dict[str, Any]], synced_count: int):
    """
    Callback function called when new messages are detected
    
    Args:
        new_messages: List of new message dictionaries from source database
        synced_count: Number of messages successfully synced
    """
    
    print("\n" + "🚨" * 20)
    print(f"📱 NEW MESSAGES DETECTED! ({len(new_messages)} found, {synced_count} synced)")
    print("🚨" * 20)
    
    # Connect to database to get user info
    messages_db = MessagesDatabase("./data/messages.db")
    
    # Show details for each new message
    for i, msg in enumerate(new_messages[:5], 1):  # Show first 5 messages
        try:
            # Get message content
            content = msg.get("extracted_text") or msg.get("text") or "[No content]"
            formatted_content = format_message_content(content)
            
            # Convert timestamp
            try:
                apple_timestamp = msg.get("date", 0)
                apple_epoch = datetime(2001, 1, 1)
                timestamp_seconds = apple_timestamp / 1_000_000_000
                message_time = apple_epoch.timestamp() + timestamp_seconds
                time_str = datetime.fromtimestamp(message_time).strftime("%I:%M:%S %p")
            except:
                time_str = "Unknown time"
            
            # Determine sender
            if msg.get("is_from_me"):
                sender = "📤 You"
            else:
                # Try to resolve handle_id to user name
                handle_id = msg.get("handle_id")
                if handle_id:
                    # Look up in our database first
                    try:
                        user = messages_db.get_user_by_handle_id(handle_id)
                        if user and (user.first_name or user.last_name):
                            sender = f"📥 {user.first_name} {user.last_name}".strip()
                        elif user and user.phone_number:
                            sender = f"📥 {user.phone_number}"
                        elif user and user.email:
                            sender = f"📥 {user.email}"
                        else:
                            sender = f"📥 Handle {handle_id}"
                    except:
                        sender = f"📥 Handle {handle_id}"
                else:
                    sender = "📥 Unknown"
            
            print(f"\n  {i}. {sender} at {time_str}")
            print(f"     💬 {formatted_content}")
            print(f"     🆔 ROWID: {msg.get('rowid', 'N/A')}")
            
        except Exception as e:
            print(f"  {i}. Error displaying message: {e}")
    
    if len(new_messages) > 5:
        print(f"\n  ... and {len(new_messages) - 5} more messages")
    
    print("\n" + "=" * 60)
    print(f"⏰ Last checked: {datetime.now().strftime('%I:%M:%S %p')}")
    print("🔄 Continuing to monitor for new messages...")
    print("   Press Ctrl+C to stop")
    print("=" * 60 + "\n")


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    print("\n\n🛑 Stopping iMessage polling service...")
    sys.exit(0)


def main():
    """Main function with real-time polling and notifications"""
    
    print("📱 iMessage Real-time Polling with Notifications")
    print("=" * 60)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize polling service
        print("🔧 Initializing polling service...")
        polling_service = MessagePollingService(
            data_dir="./data",
            poll_interval=1,  # Check every 1 second for near real-time
            batch_size=50
        )
        
        # Initialize database if needed
        if not polling_service.initialize():
            print("❌ Failed to initialize polling service")
            return
        
        print("✅ Polling service initialized")
        
        # Set up notification callback
        polling_service.set_new_message_callback(on_new_messages_received)
        print("🔔 Notification callback configured")
        
        # Show current status
        status = polling_service.get_status()
        state = status.get("polling_state", {})
        
        print(f"\n📊 Current Status:")
        print(f"   Last processed ROWID: {state.get('last_processed_rowid', 'N/A')}")
        print(f"   Total messages processed: {state.get('total_messages_processed', 'N/A')}")
        print(f"   Poll interval: {polling_service.poll_interval}s")
        
        # Run initial poll to show current state
        print(f"\n🔍 Running initial poll to check for messages...")
        result = polling_service.poll_once()
        
        if result["success"]:
            if result["new_messages"] > 0:
                print(f"✨ Found {result['new_messages']} new messages on startup!")
            else:
                print("📭 No new messages found - waiting for new ones...")
        else:
            print(f"⚠️  Initial poll failed: {result.get('error', 'Unknown error')}")
        
        print(f"\n🚀 Starting continuous monitoring...")
        print(f"🔄 Checking for new messages every {polling_service.poll_interval} seconds")
        print(f"📱 You'll be notified whenever new iMessages arrive!")
        print(f"\n   Press Ctrl+C to stop\n")
        
        # Start continuous polling
        polling_service.start_polling()
        
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Error in main: {e}")
    finally:
        print("👋 iMessage polling stopped. Goodbye!")


if __name__ == "__main__":
    main()