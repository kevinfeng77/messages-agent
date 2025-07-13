#!/usr/bin/env python3
"""Debug script to examine attributedBody binary data"""

import sqlite3
import sys
from pathlib import Path


def analyze_binary_data():
    """Analyze the structure of attributedBody data"""

    # Connect to database
    db_path = Path("data/chat_copy.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get a message where we know the text
    cursor.execute(
        """
        SELECT text, attributedBody 
        FROM message 
        WHERE text IS NOT NULL AND attributedBody IS NOT NULL 
        AND length(text) > 5 AND length(text) < 50
        LIMIT 3
    """
    )

    messages = cursor.fetchall()

    for i, (text, attributed_body) in enumerate(messages):
        print(f"\n=== Message {i+1} ===")
        print(f"Known text: '{text}'")
        print(f"Text length: {len(text)}")
        print(f"AttributedBody length: {len(attributed_body)}")

        # Find where NSString appears
        nsstring_pos = attributed_body.find(b"NSString")
        print(f"NSString position: {nsstring_pos}")

        # Look for the text bytes in the binary data
        text_bytes = text.encode("utf-8")
        text_pos = attributed_body.find(text_bytes)
        print(f"Text bytes position: {text_pos}")

        if text_pos > 0:
            # Show what comes before the text
            context_start = max(0, text_pos - 20)
            context_end = min(len(attributed_body), text_pos + len(text_bytes) + 10)
            context = attributed_body[context_start:context_end]

            print(f"Context around text:")
            print(f"  Hex: {context.hex()}")
            print(f"  Bytes: {context}")
            print(f"  Decoded: {context.decode('utf-8', errors='replace')}")

            # Check the byte right before the text (should be length)
            if text_pos > 0:
                length_byte = attributed_body[text_pos - 1]
                print(
                    f"Byte before text: {length_byte} (decimal), {hex(length_byte)} (hex)"
                )
                print(f"Text length: {len(text)} - Match: {length_byte == len(text)}")

    conn.close()


if __name__ == "__main__":
    analyze_binary_data()
