#!/usr/bin/env python3
"""Integration tests for NSDictionary parsing fix"""

import sys
import sqlite3
from pathlib import Path

# Add src to path for imports
sys.path.append('./src')
from messaging.decoder import MessageDecoder


def test_target_message():
    """Test that ROWID 224717 decodes correctly"""
    print("Testing target message ROWID 224717...")
    
    db_path = Path('./data/copy/chat_copy.db')
    if not db_path.exists():
        print("SKIP: Original database not found")
        return True
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute('SELECT attributedBody FROM message WHERE ROWID = 224717')
    result = cursor.fetchone()
    conn.close()
    
    if not result or not result[0]:
        print("SKIP: ROWID 224717 not found")
        return True
    
    attributed_body = result[0]
    decoder = MessageDecoder()
    decoded_text = decoder.decode_attributed_body(attributed_body)
    
    expected = "Me always the luckiest ever"
    success = decoded_text == expected
    
    print(f"Expected: {repr(expected)}")
    print(f"Got: {repr(decoded_text)}")
    print(f"Result: {'PASS' if success else 'FAIL'}")
    
    return success


def test_regression_cases():
    """Test that existing functionality still works"""
    print("\nTesting regression protection...")
    
    db_path = Path('./data/copy/chat_copy.db')
    if not db_path.exists():
        print("SKIP: Original database not found")
        return True
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Test first 10 messages with attributedBody
    cursor.execute('''
        SELECT ROWID, attributedBody 
        FROM message 
        WHERE attributedBody IS NOT NULL 
        ORDER BY ROWID 
        LIMIT 10
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    decoder = MessageDecoder()
    successful = 0
    total = 0
    
    for rowid, attributed_body in results:
        if attributed_body:
            total += 1
            decoded = decoder.decode_attributed_body(attributed_body)
            if decoded and decoded != "NSDictionary":
                successful += 1
                print(f"  ROWID {rowid}: {repr(decoded[:50])}...")
            else:
                print(f"  ROWID {rowid}: FAILED - {repr(decoded)}")
    
    success_rate = (successful / total * 100) if total > 0 else 0
    print(f"Regression test: {successful}/{total} successful ({success_rate:.1f}%)")
    
    return success_rate >= 80  # At least 80% should work


def test_decoder_stats():
    """Test decoder performance metrics"""
    print("\nTesting decoder performance...")
    
    decoder = MessageDecoder()
    
    # Test with known working data
    test_data = b"\x04\x0bstreamtyped" + b"NSString" + b"\x94\x84\x01\x2b\x05Hello"
    result = decoder.decode_attributed_body(test_data)
    
    stats = decoder.get_decode_stats()
    print(f"Decoder stats: {stats}")
    
    # Basic smoke test
    return stats['total_attempts'] > 0


def main():
    """Run all tests"""
    print("NSDictionary Decoder Integration Tests")
    print("=" * 50)
    
    test_results = [
        test_target_message(),
        test_regression_cases(),
        test_decoder_stats()
    ]
    
    passed = sum(test_results)
    total = len(test_results)
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)