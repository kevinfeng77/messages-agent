#!/usr/bin/env python3
"""Test script for enhanced database manager with text extraction"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database_manager import DatabaseManager
from logger_config import setup_logging

def test_enhanced_database_manager():
    """Test the enhanced database manager with text extraction"""
    setup_logging()
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Create safe copy if it doesn't exist
    if not db_manager.copy_db_path.exists():
        print("Creating database copy...")
        db_path = db_manager.create_safe_copy()
        if not db_path:
            print("Failed to create database copy")
            return
    
    # Get text extraction statistics
    print("\n=== TEXT EXTRACTION STATISTICS ===")
    stats = db_manager.get_text_extraction_stats()
    
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Test message extraction with sample
    print("\n=== TESTING MESSAGE EXTRACTION ===")
    print("Extracting 10 recent messages...")
    
    messages = db_manager.extract_messages_with_text(limit=10)
    
    for i, message in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"ROWID: {message['rowid']}")
        print(f"Original text: {message['text']}")
        print(f"Extracted text: {message['extracted_text']}")
        print(f"Text source: {message['text_source']}")
        print(f"Is from me: {message['is_from_me']}")
        print(f"Service: {message['service']}")
    
    # Show improvement statistics
    text_sources = {}
    for message in messages:
        source = message['text_source']
        text_sources[source] = text_sources.get(source, 0) + 1
    
    print(f"\n=== TEXT SOURCE BREAKDOWN (Sample of {len(messages)}) ===")
    for source, count in text_sources.items():
        percentage = (count / len(messages)) * 100
        print(f"{source}: {count} ({percentage:.1f}%)")

if __name__ == "__main__":
    test_enhanced_database_manager()