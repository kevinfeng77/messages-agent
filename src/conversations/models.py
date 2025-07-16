"""Data models for the conversations service."""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class ConversationMessage:
    """Represents a single message within a conversation."""
    message_id: int
    user_id: str
    contents: str
    is_from_me: bool
    created_at: datetime
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "message_id": self.message_id,
            "user_id": self.user_id,
            "contents": self.contents,
            "is_from_me": self.is_from_me,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ConversationBoundary:
    """Represents a boundary between conversations."""
    after_message_index: int  # Index of last message in previous conversation
    reason: str  # Why this boundary was detected (topic change, time gap, etc.)
    confidence: float  # 0.0 to 1.0


@dataclass
class Conversation:
    """Represents a conversation detected from messages."""
    conversation_id: Optional[int]  # None until saved to DB
    chat_id: int
    start_message_id: int
    end_message_id: int
    message_count: int
    start_time: datetime
    end_time: datetime
    title: Optional[str]  # Generated title/summary
    messages: List[ConversationMessage]
    
    def duration_minutes(self) -> float:
        """Calculate conversation duration in minutes."""
        return (self.end_time - self.start_time).total_seconds() / 60


@dataclass
class EmbeddingData:
    """Represents embedding data for semantic search."""
    pass