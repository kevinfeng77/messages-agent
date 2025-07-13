"""Main API function for message response generation.

This module implements the core orchestration function that coordinates the entire
message response generation workflow as specified in SERENE-59.
"""

import logging
from typing import Optional

from .types import MessageRequest, MessageResponse, NewMessage, LLMPromptData
from .chat_history import get_chat_history_for_message_generation
from .llm_client import LLMClient
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class MessageMakerService:
    """Service class for orchestrating message response generation."""
    
    def __init__(self, db_path: str = "./data/messages.db"):
        """Initialize the service with database path and LLM client.
        
        Args:
            db_path: Path to the SQLite messages database
        """
        self.db_path = db_path
        self.llm_client = LLMClient()
        self.logger = get_logger(__name__)

    def generate_message_responses(self, request: MessageRequest) -> MessageResponse:
        """Generate three response variations for a new message.
        
        Args:
            request: MessageRequest with chat_id, user_id, contents
            
        Returns:
            MessageResponse with response_1, response_2, response_3
            
        Raises:
            ValueError: If input validation fails or chat_id doesn't exist
            Exception: If database or LLM API errors occur
        """
        self.logger.info(f"Generating responses for chat_id={request.chat_id}, user_id={request.user_id}")
        
        # 1. Validate Input
        try:
            request.validate()
        except ValueError as e:
            self.logger.error(f"Input validation failed: {e}")
            raise
        
        # 2. Retrieve Chat History
        try:
            chat_history = get_chat_history_for_message_generation(
                chat_id=str(request.chat_id),
                user_id=request.user_id
            )
            self.logger.info(f"Retrieved {len(chat_history)} messages from chat history")
        except Exception as e:
            self.logger.error(f"Failed to retrieve chat history: {e}")
            raise Exception(f"Database error: {e}")
        
        # 3. Prepare LLM Prompt
        new_message = NewMessage(
            content=request.contents,
            timestamp=None  # Not required for response generation
        )
        
        prompt_data = LLMPromptData(
            system_prompt="",  # Will be set by LLM client
            user_prompt="",    # Will be set by LLM client  
            chat_history=chat_history,
            new_message=new_message
        )
        
        # 4. Generate Responses
        try:
            response = self.llm_client.generate_responses(prompt_data)
            self.logger.info("Successfully generated LLM responses")
            return response
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            raise Exception(f"LLM API error: {e}")


def generate_message_responses(request: MessageRequest) -> MessageResponse:
    """Generate three response variations for a new message.
    
    This is the main API function that orchestrates the entire message response
    generation workflow as specified in the Notion documentation.
    
    Args:
        request: MessageRequest with chat_id, user_id, contents
        
    Returns:
        MessageResponse with response_1, response_2, response_3
        
    Raises:
        ValueError: If input validation fails
        Exception: If database connection or LLM API errors occur
    """
    service = MessageMakerService()
    return service.generate_message_responses(request)