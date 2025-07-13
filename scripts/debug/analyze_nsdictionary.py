#!/usr/bin/env python3
"""Debug script to analyze NSDictionary parsing failures in message decoder"""

import sys
import sqlite3
import plistlib
from pathlib import Path

# Add src to path for imports
sys.path.append('./src')
from messaging.decoder import MessageDecoder


def analyze_nsdictionary_binary(attributed_body: bytes, rowid: int) -> None:
    """Analyze the binary structure of a failing NSDictionary case"""
    print(f"\n=== ANALYZING ROWID {rowid} ===")
    print(f"Total length: {len(attributed_body)} bytes")
    
    # Show hex dump of first 200 bytes
    print("\nHex dump (first 200 bytes):")
    for i in range(0, min(200, len(attributed_body)), 16):
        hex_part = ' '.join(f'{b:02x}' for b in attributed_body[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in attributed_body[i:i+16])
        print(f"{i:04x}: {hex_part:<48} {ascii_part}")
    
    # Check if it starts with NSKeyedArchiver magic
    if attributed_body.startswith(b"\x04\x0bstreamtyped"):
        print("\n✓ NSKeyedArchiver format detected")
    else:
        print(f"\n✗ Does NOT start with NSKeyedArchiver magic")
        print(f"Actually starts with: {attributed_body[:20]}")
    
    # Look for key strings
    key_strings = [b"NSString", b"NSDictionary", b"NSAttributedString", b"NSMutableString"]
    print("\nKey string locations:")
    for key in key_strings:
        idx = attributed_body.find(key)
        if idx != -1:
            print(f"  {key.decode()}: found at offset {idx}")
            
            # Show context around the key
            start = max(0, idx - 10)
            end = min(len(attributed_body), idx + len(key) + 20)
            context = attributed_body[start:end]
            print(f"    Context: {context}")
        else:
            print(f"  {key.decode()}: not found")
    
    # Try to parse as binary plist
    print("\nBinary plist analysis:")
    if attributed_body.startswith(b"bplist"):
        try:
            plist_data = plistlib.loads(attributed_body)
            print(f"  ✓ Valid binary plist")
            print(f"  Root type: {type(plist_data)}")
            print(f"  Root content: {plist_data}")
        except Exception as e:
            print(f"  ✗ Binary plist parse failed: {e}")
    else:
        print("  Not a binary plist")
    
    # Try current decoder
    print("\nCurrent decoder result:")
    decoder = MessageDecoder()
    result = decoder.decode_attributed_body(attributed_body)
    print(f"  Result: {repr(result)}")


def find_target_message() -> None:
    """Search for a message that should decode to 'Me always the luckiest ever'"""
    print("Searching for target message in original database...")
    
    db_path = Path('./data/copy/chat_copy.db')
    if not db_path.exists():
        print("Original database not found")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Look for text that might contain our target in various forms
    search_terms = ["always", "luckiest", "ever", "lucky"]
    
    for term in search_terms:
        cursor.execute(f"SELECT ROWID, text, attributedBody FROM message WHERE text LIKE '%{term}%'")
        results = cursor.fetchall()
        
        if results:
            print(f"\nFound {len(results)} messages with '{term}' in text column:")
            for rowid, text, attributed_body in results:
                print(f"  ROWID {rowid}: {repr(text)}")
                if attributed_body:
                    decoder = MessageDecoder()
                    decoded = decoder.decode_attributed_body(attributed_body)
                    print(f"    Decoded: {repr(decoded)}")
    
    conn.close()


def main():
    """Main analysis function"""
    print("NSDictionary Parsing Analysis")
    print("=" * 50)
    
    # First, try to find the target message
    find_target_message()
    
    # Then analyze some failing cases
    db_path = Path('./data/copy/chat_copy.db')
    if not db_path.exists():
        print("Original database not found")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get some NSDictionary cases to analyze
    cursor.execute("""
        SELECT ROWID, text, attributedBody 
        FROM message 
        WHERE attributedBody IS NOT NULL 
        ORDER BY ROWID 
        LIMIT 5
    """)
    
    cases = cursor.fetchall()
    decoder = MessageDecoder()
    
    print(f"\nAnalyzing {len(cases)} sample cases:")
    
    for rowid, text, attributed_body in cases:
        if attributed_body:
            decoded = decoder.decode_attributed_body(attributed_body)
            if decoded == "NSDictionary":
                print(f"\n{'='*60}")
                analyze_nsdictionary_binary(attributed_body, rowid)
                break  # Analyze just one for now
    
    conn.close()


if __name__ == "__main__":
    main()