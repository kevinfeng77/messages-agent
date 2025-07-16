"""Conversation detection logic."""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging

from .models import Conversation, ConversationMessage, ConversationBoundary

logger = logging.getLogger(__name__)


class ConversationDetector:
    """Detects conversations from messages using LLM analysis."""
    
    # Default configuration
    DEFAULT_TIME_GAP_HOURS = 48  # 48 hour gap for fallback detection
    DEFAULT_MIN_MESSAGES = 2
    DEFAULT_CHUNK_SIZE = 200
    DEFAULT_OVERLAP_SIZE = 30
    
    def __init__(self, 
                 time_gap_hours: int = DEFAULT_TIME_GAP_HOURS,
                 min_messages: int = DEFAULT_MIN_MESSAGES,
                 chunk_size: int = DEFAULT_CHUNK_SIZE,
                 overlap_size: int = DEFAULT_OVERLAP_SIZE):
        """Initialize the conversation detector.
        
        Args:
            time_gap_hours: Time gap in hours for fallback detection (default: 48 hours)
            min_messages: Minimum messages required to form a conversation
            chunk_size: Number of messages to process in each LLM call
            overlap_size: Number of messages to overlap between chunks
        """
        self.time_gap_hours = time_gap_hours
        self.min_messages = min_messages
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
    
    def detect_conversations(self, 
                           chat_id: int, 
                           messages: List[ConversationMessage],
                           use_llm: bool = True) -> List[Conversation]:
        """Detect conversations from a list of messages.
        
        Args:
            chat_id: The chat ID these messages belong to
            messages: List of messages sorted by created_at
            use_llm: Whether to use LLM for detection (fallback to time-based if False)
            
        Returns:
            List of detected conversations
        """
        if not messages:
            return []
        
        # Sort messages by time to ensure proper ordering
        sorted_messages = sorted(messages, key=lambda m: m.created_at)
        
        if use_llm:
            boundaries = self._detect_boundaries_with_llm(sorted_messages)
        else:
            boundaries = self._detect_boundaries_time_based(sorted_messages)
        
        return self._create_conversations_from_boundaries(chat_id, sorted_messages, boundaries)
    
    def _chunk_messages(self, messages: List[ConversationMessage]) -> List[Tuple[int, List[ConversationMessage]]]:
        """Chunk messages with overlap for LLM processing.
        
        Args:
            messages: List of messages to chunk
            
        Returns:
            List of tuples (start_index, chunk_messages)
        """
        chunks = []
        total_messages = len(messages)
        
        for start_idx in range(0, total_messages, self.chunk_size - self.overlap_size):
            end_idx = min(start_idx + self.chunk_size, total_messages)
            chunk = messages[start_idx:end_idx]
            
            if chunk:
                chunks.append((start_idx, chunk))
            
            # If we've processed all messages, stop
            if end_idx >= total_messages:
                break
        
        return chunks
    
    def _create_detection_prompt(self, messages: List[ConversationMessage]) -> str:
        """Create the LLM prompt for conversation boundary detection.
        
        Args:
            messages: List of messages to analyze
            
        Returns:
            The formatted prompt string
        """
        # Format messages for the prompt
        formatted_messages = []
        for i, msg in enumerate(messages):
            sender = "Me" if msg.is_from_me else f"Contact ({msg.user_id})"
            time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            formatted_messages.append(f"[{i}] {time_str} - {sender}: {msg.contents}")
        
        messages_text = "\n".join(formatted_messages)
        
        prompt = f"""You are an expert at analyzing message conversations and identifying natural conversation boundaries based on conversational patterns and context.

Your task is to identify where conversations end and new ones begin by analyzing the CONTENT and PATTERNS in the message history.

Focus on these text-based indicators for conversation boundaries:
1. **Greeting/Closing patterns**: New greetings (hey, hi, hello) or closings (bye, talk later, goodnight) often mark boundaries
2. **Topic changes**: Complete shifts in subject matter or context
3. **Conversational completeness**: When a discussion reaches its natural conclusion
4. **Context resets**: When messages start fresh without referencing previous discussion
5. **Question-answer completion**: When a query has been fully addressed

The messages include timestamps as metadata, but focus primarily on the conversational flow and text patterns.

Here are the messages to analyze:

{messages_text}

Analyze these messages and identify conversation boundaries based on the TEXT PATTERNS and CONVERSATIONAL FLOW. For each boundary you identify, provide:
1. The index of the last message in the conversation (the message BEFORE the boundary)
2. A brief reason explaining the conversational pattern that indicates a boundary
3. Your confidence level (0.0 to 1.0)

Return your response as a JSON array of boundaries. If there are no clear boundaries (all messages are one conversation), return an empty array.

Example response format:
[
  {{
    "after_message_index": 5,
    "reason": "Conversation about dinner plans concluded with confirmation, next message starts new topic about work project",
    "confidence": 0.9
  }},
  {{
    "after_message_index": 12,
    "reason": "Natural ending with 'goodnight' followed by new greeting 'hey' without reference to previous discussion",
    "confidence": 0.95
  }}
]

Remember:
- Message indices start at 0
- Each boundary represents the END of a conversation (the index is the last message OF that conversation)
- Focus on conversational patterns, not just time gaps
- Look for natural conversation flows and completeness
- Be conservative - only mark boundaries where the conversational context clearly shifts"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> List[ConversationBoundary]:
        """Parse the LLM response to extract conversation boundaries.
        
        Args:
            response: The LLM's response text
            
        Returns:
            List of conversation boundaries
        """
        try:
            # Extract JSON from response
            # Handle case where LLM might include extra text
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON array found in LLM response")
                return []
            
            json_str = response[json_start:json_end]
            boundaries_data = json.loads(json_str)
            
            boundaries = []
            for boundary_data in boundaries_data:
                boundary = ConversationBoundary(
                    after_message_index=boundary_data["after_message_index"],
                    reason=boundary_data["reason"],
                    confidence=float(boundary_data.get("confidence", 0.8))
                )
                boundaries.append(boundary)
            
            # Sort by message index
            boundaries.sort(key=lambda b: b.after_message_index)
            
            return boundaries
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []
    
    def _detect_boundaries_with_llm(self, messages: List[ConversationMessage]) -> List[ConversationBoundary]:
        """Detect conversation boundaries using LLM analysis.
        
        Args:
            messages: List of messages to analyze
            
        Returns:
            List of detected boundaries
        """
        # This is a placeholder - actual LLM integration will be done when testing
        # For now, return empty list (would call LLM API here)
        logger.info(f"LLM detection requested for {len(messages)} messages")
        
        # TODO: Integrate with llm_client.py when implementing full solution
        # chunks = self._chunk_messages(messages)
        # all_boundaries = []
        # for start_idx, chunk in chunks:
        #     prompt = self._create_detection_prompt(chunk)
        #     response = llm_client.generate(prompt)
        #     boundaries = self._parse_llm_response(response)
        #     # Adjust indices based on chunk position
        #     for boundary in boundaries:
        #         boundary.after_message_index += start_idx
        #     all_boundaries.extend(boundaries)
        
        return []
    
    def _detect_boundaries_time_based(self, messages: List[ConversationMessage]) -> List[ConversationBoundary]:
        """Fallback time-based boundary detection using 48-hour gaps.
        
        Args:
            messages: List of messages to analyze
            
        Returns:
            List of detected boundaries based on time gaps
        """
        boundaries = []
        
        for i in range(1, len(messages)):
            prev_msg = messages[i - 1]
            curr_msg = messages[i]
            
            time_gap_hours = (curr_msg.created_at - prev_msg.created_at).total_seconds() / 3600
            
            if time_gap_hours >= self.time_gap_hours:
                boundary = ConversationBoundary(
                    after_message_index=i - 1,
                    reason=f"Time gap of {time_gap_hours:.0f} hours",
                    confidence=0.7  # Lower confidence for time-based detection
                )
                boundaries.append(boundary)
        
        return boundaries
    
    def _create_conversations_from_boundaries(self,
                                            chat_id: int,
                                            messages: List[ConversationMessage],
                                            boundaries: List[ConversationBoundary]) -> List[Conversation]:
        """Create conversation objects from messages and boundaries.
        
        Args:
            chat_id: The chat ID
            messages: All messages
            boundaries: Detected conversation boundaries
            
        Returns:
            List of conversation objects
        """
        conversations = []
        start_idx = 0
        
        # Add boundaries for the beginning and end if needed
        boundary_indices = [b.after_message_index for b in boundaries]
        boundary_indices.append(len(messages) - 1)  # Last message
        
        for end_idx in boundary_indices:
            if end_idx < start_idx:
                continue
                
            conv_messages = messages[start_idx:end_idx + 1]
            
            if len(conv_messages) >= self.min_messages:
                conversation = Conversation(
                    conversation_id=None,  # Will be assigned when saved
                    chat_id=chat_id,
                    start_message_id=conv_messages[0].message_id,
                    end_message_id=conv_messages[-1].message_id,
                    message_count=len(conv_messages),
                    start_time=conv_messages[0].created_at,
                    end_time=conv_messages[-1].created_at,
                    title=None,  # Can be generated later
                    messages=conv_messages
                )
                conversations.append(conversation)
            
            start_idx = end_idx + 1
        
        return conversations