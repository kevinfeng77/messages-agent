#!/usr/bin/env python3
"""
Integrated Message Agent Main Script.

This script integrates the test_message_maker and test_send_message_simple workflows:
1. Prompts user for a new message and display name
2. Uses test_message_maker.py to generate 3 potential responses
3. Allows user to choose 1 of the 3 responses
4. Sends the chosen response using test_send_message_simple functionality

Usage:
    python main.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, continue without .env loading
    pass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.message_maker.api import generate_message_responses
from src.message_maker.types import MessageRequest
from src.database.messages_db import MessagesDatabase
from messaging.service import MessageService
from messaging.config import MessageConfig


def load_environment_variables():
    """Load and validate required environment variables."""
    required_vars = ["ANTHROPIC_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Debug: Show masked API key to verify it's loaded
            if var == "ANTHROPIC_API_KEY":
                masked_key = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"   🔑 {var}: {masked_key} (length: {len(value)})")
    
    if missing_vars:
        print("❌ Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set your environment variables in one of these ways:")
        print("  1. Create a .env file with: ANTHROPIC_API_KEY=your_api_key_here")
        print("  2. Export as environment variable: export ANTHROPIC_API_KEY=\"your_api_key_here\"")
        return False
    
    return True


def find_chat_by_display_name(display_name: str) -> tuple[int, str]:
    """
    Find chat_id and first user_id by display name.
    If multiple chats have the same display name, returns the one with the most messages.
    
    Args:
        display_name: The display name to search for
        
    Returns:
        Tuple of (chat_id, user_id)
        
    Raises:
        ValueError: If display name not found or no users found for the chat
    """
    db = MessagesDatabase()
    chats = db.get_chats_by_display_name(display_name)
    
    if not chats:
        raise ValueError(f"No chat found with display name '{display_name}'")
    
    # Take the first chat (which has the highest message count due to ordering)
    chat = chats[0]
    chat_id = chat['chat_id']
    user_ids = chat.get('user_ids', [])
    
    if not user_ids:
        raise ValueError(f"No users found for chat '{display_name}'")
    
    # Use the first user_id
    user_id = user_ids[0]
    
    return chat_id, user_id


def get_user_phone_number(user_id: str) -> str:
    """
    Get phone number for a user_id from the database.
    
    Args:
        user_id: The user ID to look up
        
    Returns:
        Phone number string
        
    Raises:
        ValueError: If user not found or no phone number available
    """
    db = MessagesDatabase()
    # This is a placeholder - you'll need to implement this method in MessagesDatabase
    # For now, we'll prompt the user for the phone number
    print(f"⚠️  Phone number lookup not yet implemented for user_id: {user_id}")
    phone = input("Please enter the recipient's phone number (e.g., +1234567890): ").strip()
    if not phone:
        raise ValueError("No phone number provided")
    return phone


def generate_message_responses_with_context(display_name: str, message_content: str, max_context_messages: int = 200) -> list[str]:
    """
    Generate message responses using the message maker service.
    
    Args:
        display_name: Display name of the chat
        message_content: Content of the message to respond to
        max_context_messages: Maximum number of recent messages for context
        
    Returns:
        List of generated response strings
        
    Raises:
        Exception: If message generation fails
    """
    print(f"🤖 Generating responses for: {display_name}")
    print(f"📝 Message: {message_content}")
    print(f"📚 Using {max_context_messages} messages for context")
    
    try:
        # Find chat by display name
        chat_id, user_id = find_chat_by_display_name(display_name)
        print(f"   ✅ Found chat_id: {chat_id}, user_id: {user_id}")
        
        # Create request
        request = MessageRequest(
            chat_id=chat_id,
            user_id=user_id,
            contents=message_content
        )
        
        # Generate responses
        response = generate_message_responses(request, max_context_messages)
        responses = response.get_responses()
        
        print(f"   ✅ Generated {len(responses)} responses")
        return responses
        
    except Exception as e:
        print(f"❌ Error generating responses: {e}")
        raise


def display_response_options(responses: list[str]) -> int:
    """
    Display response options and get user selection.
    
    Args:
        responses: List of response strings
        
    Returns:
        Index of selected response (0-based)
        
    Raises:
        ValueError: If invalid selection
    """
    print("\n💬 Generated Response Options:")
    print("=" * 60)
    
    for i, response in enumerate(responses, 1):
        print(f"\nOption {i}:")
        print(f"  {response}")
    
    print(f"\n" + "=" * 60)
    
    while True:
        try:
            choice = input(f"Choose a response (1-{len(responses)}): ").strip()
            if not choice:
                continue
                
            choice_num = int(choice)
            if 1 <= choice_num <= len(responses):
                return choice_num - 1  # Convert to 0-based index
            else:
                print(f"❌ Please enter a number between 1 and {len(responses)}")
                
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user.")
            raise


async def send_message_response(phone_number: str, message: str) -> bool:
    """
    Send the selected message response.
    
    Args:
        phone_number: Recipient phone number
        message: Message content to send
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n📤 Sending message to: {phone_number}")
    print(f"💬 Message: {message}")
    print("\n⏳ Sending...")
    
    try:
        # Create service (uses AppleScript)
        config = MessageConfig(
            require_imessage_enabled=False,  # Use AppleScript
            log_message_content=True,
            log_recipients=True
        )
        
        service = MessageService(config)
        result = await service.send_message(phone_number, message)
        
        if result.success:
            print(f"✅ Message sent successfully!")
            print(f"   📨 Message ID: {result.message_id}")
            print(f"   ⏱️  Duration: {result.duration_seconds:.2f}s")
            if result.retry_count > 0:
                print(f"   🔄 Retries: {result.retry_count}")
            return True
        else:
            print(f"❌ Failed to send message: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False


async def main():
    """Main integration workflow."""
    print("🤖 Message Agent - Integrated Workflow")
    print("=" * 50)
    
    try:
        # 1. Load and validate environment variables
        print("1. Checking environment variables...")
        if not load_environment_variables():
            return 1
        print("   ✅ Environment variables loaded")
        
        # 2. Check if database exists
        print("2. Checking database...")
        db_path = Path("./data/messages.db")
        if not db_path.exists():
            print("❌ Error: Database file not found at ./data/messages.db")
            print("Please run the database migration scripts first.")
            return 1
        print("   ✅ Database found")
        
        # 3. Get user input for new message
        print("\n3. Getting message details...")
        display_name = input("Enter display name of the chat: ").strip()
        if not display_name:
            print("❌ No display name provided. Exiting.")
            return 1
        
        message_content = input("Enter the message to respond to: ").strip()
        if not message_content:
            print("❌ No message content provided. Exiting.")
            return 1
        
        # 4. Generate responses with default 200 message lookback
        print("\n4. Generating response options...")
        responses = generate_message_responses_with_context(display_name, message_content, 200)
        
        if not responses:
            print("❌ No responses generated. Exiting.")
            return 1
        
        # 5. Let user choose response
        print("\n5. Selecting response...")
        selected_index = display_response_options(responses)
        selected_response = responses[selected_index]
        print(f"\n✅ Selected: {selected_response}")
        
        # 6. Get recipient phone number
        print("\n6. Getting recipient details...")
        try:
            chat_id, user_id = find_chat_by_display_name(display_name)
            phone_number = get_user_phone_number(user_id)
        except Exception as e:
            print(f"❌ Error getting recipient details: {e}")
            return 1
        
        # 7. Send the message
        print("\n7. Sending message...")
        success = await send_message_response(phone_number, selected_response)
        
        if success:
            print(f"\n🎉 Workflow completed successfully!")
            return 0
        else:
            print(f"\n❌ Workflow failed during message sending.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)