"""Tests for ResponseGenerator"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.imessage.response_generator import ResponseGenerator, ResponseSuggestion
from src.imessage.conversation_analyzer import ConversationAnalyzer, ConversationContext


class TestResponseSuggestion(unittest.TestCase):
    """Test ResponseSuggestion dataclass"""
    
    def test_response_suggestion_creation(self):
        """Test ResponseSuggestion object creation"""
        suggestion = ResponseSuggestion(
            text="Thanks!",
            confidence=0.8,
            category="acknowledgment",
            reasoning="Responding to thanks"
        )
        
        self.assertEqual(suggestion.text, "Thanks!")
        self.assertEqual(suggestion.confidence, 0.8)
        self.assertEqual(suggestion.category, "acknowledgment")
        self.assertEqual(suggestion.reasoning, "Responding to thanks")


class TestResponseGenerator(unittest.TestCase):
    """Test ResponseGenerator functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_analyzer = Mock(spec=ConversationAnalyzer)
        self.generator = ResponseGenerator(self.mock_analyzer)
    
    def test_initialization(self):
        """Test ResponseGenerator initialization"""
        self.assertIsNotNone(self.generator.response_templates)
        self.assertIn("acknowledgment", self.generator.response_templates)
        self.assertIn("affirmative", self.generator.response_templates)
        self.assertIn("question_response", self.generator.response_templates)
    
    def test_get_default_suggestions(self):
        """Test default suggestions when no context available"""
        suggestions = self.generator._get_default_suggestions(3)
        
        self.assertEqual(len(suggestions), 3)
        for suggestion in suggestions:
            self.assertIsInstance(suggestion, ResponseSuggestion)
            self.assertGreater(len(suggestion.text), 0)
            self.assertEqual(suggestion.category, "default")
    
    def test_generate_suggestions_no_context(self):
        """Test suggestion generation when no context available"""
        self.mock_analyzer.get_conversation_context.return_value = None
        
        suggestions = self.generator.generate_suggestions(123, 3)
        
        self.assertEqual(len(suggestions), 3)
        for suggestion in suggestions:
            self.assertEqual(suggestion.category, "default")
    
    def test_context_based_suggestions_question(self):
        """Test context-based suggestions for questions"""
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[
                {
                    "text": "What time should we meet?",
                    "is_from_me": False,
                    "date": 1000000000
                }
            ],
            conversation_length=1,
            last_message_time=datetime.now(),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(minutes=1)
        )
        
        suggestions = self.generator._get_context_based_suggestions(mock_context)
        
        # Should include question responses
        suggestion_texts = [s.text for s in suggestions]
        self.assertTrue(any("time" in text.lower() or "when" in text.lower() 
                           for text in suggestion_texts))
    
    def test_context_based_suggestions_thanks(self):
        """Test context-based suggestions for thank you messages"""
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[
                {
                    "text": "Thanks so much!",
                    "is_from_me": False,
                    "date": 1000000000
                }
            ],
            conversation_length=1,
            last_message_time=datetime.now(),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(minutes=1)
        )
        
        suggestions = self.generator._get_context_based_suggestions(mock_context)
        
        # Should include acknowledgment responses
        suggestion_texts = [s.text for s in suggestions]
        self.assertTrue(any("welcome" in text.lower() or "problem" in text.lower() 
                           for text in suggestion_texts))
        
        # Should have high confidence for this clear case
        high_conf_suggestions = [s for s in suggestions if s.confidence > 0.8]
        self.assertGreater(len(high_conf_suggestions), 0)
    
    def test_pattern_based_suggestions(self):
        """Test pattern-based suggestion generation"""
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[
                {
                    "text": "Sorry for the delay",
                    "is_from_me": False,
                    "date": 1000000000
                }
            ],
            conversation_length=1,
            last_message_time=datetime.now(),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(minutes=1)
        )
        
        suggestions = self.generator._get_pattern_based_suggestions(mock_context)
        
        # Should match "sorry" pattern
        suggestion_texts = [s.text for s in suggestions]
        self.assertTrue(any("worry" in text.lower() or "good" in text.lower() 
                           for text in suggestion_texts))
    
    def test_tone_based_suggestions_positive(self):
        """Test tone-based suggestions for positive tone"""
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[],
            conversation_length=0,
            last_message_time=datetime.now(),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(minutes=1),
            conversation_tone="positive"
        )
        
        suggestions = self.generator._get_tone_based_suggestions(mock_context)
        
        # Should include positive acknowledgments
        self.assertGreater(len(suggestions), 0)
        for suggestion in suggestions:
            self.assertEqual(suggestion.category, "tone_positive")
    
    def test_timing_based_suggestions_late_response(self):
        """Test timing-based suggestions for late responses"""
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[],
            conversation_length=0,
            last_message_time=datetime.now() - timedelta(hours=2),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(hours=2)
        )
        
        suggestions = self.generator._get_timing_based_suggestions(mock_context)
        
        # Should include late response acknowledgments
        suggestion_texts = [s.text for s in suggestions]
        self.assertTrue(any("sorry" in text.lower() or "late" in text.lower() 
                           for text in suggestion_texts))
    
    def test_timing_based_suggestions_quick_response(self):
        """Test timing-based suggestions for quick responses"""
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[],
            conversation_length=0,
            last_message_time=datetime.now() - timedelta(minutes=2),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(minutes=2)
        )
        
        suggestions = self.generator._get_timing_based_suggestions(mock_context)
        
        # Should include casual quick responses
        if suggestions:  # May be empty for quick responses
            for suggestion in suggestions:
                self.assertEqual(suggestion.category, "timing_quick")
    
    def test_generate_suggestions_integration(self):
        """Test full suggestion generation with mocked context"""
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[
                {
                    "text": "Thanks for your help!",
                    "is_from_me": False,
                    "date": 1000000000
                }
            ],
            conversation_length=1,
            last_message_time=datetime.now() - timedelta(minutes=5),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(minutes=5),
            conversation_tone="positive"
        )
        
        self.mock_analyzer.get_conversation_context.return_value = mock_context
        
        suggestions = self.generator.generate_suggestions(123, 3)
        
        self.assertLessEqual(len(suggestions), 3)
        self.assertGreater(len(suggestions), 0)
        
        # Should be sorted by confidence
        confidences = [s.confidence for s in suggestions]
        self.assertEqual(confidences, sorted(confidences, reverse=True))
        
        # Should not have duplicates
        suggestion_texts = [s.text for s in suggestions]
        self.assertEqual(len(suggestion_texts), len(set(suggestion_texts)))
    
    def test_analyze_user_response_patterns(self):
        """Test user response pattern analysis"""
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[
                {"text": "Yes", "is_from_me": True},
                {"text": "Sure thing", "is_from_me": True},
                {"text": "Thanks!", "is_from_me": True},
                {"text": "Hello there", "is_from_me": False},
                {"text": "No problem", "is_from_me": True}
            ],
            conversation_length=5,
            last_message_time=datetime.now(),
            user_last_spoke=True,
            contact_last_spoke=False,
            time_since_last_message=timedelta(minutes=1)
        )
        
        self.mock_analyzer.get_conversation_context.return_value = mock_context
        
        patterns = self.generator.analyze_user_response_patterns(123)
        
        self.assertIn("avg_response_length", patterns)
        self.assertIn("total_user_messages", patterns)
        self.assertIn("common_words", patterns)
        self.assertIn("typical_response_style", patterns)
        
        self.assertEqual(patterns["total_user_messages"], 4)  # 4 user messages
    
    def test_determine_response_style_brief(self):
        """Test response style determination for brief responses"""
        user_messages = [
            {"text": "Yes"},
            {"text": "No"},
            {"text": "Ok"}
        ]
        
        style = self.generator._determine_response_style(user_messages)
        self.assertEqual(style, "brief")
    
    def test_determine_response_style_detailed(self):
        """Test response style determination for detailed responses"""
        user_messages = [
            {"text": "That sounds like a really great idea and I think we should definitely consider it"},
            {"text": "I appreciate you taking the time to explain this to me in detail"},
        ]
        
        style = self.generator._determine_response_style(user_messages)
        self.assertEqual(style, "detailed")
    
    def test_determine_response_style_expressive(self):
        """Test response style determination for expressive responses"""
        user_messages = [
            {"text": "Great! 😊"},
            {"text": "Thanks! 👍"},
            {"text": "Awesome! 🎉"},
        ]
        
        style = self.generator._determine_response_style(user_messages)
        self.assertEqual(style, "expressive")


if __name__ == '__main__':
    unittest.main()