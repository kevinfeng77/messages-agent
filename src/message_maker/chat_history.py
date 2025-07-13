"""Chat history retrieval logic for message generation.

This module provides functionality to retrieve chat history for a given chat_id
and user_id, joining data from the chat_messages and messages tables for LLM
consumption and message generation context.
"""

import sqlite3
from typing import List, Optional
from pathlib import Path

from src.database.messages_db import MessagesDatabase
from src.message_maker.types import ChatMessage, DatabaseMessage
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class ChatHistoryService:
    """Service for retrieving chat history from the messages database."""

    def __init__(self, db_path: str = "./data/messages.db"):
        """
        Initialize the chat history service.

        Args:
            db_path: Path to the messages database file
        """
        self.db_path = Path(db_path)
        self.db = MessagesDatabase(db_path)

    def get_chat_history_for_message_generation(
        self, chat_id: str, user_id: str
    ) -> List[ChatMessage]:
        """
        Retrieve all messages in a chat, formatted for LLM consumption.

        This function joins the chat_messages and messages tables to get the full
        conversation history, ordered chronologically for proper context.

        Args:
            chat_id: Chat ID to retrieve messages for (converted to int internally)
            user_id: User ID making the request (to determine is_from_me context)

        Returns:
            List of ChatMessage objects ordered chronologically (oldest first)

        Raises:
            ValueError: If chat_id cannot be converted to integer
            sqlite3.Error: If database query fails
        """
        try:
            # Convert chat_id to integer for database query
            chat_id_int = int(chat_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid chat_id format: {chat_id}. Must be convertible to integer.")
            raise ValueError(f"chat_id must be convertible to integer, got: {chat_id}")

        logger.info(f"Retrieving chat history for chat_id={chat_id_int}, user_id={user_id}")

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Query to join chat_messages and messages tables
                # Order by message_date for chronological context (oldest first)
                query = """
                    SELECT m.message_id, m.user_id, m.contents, m.is_from_me, 
                           m.created_at, cm.message_date, cm.chat_id
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
                    message_id, db_user_id, contents, is_from_me, created_at, message_date, db_chat_id = row

                    # Create DatabaseMessage for validation and conversion
                    db_message = DatabaseMessage(
                        message_id=message_id,
                        user_id=db_user_id,
                        contents=contents,
                        is_from_me=bool(is_from_me),
                        created_at=created_at,
                        message_date=message_date,
                        chat_id=db_chat_id
                    )

                    # Validate the database message
                    db_message.validate()

                    # Convert to ChatMessage for LLM consumption
                    # Note: is_from_me is determined relative to the requesting user_id
                    # If the message user_id matches the requesting user_id, it's from them
                    chat_message = ChatMessage(
                        contents=contents,
                        is_from_me=(db_user_id == user_id),
                        created_at=created_at
                    )

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

    def get_recent_chat_history(
        self, chat_id: str, user_id: str, limit: int = 50
    ) -> List[ChatMessage]:
        """
        Retrieve recent messages in a chat with a limit.

        Args:
            chat_id: Chat ID to retrieve messages for
            user_id: User ID making the request
            limit: Maximum number of recent messages to return

        Returns:
            List of ChatMessage objects (most recent first, then reversed for chronological order)
        """
        try:
            chat_id_int = int(chat_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid chat_id format: {chat_id}. Must be convertible to integer.")
            raise ValueError(f"chat_id must be convertible to integer, got: {chat_id}")

        if limit <= 0:
            raise ValueError("limit must be a positive integer")

        logger.info(f"Retrieving recent {limit} messages for chat_id={chat_id_int}, user_id={user_id}")

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Get the most recent messages first, then reverse for chronological order
                query = """
                    SELECT m.message_id, m.user_id, m.contents, m.is_from_me, 
                           m.created_at, cm.message_date, cm.chat_id
                    FROM messages m
                    JOIN chat_messages cm ON m.message_id = cm.message_id
                    WHERE cm.chat_id = ?
                    ORDER BY cm.message_date DESC
                    LIMIT ?
                """

                cursor.execute(query, (chat_id_int, limit))
                rows = cursor.fetchall()

                if not rows:
                    logger.info(f"No recent messages found for chat_id={chat_id_int}")
                    return []

                # Process messages and reverse to get chronological order
                chat_messages = []
                for row in reversed(rows):  # Reverse to get oldest first
                    message_id, db_user_id, contents, is_from_me, created_at, message_date, db_chat_id = row

                    chat_message = ChatMessage(
                        contents=contents,
                        is_from_me=(db_user_id == user_id),
                        created_at=created_at
                    )

                    chat_message.validate()
                    chat_messages.append(chat_message)

                logger.info(f"Retrieved {len(chat_messages)} recent messages for chat_id={chat_id_int}")
                return chat_messages

        except sqlite3.Error as e:
            logger.error(f"Database error retrieving recent chat history for chat_id={chat_id_int}: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error retrieving recent chat history for chat_id={chat_id_int}: {e}")
            raise

    def chat_exists(self, chat_id: str) -> bool:
        """
        Check if a chat exists in the database.

        Args:
            chat_id: Chat ID to check for existence

        Returns:
            True if chat exists, False otherwise
        """
        try:
            chat_id_int = int(chat_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid chat_id format: {chat_id}. Must be convertible to integer.")
            return False

        try:
            chat_data = self.db.get_chat_by_id(chat_id_int)
            return chat_data is not None

        except Exception as e:
            logger.error(f"Error checking if chat exists for chat_id={chat_id_int}: {e}")
            return False

    def get_chat_participants(self, chat_id: str) -> List[str]:
        """
        Get the list of user IDs participating in a chat.

        Args:
            chat_id: Chat ID to get participants for

        Returns:
            List of user IDs participating in the chat
        """
        try:
            chat_id_int = int(chat_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid chat_id format: {chat_id}. Must be convertible to integer.")
            return []

        try:
            chat_data = self.db.get_chat_by_id(chat_id_int)
            if chat_data:
                return chat_data.get("user_ids", [])
            return []

        except Exception as e:
            logger.error(f"Error getting chat participants for chat_id={chat_id_int}: {e}")
            return []

    def get_message_count(self, chat_id: str) -> int:
        """
        Get the total number of messages in a chat.

        Args:
            chat_id: Chat ID to count messages for

        Returns:
            Total number of messages in the chat
        """
        try:
            chat_id_int = int(chat_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid chat_id format: {chat_id}. Must be convertible to integer.")
            return 0

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM chat_messages
                    WHERE chat_id = ?
                    """,
                    (chat_id_int,)
                )

                count = cursor.fetchone()[0]
                logger.debug(f"Chat {chat_id_int} has {count} messages")
                return count

        except sqlite3.Error as e:
            logger.error(f"Database error counting messages for chat_id={chat_id_int}: {e}")
            return 0

        except Exception as e:
            logger.error(f"Unexpected error counting messages for chat_id={chat_id_int}: {e}")
            return 0


# Convenience function for direct usage
def get_chat_history_for_message_generation(chat_id: str, user_id: str) -> List[ChatMessage]:
    """
    Convenience function to retrieve chat history for message generation.

    Args:
        chat_id: Chat ID to retrieve messages for
        user_id: User ID making the request

    Returns:
        List of ChatMessage objects ordered chronologically
    """
    service = ChatHistoryService()
    return service.get_chat_history_for_message_generation(chat_id, user_id)