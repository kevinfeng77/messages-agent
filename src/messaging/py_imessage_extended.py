"""
Extended py-imessage functionality for reading messages.

This module extends the basic py-imessage library with additional
functions for reading messages, conversations, and message history.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

try:
    from py_imessage import db_conn
    IMESSAGE_DB_AVAILABLE = True
except ImportError:
    db_conn = None
    IMESSAGE_DB_AVAILABLE = False

logger = logging.getLogger(__name__)


class PyiMessageReader:
    """Extended reader for py-imessage database access."""
    
    def __init__(self):
        self._db_connected = False
    
    def _ensure_connected(self):
        """Ensure database connection is open."""
        if not IMESSAGE_DB_AVAILABLE:
            raise RuntimeError("py-imessage database module not available")
        
        if not self._db_connected:
            try:
                db_conn.open()
                self._db_connected = True
                logger.debug("Connected to Messages database")
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Messages database: {e}")
    
    def get_recent_messages(self, limit: int = 10, include_sent: bool = True, include_received: bool = True) -> List[Dict[str, Any]]:
        """
        Get recent messages.
        
        Args:
            limit: Maximum number of messages to return
            include_sent: Include messages sent by me
            include_received: Include messages received from others
            
        Returns:
            List of message dictionaries
        """
        self._ensure_connected()
        
        # Build WHERE clause based on message direction
        conditions = []
        if include_sent and include_received:
            # No filter needed - get all messages
            pass
        elif include_sent:
            conditions.append("is_from_me = 1")
        elif include_received:
            conditions.append("is_from_me = 0")
        else:
            return []  # No messages to return
        
        where_clause = ""
        if conditions:
            where_clause = f"WHERE {' OR '.join(conditions)}"
        
        query = f"""
        SELECT 
            m.guid, 
            h.id as handle, 
            m.text, 
            m.date, 
            m.date_read, 
            m.date_delivered,
            m.is_from_me,
            m.service
        FROM message m
        LEFT OUTER JOIN handle h ON m.handle_id = h.ROWID
        {where_clause}
        ORDER BY m.date DESC
        LIMIT {limit}
        """
        
        try:
            results = db_conn.db.execute(query).fetchall()
            
            messages = []
            for row in results:
                message = {
                    'guid': row[0],
                    'handle': row[1],
                    'text': row[2],
                    'date': db_conn.from_apple_time(row[3]) if row[3] else None,
                    'date_read': db_conn.from_apple_time(row[4]) if row[4] else None,
                    'date_delivered': db_conn.from_apple_time(row[5]) if row[5] else None,
                    'is_from_me': bool(row[6]),
                    'service': row[7]
                }
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []
    
    def get_conversation(self, handle: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation history with a specific contact.
        
        Args:
            handle: Phone number or email address
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        self._ensure_connected()
        
        query = """
        SELECT 
            m.guid, 
            h.id as handle, 
            m.text, 
            m.date, 
            m.date_read, 
            m.date_delivered,
            m.is_from_me,
            m.service
        FROM message m
        LEFT OUTER JOIN handle h ON m.handle_id = h.ROWID
        WHERE h.id = ?
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        try:
            results = db_conn.db.execute(query, (handle, limit)).fetchall()
            
            messages = []
            for row in results:
                message = {
                    'guid': row[0],
                    'handle': row[1],
                    'text': row[2],
                    'date': db_conn.from_apple_time(row[3]) if row[3] else None,
                    'date_read': db_conn.from_apple_time(row[4]) if row[4] else None,
                    'date_delivered': db_conn.from_apple_time(row[5]) if row[5] else None,
                    'is_from_me': bool(row[6]),
                    'service': row[7]
                }
                messages.append(message)
            
            # Return in chronological order (oldest first)
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Failed to get conversation with {handle}: {e}")
            return []
    
    def get_contacts(self) -> List[str]:
        """
        Get list of all contacts/handles.
        
        Returns:
            List of phone numbers and email addresses
        """
        self._ensure_connected()
        
        query = """
        SELECT DISTINCT h.id
        FROM handle h
        JOIN message m ON h.ROWID = m.handle_id
        ORDER BY h.id
        """
        
        try:
            results = db_conn.db.execute(query).fetchall()
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Failed to get contacts: {e}")
            return []
    
    def search_messages(self, search_text: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for messages containing specific text.
        
        Args:
            search_text: Text to search for
            limit: Maximum number of results
            
        Returns:
            List of matching message dictionaries
        """
        self._ensure_connected()
        
        query = """
        SELECT 
            m.guid, 
            h.id as handle, 
            m.text, 
            m.date, 
            m.date_read, 
            m.date_delivered,
            m.is_from_me,
            m.service
        FROM message m
        LEFT OUTER JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.text LIKE ?
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        try:
            search_pattern = f"%{search_text}%"
            results = db_conn.db.execute(query, (search_pattern, limit)).fetchall()
            
            messages = []
            for row in results:
                message = {
                    'guid': row[0],
                    'handle': row[1],
                    'text': row[2],
                    'date': db_conn.from_apple_time(row[3]) if row[3] else None,
                    'date_read': db_conn.from_apple_time(row[4]) if row[4] else None,
                    'date_delivered': db_conn.from_apple_time(row[5]) if row[5] else None,
                    'is_from_me': bool(row[6]),
                    'service': row[7]
                }
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to search messages: {e}")
            return []
    
    def close(self):
        """Close database connection."""
        if self._db_connected:
            try:
                db_conn.clean_up()
                self._db_connected = False
                logger.debug("Closed Messages database connection")
            except Exception as e:
                logger.warning(f"Error closing database: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience functions
def get_recent_messages(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent messages (convenience function)."""
    with PyiMessageReader() as reader:
        return reader.get_recent_messages(limit)


def get_conversation(handle: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get conversation with contact (convenience function)."""
    with PyiMessageReader() as reader:
        return reader.get_conversation(handle, limit)


def search_messages(search_text: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Search messages (convenience function)."""
    with PyiMessageReader() as reader:
        return reader.search_messages(search_text, limit)