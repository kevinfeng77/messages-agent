"""Messages Database Manager - Creates and manages the new messages.db"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.user.user import User
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class MessagesDatabase:
    """Manager for the new messages.db database with users table"""

    def __init__(self, db_path: str = "./data/messages.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)

    def create_database(self) -> bool:
        """
        Create the messages database with users table

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Create users table with handle_id column
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT NOT NULL,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        phone_number TEXT NOT NULL,
                        email TEXT NOT NULL,
                        handle_id INTEGER
                    )
                """
                )

                # Create chats table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id TEXT NOT NULL,
                        display_name TEXT NOT NULL,
                        users TEXT
                    )
                """
                )

                # Create indexes for performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_users_name ON users(first_name, last_name)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_users_handle_id ON users(handle_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chats_chat_id ON chats(chat_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chats_display_name ON chats(display_name)"
                )

                conn.commit()
                logger.info(
                    f"Created messages database with users and chats tables at {self.db_path}"
                )
                return True

        except sqlite3.Error as e:
            logger.error(f"Error creating messages database: {e}")
            return False

    def insert_user(self, user: User) -> bool:
        """
        Insert a single user into the users table

        Args:
            user: User object to insert

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO users (user_id, first_name, last_name, phone_number, email, handle_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        user.user_id,
                        user.first_name,
                        user.last_name,
                        user.phone_number,
                        user.email,
                        user.handle_id,
                    ),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Error inserting user {user.user_id}: {e}")
            return False

    def insert_users_batch(self, users: List[User]) -> int:
        """
        Insert multiple users in a batch operation

        Args:
            users: List of User objects to insert

        Returns:
            Number of users successfully inserted
        """
        if not users:
            return 0

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Prepare data for batch insert
                user_data = [
                    (
                        user.user_id,
                        user.first_name,
                        user.last_name,
                        user.phone_number,
                        user.email,
                        user.handle_id,
                    )
                    for user in users
                ]

                cursor.executemany(
                    """
                    INSERT INTO users (user_id, first_name, last_name, phone_number, email, handle_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    user_data,
                )

                inserted_count = cursor.rowcount
                conn.commit()

                logger.info(f"Inserted {inserted_count} users into messages database")
                return inserted_count

        except sqlite3.Error as e:
            logger.error(f"Error inserting users batch: {e}")
            return 0

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get a user by their ID

        Args:
            user_id: User ID to search for

        Returns:
            User object if found, None otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT user_id, first_name, last_name, phone_number, email, handle_id
                    FROM users WHERE user_id = ?
                """,
                    (user_id,),
                )

                row = cursor.fetchone()
                if row:
                    return User(*row)

                return None

        except sqlite3.Error as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    def get_users_by_phone(self, phone_number: str) -> List[User]:
        """
        Get users by phone number

        Args:
            phone_number: Phone number to search for

        Returns:
            List of User objects
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT user_id, first_name, last_name, phone_number, email, handle_id
                    FROM users WHERE phone_number = ?
                """,
                    (phone_number,),
                )

                return [User(*row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Error getting users by phone {phone_number}: {e}")
            return []

    def get_users_by_email(self, email: str) -> List[User]:
        """
        Get users by email address

        Args:
            email: Email address to search for

        Returns:
            List of User objects
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT user_id, first_name, last_name, phone_number, email, handle_id
                    FROM users WHERE email = ?
                """,
                    (email.lower(),),
                )

                return [User(*row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Error getting users by email {email}: {e}")
            return []

    def get_user_by_handle_id(self, handle_id: int) -> Optional[User]:
        """
        Get a user by their handle ID

        Args:
            handle_id: Handle ID to search for

        Returns:
            User object if found, None otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT user_id, first_name, last_name, phone_number, email, handle_id
                    FROM users WHERE handle_id = ?
                """,
                    (handle_id,),
                )

                row = cursor.fetchone()
                if row:
                    return User(*row)

                return None

        except sqlite3.Error as e:
            logger.error(f"Error getting user by handle_id {handle_id}: {e}")
            return None

    def update_user_handle_id(self, user_id: str, handle_id: int) -> bool:
        """
        Update a user's handle_id

        Args:
            user_id: User ID to update
            handle_id: New handle ID value

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    UPDATE users SET handle_id = ? WHERE user_id = ?
                """,
                    (handle_id, user_id),
                )

                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Updated handle_id for user {user_id} to {handle_id}")
                    return True
                else:
                    logger.warning(f"No user found with user_id {user_id}")
                    return False

        except sqlite3.Error as e:
            logger.error(f"Error updating handle_id for user {user_id}: {e}")
            return False

    def get_all_users(self, limit: Optional[int] = None) -> List[User]:
        """
        Get all users from the database

        Args:
            limit: Optional limit on number of users to return

        Returns:
            List of User objects
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                query = "SELECT user_id, first_name, last_name, phone_number, email, handle_id FROM users"
                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query)
                return [User(*row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def clear_users_table(self) -> bool:
        """
        Clear all users from the users table

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users")
                conn.commit()

                logger.info("Cleared all users from users table")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error clearing users table: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the messages database

        Returns:
            Dictionary with database statistics
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Get total user count
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]

                # Get users with phone numbers
                cursor.execute("SELECT COUNT(*) FROM users WHERE phone_number != ''")
                users_with_phone = cursor.fetchone()[0]

                # Get users with emails
                cursor.execute("SELECT COUNT(*) FROM users WHERE email != ''")
                users_with_email = cursor.fetchone()[0]

                # Get database file size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

                return {
                    "database_path": str(self.db_path),
                    "database_size_bytes": db_size,
                    "total_users": total_users,
                    "users_with_phone": users_with_phone,
                    "users_with_email": users_with_email,
                    "users_with_both": users_with_phone
                    + users_with_email
                    - total_users,
                }

        except sqlite3.Error as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

    def database_exists(self) -> bool:
        """
        Check if the messages database exists

        Returns:
            True if database file exists, False otherwise
        """
        return self.db_path.exists()

    def table_exists(self, table_name: str = "users") -> bool:
        """
        Check if a table exists in the database

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """,
                    (table_name,),
                )

                return cursor.fetchone() is not None

        except sqlite3.Error:
            return False

    def get_table_schema(self, table_name: str = "users") -> Optional[List[tuple]]:
        """
        Get the schema for a table

        Args:
            table_name: Name of table to get schema for

        Returns:
            List of column information tuples or None if error
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                return cursor.fetchall()

        except sqlite3.Error as e:
            logger.error(f"Error getting table schema for {table_name}: {e}")
            return None

    def insert_chat(self, chat_id: str, display_name: str, user_ids: List[str]) -> bool:
        """
        Insert a chat into the chats table

        Args:
            chat_id: Unique identifier for the chat
            display_name: Display name of the chat
            user_ids: List of user IDs in the chat

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Convert user_ids list to pipe-separated string
                users_str = "|".join(user_ids) if user_ids else ""

                cursor.execute(
                    """
                    INSERT INTO chats (chat_id, display_name, users)
                    VALUES (?, ?, ?)
                """,
                    (chat_id, display_name, users_str),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Error inserting chat {chat_id}: {e}")
            return False

    def insert_chats_batch(self, chats: List[Dict[str, Any]]) -> int:
        """
        Insert multiple chats in a batch operation

        Args:
            chats: List of chat dictionaries with keys: chat_id, display_name, user_ids

        Returns:
            Number of chats successfully inserted
        """
        if not chats:
            return 0

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Prepare data for batch insert
                chat_data = []
                for chat in chats:
                    users_str = (
                        "|".join(chat.get("user_ids", []))
                        if chat.get("user_ids")
                        else ""
                    )
                    chat_data.append((chat["chat_id"], chat["display_name"], users_str))

                cursor.executemany(
                    """
                    INSERT INTO chats (chat_id, display_name, users)
                    VALUES (?, ?, ?)
                """,
                    chat_data,
                )

                inserted_count = cursor.rowcount
                conn.commit()

                logger.info(f"Inserted {inserted_count} chats into messages database")
                return inserted_count

        except sqlite3.Error as e:
            logger.error(f"Error inserting chats batch: {e}")
            return 0

    def get_chat_by_id(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a chat by its ID

        Args:
            chat_id: Chat ID to search for

        Returns:
            Chat dictionary if found, None otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT chat_id, display_name, users
                    FROM chats WHERE chat_id = ?
                """,
                    (chat_id,),
                )

                row = cursor.fetchone()
                if row:
                    chat_id, display_name, users_str = row
                    user_ids = users_str.split("|") if users_str else []
                    return {
                        "chat_id": chat_id,
                        "display_name": display_name,
                        "user_ids": user_ids,
                    }

                return None

        except sqlite3.Error as e:
            logger.error(f"Error getting chat {chat_id}: {e}")
            return None

    def get_chats_by_display_name(self, display_name: str) -> List[Dict[str, Any]]:
        """
        Get chats by display name

        Args:
            display_name: Display name to search for

        Returns:
            List of chat dictionaries
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT chat_id, display_name, users
                    FROM chats WHERE display_name = ?
                """,
                    (display_name,),
                )

                chats = []
                for row in cursor.fetchall():
                    chat_id, display_name, users_str = row
                    user_ids = users_str.split("|") if users_str else []
                    chats.append(
                        {
                            "chat_id": chat_id,
                            "display_name": display_name,
                            "user_ids": user_ids,
                        }
                    )

                return chats

        except sqlite3.Error as e:
            logger.error(f"Error getting chats by display name {display_name}: {e}")
            return []

    def get_all_chats(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all chats from the database

        Args:
            limit: Optional limit on number of chats to return

        Returns:
            List of chat dictionaries
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                query = "SELECT chat_id, display_name, users FROM chats"
                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query)

                chats = []
                for row in cursor.fetchall():
                    chat_id, display_name, users_str = row
                    user_ids = users_str.split("|") if users_str else []
                    chats.append(
                        {
                            "chat_id": chat_id,
                            "display_name": display_name,
                            "user_ids": user_ids,
                        }
                    )

                return chats

        except sqlite3.Error as e:
            logger.error(f"Error getting all chats: {e}")
            return []

    def clear_chats_table(self) -> bool:
        """
        Clear all chats from the chats table

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chats")
                conn.commit()

                logger.info("Cleared all chats from chats table")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error clearing chats table: {e}")
            return False
