"""Tests for ConversationAnalyzer"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import tempfile
import os

from src.imessage.conversation_analyzer import ConversationAnalyzer, ConversationContext
from src.database.manager import DatabaseManager


class TestConversationAnalyzer(unittest.TestCase):
    """Test ConversationAnalyzer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.analyzer = ConversationAnalyzer(self.mock_db_manager)
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cocoa_timestamp_conversion(self):
        """Test conversion of Cocoa timestamps to Python datetime"""
        # Test timestamp for a known date
        # 2023-01-01 00:00:00 UTC is approximately 694224000000000000 nanoseconds since 2001-01-01
        cocoa_timestamp = 694224000000000000
        result = self.analyzer._cocoa_timestamp_to_datetime(cocoa_timestamp)
        
        # Should be approximately January 1, 2023
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)
    
    def test_analyze_conversation_tone_positive(self):
        """Test tone analysis for positive messages"""
        messages = [
            {"text": "Thanks so much! This is great", "is_from_me": False},
            {"text": "Yes, I love this idea", "is_from_me": True},
            {"text": "Awesome work!", "is_from_me": False}
        ]
        
        tone = self.analyzer._analyze_conversation_tone(messages)
        self.assertEqual(tone, "positive")
    
    def test_analyze_conversation_tone_negative(self):
        """Test tone analysis for negative messages"""
        messages = [
            {"text": "Sorry, this won't work", "is_from_me": False},
            {"text": "No, I can't do that", "is_from_me": True},
            {"text": "This is a problem", "is_from_me": False}
        ]
        
        tone = self.analyzer._analyze_conversation_tone(messages)
        self.assertEqual(tone, "negative")
    
    def test_analyze_conversation_tone_questioning(self):
        """Test tone analysis for questioning messages"""
        messages = [
            {"text": "What do you think about this?", "is_from_me": False},
            {"text": "When should we meet?", "is_from_me": True},
            {"text": "How does this work?", "is_from_me": False}
        ]
        
        tone = self.analyzer._analyze_conversation_tone(messages)
        self.assertEqual(tone, "questioning")
    
    def test_extract_topic_keywords(self):
        """Test keyword extraction from conversation"""
        messages = [
            {"text": "Let's meet for lunch today", "is_from_me": False},
            {"text": "Sure, where do you want to have lunch?", "is_from_me": True},
            {"text": "How about that new restaurant?", "is_from_me": False},
            {"text": "Perfect, see you at the restaurant", "is_from_me": True}
        ]
        
        keywords = self.analyzer._extract_topic_keywords(messages)
        
        # Should include topic words but not stop words
        self.assertIn("lunch", keywords)
        self.assertIn("restaurant", keywords)
        self.assertNotIn("the", keywords)
        self.assertNotIn("you", keywords)
    
    def test_get_conversation_context_no_database(self):
        """Test behavior when database doesn't exist"""
        self.mock_db_manager.copy_db_path.exists.return_value = False
        
        result = self.analyzer.get_conversation_context(123)
        self.assertIsNone(result)
    
    @patch('sqlite3.connect')
    def test_get_conversation_context_no_messages(self, mock_connect):
        """Test behavior when no messages found for handle"""
        self.mock_db_manager.copy_db_path.exists.return_value = True
        self.mock_db_manager.copy_db_path = "test.db"
        
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        result = self.analyzer.get_conversation_context(123)
        self.assertIsNone(result)
    
    @patch('sqlite3.connect')
    @patch('src.messaging.decoder.extract_message_text')
    def test_get_conversation_context_success(self, mock_extract_text, mock_connect):
        """Test successful conversation context retrieval"""
        self.mock_db_manager.copy_db_path.exists.return_value = True
        self.mock_db_manager.copy_db_path = "test.db"
        
        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, "guid1", "Hello", None, 123, 694224000000000000, None, 0, "iMessage"),
            (2, "guid2", "Hi there", None, 123, 694224001000000000, None, 1, "iMessage")
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock text extraction
        mock_extract_text.side_effect = ["Hello", "Hi there"]
        
        result = self.analyzer.get_conversation_context(123)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ConversationContext)
        self.assertEqual(result.handle_id, 123)
        self.assertEqual(result.conversation_length, 2)
        self.assertTrue(result.user_last_spoke)  # Last message is from user (is_from_me=1)
    
    def test_get_conversation_summary_no_context(self):
        """Test summary when no context available"""
        with patch.object(self.analyzer, 'get_conversation_context', return_value=None):
            result = self.analyzer.get_conversation_summary(123)
            self.assertEqual(result, {})
    
    def test_get_conversation_summary_with_context(self):
        """Test summary generation with valid context"""
        # Create mock context
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[
                {"is_from_me": True, "date": 1000000000},
                {"is_from_me": False, "date": 2000000000},
                {"is_from_me": True, "date": 3000000000}
            ],
            conversation_length=3,
            last_message_time=datetime.now(),
            user_last_spoke=True,
            contact_last_spoke=False,
            time_since_last_message=timedelta(minutes=5),
            conversation_tone="positive",
            topic_keywords=["lunch", "meeting"]
        )
        
        with patch.object(self.analyzer, 'get_conversation_context', return_value=mock_context):
            result = self.analyzer.get_conversation_summary(123)
            
            self.assertEqual(result["handle_id"], 123)
            self.assertEqual(result["total_messages"], 3)
            self.assertEqual(result["user_messages"], 2)
            self.assertEqual(result["contact_messages"], 1)
            self.assertEqual(result["conversation_tone"], "positive")
            self.assertEqual(result["topic_keywords"], ["lunch", "meeting"])
            self.assertTrue(result["user_last_spoke"])


class TestConversationContext(unittest.TestCase):
    """Test ConversationContext dataclass"""
    
    def test_conversation_context_creation(self):
        """Test ConversationContext object creation"""
        context = ConversationContext(
            handle_id=123,
            recent_messages=[],
            conversation_length=0,
            last_message_time=None,
            user_last_spoke=False,
            contact_last_spoke=False,
            time_since_last_message=None
        )
        
        self.assertEqual(context.handle_id, 123)
        self.assertEqual(context.recent_messages, [])
        self.assertEqual(context.conversation_length, 0)
        self.assertEqual(context.topic_keywords, [])  # Should initialize empty list
    
    def test_conversation_context_with_keywords(self):
        """Test ConversationContext with topic keywords"""
        keywords = ["meeting", "lunch", "project"]
        context = ConversationContext(
            handle_id=123,
            recent_messages=[],
            conversation_length=0,
            last_message_time=None,
            user_last_spoke=False,
            contact_last_spoke=False,
            time_since_last_message=None,
            topic_keywords=keywords
        )
        
        self.assertEqual(context.topic_keywords, keywords)


if __name__ == '__main__':
    unittest.main()