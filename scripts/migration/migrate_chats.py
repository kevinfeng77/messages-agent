#!/usr/bin/env python3
"""Chat Migration Script - Populate chats table from existing chat and chat_handle_join tables"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database.messages_db import MessagesDatabase
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class ChatMigrator:
    """Handles migration of chat data from macOS Messages database to our chats table"""

    def __init__(
        self,
        source_db_path: str = "./data/chat_copy.db",
        target_db_path: str = "./data/messages.db",
    ):
        self.source_db_path = Path(source_db_path)
        self.target_db_path = Path(target_db_path)
        self.messages_db = MessagesDatabase(str(target_db_path))

    def get_chats_from_source(self) -> List[Dict]:
        """
        Extract chat data from the source Messages database

        Returns:
            List of chat dictionaries with chat_id, display_name, and handle_ids
        """
        if not self.source_db_path.exists():
            logger.error(f"Source database not found at {self.source_db_path}")
            return []

        try:
            with sqlite3.connect(str(self.source_db_path)) as conn:
                cursor = conn.cursor()

                # Get all chats with their handle associations
                query = """
                    SELECT 
                        c.ROWID as chat_id,
                        c.display_name,
                        c.chat_identifier,
                        c.service_name,
                        GROUP_CONCAT(chj.handle_id) as handle_ids
                    FROM chat c
                    LEFT JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
                    GROUP BY c.ROWID, c.display_name, c.chat_identifier, c.service_name
                    ORDER BY c.ROWID
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                chats = []
                for row in rows:
                    (
                        chat_id,
                        display_name,
                        chat_identifier,
                        service_name,
                        handle_ids_str,
                    ) = row

                    # Parse handle_ids
                    handle_ids = []
                    if handle_ids_str:
                        handle_ids = [
                            int(h) for h in handle_ids_str.split(",") if h.strip()
                        ]

                    # Use chat_identifier as display_name if display_name is None
                    if not display_name:
                        display_name = chat_identifier or f"Chat {chat_id}"

                    chats.append(
                        {
                            "chat_id": str(chat_id),
                            "display_name": display_name,
                            "chat_identifier": chat_identifier,
                            "service_name": service_name,
                            "handle_ids": handle_ids,
                        }
                    )

                logger.info(f"Extracted {len(chats)} chats from source database")
                return chats

        except sqlite3.Error as e:
            logger.error(f"Error reading from source database: {e}")
            return []

    def get_user_id_mapping(self) -> Dict[int, str]:
        """
        Get mapping of handle_id to user_id from the users table

        Returns:
            Dictionary mapping handle_id -> user_id
        """
        try:
            users = self.messages_db.get_all_users()
            mapping = {}

            for user in users:
                if user.handle_id:
                    mapping[user.handle_id] = user.user_id

            logger.info(f"Found {len(mapping)} handle_id to user_id mappings")
            return mapping

        except Exception as e:
            logger.error(f"Error getting user ID mapping: {e}")
            return {}

    def convert_handle_ids_to_user_ids(
        self, chats: List[Dict], handle_mapping: Dict[int, str]
    ) -> List[Dict]:
        """
        Convert handle_ids to user_ids for each chat

        Args:
            chats: List of chat dictionaries with handle_ids
            handle_mapping: Dictionary mapping handle_id -> user_id

        Returns:
            List of chat dictionaries with user_ids
        """
        converted_chats = []

        for chat in chats:
            user_ids = []
            handle_ids = chat.get("handle_ids", [])

            for handle_id in handle_ids:
                if handle_id in handle_mapping:
                    user_ids.append(handle_mapping[handle_id])
                else:
                    logger.warning(
                        f"No user found for handle_id {handle_id} in chat {chat['chat_id']}"
                    )

            converted_chat = {
                "chat_id": chat["chat_id"],
                "display_name": chat["display_name"],
                "user_ids": user_ids,
            }

            converted_chats.append(converted_chat)

        return converted_chats

    def migrate_chats(self) -> bool:
        """
        Perform the complete chat migration

        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting chat migration...")

        # Step 1: Extract chats from source database
        source_chats = self.get_chats_from_source()
        if not source_chats:
            logger.error("No chats found in source database")
            return False

        # Step 2: Get handle_id to user_id mapping
        handle_mapping = self.get_user_id_mapping()
        if not handle_mapping:
            logger.warning("No handle_id mappings found - proceeding without user_ids")

        # Step 3: Convert handle_ids to user_ids
        target_chats = self.convert_handle_ids_to_user_ids(source_chats, handle_mapping)

        # Step 4: Clear existing chats and insert new ones
        logger.info("Clearing existing chats table...")
        if not self.messages_db.clear_chats_table():
            logger.error("Failed to clear chats table")
            return False

        # Step 5: Insert migrated chats
        logger.info(f"Inserting {len(target_chats)} chats...")
        inserted_count = self.messages_db.insert_chats_batch(target_chats)

        if inserted_count == len(target_chats):
            logger.info(f"Successfully migrated {inserted_count} chats")
            return True
        else:
            logger.error(
                f"Migration incomplete: {inserted_count}/{len(target_chats)} chats inserted"
            )
            return False

    def get_migration_stats(self) -> Dict:
        """
        Get statistics about the migration

        Returns:
            Dictionary with migration statistics
        """
        try:
            # Get source stats
            source_stats = {"total_chats": 0, "chats_with_handles": 0}

            if self.source_db_path.exists():
                with sqlite3.connect(str(self.source_db_path)) as conn:
                    cursor = conn.cursor()

                    cursor.execute("SELECT COUNT(*) FROM chat")
                    source_stats["total_chats"] = cursor.fetchone()[0]

                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT c.ROWID) 
                        FROM chat c 
                        JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
                    """
                    )
                    source_stats["chats_with_handles"] = cursor.fetchone()[0]

            # Get target stats
            target_chats = self.messages_db.get_all_chats()
            target_stats = {
                "migrated_chats": len(target_chats),
                "chats_with_users": len([c for c in target_chats if c["user_ids"]]),
                "chats_without_users": len(
                    [c for c in target_chats if not c["user_ids"]]
                ),
            }

            return {
                "source": source_stats,
                "target": target_stats,
                "migration_success_rate": (
                    round(
                        (target_stats["migrated_chats"] / source_stats["total_chats"])
                        * 100,
                        2,
                    )
                    if source_stats["total_chats"] > 0
                    else 0
                ),
            }

        except Exception as e:
            logger.error(f"Error getting migration stats: {e}")
            return {"error": str(e)}


def main():
    """Main function to run chat migration"""
    logger.info("=== Chat Migration Script ===")

    # Initialize migrator
    migrator = ChatMigrator()

    # Ensure target database exists
    if not migrator.messages_db.create_database():
        logger.error("Failed to create target database")
        sys.exit(1)

    # Run migration
    success = migrator.migrate_chats()

    # Get and display stats
    stats = migrator.get_migration_stats()
    logger.info(f"Migration stats: {stats}")

    if success:
        logger.info("Chat migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("Chat migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
