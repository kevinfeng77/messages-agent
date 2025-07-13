"""Comprehensive test suite for the main API function."""

import pytest
import unittest.mock as mock
from unittest.mock import Mock, patch
import sqlite3
from datetime import datetime

from src.message_maker.api import MessageMakerService, generate_message_responses
from src.message_maker.types import MessageRequest, MessageResponse, ChatMessage, NewMessage, LLMPromptData


class TestMessageMakerService:
    """Test cases for MessageMakerService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.valid_request = MessageRequest(
            chat_id=123,
            user_id="test_user",
            contents="Hello world"
        )
    
    @patch('src.message_maker.api.LLMClient')
    def test_init_with_default_db_path(self, mock_llm_client_class):
        """Test service initialization with default database path."""
        mock_llm_client_class.return_value = Mock()
        service = MessageMakerService()
        assert service.db_path == "./data/messages.db"
        assert service.llm_client is not None
        assert service.logger is not None
    
    @patch('src.message_maker.api.LLMClient')
    def test_init_with_custom_db_path(self, mock_llm_client_class):
        """Test service initialization with custom database path."""
        mock_llm_client_class.return_value = Mock()
        custom_path = "/custom/path/messages.db"
        service = MessageMakerService(db_path=custom_path)
        assert service.db_path == custom_path
    
    @patch('src.message_maker.api.get_chat_history_for_message_generation')
    @patch('src.message_maker.api.LLMClient')
    def test_generate_message_responses_success(self, mock_llm_client_class, mock_get_chat_history):
        """Test successful message response generation."""
        # Setup mocks
        mock_chat_history = [
            ChatMessage(contents="Hi there", is_from_me=False, created_at="2023-01-01T10:00:00Z"),
            ChatMessage(contents="Hello!", is_from_me=True, created_at="2023-01-01T10:01:00Z")
        ]
        mock_get_chat_history.return_value = mock_chat_history
        
        mock_llm_client = Mock()
        mock_response = MessageResponse(
            response_1="Great to hear from you!",
            response_2="Hey! How's it going?", 
            response_3="Nice to hear from you again!"
        )
        mock_llm_client.generate_responses.return_value = mock_response
        mock_llm_client_class.return_value = mock_llm_client
        
        # Execute
        service = MessageMakerService()
        result = service.generate_message_responses(self.valid_request)
        
        # Verify
        assert isinstance(result, MessageResponse)
        assert result.response_1 == "Great to hear from you!"
        assert result.response_2 == "Hey! How's it going?"
        assert result.response_3 == "Nice to hear from you again!"
        
        # Verify chat history was retrieved with correct parameters
        mock_get_chat_history.assert_called_once_with(
            chat_id="123",
            user_id="test_user"
        )
        
        # Verify LLM client was called with correct prompt data
        mock_llm_client.generate_responses.assert_called_once()
        call_args = mock_llm_client.generate_responses.call_args[0][0]
        assert isinstance(call_args, LLMPromptData)
        assert call_args.chat_history == mock_chat_history
        assert call_args.new_message.contents == "Hello world"
    
    @patch('src.message_maker.api.LLMClient')
    def test_generate_message_responses_invalid_input(self, mock_llm_client_class):
        """Test response generation with invalid input."""
        invalid_request = MessageRequest(
            chat_id=-1,  # Invalid chat_id
            user_id="test_user",
            contents="Hello world"
        )
        
        with pytest.raises(ValueError, match="chat_id must be a positive integer"):
            service = MessageMakerService()
            service.generate_message_responses(invalid_request)
    
    @patch('src.message_maker.api.LLMClient')
    def test_generate_message_responses_empty_user_id(self, mock_llm_client_class):
        """Test response generation with empty user_id."""
        invalid_request = MessageRequest(
            chat_id=123,
            user_id="",  # Empty user_id
            contents="Hello world"
        )
        
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            service = MessageMakerService()
            service.generate_message_responses(invalid_request)
    
    @patch('src.message_maker.api.LLMClient')
    def test_generate_message_responses_empty_contents(self, mock_llm_client_class):
        """Test response generation with empty contents."""
        invalid_request = MessageRequest(
            chat_id=123,
            user_id="test_user",
            contents=""  # Empty contents
        )
        
        with pytest.raises(ValueError, match="contents must be a non-empty string"):
            service = MessageMakerService()
            service.generate_message_responses(invalid_request)
    
    @patch('src.message_maker.api.get_chat_history_for_message_generation')
    @patch('src.message_maker.api.LLMClient')
    def test_generate_message_responses_database_error(self, mock_llm_client_class, mock_get_chat_history):
        """Test response generation with database error."""
        mock_get_chat_history.side_effect = sqlite3.Error("Database connection failed")
        
        with pytest.raises(Exception, match="Database error"):
            service = MessageMakerService()
            service.generate_message_responses(self.valid_request)
    
    @patch('src.message_maker.api.get_chat_history_for_message_generation')
    @patch('src.message_maker.api.LLMClient')
    def test_generate_message_responses_llm_error(self, mock_llm_client_class, mock_get_chat_history):
        """Test response generation with LLM API error."""
        # Setup mocks
        mock_get_chat_history.return_value = []
        mock_llm_client = Mock()
        mock_llm_client.generate_responses.side_effect = Exception("LLM API unavailable")
        mock_llm_client_class.return_value = mock_llm_client
        
        with pytest.raises(Exception, match="LLM API error"):
            service = MessageMakerService()
            service.generate_message_responses(self.valid_request)
    
    @patch('src.message_maker.api.get_chat_history_for_message_generation')
    @patch('src.message_maker.api.LLMClient')
    def test_generate_message_responses_empty_chat_history(self, mock_llm_client_class, mock_get_chat_history):
        """Test response generation with empty chat history."""
        # Setup mocks
        mock_get_chat_history.return_value = []  # Empty chat history
        mock_llm_client = Mock()
        mock_response = MessageResponse(
            response_1="Hello there!",
            response_2="Hi!",
            response_3="Hey!"
        )
        mock_llm_client.generate_responses.return_value = mock_response
        mock_llm_client_class.return_value = mock_llm_client
        
        # Execute
        service = MessageMakerService()
        result = service.generate_message_responses(self.valid_request)
        
        # Verify it still works with empty history
        assert isinstance(result, MessageResponse)
        assert result.response_1 == "Hello there!"


class TestGenerateMessageResponsesFunction:
    """Test cases for the standalone generate_message_responses function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.valid_request = MessageRequest(
            chat_id=456,
            user_id="standalone_user",
            contents="Test message"
        )
    
    @patch('src.message_maker.api.MessageMakerService')
    def test_generate_message_responses_function_success(self, mock_service_class):
        """Test the standalone function creates service and calls method."""
        # Setup mock
        mock_service = Mock()
        mock_response = MessageResponse(
            response_1="Response 1",
            response_2="Response 2", 
            response_3="Response 3"
        )
        mock_service.generate_message_responses.return_value = mock_response
        mock_service_class.return_value = mock_service
        
        # Execute
        result = generate_message_responses(self.valid_request)
        
        # Verify
        assert result == mock_response
        mock_service_class.assert_called_once_with()
        mock_service.generate_message_responses.assert_called_once_with(self.valid_request)
    
    @patch('src.message_maker.api.MessageMakerService')
    def test_generate_message_responses_function_error_propagation(self, mock_service_class):
        """Test that the standalone function properly propagates errors."""
        # Setup mock to raise error
        mock_service = Mock()
        mock_service.generate_message_responses.side_effect = ValueError("Invalid input")
        mock_service_class.return_value = mock_service
        
        # Execute and verify error is propagated
        with pytest.raises(ValueError, match="Invalid input"):
            generate_message_responses(self.valid_request)


