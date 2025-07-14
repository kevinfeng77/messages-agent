"""Real-time iMessage Polling Service - Monitors Messages database for new entries"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from src.database.manager import DatabaseManager
from src.database.messages_db import MessagesDatabase
from src.messaging.decoder import extract_message_text
from src.user.handle_matcher import HandleMatcher
from src.user.user import User
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class MessagePollingService:
    """Service for real-time polling of iMessage database and incremental sync"""

    def __init__(
        self, data_dir: str = "./data", poll_interval: int = 5, batch_size: int = 100
    ):
        """
        Initialize the polling service

        Args:
            data_dir: Directory for database files
            poll_interval: Seconds between polling cycles
            batch_size: Maximum messages to process per batch
        """
        self.data_dir = Path(data_dir)
        self.poll_interval = poll_interval
        self.batch_size = batch_size

        # Initialize components
        self.db_manager = DatabaseManager(data_dir)
        self.messages_db = MessagesDatabase(f"{data_dir}/messages.db")
        self.handle_matcher = HandleMatcher()

        # Runtime state
        self.is_running = False
        self.last_error = None
        self.on_new_messages = None  # Callback for new message notifications

    def initialize(self) -> bool:
        """
        Initialize the polling service and database structures

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create messages database and tables
            if not self.messages_db.create_database():
                logger.error("Failed to create messages database")
                return False

            # Initialize polling state
            if not self.messages_db.initialize_polling_state():
                logger.error("Failed to initialize polling state")
                return False

            logger.info("Polling service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing polling service: {e}")
            return False


    def get_new_messages_from_source(
        self, last_processed_rowid: int
    ) -> List[Dict[str, Any]]:
        """
        Get new messages from the source Messages database since last ROWID

        Args:
            last_processed_rowid: Last ROWID that was processed

        Returns:
            List of new message dictionaries
        """
        try:
            # Create a fresh copy of the Messages database
            copy_path = self.db_manager.create_safe_copy()
            if not copy_path:
                logger.error("Failed to create database copy")
                return []

            # Query for new messages
            with sqlite3.connect(str(copy_path)) as conn:
                cursor = conn.cursor()

                # Get messages with ROWID > last_processed_rowid
                cursor.execute(
                    """
                    SELECT 
                        ROWID,
                        guid,
                        text,
                        attributedBody,
                        handle_id,
                        date,
                        date_read,
                        is_from_me,
                        service
                    FROM message 
                    WHERE ROWID > ?
                    ORDER BY ROWID ASC
                    LIMIT ?
                    """,
                    (last_processed_rowid, self.batch_size),
                )

                raw_messages = cursor.fetchall()

            # Process messages with text extraction
            new_messages = []
            for row in raw_messages:
                (
                    rowid,
                    guid,
                    text,
                    attributed_body,
                    handle_id,
                    date,
                    date_read,
                    is_from_me,
                    service,
                ) = row

                # Extract the best available text
                extracted_text = extract_message_text(text, attributed_body)

                message = {
                    "rowid": rowid,
                    "guid": guid,
                    "text": text,
                    "extracted_text": extracted_text,
                    "handle_id": handle_id,
                    "date": date,
                    "date_read": date_read,
                    "is_from_me": bool(is_from_me),
                    "service": service,
                    "has_attributed_body": attributed_body is not None,
                }

                new_messages.append(message)

            logger.info(
                f"Found {len(new_messages)} new messages since ROWID {last_processed_rowid}"
            )
            return new_messages

        except sqlite3.Error as e:
            logger.error(f"Database error getting new messages: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting new messages: {e}")
            return []

    def resolve_user_from_handle(self, handle_id: int) -> Optional[User]:
        """
        Resolve a user from a handle_id, creating new user if needed

        Args:
            handle_id: Handle ID from Messages database

        Returns:
            User object or None if resolution fails
        """
        try:
            # First check if we already have this user
            existing_user = self.messages_db.get_user_by_handle_id(handle_id)
            if existing_user:
                return existing_user

            # Use handle matcher to resolve new user
            user = self.handle_matcher.resolve_user_from_handle_id(handle_id)
            if user:
                # Store the new user in our database
                if self.messages_db.insert_user(user):
                    logger.info(
                        f"Created new user for handle_id {handle_id}: {user.first_name} {user.last_name}"
                    )
                    return user
                else:
                    logger.error(f"Failed to store new user for handle_id {handle_id}")

            return None

        except Exception as e:
            logger.error(f"Error resolving user from handle_id {handle_id}: {e}")
            return None

    def convert_apple_timestamp(self, apple_timestamp: int) -> str:
        """
        Convert Apple's timestamp format to ISO format

        Args:
            apple_timestamp: Apple's timestamp (nanoseconds since 2001-01-01)

        Returns:
            ISO format timestamp string
        """
        try:
            # Apple timestamps are nanoseconds since 2001-01-01 00:00:00 UTC
            # Convert to seconds and add to reference date
            apple_epoch = datetime(2001, 1, 1)
            timestamp_seconds = apple_timestamp / 1_000_000_000
            message_time = apple_epoch.timestamp() + timestamp_seconds

            return datetime.fromtimestamp(message_time).isoformat()

        except Exception as e:
            logger.error(f"Error converting timestamp {apple_timestamp}: {e}")
            return datetime.now().isoformat()

    def sync_new_messages(self, new_messages: List[Dict[str, Any]]) -> int:
        """
        Sync new messages to normalized database

        Args:
            new_messages: List of new message dictionaries

        Returns:
            Number of messages successfully synced
        """
        if not new_messages:
            return 0

        synced_count = 0

        try:
            # Process each message
            normalized_messages = []

            for msg in new_messages:
                # Resolve user from handle_id
                user = self.resolve_user_from_handle(msg["handle_id"])
                if not user:
                    logger.warning(
                        f"Could not resolve user for handle_id {msg['handle_id']}, skipping message"
                    )
                    continue

                # Convert timestamp
                created_at = self.convert_apple_timestamp(msg["date"])

                # Use extracted text if available, otherwise use original text
                contents = msg["extracted_text"] or msg["text"] or ""

                if not contents.strip():
                    logger.debug(
                        f"Message ROWID {msg['rowid']} has no text content, skipping"
                    )
                    continue

                # Create normalized message
                normalized_message = {
                    "message_id": msg["rowid"],  # Use ROWID as message_id
                    "user_id": user.user_id,
                    "contents": contents,
                    "is_from_me": msg["is_from_me"],
                    "created_at": created_at,
                }

                normalized_messages.append(normalized_message)

            # Batch insert messages
            if normalized_messages:
                synced_count = self.messages_db.insert_messages_batch(
                    normalized_messages
                )
                logger.info(
                    f"Synced {synced_count} new messages to normalized database"
                )

            return synced_count

        except Exception as e:
            logger.error(f"Error syncing new messages: {e}")
            return synced_count

    def poll_once(self) -> Dict[str, Any]:
        """
        Perform a single polling cycle

        Returns:
            Dictionary with polling results
        """
        start_time = datetime.now()

        try:
            # Set status to polling
            self.messages_db.set_sync_status("polling")

            # Get current polling state
            state = self.messages_db.get_polling_state()
            if not state:
                logger.error("Could not get polling state")
                self.messages_db.set_sync_status("error")
                return {"success": False, "error": "No polling state"}

            last_processed_rowid = state["last_processed_rowid"]

            # Get new messages from source database
            new_messages = self.get_new_messages_from_source(last_processed_rowid)

            if not new_messages:
                # No new messages, update timestamp and return
                self.messages_db.set_sync_status("idle")
                return {
                    "success": True,
                    "new_messages": 0,
                    "synced_messages": 0,
                    "last_processed_rowid": last_processed_rowid,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                }

            # Set status to syncing
            self.messages_db.set_sync_status("syncing")

            # Sync new messages to normalized database
            synced_count = self.sync_new_messages(new_messages)

            # Update polling state with latest ROWID
            latest_rowid = max(msg["rowid"] for msg in new_messages)
            self.messages_db.update_polling_state(
                last_processed_rowid=latest_rowid,
                messages_processed_count=synced_count,
                sync_status="idle",
            )

            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Polling cycle complete: {len(new_messages)} new, {synced_count} synced in {duration:.2f}s"
            )
            
            # Trigger notification callback if new messages were found
            if new_messages and hasattr(self, 'on_new_messages') and self.on_new_messages:
                try:
                    self.on_new_messages(new_messages, synced_count)
                except Exception as e:
                    logger.error(f"Error in new message callback: {e}")

            return {
                "success": True,
                "new_messages": len(new_messages),
                "synced_messages": synced_count,
                "last_processed_rowid": latest_rowid,
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Error in polling cycle: {e}")
            self.messages_db.set_sync_status("error")
            self.last_error = str(e)

            return {
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }

    def start_polling(self) -> None:
        """
        Start continuous polling loop
        """
        if self.is_running:
            logger.warning("Polling service is already running")
            return

        logger.info(
            f"Starting message polling service (interval: {self.poll_interval}s)"
        )
        self.is_running = True

        try:
            while self.is_running:
                result = self.poll_once()

                if not result["success"]:
                    logger.error(
                        f"Polling cycle failed: {result.get('error', 'Unknown error')}"
                    )
                    # Continue polling even after errors

                # Wait for next cycle
                if self.is_running:
                    time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("Polling interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in polling loop: {e}")
        finally:
            self.is_running = False
            self.messages_db.set_sync_status("stopped")
            logger.info("Polling service stopped")

    def stop_polling(self) -> None:
        """
        Stop the polling loop
        """
        if self.is_running:
            logger.info("Stopping polling service...")
            self.is_running = False
        else:
            logger.info("Polling service is not running")

    def set_new_message_callback(self, callback):
        """
        Set callback function to be called when new messages are found
        
        Args:
            callback: Function that takes (new_messages, synced_count) as parameters
        """
        self.on_new_messages = callback
        logger.info("New message notification callback set")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the polling service

        Returns:
            Dictionary with service status
        """
        try:
            state = self.messages_db.get_polling_state()

            return {
                "is_running": self.is_running,
                "polling_state": state,
                "last_error": self.last_error,
                "poll_interval": self.poll_interval,
                "batch_size": self.batch_size,
            }

        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {"is_running": self.is_running, "error": str(e)}
