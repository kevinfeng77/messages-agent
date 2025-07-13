"""Comprehensive tests for Message Maker data classes and types."""

import json
import pytest
from datetime import datetime
from typing import Dict, Any

from src.message_maker.types import (
    MessageRequest,
    MessageResponse,
    ChatMessage,
    NewMessage,
    DatabaseMessage,
    LLMPromptData,
)


class TestMessageRequest:
    """Test cases for MessageRequest data class."""

    def test_valid_message_request(self):
        """Test creating a valid MessageRequest."""
        request = MessageRequest(
            chat_id=123,
            user_id="user-456",
            contents="Hello, how are you?"
        )
        
        assert request.chat_id == 123
        assert request.user_id == "user-456"
        assert request.contents == "Hello, how are you?"

    def test_message_request_validation_success(self):
        """Test successful validation."""
        request = MessageRequest(
            chat_id=1,
            user_id="valid-user",
            contents="Valid message"
        )
        request.validate()  # Should not raise

    def test_message_request_validation_invalid_chat_id(self):
        """Test validation with invalid chat_id."""
        request = MessageRequest(
            chat_id=0,
            user_id="user-456",
            contents="Hello"
        )
        
        with pytest.raises(ValueError, match="chat_id must be a positive integer"):
            request.validate()

    def test_message_request_validation_empty_user_id(self):
        """Test validation with empty user_id."""
        request = MessageRequest(
            chat_id=123,
            user_id="",
            contents="Hello"
        )
        
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            request.validate()

    def test_message_request_validation_empty_contents(self):
        """Test validation with empty contents."""
        request = MessageRequest(
            chat_id=123,
            user_id="user-456",
            contents=""
        )
        
        with pytest.raises(ValueError, match="contents must be a non-empty string"):
            request.validate()

    def test_message_request_serialization(self):
        """Test JSON serialization and deserialization."""
        original = MessageRequest(
            chat_id=123,
            user_id="user-456",
            contents="Test message"
        )
        
        # Test to_dict
        data = original.to_dict()
        expected = {
            "chat_id": 123,
            "user_id": "user-456",
            "contents": "Test message"
        }
        assert data == expected
        
        # Test from_dict
        reconstructed = MessageRequest.from_dict(data)
        assert reconstructed == original
        
        # Test JSON serialization
        json_str = original.to_json()
        from_json = MessageRequest.from_json(json_str)
        assert from_json == original


class TestMessageResponse:
    """Test cases for MessageResponse data class."""

    def test_valid_message_response(self):
        """Test creating a valid MessageResponse."""
        response = MessageResponse(
            response_1="Great!",
            response_2="Sounds good",
            response_3="Perfect"
        )
        
        assert response.response_1 == "Great!"
        assert response.response_2 == "Sounds good"
        assert response.response_3 == "Perfect"

    def test_message_response_validation_success(self):
        """Test successful validation."""
        response = MessageResponse(
            response_1="Response 1",
            response_2="Response 2",
            response_3="Response 3"
        )
        response.validate()  # Should not raise

    def test_message_response_validation_empty_response(self):
        """Test validation with empty response."""
        response = MessageResponse(
            response_1="Valid",
            response_2="",
            response_3="Also valid"
        )
        
        with pytest.raises(ValueError, match="response_2 must be a non-empty string"):
            response.validate()

    def test_message_response_get_responses(self):
        """Test get_responses method."""
        response = MessageResponse(
            response_1="First",
            response_2="Second", 
            response_3="Third"
        )
        
        responses = response.get_responses()
        assert responses == ["First", "Second", "Third"]

    def test_message_response_serialization(self):
        """Test JSON serialization and deserialization."""
        original = MessageResponse(
            response_1="Response 1",
            response_2="Response 2",
            response_3="Response 3"
        )
        
        # Test serialization round trip
        json_str = original.to_json()
        reconstructed = MessageResponse.from_json(json_str)
        assert reconstructed == original


