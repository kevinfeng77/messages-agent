"""Unit tests for LLM client functionality."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import anthropic

from src.message_maker.llm_client import LLMClient, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.message_maker.types import LLMPromptData, MessageResponse, ChatMessage, NewMessage


class TestLLMClient:
    """Test cases for LLMClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"
        self.sample_chat_history = [
            ChatMessage(
                contents="Hey, how's it going?",
                is_from_me=True,
                created_at="2023-01-01T10:00:00Z"
            ),
            ChatMessage(
                contents="Pretty good! Just working on some projects.",
                is_from_me=False,
                created_at="2023-01-01T10:05:00Z"
            ),
            ChatMessage(
                contents="Nice! What kind of projects?",
                is_from_me=True,
                created_at="2023-01-01T10:06:00Z"
            )
        ]
        self.sample_new_message = NewMessage(
            contents="I'm building a messaging AI assistant",
            created_at="2023-01-01T10:10:00Z"
        )
        self.sample_prompt_data = LLMPromptData(
            system_prompt=SYSTEM_PROMPT,
            user_prompt="test prompt",
            chat_history=self.sample_chat_history,
            new_message=self.sample_new_message
        )
    
    def test_init_with_api_key(self):
        """Test client initialization with provided API key."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic') as mock_anthropic:
            client = LLMClient(api_key=self.api_key)
            assert client.api_key == self.api_key
            assert client.model == "claude-3-5-sonnet-20241022"
            mock_anthropic.assert_called_once_with(api_key=self.api_key)
    
    def test_init_with_env_var(self):
        """Test client initialization with API key from environment."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': self.api_key}):
            with patch('src.message_maker.llm_client.anthropic.Anthropic') as mock_anthropic:
                client = LLMClient()
                assert client.api_key == self.api_key
                mock_anthropic.assert_called_once_with(api_key=self.api_key)
    
    def test_init_without_api_key(self):
        """Test client initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key required"):
                LLMClient()
    
    def test_init_with_custom_params(self):
        """Test client initialization with custom parameters."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(
                api_key=self.api_key,
                model="claude-3-opus-20240229",
                max_tokens=2000,
                temperature=0.5
            )
            assert client.model == "claude-3-opus-20240229"
            assert client.max_tokens == 2000
            assert client.temperature == 0.5
    
    def test_format_chat_history_empty(self):
        """Test formatting empty chat history."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            result = client.format_chat_history([])
            assert result == "(No previous chat history)"
    
    def test_format_chat_history_with_messages(self):
        """Test formatting chat history with messages."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            result = client.format_chat_history(self.sample_chat_history)
            
            expected_lines = [
                "[2023-01-01T10:00:00Z] You: Hey, how's it going?",
                "[2023-01-01T10:05:00Z] Contact: Pretty good! Just working on some projects.",
                "[2023-01-01T10:06:00Z] You: Nice! What kind of projects?"
            ]
            assert result == "\n".join(expected_lines)
    
    def test_parse_json_response_valid(self):
        """Test parsing valid JSON response."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            
            response_text = '''{"response_1": "That's awesome!", "response_2": "Cool project!", "response_3": "Sounds interesting!"}'''
            result = client._parse_json_response(response_text)
            
            assert result["response_1"] == "That's awesome!"
            assert result["response_2"] == "Cool project!"
            assert result["response_3"] == "Sounds interesting!"
    
    def test_parse_json_response_with_extra_text(self):
        """Test parsing JSON response with extra text around it."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            
            response_text = '''Here are the responses:
            {"response_1": "That's awesome!", "response_2": "Cool project!", "response_3": "Sounds interesting!"}
            Hope this helps!'''
            result = client._parse_json_response(response_text)
            
            assert result["response_1"] == "That's awesome!"
            assert result["response_2"] == "Cool project!"
            assert result["response_3"] == "Sounds interesting!"
    
    def test_parse_json_response_invalid_json(self):
        """Test parsing invalid JSON response."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            
            response_text = '''{"response_1": "That's awesome!", "response_2": "Cool project"'''
            with pytest.raises(ValueError, match="No JSON object found in response"):
                client._parse_json_response(response_text)
    
    def test_parse_json_response_missing_fields(self):
        """Test parsing JSON response with missing required fields."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            
            response_text = '''{"response_1": "That's awesome!", "response_2": "Cool project!"}'''
            with pytest.raises(ValueError, match="Missing required field: response_3"):
                client._parse_json_response(response_text)
    
    def test_parse_json_response_empty_fields(self):
        """Test parsing JSON response with empty fields."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            
            response_text = '''{"response_1": "", "response_2": "Cool project!", "response_3": "Sounds interesting!"}'''
            with pytest.raises(ValueError, match="Field response_1 must be a non-empty string"):
                client._parse_json_response(response_text)
    
    def test_parse_json_response_no_json(self):
        """Test parsing response with no JSON object."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            
            response_text = '''This is just plain text with no JSON'''
            with pytest.raises(ValueError, match="No JSON object found in response"):
                client._parse_json_response(response_text)
    
    @patch('src.message_maker.llm_client.anthropic.Anthropic')
    def test_generate_responses_success(self, mock_anthropic_class):
        """Test successful response generation."""
        # Mock the API response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '''{"response_1": "That sounds really cool!", "response_2": "Nice work on the AI project!", "response_3": "I'd love to hear more about it!"}'''
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        client = LLMClient(api_key=self.api_key)
        result = client.generate_responses(self.sample_prompt_data)
        
        # Verify the result
        assert isinstance(result, MessageResponse)
        assert result.response_1 == "That sounds really cool!"
        assert result.response_2 == "Nice work on the AI project!"
        assert result.response_3 == "I'd love to hear more about it!"
        
        # Verify API call
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert call_args[1]['model'] == "claude-3-5-sonnet-20241022"
        assert call_args[1]['system'] == SYSTEM_PROMPT
        assert len(call_args[1]['messages']) == 1
        assert call_args[1]['messages'][0]['role'] == "user"
    
    @patch('src.message_maker.llm_client.anthropic.Anthropic')
    def test_generate_responses_api_error(self, mock_anthropic_class):
        """Test handling of Anthropic API errors."""
        mock_client = Mock()
        # Use a generic exception to test error handling
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic_class.return_value = mock_client
        
        client = LLMClient(api_key=self.api_key)
        
        with pytest.raises(ValueError, match="Failed to generate responses"):
            client.generate_responses(self.sample_prompt_data)
    
    @patch('src.message_maker.llm_client.anthropic.Anthropic')
    def test_generate_responses_invalid_json(self, mock_anthropic_class):
        """Test handling of invalid JSON response from API."""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "This is not valid JSON"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        client = LLMClient(api_key=self.api_key)
        
        with pytest.raises(ValueError, match="Failed to generate responses"):
            client.generate_responses(self.sample_prompt_data)
    
    def test_generate_responses_invalid_prompt_data(self):
        """Test handling of invalid prompt data."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(api_key=self.api_key)
            
            # Create invalid prompt data (missing required fields)
            invalid_prompt_data = LLMPromptData(
                system_prompt="",  # Empty system prompt (invalid)
                user_prompt="test",
                chat_history=[],
                new_message=self.sample_new_message
            )
            
            with pytest.raises(ValueError):
                client.generate_responses(invalid_prompt_data)
    
    def test_get_model_info(self):
        """Test getting model configuration information."""
        with patch('src.message_maker.llm_client.anthropic.Anthropic'):
            client = LLMClient(
                api_key=self.api_key,
                model="claude-3-opus-20240229",
                max_tokens=2000,
                temperature=0.5
            )
            
            info = client.get_model_info()
            
            assert info["model"] == "claude-3-opus-20240229"
            assert info["max_tokens"] == 2000
            assert info["temperature"] == 0.5
            assert info["provider"] == "anthropic"


class TestLLMClientIntegration:
    """Integration-style tests for LLMClient."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"
    
    @patch('src.message_maker.llm_client.anthropic.Anthropic')
    def test_end_to_end_response_generation(self, mock_anthropic_class):
        """Test complete end-to-end response generation flow."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '''
        Here are three natural response variations:
        {"response_1": "That's so cool! AI assistants are the future.", "response_2": "Wow, that sounds like an amazing project!", "response_3": "I'd love to try it out when it's ready!"}
        '''
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        # Create client and test data
        client = LLMClient(api_key=self.api_key)
        
        chat_history = [
            ChatMessage("Hey!", True, "2023-01-01T10:00:00Z"),
            ChatMessage("Hi there!", False, "2023-01-01T10:01:00Z")
        ]
        new_message = NewMessage("Working on an AI project", "2023-01-01T10:02:00Z")
        prompt_data = LLMPromptData(
            system_prompt=SYSTEM_PROMPT,
            user_prompt="test",
            chat_history=chat_history,
            new_message=new_message
        )
        
        # Generate responses
        result = client.generate_responses(prompt_data)
        
        # Verify results
        assert isinstance(result, MessageResponse)
        assert "AI assistants" in result.response_1
        assert "amazing project" in result.response_2
        assert "try it out" in result.response_3
        
        # Verify API was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['system'] == SYSTEM_PROMPT
        assert "Working on an AI project" in call_kwargs['messages'][0]['content']
        assert "Hey!" in call_kwargs['messages'][0]['content']


if __name__ == "__main__":
    pytest.main([__file__])