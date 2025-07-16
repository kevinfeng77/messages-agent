#!/usr/bin/env python3
"""Validation script for conversation tables functionality"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.messages_db import MessagesDatabase
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


def validate_table_structure(db_path: str) -> dict:
    """Validate that all conversation tables exist with correct structure"""
    results = {"success": True, "errors": []}
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check conversations table
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='conversations'")
            conv_table = cursor.fetchone()
            if not conv_table:
                results["success"] = False
                results["errors"].append("conversations table not found")
            else:
                logger.info("✓ conversations table exists")
                
            # Check conversation_messages table
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='conversation_messages'")
            conv_msg_table = cursor.fetchone()
            if not conv_msg_table:
                results["success"] = False
                results["errors"].append("conversation_messages table not found")
            else:
                logger.info("✓ conversation_messages table exists")
                
            # Check conversation_embeddings table
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='conversation_embeddings'")
            conv_emb_table = cursor.fetchone()
            if not conv_emb_table:
                results["success"] = False
                results["errors"].append("conversation_embeddings table not found")
            else:
                logger.info("✓ conversation_embeddings table exists")
                
            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_conversation%'")
            indexes = [row[0] for row in cursor.fetchall()]
            expected_indexes = [
                "idx_conversations_chat_id",
                "idx_conversations_status", 
                "idx_conversations_created_at",
                "idx_conversation_messages_sequence",
                "idx_embeddings_conversation"
            ]
            
            for idx in expected_indexes:
                if idx in indexes:
                    logger.info(f"✓ {idx} index exists")
                else:
                    results["success"] = False
                    results["errors"].append(f"{idx} index not found")
                    
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Error checking table structure: {str(e)}")
        
    return results


def validate_crud_operations(messages_db: MessagesDatabase) -> dict:
    """Validate CRUD operations on conversation tables"""
    results = {"success": True, "errors": [], "operations": {}}
    
    try:
        # Test data
        test_chat_id = 999
        test_users = ["user1", "user2"]
        test_conversation_id = "test_conv_123"
        
        # Create a test chat first
        messages_db.insert_chat(
            chat_id=test_chat_id,
            display_name="Test Chat for Conversations",
            user_ids=test_users
        )
        
        # Test conversation creation
        created_at = datetime.now().isoformat()
        success = messages_db.insert_conversation(
            conversation_id=test_conversation_id,
            chat_id=test_chat_id,
            users=test_users,
            created_at=created_at,
            initiated_by=test_users[0],
            count=0,
            status="active"
        )
        
        if success:
            logger.info("✓ Conversation creation successful")
            results["operations"]["create"] = True
        else:
            results["success"] = False
            results["errors"].append("Failed to create conversation")
            results["operations"]["create"] = False
            
        # Test conversation retrieval
        conversation = messages_db.get_conversation_by_id(test_conversation_id)
        if conversation and conversation["conversation_id"] == test_conversation_id:
            logger.info("✓ Conversation retrieval successful")
            results["operations"]["read"] = True
        else:
            results["success"] = False
            results["errors"].append("Failed to retrieve conversation")
            results["operations"]["read"] = False
            
        # Test conversation update
        completed_at = datetime.now().isoformat()
        summary = "Test conversation completed"
        success = messages_db.update_conversation_status(
            conversation_id=test_conversation_id,
            status="completed",
            completed_at=completed_at,
            summary=summary
        )
        
        if success:
            logger.info("✓ Conversation update successful")
            results["operations"]["update"] = True
        else:
            results["success"] = False
            results["errors"].append("Failed to update conversation")
            results["operations"]["update"] = False
            
        # Test querying by chat_id
        conversations = messages_db.get_conversations_by_chat_id(test_chat_id)
        if conversations and len(conversations) > 0:
            logger.info("✓ Conversation query by chat_id successful")
            results["operations"]["query"] = True
        else:
            results["success"] = False
            results["errors"].append("Failed to query conversations by chat_id")
            results["operations"]["query"] = False
            
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Error during CRUD operations: {str(e)}")
        
    return results


def main():
    """Main validation function"""
    print("=== Conversation Tables Validation ===\n")
    
    # Check database exists
    db_path = "./data/messages.db"
    if not Path(db_path).exists():
        print("❌ Messages database not found at ./data/messages.db")
        print("   Please run: python scripts/setup_messages_database.py")
        return False
        
    messages_db = MessagesDatabase(db_path)
    
    # Validate table structure
    print("1. Validating table structure...")
    structure_results = validate_table_structure(db_path)
    
    if structure_results["success"]:
        print("✅ All tables and indexes exist")
    else:
        print("❌ Table structure validation failed:")
        for error in structure_results["errors"]:
            print(f"   - {error}")
            
    # Validate CRUD operations
    print("\n2. Validating CRUD operations...")
    crud_results = validate_crud_operations(messages_db)
    
    if crud_results["success"]:
        print("✅ All CRUD operations successful")
        for op, success in crud_results["operations"].items():
            print(f"   - {op}: {'✓' if success else '✗'}")
    else:
        print("❌ CRUD operations validation failed:")
        for error in crud_results["errors"]:
            print(f"   - {error}")
            
    # Summary
    print("\n=== Validation Summary ===")
    all_success = structure_results["success"] and crud_results["success"]
    
    if all_success:
        print("✅ All conversation table validations passed!")
    else:
        print("❌ Some validations failed. Please check the errors above.")
        
    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)