"""Data classes and types for the Message Maker service.

This module defines the core data structures used throughout the Message Maker
service for handling messages, conversations, AI responses, and API interactions.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


@dataclass
class MessageRequest:
    """Request model for message generation."""
    chat_id: int
    user_id: str
    contents: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageRequest":
        """Create instance from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "MessageRequest":
        """Create instance from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def validate(self) -> None:
        """Validate request data integrity."""
        if not isinstance(self.chat_id, int) or self.chat_id <= 0:
            raise ValueError("chat_id must be a positive integer")
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string")
        if not self.contents or not isinstance(self.contents, str):
            raise ValueError("contents must be a non-empty string")


@dataclass
class MessageResponse:
    """Response model containing generated message suggestions."""
    response_1: str
    response_2: str
    response_3: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageResponse":
        """Create instance from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "MessageResponse":
        """Create instance from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def validate(self) -> None:
        """Validate response data integrity."""
        responses = [self.response_1, self.response_2, self.response_3]
        for i, response in enumerate(responses, 1):
            if not response or not isinstance(response, str):
                raise ValueError(f"response_{i} must be a non-empty string")

    def get_responses(self) -> List[str]:
        """Get all responses as a list."""
        return [self.response_1, self.response_2, self.response_3]


@dataclass
class ChatMessage:
    """Represents a message in chat history."""
    contents: str
    is_from_me: bool
    created_at: str  # ISO8601 timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create instance from dictionary."""
        return cls(**data)

    def validate(self) -> None:
        """Validate chat message data integrity."""
        if not self.contents or not isinstance(self.contents, str):
            raise ValueError("contents must be a non-empty string")
        if not isinstance(self.is_from_me, bool):
            raise ValueError("is_from_me must be a boolean")
        if not self.created_at or not isinstance(self.created_at, str):
            raise ValueError("created_at must be a non-empty string")
        
        # Validate ISO8601 format
        try:
            datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("created_at must be a valid ISO8601 timestamp")


@dataclass
class NewMessage:
    """Represents a new incoming message."""
    contents: str
    created_at: str  # ISO8601 timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewMessage":
        """Create instance from dictionary."""
        return cls(**data)

    def validate(self) -> None:
        """Validate new message data integrity."""
        if not self.contents or not isinstance(self.contents, str):
            raise ValueError("contents must be a non-empty string")
        if not self.created_at or not isinstance(self.created_at, str):
            raise ValueError("created_at must be a non-empty string")
        
        # Validate ISO8601 format
        try:
            datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("created_at must be a valid ISO8601 timestamp")


@dataclass
class DatabaseMessage:
    """Database query result model for messages with chat context."""
    message_id: int
    user_id: str
    contents: str
    is_from_me: bool
    created_at: str
    message_date: str  # from chat_messages join
    chat_id: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseMessage":
        """Create instance from dictionary."""
        return cls(**data)

    def validate(self) -> None:
        """Validate database message data integrity."""
        if not isinstance(self.message_id, int) or self.message_id <= 0:
            raise ValueError("message_id must be a positive integer")
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string")
        if not self.contents or not isinstance(self.contents, str):
            raise ValueError("contents must be a non-empty string")
        if not isinstance(self.is_from_me, bool):
            raise ValueError("is_from_me must be a boolean")
        if not isinstance(self.chat_id, int) or self.chat_id <= 0:
            raise ValueError("chat_id must be a positive integer")
        
        # Validate timestamp formats
        for field_name, timestamp in [("created_at", self.created_at), ("message_date", self.message_date)]:
            if not timestamp or not isinstance(timestamp, str):
                raise ValueError(f"{field_name} must be a non-empty string")

    def to_chat_message(self) -> ChatMessage:
        """Convert to ChatMessage for use in chat history."""
        return ChatMessage(
            contents=self.contents,
            is_from_me=self.is_from_me,
            created_at=self.created_at
        )


@dataclass
class LLMPromptData:
    """Data structure for LLM prompt generation."""
    system_prompt: str
    user_prompt: str
    chat_history: List[ChatMessage]
    new_message: NewMessage

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "chat_history": [msg.to_dict() for msg in self.chat_history],
            "new_message": self.new_message.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMPromptData":
        """Create instance from dictionary."""
        return cls(
            system_prompt=data["system_prompt"],
            user_prompt=data["user_prompt"],
            chat_history=[ChatMessage.from_dict(msg) for msg in data["chat_history"]],
            new_message=NewMessage.from_dict(data["new_message"])
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "LLMPromptData":
        """Create instance from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def validate(self) -> None:
        """Validate LLM prompt data integrity."""
        if not self.system_prompt or not isinstance(self.system_prompt, str):
            raise ValueError("system_prompt must be a non-empty string")
        if not self.user_prompt or not isinstance(self.user_prompt, str):
            raise ValueError("user_prompt must be a non-empty string")
        if not isinstance(self.chat_history, list):
            raise ValueError("chat_history must be a list")
        
        # Validate each chat message
        for i, msg in enumerate(self.chat_history):
            if not isinstance(msg, ChatMessage):
                raise ValueError(f"chat_history[{i}] must be a ChatMessage instance")
            msg.validate()
        
        # Validate new message
        if not isinstance(self.new_message, NewMessage):
            raise ValueError("new_message must be a NewMessage instance")
        self.new_message.validate()

    def get_formatted_history(self, max_messages: Optional[int] = None) -> str:
        """Get formatted chat history for prompt construction."""
        messages = self.chat_history
        if max_messages:
            messages = messages[-max_messages:]
        
        formatted = []
        for msg in messages:
            sender = "You" if msg.is_from_me else "Contact"
            formatted.append(f"{sender}: {msg.contents}")
        
        return "\n".join(formatted)