#!/usr/bin/env python3
"""
Simple test script for Message Maker Service.

Usage:
    python test_message_maker.py "display_name" "message_content" [context_limit]

Examples:
    python test_message_maker.py "Nick Kim" "how have you been"
    python test_message_maker.py "Nick Kim" "how have you been" 500
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from message_maker.api import generate_message_responses
from message_maker.types import MessageRequest
from database.messages_db import MessagesDatabase


def find_chat_by_display_name(display_name: str) -> tuple[int, str]:
    """
    Find chat_id and first user_id by display name.
    
    Args:
        display_name: The display name to search for
        
    Returns:
        Tuple of (chat_id, user_id)
        
    Raises:
        ValueError: If display name not found or multiple chats found
    """
    db = MessagesDatabase()
    chats = db.get_chats_by_display_name(display_name)
    
    if not chats:
        raise ValueError(f"No chat found with display name '{display_name}'")
    
    if len(chats) > 1:
        raise ValueError(f"Multiple chats found with display name '{display_name}'. Please use a more specific name.")
    
    chat = chats[0]
    chat_id = chat['chat_id']
    user_ids = chat.get('user_ids', [])
    
    if not user_ids:
        raise ValueError(f"No users found for chat '{display_name}'")
    
    # Use the first user_id
    user_id = user_ids[0]
    
    return chat_id, user_id


def test_message_generation(display_name: str, message_content: str, max_context_messages: int = 500):
    """
    Test message generation for a specific chat and message.
    
    Args:
        display_name: Display name of the chat
        message_content: Content of the message to respond to
        max_context_messages: Maximum number of recent messages for context (default: 500)
    """
    print(f"🧪 Testing Message Generation")
    print(f"Chat: {display_name}")
    print(f"Message: {message_content}")
    print(f"Context Limit: {max_context_messages} messages")
    print("=" * 60)
    
    try:
        # 1. Find chat by display name
        print("1. Looking up chat...")
        chat_id, user_id = find_chat_by_display_name(display_name)
        print(f"   ✅ Found chat_id: {chat_id}, user_id: {user_id}")
        
        # 2. Create request
        print("2. Creating request...")
        request = MessageRequest(
            chat_id=chat_id,
            user_id=user_id,
            contents=message_content
        )
        print(f"   ✅ Request created")
        
        # 3. Generate responses
        print("3. Generating responses...")
        response = generate_message_responses(request, max_context_messages)
        print(f"   ✅ Responses generated")
        
        # 4. Display results
        print("\n📱 Generated Responses:")
        print("=" * 60)
        responses = response.get_responses()
        for i, resp in enumerate(responses, 1):
            print(f"\nOption {i}:")
            print(f"  {resp}")
        
        print(f"\n✅ Test completed successfully!")
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python test_message_maker.py \"display_name\" \"message_content\" [context_limit]")
        print("\nExamples:")
        print("  python test_message_maker.py \"Nick Kim\" \"how have you been\"")
        print("  python test_message_maker.py \"Nick Kim\" \"how have you been\" 500")
        sys.exit(1)
    
    display_name = sys.argv[1]
    message_content = sys.argv[2]
    max_context_messages = int(sys.argv[3]) if len(sys.argv) == 4 else 500
    
    # Check for required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable is required")
        print("Please set your Anthropic API key:")
        print("  export ANTHROPIC_API_KEY=\"your_api_key_here\"")
        sys.exit(1)
    
    # Check if database exists
    db_path = Path("./data/messages.db")
    if not db_path.exists():
        print("❌ Error: Database file not found at ./data/messages.db")
        print("Please run the database migration scripts first.")
        sys.exit(1)
    
    success = test_message_generation(display_name, message_content, max_context_messages)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()