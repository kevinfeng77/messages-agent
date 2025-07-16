#!/usr/bin/env python3
"""Test script for conversation detection prompt generation.

This script extracts 200 messages from a chat and tests the prompt generation.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.messages_db import MessagesDatabase
from src.conversations.detector import ConversationDetector
from src.conversations.models import ConversationMessage
from src.utils.logger_config import setup_logging


def extract_test_messages(db_path: str, limit: int = 200) -> tuple[int, list[ConversationMessage]]:
    """Extract test messages from the database.
    
    Args:
        db_path: Path to the messages database
        limit: Number of messages to extract
        
    Returns:
        Tuple of (chat_id, list of ConversationMessage objects)
    """
    db = MessagesDatabase(db_path)
    
    # Get a chat with sufficient messages
    query = """
        SELECT chat_id, COUNT(*) as msg_count
        FROM messages
        GROUP BY chat_id
        HAVING msg_count >= ?
        ORDER BY msg_count DESC
        LIMIT 1
    """
    
    result = db.execute_query(query, (limit,))
    if not result:
        raise ValueError(f"No chat found with at least {limit} messages")
    
    chat_id = result[0]["chat_id"]
    print(f"Using chat_id: {chat_id} with {result[0]['msg_count']} messages")
    
    # Get messages from this chat
    messages_query = """
        SELECT 
            m.message_id,
            m.user_id,
            m.contents,
            m.is_from_me,
            m.created_at
        FROM messages m
        WHERE m.chat_id = ?
        ORDER BY m.created_at DESC
        LIMIT ?
    """
    
    results = db.execute_query(messages_query, (chat_id, limit))
    
    # Convert to ConversationMessage objects
    messages = []
    for row in results:
        # Parse the timestamp
        created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        
        msg = ConversationMessage(
            message_id=row["message_id"],
            user_id=row["user_id"],
            contents=row["contents"],
            is_from_me=bool(row["is_from_me"]),
            created_at=created_at
        )
        messages.append(msg)
    
    # Sort by created_at (oldest first)
    messages.sort(key=lambda m: m.created_at)
    
    return chat_id, messages


def test_prompt_generation():
    """Test the conversation detection prompt generation."""
    setup_logging()
    
    # Path to the messages database
    db_path = "data/messages.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Please run 'just setup' to create the database")
        return
    
    try:
        # Extract test messages
        print("Extracting 200 test messages from database...")
        chat_id, messages = extract_test_messages(db_path, limit=200)
        print(f"Extracted {len(messages)} messages")
        
        # Create detector
        detector = ConversationDetector()
        
        # Generate the prompt
        print("\nGenerating conversation detection prompt...")
        prompt = detector._create_detection_prompt(messages)
        
        # Display prompt info
        print(f"\nPrompt length: {len(prompt)} characters")
        print(f"Estimated tokens: ~{len(prompt) // 4}")
        
        # Save prompt to file for inspection
        output_path = "data/test_conversation_prompt.txt"
        with open(output_path, "w") as f:
            f.write(prompt)
        print(f"\nFull prompt saved to: {output_path}")
        
        # Show a sample of the prompt
        print("\n" + "="*80)
        print("PROMPT PREVIEW (first 1000 characters):")
        print("="*80)
        print(prompt[:1000] + "...")
        
        # Test chunking
        print("\n" + "="*80)
        print("CHUNKING TEST:")
        print("="*80)
        chunks = detector._chunk_messages(messages)
        print(f"Messages split into {len(chunks)} chunks:")
        for i, (start_idx, chunk) in enumerate(chunks):
            print(f"  Chunk {i+1}: Start index {start_idx}, {len(chunk)} messages")
        
        # Test time-based fallback
        print("\n" + "="*80)
        print("TIME-BASED FALLBACK TEST:")
        print("="*80)
        boundaries = detector._detect_boundaries_time_based(messages)
        print(f"Found {len(boundaries)} boundaries using 48-hour gaps:")
        for boundary in boundaries:
            print(f"  After message {boundary.after_message_index}: {boundary.reason} (confidence: {boundary.confidence})")
        
        # Create conversations from time-based boundaries
        conversations = detector._create_conversations_from_boundaries(chat_id, messages, boundaries)
        print(f"\nCreated {len(conversations)} conversations from time-based detection:")
        for i, conv in enumerate(conversations):
            print(f"  Conversation {i+1}: {conv.message_count} messages, {conv.duration_minutes():.1f} minutes")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_prompt_generation()