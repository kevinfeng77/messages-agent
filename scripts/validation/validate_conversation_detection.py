#!/usr/bin/env python3
"""Validation script for conversation detection with LLM.

This script tests the conversation detection prompt with real messages
and validates the LLM's ability to identify conversation boundaries.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.messages_db import MessagesDatabase
from src.conversations.detector import ConversationDetector
from src.conversations.models import ConversationMessage
from src.message_maker.llm_client import LLMClient
from src.utils.logger_config import setup_logging


class ConversationDetectionValidator:
    """Validates conversation detection using LLM."""
    
    def __init__(self, db_path: str):
        """Initialize the validator.
        
        Args:
            db_path: Path to the messages database
        """
        self.db = MessagesDatabase(db_path)
        self.detector = ConversationDetector()
        self.llm_client = LLMClient()
        setup_logging()
    
    def extract_test_messages(self, limit: int = 200) -> tuple[int, list[ConversationMessage]]:
        """Extract test messages from the database.
        
        Args:
            limit: Number of messages to extract
            
        Returns:
            Tuple of (chat_id, list of ConversationMessage objects)
        """
        # Get a chat with sufficient messages
        query = """
            SELECT chat_id, COUNT(*) as msg_count
            FROM messages
            GROUP BY chat_id
            HAVING msg_count >= ?
            ORDER BY msg_count DESC
            LIMIT 1
        """
        
        result = self.db.execute_query(query, (limit,))
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
        
        results = self.db.execute_query(messages_query, (chat_id, limit))
        
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
    
    def test_llm_detection(self, messages: list[ConversationMessage]) -> dict:
        """Test LLM-based conversation detection.
        
        Args:
            messages: List of messages to analyze
            
        Returns:
            Dictionary with test results
        """
        # Generate prompt
        prompt = self.detector._create_detection_prompt(messages)
        
        print(f"\nSending prompt to LLM ({len(prompt)} characters)...")
        
        try:
            # Call LLM
            response = self.llm_client.generate_response(
                system_prompt="You are a helpful assistant that analyzes conversations.",
                user_prompt=prompt,
                max_tokens=1000
            )
            
            print(f"\nLLM Response:\n{response}")
            
            # Parse boundaries
            boundaries = self.detector._parse_llm_response(response)
            
            return {
                "success": True,
                "prompt_length": len(prompt),
                "response": response,
                "boundaries": boundaries,
                "boundary_count": len(boundaries)
            }
            
        except Exception as e:
            print(f"LLM Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "prompt_length": len(prompt)
            }
    
    def compare_detection_methods(self, chat_id: int, messages: list[ConversationMessage]) -> dict:
        """Compare LLM detection with time-based fallback.
        
        Args:
            chat_id: The chat ID
            messages: List of messages to analyze
            
        Returns:
            Comparison results
        """
        # Time-based detection
        time_boundaries = self.detector._detect_boundaries_time_based(messages)
        time_conversations = self.detector._create_conversations_from_boundaries(
            chat_id, messages, time_boundaries
        )
        
        # LLM detection
        llm_result = self.test_llm_detection(messages)
        
        if llm_result["success"]:
            llm_boundaries = llm_result["boundaries"]
            llm_conversations = self.detector._create_conversations_from_boundaries(
                chat_id, messages, llm_boundaries
            )
        else:
            llm_boundaries = []
            llm_conversations = []
        
        return {
            "time_based": {
                "boundaries": len(time_boundaries),
                "conversations": len(time_conversations),
                "details": [
                    {
                        "after_index": b.after_message_index,
                        "reason": b.reason,
                        "confidence": b.confidence
                    }
                    for b in time_boundaries
                ]
            },
            "llm_based": {
                "success": llm_result["success"],
                "boundaries": len(llm_boundaries),
                "conversations": len(llm_conversations),
                "details": [
                    {
                        "after_index": b.after_message_index,
                        "reason": b.reason,
                        "confidence": b.confidence
                    }
                    for b in llm_boundaries
                ] if llm_result["success"] else [],
                "error": llm_result.get("error")
            }
        }
    
    def run_validation(self):
        """Run the full validation test."""
        print("=== Conversation Detection Validation ===\n")
        
        # Extract test messages
        print("Step 1: Extracting test messages...")
        chat_id, messages = self.extract_test_messages(limit=200)
        print(f"✓ Extracted {len(messages)} messages")
        
        # Show sample messages
        print("\nSample messages:")
        for i in [0, 50, 100, 150, 199]:
            if i < len(messages):
                msg = messages[i]
                print(f"  [{i}] {msg.created_at.strftime('%Y-%m-%d %H:%M')} - "
                      f"{'Me' if msg.is_from_me else 'Contact'}: "
                      f"{msg.contents[:50]}...")
        
        # Test prompt generation
        print("\nStep 2: Testing prompt generation...")
        prompt = self.detector._create_detection_prompt(messages)
        print(f"✓ Generated prompt: {len(prompt)} characters (~{len(prompt)//4} tokens)")
        
        # Save prompt for inspection
        prompt_path = "data/validation_prompt.txt"
        with open(prompt_path, "w") as f:
            f.write(prompt)
        print(f"✓ Prompt saved to: {prompt_path}")
        
        # Compare detection methods
        print("\nStep 3: Comparing detection methods...")
        comparison = self.compare_detection_methods(chat_id, messages)
        
        # Display results
        print("\n" + "="*60)
        print("RESULTS:")
        print("="*60)
        
        print("\nTime-based Detection (48-hour gaps):")
        print(f"  Boundaries found: {comparison['time_based']['boundaries']}")
        print(f"  Conversations created: {comparison['time_based']['conversations']}")
        for detail in comparison['time_based']['details']:
            print(f"    - After message {detail['after_index']}: {detail['reason']}")
        
        print("\nLLM-based Detection:")
        if comparison['llm_based']['success']:
            print(f"  Boundaries found: {comparison['llm_based']['boundaries']}")
            print(f"  Conversations created: {comparison['llm_based']['conversations']}")
            for detail in comparison['llm_based']['details']:
                print(f"    - After message {detail['after_index']}: {detail['reason']} "
                      f"(confidence: {detail['confidence']})")
        else:
            print(f"  Error: {comparison['llm_based']['error']}")
        
        # Save results
        results_path = "data/validation_results.json"
        with open(results_path, "w") as f:
            json.dump(comparison, f, indent=2)
        print(f"\n✓ Detailed results saved to: {results_path}")
        
        print("\n=== Validation Complete ===")


def main():
    """Run the validation script."""
    # Check database exists
    db_path = "data/messages.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Please run 'just setup' to create the database")
        return
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not found in environment")
        print("Please set it to test with the LLM")
        return
    
    # Run validation
    validator = ConversationDetectionValidator(db_path)
    validator.run_validation()


if __name__ == "__main__":
    main()