class TestIntegrationScenarios:
    """Integration test scenarios for different use cases."""
    
    @patch('src.message_maker.api.get_chat_history_for_message_generation')
    @patch('src.message_maker.api.LLMClient')
    def test_typical_conversation_flow(self, mock_llm_client_class, mock_get_chat_history):
        """Test a typical conversation flow with realistic chat history."""
        # Setup realistic chat history
        mock_chat_history = [
            ChatMessage(contents="Hey, are you free for lunch tomorrow?", is_from_me=False, created_at="2023-01-01T09:00:00Z"),
            ChatMessage(contents="Yeah! What time works for you?", is_from_me=True, created_at="2023-01-01T09:05:00Z"),
            ChatMessage(contents="How about 12:30 at that new Italian place?", is_from_me=False, created_at="2023-01-01T09:10:00Z")
        ]
        mock_get_chat_history.return_value = mock_chat_history
        
        # Setup LLM response
        mock_llm_client = Mock()
        mock_response = MessageResponse(
            response_1="Sounds perfect! See you there at 12:30",
            response_2="Great choice! I'll meet you at 12:30",
            response_3="Perfect timing! Looking forward to trying that place"
        )
        mock_llm_client.generate_responses.return_value = mock_response
        mock_llm_client_class.return_value = mock_llm_client
        
        # Create request
        request = MessageRequest(
            chat_id=789,
            user_id="conversation_user",
            contents="How about 12:30 at that new Italian place?"
        )
        
        # Execute
        service = MessageMakerService()
        result = service.generate_message_responses(request)
        
        # Verify realistic responses
        assert "12:30" in result.response_1
        assert isinstance(result, MessageResponse)
    
    def test_edge_case_very_long_content(self):
        """Test handling of very long message content."""
        long_content = "A" * 10000  # Very long message
        request = MessageRequest(
            chat_id=999,
            user_id="long_user",
            contents=long_content
        )
        
        # Should not raise validation error for long content
        try:
            request.validate()
        except ValueError:
            pytest.fail("Validation should not fail for long content")
    
    def test_edge_case_unicode_content(self):
        """Test handling of unicode and special characters."""
        unicode_content = "Hello 👋 这是中文 🎉 Émojis and spéciàl chars"
        request = MessageRequest(
            chat_id=888,
            user_id="unicode_user",
            contents=unicode_content
        )
        
        # Should not raise validation error for unicode content
        try:
            request.validate()
        except ValueError:
            pytest.fail("Validation should not fail for unicode content")