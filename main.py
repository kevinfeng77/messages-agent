#!/usr/bin/env python3
"""
Integrated Message Agent Main Script.

This script integrates the test_message_maker and
test_send_message_simple workflows:
1. Prompts user for a new message and display name
2. Uses test_message_maker.py to generate 3 potential responses
3. Allows user to choose 1 of the 3 responses
4. Sends the chosen response using test_send_message_simple functionality

Usage:
    python main.py
"""

# Configuration constants
REQUIRED_ENV_VARS = ["ANTHROPIC_API_KEY"]
DEFAULT_MAX_CONTEXT_MESSAGES = 200
DATABASE_PATH = "./data/messages.db"

import asyncio  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, continue without .env loading
    pass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.message_maker.api import generate_message_responses  # noqa: E402
from src.message_maker.types import MessageRequest  # noqa: E402
from src.database.messages_db import MessagesDatabase  # noqa: E402
from messaging.service import MessageService  # noqa: E402
from messaging.config import MessageConfig  # noqa: E402


# Find chat by display name
def find_chat_by_display_name(display_name: str) -> tuple[int, str]:
    """
    Find chat_id and first user_id by display name.
    If multiple chats have the same display name, returns the one with
    the most messages.

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
    chat_id = chat["chat_id"]
    user_ids = chat.get("user_ids", [])

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
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            print(f"⚠️  User not found in database for user_id: {user_id}")
            # Fallback to manual input
            phone = input(
                "Please enter the recipient's phone number " "(e.g., +1234567890): "
            ).strip()
            if not phone:
                raise ValueError("No phone number provided")
            return phone

        if not user.phone_number:
            print(
                f"⚠️  No phone number found for user: "
                f"{user.first_name} {user.last_name}"
            )
            # Fallback to manual input
            phone = input(
                f"Please enter phone number for {user.first_name} "
                f"{user.last_name} (e.g., +1234567890): "
            ).strip()
            if not phone:
                raise ValueError("No phone number provided")
            return phone

        print(
            f"📞 Found phone number for {user.first_name} "
            f"{user.last_name}: {user.phone_number}"
        )
        return user.phone_number

    except Exception as e:
        print(f"❌ Error looking up user: {e}")
        # Fallback to manual input
        phone = input(
            "Please enter the recipient's phone number (e.g., +1234567890): "
        ).strip()
        if not phone:
            raise ValueError("No phone number provided")
        return phone


def generate_message_responses_with_context(
    display_name: str,
    message_content: str,
    max_context_messages: int = DEFAULT_MAX_CONTEXT_MESSAGES,
) -> list[str]:
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

    try:
        # Find chat by display name
        chat_id, user_id = find_chat_by_display_name(display_name)

        # Create request
        request = MessageRequest(
            chat_id=chat_id, user_id=user_id, contents=message_content
        )

        # Generate responses
        response = generate_message_responses(request, max_context_messages)
        responses = response.get_responses()

        return responses

    except Exception as e:
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

    print("\n" + "=" * 60)

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

    try:
        # Create service (uses AppleScript)
        config = MessageConfig(
            require_imessage_enabled=False,  # Use AppleScript
            log_message_content=True,
            log_recipients=True,
        )

        service = MessageService(config)
        result = await service.send_message(phone_number, message)

        if result.success:
            print("✅ Message sent successfully!")
            return True
        else:
            return False

    except Exception as e:
        return False


async def main():

    # Get environment variables
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            print(f"Error: Missing required environment variable: {var}")
            return 1

    # Check database
    db_path = Path(DATABASE_PATH)
    if not db_path.exists():
        print(f"Database file not found at {DATABASE_PATH}")
        return 1

    # Get display name
    display_name = input("Enter display name of the chat: ").strip()
    if not display_name:
        print("No display name provided. Exiting.")
        return 1

    # Get message content
    message_content = input("Enter the message to respond to: ").strip()
    if not message_content:
        print("No message content provided. Exiting.")
        return 1

    # Generate responses
    responses = generate_message_responses_with_context(
        display_name, message_content
    )

    if not responses:
        print("No responses generated. Exiting.")
        return 1

    # Display response options
    selected_index = display_response_options(responses)
    selected_response = responses[selected_index]
    print(f"\nSelected: {selected_response}")

    # Get recipient details
    _, user_id = find_chat_by_display_name(display_name)
    phone_number = get_user_phone_number(user_id)

    # Send message
    success = await send_message_response(phone_number, selected_response)

    if not success:
        print("Workflow failed during message sending.")
        return 1

    print("Workflow completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
