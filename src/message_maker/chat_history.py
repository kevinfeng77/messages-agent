"""Chat history retrieval logic for message generation.

This module implements the core database query logic to retrieve chat history
for a given chat_id and user_id, joining data from the chat_messages and 
messages tables for LLM consumption.
"""

import sqlite3
from typing import List
from pathlib import Path

from src.database.messages_db import MessagesDatabase
from src.message_maker.types import ChatMessage
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def get_chat_history_for_message_generation(chat_id: str, user_id: str) -> List[ChatMessage]:
    """
    Retrieve all messages in a chat, formatted for LLM consumption.
    
    This function joins the chat_messages and messages tables to get the full
    conversation history, ordered chronologically for proper context.
    
    Args:
        chat_id: Chat ID to retrieve messages for
        user_id: User ID making the request (to determine is_from_me)
        
    Returns:
        List of ChatMessage objects ordered chronologically (oldest first)
        
    Raises:
        ValueError: If chat_id cannot be converted to integer
        sqlite3.Error: If database query fails
    """
    # Convert chat_id to integer for database query
    try:
        chat_id_int = int(chat_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid chat_id format: {chat_id}. Must be convertible to integer.")
        raise ValueError(f"chat_id must be convertible to integer, got: {chat_id}")

    logger.info(f"Retrieving chat history for chat_id={chat_id_int}, user_id={user_id}")

    # Use default database path
    db_path = Path("./data/messages.db")
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # Query to join chat_messages and messages tables
            # Order by message_date for chronological context (oldest first)
            query = """
                SELECT m.contents, m.user_id, m.created_at
                FROM messages m
                JOIN chat_messages cm ON m.message_id = cm.message_id
                WHERE cm.chat_id = ?
                ORDER BY cm.message_date ASC
            """

            cursor.execute(query, (chat_id_int,))
            rows = cursor.fetchall()

            if not rows:
                logger.info(f"No messages found for chat_id={chat_id_int}")
                return []

            # Convert database results to ChatMessage objects
            chat_messages = []
            for row in rows:
                contents, db_user_id, created_at = row

                # Create ChatMessage for LLM consumption
                # is_from_me is determined relative to the requesting user_id
                chat_message = ChatMessage(
                    contents=contents,
                    is_from_me=(db_user_id == user_id),
                    created_at=created_at
                )

                # Validate the chat message
                chat_message.validate()
                chat_messages.append(chat_message)

            logger.info(f"Retrieved {len(chat_messages)} messages for chat_id={chat_id_int}")
            return chat_messages

    except sqlite3.Error as e:
        logger.error(f"Database error retrieving chat history for chat_id={chat_id_int}: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error retrieving chat history for chat_id={chat_id_int}: {e}")
        raise