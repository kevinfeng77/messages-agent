#!/usr/bin/env python3
"""Test script to validate the enhanced NSDictionary parsing in message decoder"""

import sys
import sqlite3
from pathlib import Path

# Add src to path for imports
sys.path.append('./src')
from messaging.decoder import MessageDecoder


def test_rowid_224717():
    """Test that ROWID 224717 now decodes to 'Me always the luckiest ever'"""
    print("Testing ROWID 224717 decoder fix...")
    
    db_path = Path('./data/copy/chat_copy.db')
    if not db_path.exists():
        print("ERROR: Original database not found")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute('SELECT ROWID, text, attributedBody FROM message WHERE ROWID = 224717')
    result = cursor.fetchone()
    
    if not result:
        print("ERROR: ROWID 224717 not found")
        conn.close()
        return False
    
    rowid, text, attributed_body = result
    print(f"ROWID {rowid}: text={repr(text)}")
    
    if not attributed_body:
        print("ERROR: No attributedBody to decode")
        conn.close()
        return False
    
    # Test with enhanced decoder
    decoder = MessageDecoder()
    decoded_result = decoder.decode_attributed_body(attributed_body)
    
    print(f"Decoded result: {repr(decoded_result)}")
    
    expected_text = "Me always the luckiest ever"
    success = decoded_result == expected_text
    
    if success:
        print("✅ SUCCESS: ROWID 224717 correctly decoded!")
    else:
        print("❌ FAILURE: ROWID 224717 still not decoded correctly")
        print(f"Expected: {repr(expected_text)}")
        print(f"Got: {repr(decoded_result)}")
    
    conn.close()
    return success


def test_nsdictionary_cases():
    """Test multiple cases that were previously returning 'NSDictionary'"""
    print("\nTesting multiple NSDictionary cases...")
    
    db_path = Path('./data/copy/chat_copy.db')
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get some cases that were previously failing
    test_rowids = [224717, 129543, 24119, 35669, 56232, 69918, 73711]
    
    decoder = MessageDecoder()
    successful_fixes = 0
    total_tests = 0
    
    for rowid in test_rowids:
        cursor.execute('SELECT ROWID, text, attributedBody FROM message WHERE ROWID = ?', (rowid,))
        result = cursor.fetchone()
        
        if result and result[2]:  # Has attributedBody
            total_tests += 1
            _, text, attributed_body = result
            decoded = decoder.decode_attributed_body(attributed_body)
            
            if decoded and decoded != "NSDictionary":
                successful_fixes += 1
                print(f"✅ ROWID {rowid}: {repr(decoded)}")
            else:
                print(f"❌ ROWID {rowid}: still returns {repr(decoded)}")
    
    success_rate = (successful_fixes / total_tests * 100) if total_tests > 0 else 0
    print(f"\nFixed {successful_fixes}/{total_tests} previously failing cases ({success_rate:.1f}%)")
    
    conn.close()
    return successful_fixes, total_tests


def test_decoder_stats():
    """Test decoder performance on a larger sample"""
    print("\nTesting decoder performance on sample data...")
    
    db_path = Path('./data/copy/chat_copy.db')
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Test on first 100 messages with attributedBody
    cursor.execute('''
        SELECT ROWID, text, attributedBody 
        FROM message 
        WHERE attributedBody IS NOT NULL 
        ORDER BY ROWID 
        LIMIT 100
    ''')
    
    results = cursor.fetchall()
    decoder = MessageDecoder()
    
    nsdictionary_count = 0
    successful_decode_count = 0
    
    for rowid, text, attributed_body in results:
        if attributed_body:
            decoded = decoder.decode_attributed_body(attributed_body)
            if decoded == "NSDictionary":
                nsdictionary_count += 1
            elif decoded and decoded.strip():
                successful_decode_count += 1
    
    total_tested = len(results)
    nsdictionary_rate = (nsdictionary_count / total_tested * 100) if total_tested > 0 else 0
    success_rate = (successful_decode_count / total_tested * 100) if total_tested > 0 else 0
    
    print(f"Sample of {total_tested} messages:")
    print(f"  Successful decodes: {successful_decode_count} ({success_rate:.1f}%)")
    print(f"  NSDictionary failures: {nsdictionary_count} ({nsdictionary_rate:.1f}%)")
    
    conn.close()
    return nsdictionary_count < total_tested * 0.1  # Success if <10% NSDictionary failures


def main():
    """Main test function"""
    print("Enhanced NSDictionary Decoder Validation")
    print("=" * 50)
    
    # Test the specific case
    test1_success = test_rowid_224717()
    
    # Test multiple cases
    fixed_count, total_count = test_nsdictionary_cases()
    
    # Test performance
    test3_success = test_decoder_stats()
    
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY:")
    print(f"✅ Target message fix: {'PASS' if test1_success else 'FAIL'}")
    print(f"✅ Multiple case fixes: {fixed_count}/{total_count} improved")
    print(f"✅ Overall performance: {'PASS' if test3_success else 'FAIL'}")
    
    overall_success = test1_success and fixed_count > 0 and test3_success
    print(f"\n🎯 OVERALL RESULT: {'SUCCESS' if overall_success else 'NEEDS WORK'}")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)