class TestChatMessage:
    """Test cases for ChatMessage data class."""

    def test_valid_chat_message(self):
        """Test creating a valid ChatMessage."""
        message = ChatMessage(
            contents="Hello there!",
            is_from_me=True,
            created_at="2023-01-01T12:00:00Z"
        )
        
        assert message.contents == "Hello there!"
        assert message.is_from_me is True
        assert message.created_at == "2023-01-01T12:00:00Z"

    def test_chat_message_validation_success(self):
        """Test successful validation."""
        message = ChatMessage(
            contents="Valid message",
            is_from_me=False,
            created_at="2023-01-01T12:00:00+00:00"
        )
        message.validate()  # Should not raise

    def test_chat_message_validation_empty_contents(self):
        """Test validation with empty contents."""
        message = ChatMessage(
            contents="",
            is_from_me=True,
            created_at="2023-01-01T12:00:00Z"
        )
        
        with pytest.raises(ValueError, match="contents must be a non-empty string"):
            message.validate()

    def test_chat_message_validation_invalid_timestamp(self):
        """Test validation with invalid timestamp."""
        message = ChatMessage(
            contents="Valid message",
            is_from_me=True,
            created_at="invalid-timestamp"
        )
        
        with pytest.raises(ValueError, match="created_at must be a valid ISO8601 timestamp"):
            message.validate()

    def test_chat_message_validation_various_timestamp_formats(self):
        """Test validation with various valid timestamp formats."""
        valid_timestamps = [
            "2023-01-01T12:00:00Z",
            "2023-01-01T12:00:00+00:00",
            "2023-01-01T12:00:00.123456",
            "2023-01-01T12:00:00"
        ]
        
        for timestamp in valid_timestamps:
            message = ChatMessage(
                contents="Test",
                is_from_me=True,
                created_at=timestamp
            )
            message.validate()  # Should not raise


class TestNewMessage:
    """Test cases for NewMessage data class."""

    def test_valid_new_message(self):
        """Test creating a valid NewMessage."""
        message = NewMessage(
            contents="New message content",
            created_at="2023-01-01T12:00:00Z"
        )
        
        assert message.contents == "New message content"
        assert message.created_at == "2023-01-01T12:00:00Z"

    def test_new_message_validation_success(self):
        """Test successful validation."""
        message = NewMessage(
            contents="Valid content",
            created_at="2023-01-01T12:00:00Z"
        )
        message.validate()  # Should not raise

    def test_new_message_validation_empty_contents(self):
        """Test validation with empty contents."""
        message = NewMessage(
            contents="",
            created_at="2023-01-01T12:00:00Z"
        )
        
        with pytest.raises(ValueError, match="contents must be a non-empty string"):
            message.validate()


class TestDatabaseMessage:
    """Test cases for DatabaseMessage data class."""

    def test_valid_database_message(self):
        """Test creating a valid DatabaseMessage."""
        message = DatabaseMessage(
            message_id=123,
            user_id="user-456",
            contents="Database message",
            is_from_me=False,
            created_at="2023-01-01T12:00:00Z",
            message_date="2023-01-01T12:00:00Z",
            chat_id=789
        )
        
        assert message.message_id == 123
        assert message.user_id == "user-456"
        assert message.contents == "Database message"
        assert message.is_from_me is False
        assert message.chat_id == 789

    def test_database_message_validation_success(self):
        """Test successful validation."""
        message = DatabaseMessage(
            message_id=1,
            user_id="valid-user",
            contents="Valid message",
            is_from_me=True,
            created_at="2023-01-01T12:00:00Z",
            message_date="2023-01-01T12:00:00Z",
            chat_id=1
        )
        message.validate()  # Should not raise

    def test_database_message_validation_invalid_message_id(self):
        """Test validation with invalid message_id."""
        message = DatabaseMessage(
            message_id=0,
            user_id="user-456",
            contents="Message",
            is_from_me=True,
            created_at="2023-01-01T12:00:00Z",
            message_date="2023-01-01T12:00:00Z",
            chat_id=1
        )
        
        with pytest.raises(ValueError, match="message_id must be a positive integer"):
            message.validate()

    def test_database_message_to_chat_message(self):
        """Test conversion to ChatMessage."""
        db_message = DatabaseMessage(
            message_id=123,
            user_id="user-456",
            contents="Test content",
            is_from_me=True,
            created_at="2023-01-01T12:00:00Z",
            message_date="2023-01-01T12:00:00Z",
            chat_id=789
        )
        
        chat_message = db_message.to_chat_message()
        
        assert isinstance(chat_message, ChatMessage)
        assert chat_message.contents == "Test content"
        assert chat_message.is_from_me is True
        assert chat_message.created_at == "2023-01-01T12:00:00Z"


