"""Tests for message generator module"""

import pytest
from unittest.mock import patch, MagicMock

from src.message_maker.generator import MessageGenerator, MessageContext


class TestMessageContext:
    """Test MessageContext dataclass"""
    
    def test_message_context_creation(self):
        """Test creating MessageContext with required fields"""
        context = MessageContext(
            conversation_history=["Hello", "Hi there"]
        )
        
        assert context.conversation_history == ["Hello", "Hi there"]
        assert context.user_profile is None
        assert context.message_type == "text"
        assert context.platform == "imessage"
        assert context.tone == "casual"
        assert context.urgency == "normal"
        
    def test_message_context_with_custom_values(self):
        """Test MessageContext with custom values"""
        context = MessageContext(
            conversation_history=["How are you?"],
            user_profile={"name": "John"},
            message_type="greeting",
            platform="whatsapp",
            tone="formal",
            urgency="high"
        )
        
        assert context.conversation_history == ["How are you?"]
        assert context.user_profile == {"name": "John"}
        assert context.message_type == "greeting"
        assert context.platform == "whatsapp"
        assert context.tone == "formal"
        assert context.urgency == "high"


class TestMessageGenerator:
    """Test MessageGenerator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.generator = MessageGenerator()
        
    def test_generator_initialization(self):
        """Test generator initializes with empty collections"""
        assert isinstance(self.generator.templates, dict)
        assert isinstance(self.generator.user_patterns, dict)
        assert len(self.generator.templates) == 0
        assert len(self.generator.user_patterns) == 0
        
    def test_generate_response_empty_history(self):
        """Test generating response with empty conversation history"""
        context = MessageContext(conversation_history=[])
        
        with patch('src.message_maker.generator.logger') as mock_logger:
            result = self.generator.generate_response(context)
            
            assert result == ""
            mock_logger.warning.assert_called_once_with("No conversation history provided")
            
    def test_generate_response_with_history(self):
        """Test generating response with conversation history"""
        context = MessageContext(conversation_history=["Hello", "Hi there", "How are you?"])
        
        with patch('src.message_maker.generator.logger') as mock_logger:
            result = self.generator.generate_response(context)
            
            assert "Generated response based on 3 previous messages" in result
            mock_logger.info.assert_called_once_with("Generating response for text message")
            
    def test_suggest_responses(self):
        """Test generating multiple response suggestions"""
        context = MessageContext(conversation_history=["Hello"])
        
        with patch('src.message_maker.generator.logger') as mock_logger:
            suggestions = self.generator.suggest_responses(context, count=3)
            
            assert len(suggestions) == 3
            assert all("suggestion" in suggestion for suggestion in suggestions)
            # Check that the logger was called (the exact message may vary)
            mock_logger.info.assert_called()
            
    def test_suggest_responses_custom_count(self):
        """Test generating custom number of suggestions"""
        context = MessageContext(conversation_history=["Hello"])
        
        suggestions = self.generator.suggest_responses(context, count=5)
        
        assert len(suggestions) == 5
        
    def test_analyze_message_patterns_empty_messages(self):
        """Test analyzing patterns with empty message list"""
        user_id = "test_user_123"
        
        patterns = self.generator.analyze_message_patterns(user_id, [])
        
        assert patterns["avg_length"] == 0
        assert patterns["common_words"] == []
        assert patterns["tone_preferences"] == "casual"
        assert patterns["response_time_preference"] == "normal"
        assert user_id in self.generator.user_patterns
        
    def test_analyze_message_patterns_with_messages(self):
        """Test analyzing patterns with actual messages"""
        user_id = "test_user_456"
        messages = ["Hello there", "How are you doing?", "Great!"]
        
        with patch('src.message_maker.generator.logger') as mock_logger:
            patterns = self.generator.analyze_message_patterns(user_id, messages)
            
            expected_avg_length = sum(len(msg) for msg in messages) / len(messages)
            assert patterns["avg_length"] == expected_avg_length
            assert user_id in self.generator.user_patterns
            mock_logger.info.assert_called_once_with(f"Analyzing patterns for user {user_id} from 3 messages")
            
    def test_multiple_users_patterns(self):
        """Test storing patterns for multiple users"""
        user1 = "user_1"
        user2 = "user_2"
        
        self.generator.analyze_message_patterns(user1, ["Short"])
        self.generator.analyze_message_patterns(user2, ["This is a longer message"])
        
        assert user1 in self.generator.user_patterns
        assert user2 in self.generator.user_patterns
        assert len(self.generator.user_patterns) == 2
        
        # Verify different average lengths
        assert self.generator.user_patterns[user1]["avg_length"] < self.generator.user_patterns[user2]["avg_length"]


class TestMessageGeneratorIntegration:
    """Integration tests for MessageGenerator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.generator = MessageGenerator()
        
    def test_complete_workflow(self):
        """Test complete message generation workflow"""
        user_id = "integration_test_user"
        messages = ["Hey!", "What's up?", "Not much, you?"]
        
        # Analyze patterns first
        patterns = self.generator.analyze_message_patterns(user_id, messages)
        
        # Create context
        context = MessageContext(
            conversation_history=messages,
            user_profile={"user_id": user_id},
            tone="casual"
        )
        
        # Generate response
        response = self.generator.generate_response(context)
        
        # Generate suggestions
        suggestions = self.generator.suggest_responses(context, count=2)
        
        # Verify results
        assert response != ""
        assert len(suggestions) == 2
        assert user_id in self.generator.user_patterns
        assert patterns["avg_length"] > 0