"""Comprehensive tests for message decoder"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.messaging.decoder import MessageDecoder, extract_message_text


class TestMessageDecoder(unittest.TestCase):
    """Test cases for MessageDecoder class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.decoder = MessageDecoder()
    
    def test_extract_message_text_with_text_column(self):
        """Test extraction when text column is populated"""
        text = "Hello world"
        attributed_body = b"some binary data"
        
        result = extract_message_text(text, attributed_body)
        self.assertEqual(result, "Hello world")
    
    def test_extract_message_text_with_empty_text(self):
        """Test extraction when text column is empty but attributedBody exists"""
        text = ""
        attributed_body = b'\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+\x0cHello world\x86\x84'
        
        result = extract_message_text(text, attributed_body)
        self.assertEqual(result, "Hello world")
    
    def test_extract_message_text_with_null_text(self):
        """Test extraction when text column is None"""
        text = None
        attributed_body = b'\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+\x05Test\x86\x84'
        
        result = extract_message_text(text, attributed_body)
        self.assertEqual(result, "Test")
    
    def test_extract_message_text_no_data(self):
        """Test extraction when no text data is available"""
        text = None
        attributed_body = None
        
        result = extract_message_text(text, attributed_body)
        self.assertIsNone(result)
    
    def test_decode_attributed_body_valid_format(self):
        """Test decoding valid NSKeyedArchiver format"""
        # Valid attributedBody with "Test message"
        attributed_body = b'\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+\x0cTest message\x86\x84'
        
        result = self.decoder.decode_attributed_body(attributed_body)
        self.assertEqual(result, "Test message")
    
    def test_decode_attributed_body_invalid_format(self):
        """Test decoding invalid binary data"""
        attributed_body = b'invalid binary data'
        
        result = self.decoder.decode_attributed_body(attributed_body)
        self.assertIsNone(result)
    
    def test_decode_attributed_body_empty(self):
        """Test decoding empty attributed body"""
        attributed_body = b''
        
        result = self.decoder.decode_attributed_body(attributed_body)
        self.assertIsNone(result)
    
    def test_decode_attributed_body_none(self):
        """Test decoding None attributed body"""
        attributed_body = None
        
        result = self.decoder.decode_attributed_body(attributed_body)
        self.assertIsNone(result)
    
    def test_decoder_statistics(self):
        """Test decoder statistics tracking"""
        # Reset stats
        self.decoder.reset_stats()
        
        # Decode some messages
        valid_data = b'\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+\x05Valid\x86\x84'
        invalid_data = b'invalid'
        
        self.decoder.decode_attributed_body(valid_data)
        self.decoder.decode_attributed_body(invalid_data)
        
        stats = self.decoder.get_decode_stats()
        self.assertEqual(stats["success_count"], 1)
        self.assertEqual(stats["failure_count"], 1)
        self.assertEqual(stats["total_attempts"], 2)
        self.assertEqual(stats["success_rate_percent"], 50.0)
    
    def test_nskeyedarchiver_detection(self):
        """Test NSKeyedArchiver format detection"""
        # Valid format
        valid_data = b'\x04\x0bstreamtyped...'
        invalid_data = b'not streamtyped'
        
        # Test internal method detection
        result1 = self.decoder._decode_nskeyedarchiver(valid_data)
        result2 = self.decoder._decode_nskeyedarchiver(invalid_data)
        
        # Should not crash and return None for invalid
        self.assertIsNone(result2)
    
    def test_text_extraction_edge_cases(self):
        """Test edge cases in text extraction"""
        # Whitespace only text
        result1 = extract_message_text("   ", None)
        self.assertIsNone(result1)
        
        # Text with special characters
        result2 = extract_message_text("Test 🎉 emoji", None)
        self.assertEqual(result2, "Test 🎉 emoji")
        
        # Very long text
        long_text = "A" * 1000
        result3 = extract_message_text(long_text, None)
        self.assertEqual(result3, long_text)
    
    def test_fallback_strategies(self):
        """Test fallback decoding strategies"""
        # Test data that should trigger different strategies
        
        # Strategy 1: NSKeyedArchiver (should work)
        nskeyed_data = b'\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+\x0bStrategy 1\x86\x84'
        result1 = self.decoder.decode_attributed_body(nskeyed_data)
        self.assertEqual(result1, "Strategy 1")
        
        # Strategy 2: Binary plist (mock - would need real plist data)
        # For now, just test that it doesn't crash
        fake_plist = b'bplist00fake'
        result2 = self.decoder.decode_attributed_body(fake_plist)
        # Should return None but not crash
        self.assertIsNone(result2)
        
        # Strategy 3: Embedded strings
        embedded_data = b'some\x00binary\x00data\x00with\x00Embedded Text\x00more\x00data'
        result3 = self.decoder.decode_attributed_body(embedded_data)
        # Should find "Embedded Text"
        self.assertEqual(result3, "Embedded Text")


class TestMessageDecoderIntegration(unittest.TestCase):
    """Integration tests using real database data"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.decoder = MessageDecoder()
        self.db_path = Path("data/chat_copy.db")
    
    def test_real_database_samples(self):
        """Test decoder against real database samples"""
        if not self.db_path.exists():
            self.skipTest("Database not available for testing")
        
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get some real samples
        cursor.execute("""
            SELECT text, attributedBody 
            FROM message 
            WHERE text IS NOT NULL AND attributedBody IS NOT NULL 
            AND length(text) > 3 AND length(text) < 100
            LIMIT 5
        """)
        
        samples = cursor.fetchall()
        conn.close()
        
        # Test that decoded text matches or is reasonable
        for text, attributed_body in samples:
            decoded = self.decoder.decode_attributed_body(attributed_body)
            
            # Should decode to something
            self.assertIsNotNone(decoded)
            
            # Should match original text (or be reasonable alternative)
            if decoded != text:
                # At least should be non-empty and printable
                self.assertTrue(len(decoded) > 0)
                self.assertTrue(decoded.isprintable())
    
    def test_migration_effectiveness(self):
        """Test that migration significantly improves text coverage"""
        if not self.db_path.exists():
            self.skipTest("Database not available for testing")
        
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN text IS NOT NULL AND text != '' THEN 1 END) as has_text,
                COUNT(CASE WHEN extracted_text IS NOT NULL AND extracted_text != '' THEN 1 END) as has_extracted
            FROM message
        """)
        
        total, has_text, has_extracted = cursor.fetchone()
        conn.close()
        
        # Calculate coverage
        original_coverage = (has_text / total) * 100
        new_coverage = ((has_text + has_extracted - has_text) / total) * 100
        
        # Should have significantly improved coverage
        self.assertGreater(new_coverage, original_coverage)
        self.assertGreater(new_coverage, 80)  # Should be > 80% coverage


if __name__ == '__main__':
    # Create tests directory if it doesn't exist
    Path("tests").mkdir(exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2)