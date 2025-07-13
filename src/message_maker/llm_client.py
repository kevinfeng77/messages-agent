"""LLM client for response generation using Anthropic Claude models.

This module implements an LLM client that takes chat history and generates
three response variations using the system and user prompts specified in
the Notion workflow.
"""

import json
import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import asdict

import anthropic

from .types import LLMPromptData, MessageResponse, ChatMessage, NewMessage


# Configure logger
logger = logging.getLogger(__name__)

# Prompt templates from Notion specification
SYSTEM_PROMPT = """You are a replacement of me that generates contextually appropriate chat responses. Given the past chat history with this specific person and a new incoming message, generate exactly three variations of how I might naturally reply. Your goal is to sound like me, reflecting my typical texting style, tone, and pacing with this person. Understand and incorporate the recent topics, emotional tone, and timing of the conversation, especially what I tend to say and how I respond over time (e.g., quick/slow, long/short, serious/playful)."""

USER_PROMPT_TEMPLATE = """Based on the following conversation history and the new message, generate 3 variations of how I might reply naturally. Pay attention to:
- How I usually talk to this person (tone, formatting, emojis, length, punctuation)
- The most recent topic(s) we've discussed
- How much time usually passes between our texts
- Whether this is a continuation, shift, or response to something
- My usual emotional or conversational rhythm with this person

Chat History:
{chat_history}

New Message:
{new_message}

Generate exactly 3 variations in this JSON format:
{{"response_1": "<Natural variation 1>", "response_2": "<Natural variation 2>", "response_3": "<Natural variation 3>"}}"""


class LLMClient:
    """LLM client for generating message response variations using Anthropic Claude."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """Initialize the LLM client.
        
        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Claude model to use for generation.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0 to 1.0).
            
        Raises:
            ValueError: If API key is not provided or found in environment.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Provide via api_key parameter "
                "or ANTHROPIC_API_KEY environment variable."
            )
        
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        logger.info(f"Initialized LLM client with model: {model}")
    
    def format_chat_history(self, chat_history: List[ChatMessage]) -> str:
        """Format chat history for LLM consumption.
        
        Args:
            chat_history: List of chat messages to format.
            
        Returns:
            Formatted chat history string.
        """
        if not chat_history:
            return "(No previous chat history)"
        
        formatted_messages = []
        for msg in chat_history:
            sender = "You" if msg.is_from_me else "Contact"
            # Include timestamp for context
            formatted_messages.append(f"[{msg.created_at}] {sender}: {msg.contents}")
        
        return "\n".join(formatted_messages)
    
    def _parse_json_response(self, response_text: str) -> Dict[str, str]:
        """Parse JSON response from LLM and validate structure.
        
        Args:
            response_text: Raw response text from LLM.
            
        Returns:
            Parsed JSON response with validated structure.
            
        Raises:
            ValueError: If response is not valid JSON or missing required fields.
        """
        try:
            # Try to extract JSON from response text
            # Sometimes the model includes additional text before/after JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["response_1", "response_2", "response_3"]
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field: {field}")
                if not isinstance(parsed[field], str) or not parsed[field].strip():
                    raise ValueError(f"Field {field} must be a non-empty string")
            
            return parsed
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
    
    def generate_responses(self, prompt_data: LLMPromptData) -> MessageResponse:
        """Generate 3 response variations using the LLM.
        
        Args:
            prompt_data: Structured data containing system prompt, user prompt,
                        chat history, and new message.
                        
        Returns:
            MessageResponse containing the 3 generated variations.
            
        Raises:
            ValueError: If prompt data is invalid or API response is malformed.
            anthropic.APIError: If there's an error calling the Anthropic API.
        """
        # Validate input data
        prompt_data.validate()
        
        # Format chat history
        formatted_history = self.format_chat_history(prompt_data.chat_history)
        
        # Construct user prompt with chat history and new message
        user_prompt = USER_PROMPT_TEMPLATE.format(
            chat_history=formatted_history,
            new_message=f"[{prompt_data.new_message.created_at}] Contact: {prompt_data.new_message.contents}"
        )
        
        logger.info(f"Generating responses for new message: {prompt_data.new_message.contents[:50]}...")
        
        try:
            # Call Anthropic API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            
            # Extract response text
            response_text = response.content[0].text
            logger.debug(f"Raw LLM response: {response_text}")
            
            # Parse JSON response
            parsed_response = self._parse_json_response(response_text)
            
            # Create MessageResponse object
            message_response = MessageResponse(
                response_1=parsed_response["response_1"],
                response_2=parsed_response["response_2"],
                response_3=parsed_response["response_3"]
            )
            
            # Validate the response
            message_response.validate()
            
            logger.info("Successfully generated 3 response variations")
            return message_response
            
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating responses: {e}")
            raise ValueError(f"Failed to generate responses: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration.
        
        Returns:
            Dictionary containing model configuration details.
        """
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "provider": "anthropic"
        }