class TestLLMPromptData:
    """Test cases for LLMPromptData data class."""

    def test_valid_llm_prompt_data(self):
        """Test creating valid LLMPromptData."""
        chat_history = [
            ChatMessage("Hi", True, "2023-01-01T12:00:00Z"),
            ChatMessage("Hello", False, "2023-01-01T12:01:00Z")
        ]
        new_message = NewMessage("How are you?", "2023-01-01T12:02:00Z")
        
        prompt_data = LLMPromptData(
            system_prompt="You are a helpful assistant",
            user_prompt="Generate responses",
            chat_history=chat_history,
            new_message=new_message
        )
        
        assert prompt_data.system_prompt == "You are a helpful assistant"
        assert prompt_data.user_prompt == "Generate responses"
        assert len(prompt_data.chat_history) == 2
        assert isinstance(prompt_data.new_message, NewMessage)

    def test_llm_prompt_data_validation_success(self):
        """Test successful validation."""
        chat_history = [
            ChatMessage("Test", True, "2023-01-01T12:00:00Z")
        ]
        new_message = NewMessage("New", "2023-01-01T12:01:00Z")
        
        prompt_data = LLMPromptData(
            system_prompt="System",
            user_prompt="User",
            chat_history=chat_history,
            new_message=new_message
        )
        prompt_data.validate()  # Should not raise

    def test_llm_prompt_data_validation_empty_system_prompt(self):
        """Test validation with empty system prompt."""
        prompt_data = LLMPromptData(
            system_prompt="",
            user_prompt="User prompt",
            chat_history=[],
            new_message=NewMessage("Test", "2023-01-01T12:00:00Z")
        )
        
        with pytest.raises(ValueError, match="system_prompt must be a non-empty string"):
            prompt_data.validate()

    def test_llm_prompt_data_get_formatted_history(self):
        """Test get_formatted_history method."""
        chat_history = [
            ChatMessage("Hi there", True, "2023-01-01T12:00:00Z"),
            ChatMessage("Hello back", False, "2023-01-01T12:01:00Z"),
            ChatMessage("How are you?", True, "2023-01-01T12:02:00Z")
        ]
        new_message = NewMessage("I'm good", "2023-01-01T12:03:00Z")
        
        prompt_data = LLMPromptData(
            system_prompt="System",
            user_prompt="User",
            chat_history=chat_history,
            new_message=new_message
        )
        
        formatted = prompt_data.get_formatted_history()
        expected = "You: Hi there\nContact: Hello back\nYou: How are you?"
        assert formatted == expected
        
        # Test with limit
        formatted_limited = prompt_data.get_formatted_history(max_messages=2)
        expected_limited = "Contact: Hello back\nYou: How are you?"
        assert formatted_limited == expected_limited

    def test_llm_prompt_data_serialization(self):
        """Test JSON serialization and deserialization."""
        chat_history = [
            ChatMessage("Test message", True, "2023-01-01T12:00:00Z")
        ]
        new_message = NewMessage("New message", "2023-01-01T12:01:00Z")
        
        original = LLMPromptData(
            system_prompt="System prompt",
            user_prompt="User prompt",
            chat_history=chat_history,
            new_message=new_message
        )
        
        # Test serialization round trip
        json_str = original.to_json()
        reconstructed = LLMPromptData.from_json(json_str)
        
        assert reconstructed.system_prompt == original.system_prompt
        assert reconstructed.user_prompt == original.user_prompt
        assert len(reconstructed.chat_history) == len(original.chat_history)
        assert reconstructed.chat_history[0].contents == original.chat_history[0].contents
        assert reconstructed.new_message.contents == original.new_message.contents


class TestIntegration:
    """Integration tests for data classes working together."""

    def test_full_workflow_integration(self):
        """Test a complete workflow using all data classes."""
        # Create a message request
        request = MessageRequest(
            chat_id=123,
            user_id="user-456",
            contents="How's the weather?"
        )
        request.validate()
        
        # Create chat history
        chat_history = [
            ChatMessage("Hi", True, "2023-01-01T12:00:00Z"),
            ChatMessage("Hello", False, "2023-01-01T12:01:00Z")
        ]
        
        # Create new message
        new_message = NewMessage(
            contents=request.contents,
            created_at="2023-01-01T12:02:00Z"
        )
        
        # Create LLM prompt data
        prompt_data = LLMPromptData(
            system_prompt="You are a helpful assistant",
            user_prompt="Generate three response suggestions",
            chat_history=chat_history,
            new_message=new_message
        )
        prompt_data.validate()
        
        # Create response
        response = MessageResponse(
            response_1="It's sunny today!",
            response_2="The weather is great",
            response_3="Perfect day outside"
        )
        response.validate()
        
        # Verify everything works together
        assert len(response.get_responses()) == 3
        assert prompt_data.get_formatted_history() == "You: Hi\nContact: Hello"

    def test_database_message_to_chat_integration(self):
        """Test converting database messages to chat history."""
        db_messages = [
            DatabaseMessage(
                message_id=1,
                user_id="user-1",
                contents="First message",
                is_from_me=True,
                created_at="2023-01-01T12:00:00Z",
                message_date="2023-01-01T12:00:00Z",
                chat_id=123
            ),
            DatabaseMessage(
                message_id=2,
                user_id="user-2",
                contents="Second message",
                is_from_me=False,
                created_at="2023-01-01T12:01:00Z",
                message_date="2023-01-01T12:01:00Z",
                chat_id=123
            )
        ]
        
        # Convert to chat messages
        chat_messages = [db_msg.to_chat_message() for db_msg in db_messages]
        
        # Verify conversion
        assert len(chat_messages) == 2
        assert all(isinstance(msg, ChatMessage) for msg in chat_messages)
        assert chat_messages[0].contents == "First message"
        assert chat_messages[1].is_from_me is False