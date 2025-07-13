"""Unit tests for NSDictionary parsing fix in MessageDecoder"""

import unittest
import sqlite3
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append('../src')
from messaging.decoder import MessageDecoder


class TestNSDictionaryDecoder(unittest.TestCase):
    """Test cases for enhanced NSDictionary parsing in MessageDecoder"""

    def setUp(self):
        """Set up test environment"""
        self.decoder = MessageDecoder()
        self.db_path = Path('../data/copy/chat_copy.db')

    def test_target_message_224717(self):
        """Test that ROWID 224717 decodes to expected text"""
        if not self.db_path.exists():
            self.skipTest("Original database not available")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT attributedBody FROM message WHERE ROWID = 224717')
        result = cursor.fetchone()
        conn.close()

        if not result or not result[0]:
            self.skipTest("ROWID 224717 not found or no attributedBody")

        attributed_body = result[0]
        decoded_text = self.decoder.decode_attributed_body(attributed_body)
        
        self.assertEqual(decoded_text, "Me always the luckiest ever")

    def test_multiple_previously_failing_cases(self):
        """Test multiple ROWIDs that were previously returning 'NSDictionary'"""
        if not self.db_path.exists():
            self.skipTest("Original database not available")

        test_cases = [
            (224717, 'Me always the luckiest ever'),
            (129543, 'Me is luckiest ever :Do'),
            (24119, 'Me always now fr'),
            (35669, "U can't always be market making's"),
            (56232, 'I always get it'),
            (69918, 'Me always loves bubs'),
            (73711, 'I always love you!')
        ]

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        for rowid, expected_text in test_cases:
            with self.subTest(rowid=rowid):
                cursor.execute('SELECT attributedBody FROM message WHERE ROWID = ?', (rowid,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    attributed_body = result[0]
                    decoded_text = self.decoder.decode_attributed_body(attributed_body)
                    
                    self.assertNotEqual(decoded_text, "NSDictionary", 
                                      f"ROWID {rowid} still returns NSDictionary")
                    self.assertEqual(decoded_text, expected_text,
                                   f"ROWID {rowid} decoded incorrectly")

        conn.close()

    def test_decoder_stats_improvement(self):
        """Test that decoder stats show improvement"""
        original_success = self.decoder.decode_success_count
        original_failure = self.decoder.decode_failure_count
        
        if not self.db_path.exists():
            self.skipTest("Original database not available")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Test on a sample of messages
        cursor.execute('''
            SELECT attributedBody 
            FROM message 
            WHERE attributedBody IS NOT NULL 
            ORDER BY ROWID 
            LIMIT 50
        ''')
        
        results = cursor.fetchall()
        conn.close()

        nsdictionary_count = 0
        successful_decodes = 0

        for (attributed_body,) in results:
            if attributed_body:
                decoded = self.decoder.decode_attributed_body(attributed_body)
                if decoded == "NSDictionary":
                    nsdictionary_count += 1
                elif decoded and decoded.strip():
                    successful_decodes += 1

        # Should have very few NSDictionary failures now
        nsdictionary_rate = nsdictionary_count / len(results) if results else 0
        self.assertLess(nsdictionary_rate, 0.1, "Too many NSDictionary failures remain")
        
        # Should have good success rate
        success_rate = successful_decodes / len(results) if results else 0
        self.assertGreater(success_rate, 0.8, "Success rate too low")

    def test_enhanced_pattern_recognition(self):
        """Test the enhanced pattern recognition methods"""
        if not self.db_path.exists():
            self.skipTest("Original database not available")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT attributedBody FROM message WHERE ROWID = 224717')
        result = cursor.fetchone()
        conn.close()

        if not result or not result[0]:
            self.skipTest("Test data not available")

        attributed_body = result[0]
        
        # Test that NSKeyedArchiver format is detected
        self.assertTrue(attributed_body.startswith(b"\x04\x0bstreamtyped"))
        
        # Test that NSString marker is found
        nsstring_idx = attributed_body.find(b"NSString")
        self.assertNotEqual(nsstring_idx, -1)
        
        # Test the specific pattern recognition
        pattern = b"\x94\x84\x01\x2b"
        pattern_idx = attributed_body.find(pattern, nsstring_idx)
        self.assertNotEqual(pattern_idx, -1)

    def test_fallback_mechanisms(self):
        """Test that fallback mechanisms work properly"""
        # Test with various edge cases to ensure fallbacks work
        
        # Test with minimal NSKeyedArchiver data
        minimal_data = b"\x04\x0bstreamtyped" + b"NSString" + b"\x00" * 20
        result = self.decoder.decode_attributed_body(minimal_data)
        # Should return None rather than crash
        self.assertIsNone(result)
        
        # Test with corrupted data
        corrupted_data = b"\x04\x0bstreamtyped" + b"\xFF" * 100
        result = self.decoder.decode_attributed_body(corrupted_data)
        # Should return None rather than crash
        self.assertIsNone(result)

    def test_regression_protection(self):
        """Test that previously working messages still work"""
        if not self.db_path.exists():
            self.skipTest("Original database not available")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Test some messages that should decode with the '+' pattern
        cursor.execute('''
            SELECT ROWID, attributedBody 
            FROM message 
            WHERE attributedBody IS NOT NULL 
            AND ROWID IN (1, 3, 4, 6, 9, 10)
        ''')
        
        results = cursor.fetchall()
        conn.close()

        for rowid, attributed_body in results:
            with self.subTest(rowid=rowid):
                if attributed_body:
                    decoded = self.decoder.decode_attributed_body(attributed_body)
                    # Should not be None and should not be NSDictionary
                    self.assertIsNotNone(decoded)
                    self.assertNotEqual(decoded, "NSDictionary")
                    self.assertGreater(len(decoded.strip()), 0)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)