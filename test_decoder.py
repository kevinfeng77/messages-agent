#!/usr/bin/env python3
"""Test script for message decoder"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from message_decoder import MessageDecoder, extract_message_text
from logger_config import setup_logging

def test_decoder():
    """Test the message decoder with real data"""
    setup_logging()
    
    # Connect to database
    db_path = Path("data/chat_copy.db")
    if not db_path.exists():
        print("Database not found. Please run database manager first.")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get some test messages
    cursor.execute("""
        SELECT ROWID, text, attributedBody 
        FROM message 
        WHERE text IS NULL AND attributedBody IS NOT NULL 
        LIMIT 20
    """)
    
    test_messages = cursor.fetchall()
    print(f"Testing with {len(test_messages)} messages...")
    
    decoder = MessageDecoder()
    successful_decodes = 0
    
    for rowid, text, attributed_body in test_messages:
        print(f"\n--- Testing message {rowid} ---")
        print(f"Text column: {text}")
        print(f"AttributedBody length: {len(attributed_body) if attributed_body else 0}")
        
        # Test extraction
        extracted_text = extract_message_text(text, attributed_body)
        
        if extracted_text:
            print(f"✅ Extracted: '{extracted_text}'")
            successful_decodes += 1
        else:
            print("❌ Failed to extract text")
    
    # Print statistics
    stats = decoder.get_decode_stats()
    print(f"\n=== RESULTS ===")
    print(f"Successful decodes: {successful_decodes}/{len(test_messages)}")
    print(f"Decoder stats: {stats}")
    
    conn.close()

if __name__ == "__main__":
    test_decoder()