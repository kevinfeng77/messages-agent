"""Simple test to verify conversation tables are created"""

import pytest
import sqlite3
from src.database.messages_db import MessagesDatabase


def test_conversation_tables_exist(tmp_path):
    """Test that all conversation tables and indexes are created"""
    db_path = tmp_path / "test.db"
    db = MessagesDatabase(str(db_path))
    
    # Create database
    assert db.create_database() is True
    
    # Verify tables exist
    assert db.table_exists("conversations")
    assert db.table_exists("conversation_messages")
    assert db.table_exists("conversation_embeddings")
    
    # Verify basic schema
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Check conversations table columns
        cursor.execute("PRAGMA table_info(conversations)")
        conv_columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            "conversation_id", "chat_id", "users", "created_at",
            "completed_at", "count", "summary", "status", "initiated_by"
        }
        assert expected_columns.issubset(conv_columns)
        
        # Check indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_conversation%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        expected_indexes = {
            "idx_conversations_chat_id",
            "idx_conversations_status",
            "idx_conversations_created_at",
            "idx_conversation_messages_sequence"
        }
        assert expected_indexes.issubset(indexes)