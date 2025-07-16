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
                
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys = ON")

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

                # Create chats table (normalized - no users field)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id INTEGER NOT NULL PRIMARY KEY,
                        display_name TEXT NOT NULL
                    )
                """
                )

                # Create chat_users junction table for many-to-many relationship
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_users (
                        chat_id INTEGER NOT NULL,
                        user_id TEXT NOT NULL,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                        PRIMARY KEY (chat_id, user_id)
                    )
                """
                )

                # Create messages table with simplified schema
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id INTEGER NOT NULL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        contents TEXT NOT NULL,
                        is_from_me BOOLEAN,
                        created_at TIMESTAMP NOT NULL
                    )
                """
                )
                
                # COMPATIBILITY: Create 'message' table alias for polling service
                # The polling service expects 'message' (singular) but we use 'messages' (plural)
                cursor.execute(
                    """
                    CREATE VIEW IF NOT EXISTS message AS 
                    SELECT 
                        message_id as ROWID,
                        message_id,
                        user_id,
                        contents as text,
                        NULL as attributedBody,
                        0 as handle_id,
                        created_at as date,
                        NULL as date_read,
                        is_from_me,
                        'iMessage' as service,
                        NULL as guid
                    FROM messages
                """
                )

                # Create chat_messages junction table (from chat_message_join)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        chat_id INTEGER NOT NULL,
                        message_id INTEGER NOT NULL,
                        message_date TIMESTAMP NOT NULL,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id) ON DELETE CASCADE,
                        FOREIGN KEY (message_id) REFERENCES messages (message_id) ON DELETE CASCADE,
                        PRIMARY KEY (chat_id, message_id)
                    )
                """
                )

                # Create polling_state table for sync tracking
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS polling_state (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        last_processed_rowid INTEGER NOT NULL DEFAULT 0,
                        last_sync_timestamp TEXT NOT NULL,
                        total_messages_processed INTEGER NOT NULL DEFAULT 0,
                        sync_status TEXT NOT NULL DEFAULT 'idle',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
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
                    "CREATE INDEX IF NOT EXISTS idx_chats_display_name ON chats(display_name)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_users_chat_id ON chat_users(chat_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_users_user_id ON chat_users(user_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_message_id ON messages(message_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_is_from_me ON messages(is_from_me)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_id ON chat_messages(chat_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_messages_message_id ON chat_messages(message_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_messages_message_date ON chat_messages(message_date)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_polling_state_last_sync ON polling_state(last_sync_timestamp)"
                )

                # Create conversations table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        chat_id INTEGER NOT NULL,
                        users TEXT NOT NULL,  -- JSON array of participant user_ids
                        created_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,  -- can be null for in progress chats
                        count INTEGER NOT NULL,
                        summary TEXT,  -- AI generated summary
                        status TEXT DEFAULT 'active',  -- active, completed
                        initiated_by TEXT NOT NULL,  -- user_id that initiated this chat
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id) ON DELETE CASCADE
                    )
                """
                )

                # Create conversation_messages table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                        conversation_id TEXT NOT NULL,
                        message_id INTEGER NOT NULL,
                        sequence_number INTEGER NOT NULL,  -- order within conversation
                        PRIMARY KEY (conversation_id, message_id),
                        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                        FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
                    )
                """
                )

                # Create conversation_embeddings table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_embeddings (
                        embedding_id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        embedding_vector BLOB NOT NULL,  -- numpy array as bytes
                        embedding_model TEXT NOT NULL,  -- e.g., 'text-embedding-3-small'
                        embedding_dimension INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,  -- JSON: Store participant names, dates, etc.
                        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                    )
                """
                )


                conn.commit()
                logger.info(
                    f"Created messages database with users, chats, messages, chat_messages, conversations, and embeddings tables at {self.db_path}"
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

    def insert_chat(
        self, chat_id: int, display_name: str, user_ids: List[str] = None
    ) -> bool:
        """
        Insert a chat into the chats table and optionally add users

        Args:
            chat_id: Unique integer identifier for the chat
            display_name: Display name of the chat
            user_ids: Optional list of user IDs to add to the chat

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Insert chat
                cursor.execute(
                    """
                    INSERT INTO chats (chat_id, display_name)
                    VALUES (?, ?)
                """,
                    (chat_id, display_name),
                )

                # Add users to the chat if provided
                if user_ids:
                    chat_user_data = [(chat_id, user_id) for user_id in user_ids]
                    cursor.executemany(
                        """
                        INSERT INTO chat_users (chat_id, user_id)
                        VALUES (?, ?)
                    """,
                        chat_user_data,
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
            chats: List of chat dictionaries with keys: chat_id (int), display_name, user_ids

        Returns:
            Number of chats successfully inserted
        """
        if not chats:
            return 0

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Prepare chat data for batch insert
                chat_data = [(chat["chat_id"], chat["display_name"]) for chat in chats]

                cursor.executemany(
                    """
                    INSERT INTO chats (chat_id, display_name)
                    VALUES (?, ?)
                """,
                    chat_data,
                )

                # Prepare chat_users data for batch insert
                chat_user_data = []
                for chat in chats:
                    chat_id = chat["chat_id"]
                    user_ids = chat.get("user_ids", [])
                    if user_ids:
                        for user_id in user_ids:
                            chat_user_data.append((chat_id, user_id))

                if chat_user_data:
                    cursor.executemany(
                        """
                        INSERT INTO chat_users (chat_id, user_id)
                        VALUES (?, ?)
                    """,
                        chat_user_data,
                    )

                inserted_count = len(chat_data)
                conn.commit()

                logger.info(
                    f"Inserted {inserted_count} chats and {len(chat_user_data)} chat-user relationships into messages database"
                )
                return inserted_count

        except sqlite3.Error as e:
            logger.error(f"Error inserting chats batch: {e}")
            return 0

    def get_chat_by_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a chat by its ID with associated users

        Args:
            chat_id: Integer chat ID to search for

        Returns:
            Chat dictionary with user_ids list if found, None otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Get chat details
                cursor.execute(
                    """
                    SELECT chat_id, display_name
                    FROM chats WHERE chat_id = ?
                """,
                    (chat_id,),
                )

                chat_row = cursor.fetchone()
                if not chat_row:
                    return None

                chat_id, display_name = chat_row

                # Get associated user IDs
                cursor.execute(
                    """
                    SELECT user_id
                    FROM chat_users WHERE chat_id = ?
                    ORDER BY user_id
                """,
                    (chat_id,),
                )

                user_ids = [row[0] for row in cursor.fetchall()]

                return {
                    "chat_id": chat_id,
                    "display_name": display_name,
                    "user_ids": user_ids,
                }

        except sqlite3.Error as e:
            logger.error(f"Error getting chat {chat_id}: {e}")
            return None

    def get_chats_by_display_name(self, display_name: str) -> List[Dict[str, Any]]:
        """
        Get chats by display name with associated users

        Args:
            display_name: Display name to search for

        Returns:
            List of chat dictionaries with user_ids, ordered by message count (highest first)
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Get chats with the display name, ordered by message count (highest first)
                cursor.execute(
                    """
                    SELECT c.chat_id, c.display_name, COALESCE(COUNT(cm.message_id), 0) as message_count
                    FROM chats c
                    LEFT JOIN chat_messages cm ON c.chat_id = cm.chat_id
                    WHERE c.display_name = ?
                    GROUP BY c.chat_id, c.display_name
                    ORDER BY message_count DESC, c.chat_id
                """,
                    (display_name,),
                )

                chat_rows = cursor.fetchall()
                if not chat_rows:
                    return []

                chats = []
                for chat_id, display_name, message_count in chat_rows:
                    # Get users for this chat
                    cursor.execute(
                        """
                        SELECT user_id
                        FROM chat_users WHERE chat_id = ?
                        ORDER BY user_id
                    """,
                        (chat_id,),
                    )

                    user_ids = [row[0] for row in cursor.fetchall()]

                    chats.append(
                        {
                            "chat_id": chat_id,
                            "display_name": display_name,
                            "user_ids": user_ids,
                            "message_count": message_count,
                        }
                    )

                return chats

        except sqlite3.Error as e:
            logger.error(f"Error getting chats by display name {display_name}: {e}")
            return []

    def get_all_chats(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all chats from the database with their associated users

        Args:
            limit: Optional limit on number of chats to return

        Returns:
            List of chat dictionaries with user_ids
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Get all chats
                query = "SELECT chat_id, display_name FROM chats ORDER BY chat_id"
                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query)
                chat_rows = cursor.fetchall()

                chats = []
                for chat_id, display_name in chat_rows:
                    # Get users for this chat
                    cursor.execute(
                        """
                        SELECT user_id
                        FROM chat_users WHERE chat_id = ?
                        ORDER BY user_id
                    """,
                        (chat_id,),
                    )

                    user_ids = [row[0] for row in cursor.fetchall()]

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
        Clear all chats and chat-user relationships

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Clear chat_users first due to foreign key constraint
                cursor.execute("DELETE FROM chat_users")
                cursor.execute("DELETE FROM chats")

                conn.commit()

                logger.info("Cleared all chats and chat-user relationships")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error clearing chats tables: {e}")
            return False

    def add_user_to_chat(self, chat_id: int, user_id: str) -> bool:
        """
        Add a user to an existing chat

        Args:
            chat_id: Integer chat ID to add user to
            user_id: User ID to add

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO chat_users (chat_id, user_id)
                    VALUES (?, ?)
                """,
                    (chat_id, user_id),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Error adding user {user_id} to chat {chat_id}: {e}")
            return False

    def remove_user_from_chat(self, chat_id: int, user_id: str) -> bool:
        """
        Remove a user from a chat

        Args:
            chat_id: Integer chat ID to remove user from
            user_id: User ID to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    DELETE FROM chat_users 
                    WHERE chat_id = ? AND user_id = ?
                """,
                    (chat_id, user_id),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Error removing user {user_id} from chat {chat_id}: {e}")
            return False

    def get_chats_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all chats that a user participates in

        Args:
            user_id: User ID to get chats for

        Returns:
            List of chat dictionaries
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT c.chat_id, c.display_name
                    FROM chats c
                    JOIN chat_users cu ON c.chat_id = cu.chat_id
                    WHERE cu.user_id = ?
                    ORDER BY c.chat_id
                """,
                    (user_id,),
                )

                chats = []
                for chat_id, display_name in cursor.fetchall():
                    # Get all users for this chat
                    cursor.execute(
                        """
                        SELECT user_id
                        FROM chat_users WHERE chat_id = ?
                        ORDER BY user_id
                    """,
                        (chat_id,),
                    )

                    user_ids = [row[0] for row in cursor.fetchall()]

                    chats.append(
                        {
                            "chat_id": chat_id,
                            "display_name": display_name,
                            "user_ids": user_ids,
                        }
                    )

                return chats

        except sqlite3.Error as e:
            logger.error(f"Error getting chats for user {user_id}: {e}")
            return []

    def get_chat_users_with_details(self, chat_id: int) -> List[Dict[str, Any]]:
        """
        Get full user details for all users in a chat

        Args:
            chat_id: Integer chat ID to get users for

        Returns:
            List of user detail dictionaries
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT u.user_id, u.first_name, u.last_name, u.phone_number, u.email, u.handle_id
                    FROM users u
                    JOIN chat_users cu ON u.user_id = cu.user_id
                    WHERE cu.chat_id = ?
                    ORDER BY u.first_name, u.last_name
                """,
                    (chat_id,),
                )

                users = []
                for row in cursor.fetchall():
                    user_id, first_name, last_name, phone_number, email, handle_id = row
                    users.append(
                        {
                            "user_id": user_id,
                            "first_name": first_name,
                            "last_name": last_name,
                            "phone_number": phone_number,
                            "email": email,
                            "handle_id": handle_id,
                        }
                    )

                return users

        except sqlite3.Error as e:
            logger.error(f"Error getting user details for chat {chat_id}: {e}")
            return []

    def insert_message(
        self,
        message_id: int,
        user_id: str,
        contents: str,
        is_from_me: bool,
        created_at: str,
    ) -> bool:
        """
        Insert a single message into the messages table

        Args:
            message_id: Unique numeric identifier for the message
            user_id: ID of the user who sent/received the message
            contents: Text content of the message
            is_from_me: Whether the message was sent by the user
            created_at: Timestamp when the message was created (ISO format)

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO messages (message_id, user_id, contents, is_from_me, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (message_id, user_id, contents, is_from_me, created_at),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Error inserting message {message_id}: {e}")
            return False

    def insert_messages_batch(self, messages: List[Dict[str, Any]]) -> int:
        """
        Insert multiple messages in a batch operation

        Args:
            messages: List of message dictionaries with keys:
                     message_id (int), user_id, contents, is_from_me, created_at

        Returns:
            Number of messages successfully inserted
        """
        if not messages:
            return 0

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Prepare data for batch insert
                message_data = [
                    (
                        msg["message_id"],
                        msg["user_id"],
                        msg["contents"],
                        msg["is_from_me"],
                        msg["created_at"],
                    )
                    for msg in messages
                ]

                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO messages (message_id, user_id, contents, is_from_me, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    message_data,
                )

                inserted_count = cursor.rowcount
                conn.commit()

                logger.info(
                    f"Inserted {inserted_count} messages into messages database"
                )
                return inserted_count

        except sqlite3.Error as e:
            logger.error(f"Error inserting messages batch: {e}")
            return 0

    def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a message by its ID

        Args:
            message_id: Numeric message ID to search for

        Returns:
            Message dictionary if found, None otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT message_id, user_id, contents, is_from_me, created_at
                    FROM messages WHERE message_id = ?
                """,
                    (message_id,),
                )

                row = cursor.fetchone()
                if row:
                    message_id, user_id, contents, is_from_me, created_at = row
                    return {
                        "message_id": message_id,
                        "user_id": user_id,
                        "contents": contents,
                        "is_from_me": bool(is_from_me),
                        "created_at": created_at,
                    }

                return None

        except sqlite3.Error as e:
            logger.error(f"Error getting message {message_id}: {e}")
            return None

    def get_messages_by_user(
        self, user_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a specific user

        Args:
            user_id: User ID to get messages for
            limit: Optional limit on number of messages to return

        Returns:
            List of message dictionaries
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT message_id, user_id, contents, is_from_me, created_at
                    FROM messages WHERE user_id = ?
                    ORDER BY created_at DESC
                """
                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query, (user_id,))

                messages = []
                for row in cursor.fetchall():
                    message_id, user_id, contents, is_from_me, created_at = row
                    messages.append(
                        {
                            "message_id": message_id,
                            "user_id": user_id,
                            "contents": contents,
                            "is_from_me": bool(is_from_me),
                            "created_at": created_at,
                        }
                    )

                return messages

        except sqlite3.Error as e:
            logger.error(f"Error getting messages for user {user_id}: {e}")
            return []

    def get_all_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all messages from the database

        Args:
            limit: Optional limit on number of messages to return

        Returns:
            List of message dictionaries
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT message_id, user_id, contents, is_from_me, created_at
                    FROM messages
                    ORDER BY created_at DESC
                """
                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query)

                messages = []
                for row in cursor.fetchall():
                    message_id, user_id, contents, is_from_me, created_at = row
                    messages.append(
                        {
                            "message_id": message_id,
                            "user_id": user_id,
                            "contents": contents,
                            "is_from_me": bool(is_from_me),
                            "created_at": created_at,
                        }
                    )

                return messages

        except sqlite3.Error as e:
            logger.error(f"Error getting all messages: {e}")
            return []

    def clear_messages_table(self) -> bool:
        """
        Clear all messages from the messages table

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages")
                conn.commit()

                logger.info("Cleared all messages from messages table")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error clearing messages table: {e}")
            return False

    def insert_chat_message(
        self, chat_id: int, message_id: int, message_date: str
    ) -> bool:
        """
        Insert a chat-message relationship into the chat_messages table

        Args:
            chat_id: Integer chat ID
            message_id: Integer message ID
            message_date: Timestamp when the message was in the chat (ISO format)

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO chat_messages (chat_id, message_id, message_date)
                    VALUES (?, ?, ?)
                """,
                    (chat_id, message_id, message_date),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Error inserting chat_message ({chat_id}, {message_id}): {e}")
            return False

    def insert_chat_messages_batch(self, chat_messages: List[Dict[str, Any]]) -> int:
        """
        Insert multiple chat-message relationships in a batch operation

        Args:
            chat_messages: List of dictionaries with keys:
                          chat_id (int), message_id (int), message_date

        Returns:
            Number of chat-message relationships successfully inserted
        """
        if not chat_messages:
            return 0

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Prepare data for batch insert
                chat_message_data = [
                    (
                        cm["chat_id"],
                        cm["message_id"],
                        cm["message_date"],
                    )
                    for cm in chat_messages
                ]

                cursor.executemany(
                    """
                    INSERT INTO chat_messages (chat_id, message_id, message_date)
                    VALUES (?, ?, ?)
                """,
                    chat_message_data,
                )

                inserted_count = cursor.rowcount
                conn.commit()

                logger.info(
                    f"Inserted {inserted_count} chat-message relationships into messages database"
                )
                return inserted_count

        except sqlite3.Error as e:
            logger.error(f"Error inserting chat_messages batch: {e}")
            return 0

    def get_messages_in_chat(
        self, chat_id: int, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all messages in a specific chat

        Args:
            chat_id: Integer chat ID to get messages for
            limit: Optional limit on number of messages to return

        Returns:
            List of message dictionaries with chat context
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT m.message_id, m.user_id, m.contents, m.is_from_me, 
                           m.created_at, cm.message_date
                    FROM messages m
                    JOIN chat_messages cm ON m.message_id = cm.message_id
                    WHERE cm.chat_id = ?
                    ORDER BY cm.message_date DESC
                """
                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query, (chat_id,))

                messages = []
                for row in cursor.fetchall():
                    (
                        message_id,
                        user_id,
                        contents,
                        is_from_me,
                        created_at,
                        message_date,
                    ) = row
                    messages.append(
                        {
                            "message_id": message_id,
                            "user_id": user_id,
                            "contents": contents,
                            "is_from_me": bool(is_from_me),
                            "created_at": created_at,
                            "message_date": message_date,
                            "chat_id": chat_id,
                        }
                    )

                return messages

        except sqlite3.Error as e:
            logger.error(f"Error getting messages for chat {chat_id}: {e}")
            return []

    def get_chats_for_message(self, message_id: int) -> List[Dict[str, Any]]:
        """
        Get all chats that contain a specific message

        Args:
            message_id: Integer message ID to search for

        Returns:
            List of chat dictionaries
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT c.chat_id, c.display_name, cm.message_date
                    FROM chats c
                    JOIN chat_messages cm ON c.chat_id = cm.chat_id
                    WHERE cm.message_id = ?
                    ORDER BY cm.message_date DESC
                """,
                    (message_id,),
                )

                chats = []
                for row in cursor.fetchall():
                    chat_id, display_name, message_date = row
                    chats.append(
                        {
                            "chat_id": chat_id,
                            "display_name": display_name,
                            "message_date": message_date,
                        }
                    )

                return chats

        except sqlite3.Error as e:
            logger.error(f"Error getting chats for message {message_id}: {e}")
            return []

    def clear_chat_messages_table(self) -> bool:
        """
        Clear all chat-message relationships

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chat_messages")
                conn.commit()

                logger.info("Cleared all chat-message relationships")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error clearing chat_messages table: {e}")
            return False

    def create_polling_state_table(self) -> bool:
        """
        Create the polling_state table to track sync progress

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Create polling_state table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS polling_state (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        last_processed_rowid INTEGER NOT NULL DEFAULT 0,
                        last_sync_timestamp TEXT NOT NULL,
                        total_messages_processed INTEGER NOT NULL DEFAULT 0,
                        sync_status TEXT NOT NULL DEFAULT 'idle',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

                # Create index for performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_polling_state_last_sync ON polling_state(last_sync_timestamp)"
                )

                conn.commit()
                logger.info("Created polling_state table for sync tracking")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error creating polling_state table: {e}")
            return False

    def initialize_polling_state(self) -> bool:
        """
        Initialize the polling state if it doesn't exist

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Check if polling state already exists
                cursor.execute("SELECT COUNT(*) FROM polling_state WHERE id = 1")
                if cursor.fetchone()[0] > 0:
                    logger.info("Polling state already initialized")
                    return True

                # Initialize with timestamp
                from datetime import datetime

                current_time = datetime.now().isoformat()

                cursor.execute(
                    """
                    INSERT INTO polling_state 
                    (id, last_processed_rowid, last_sync_timestamp, total_messages_processed, 
                     sync_status, created_at, updated_at)
                    VALUES (1, 0, ?, 0, 'initialized', ?, ?)
                    """,
                    (current_time, current_time, current_time),
                )

                conn.commit()
                logger.info("Initialized polling state")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error initializing polling state: {e}")
            return False

    def get_polling_state(self) -> Optional[Dict[str, Any]]:
        """
        Get the current polling state

        Returns:
            Dictionary with polling state or None if error
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT last_processed_rowid, last_sync_timestamp, total_messages_processed,
                           sync_status, created_at, updated_at
                    FROM polling_state WHERE id = 1
                    """
                )

                row = cursor.fetchone()
                if row:
                    (
                        last_processed_rowid,
                        last_sync_timestamp,
                        total_messages_processed,
                        sync_status,
                        created_at,
                        updated_at,
                    ) = row
                    return {
                        "last_processed_rowid": last_processed_rowid,
                        "last_sync_timestamp": last_sync_timestamp,
                        "total_messages_processed": total_messages_processed,
                        "sync_status": sync_status,
                        "created_at": created_at,
                        "updated_at": updated_at,
                    }

                return None

        except sqlite3.Error as e:
            logger.error(f"Error getting polling state: {e}")
            return None

    def update_polling_state(
        self,
        last_processed_rowid: int,
        messages_processed_count: int = 0,
        sync_status: str = "idle",
    ) -> bool:
        """
        Update the polling state with new sync information

        Args:
            last_processed_rowid: Latest ROWID that was processed
            messages_processed_count: Number of new messages processed in this sync
            sync_status: Current sync status ('idle', 'polling', 'syncing', 'error')

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                from datetime import datetime

                current_time = datetime.now().isoformat()

                cursor.execute(
                    """
                    UPDATE polling_state SET
                        last_processed_rowid = ?,
                        last_sync_timestamp = ?,
                        total_messages_processed = total_messages_processed + ?,
                        sync_status = ?,
                        updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        last_processed_rowid,
                        current_time,
                        messages_processed_count,
                        sync_status,
                        current_time,
                    ),
                )

                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(
                        f"Updated polling state: ROWID={last_processed_rowid}, processed={messages_processed_count}, status={sync_status}"
                    )
                    return True
                else:
                    logger.error("No polling state record found to update")
                    return False

        except sqlite3.Error as e:
            logger.error(f"Error updating polling state: {e}")
            return False

    def set_sync_status(self, status: str) -> bool:
        """
        Update only the sync status

        Args:
            status: New sync status ('idle', 'polling', 'syncing', 'error')

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                from datetime import datetime

                current_time = datetime.now().isoformat()

                cursor.execute(
                    """
                    UPDATE polling_state SET
                        sync_status = ?,
                        updated_at = ?
                    WHERE id = 1
                    """,
                    (status, current_time),
                )

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            logger.error(f"Error setting sync status: {e}")
            return False
        
