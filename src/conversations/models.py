"""Data models for the conversations service."""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class ConversationMessage:
    """Represents a single message within a conversation."""
    pass


@dataclass
class Conversation:
    """Represents a conversation detected from messages."""
    pass


@dataclass
class EmbeddingData:
    """Represents embedding data for semantic search."""
    pass