"""Tests for conversation detection logic."""
import pytest
from datetime import datetime, timedelta
import json

from ..detector import ConversationDetector
from ..models import Conversation, ConversationMessage, ConversationBoundary


class TestConversationDetector:
    """Test cases for ConversationDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create a ConversationDetector instance."""
        return ConversationDetector()
    
    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        messages = [
            # First conversation - greeting and planning
            ConversationMessage(
                message_id=1,
                user_id="user1",
                contents="Hey! How are you doing?",
                is_from_me=True,
                created_at=base_time
            ),
            ConversationMessage(
                message_id=2,
                user_id="user1",
                contents="I'm good! Just working on some code",
                is_from_me=False,
                created_at=base_time + timedelta(minutes=1)
            ),
            ConversationMessage(
                message_id=3,
                user_id="user1",
                contents="Want to grab lunch today?",
                is_from_me=True,
                created_at=base_time + timedelta(minutes=2)
            ),
            ConversationMessage(
                message_id=4,
                user_id="user1",
                contents="Sure! How about noon?",
                is_from_me=False,
                created_at=base_time + timedelta(minutes=3)
            ),
            ConversationMessage(
                message_id=5,
                user_id="user1",
                contents="Perfect, see you then!",
                is_from_me=True,
                created_at=base_time + timedelta(minutes=4)
            ),
            
            # Gap of 3 days - new conversation
            ConversationMessage(
                message_id=6,
                user_id="user1",
                contents="Hi! Did you see the game last night?",
                is_from_me=False,
                created_at=base_time + timedelta(days=3)
            ),
            ConversationMessage(
                message_id=7,
                user_id="user1",
                contents="No, I missed it. Was it good?",
                is_from_me=True,
                created_at=base_time + timedelta(days=3, minutes=1)
            ),
            ConversationMessage(
                message_id=8,
                user_id="user1",
                contents="Amazing! Best game of the season",
                is_from_me=False,
                created_at=base_time + timedelta(days=3, minutes=2)
            ),
        ]
        
        return messages
    
    def test_init(self, detector):
        """Test detector initialization."""
        assert detector.time_gap_hours == 48
        assert detector.min_messages == 2
        assert detector.chunk_size == 200
        assert detector.overlap_size == 30
    
    def test_custom_init(self):
        """Test detector with custom parameters."""
        detector = ConversationDetector(
            time_gap_hours=24,
            min_messages=3,
            chunk_size=100,
            overlap_size=20
        )
        assert detector.time_gap_hours == 24
        assert detector.min_messages == 3
        assert detector.chunk_size == 100
        assert detector.overlap_size == 20
    
    def test_chunk_messages(self, detector):
        """Test message chunking with overlap."""
        # Create 500 messages
        messages = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        for i in range(500):
            messages.append(ConversationMessage(
                message_id=i,
                user_id="user1",
                contents=f"Message {i}",
                is_from_me=i % 2 == 0,
                created_at=base_time + timedelta(minutes=i)
            ))
        
        chunks = detector._chunk_messages(messages)
        
        # With chunk_size=200 and overlap=30, we expect specific chunks
        assert len(chunks) == 3
        
        # First chunk: 0-199 (200 messages)
        assert chunks[0][0] == 0
        assert len(chunks[0][1]) == 200
        
        # Second chunk: 170-369 (200 messages, with 30 overlap)
        assert chunks[1][0] == 170
        assert len(chunks[1][1]) == 200
        
        # Third chunk: 340-499 (160 messages)
        assert chunks[2][0] == 340
        assert len(chunks[2][1]) == 160
    
    def test_chunk_messages_small_list(self, detector, sample_messages):
        """Test chunking with fewer messages than chunk size."""
        chunks = detector._chunk_messages(sample_messages)
        
        assert len(chunks) == 1
        assert chunks[0][0] == 0
        assert len(chunks[0][1]) == len(sample_messages)
    
    def test_create_detection_prompt(self, detector, sample_messages):
        """Test prompt generation."""
        prompt = detector._create_detection_prompt(sample_messages)
        
        # Check prompt contains key elements
        assert "conversation boundaries" in prompt
        assert "Greeting/Closing patterns" in prompt
        assert "Topic changes" in prompt
        assert "Conversational completeness" in prompt
        
        # Check messages are formatted correctly
        assert "[0] 2024-01-01 10:00:00 - Me: Hey! How are you doing?" in prompt
        assert "[7] 2024-01-04 10:02:00 - Contact (user1): Amazing! Best game of the season" in prompt
        
        # Check JSON format example is included
        assert '"after_message_index"' in prompt
        assert '"reason"' in prompt
        assert '"confidence"' in prompt
    
    def test_parse_llm_response_valid(self, detector):
        """Test parsing valid LLM response."""
        response = """
        Based on the analysis, I found the following boundaries:
        
        [
          {
            "after_message_index": 4,
            "reason": "Conversation about lunch plans concluded, followed by 3-day gap and new topic",
            "confidence": 0.95
          }
        ]
        """
        
        boundaries = detector._parse_llm_response(response)
        
        assert len(boundaries) == 1
        assert boundaries[0].after_message_index == 4
        assert "lunch plans concluded" in boundaries[0].reason
        assert boundaries[0].confidence == 0.95
    
    def test_parse_llm_response_multiple(self, detector):
        """Test parsing multiple boundaries."""
        response = """[
          {
            "after_message_index": 4,
            "reason": "First conversation ended",
            "confidence": 0.9
          },
          {
            "after_message_index": 10,
            "reason": "Second conversation ended",
            "confidence": 0.8
          }
        ]"""
        
        boundaries = detector._parse_llm_response(response)
        
        assert len(boundaries) == 2
        assert boundaries[0].after_message_index == 4
        assert boundaries[1].after_message_index == 10
    
    def test_parse_llm_response_empty(self, detector):
        """Test parsing empty boundary list."""
        response = "No clear boundaries found. []"
        
        boundaries = detector._parse_llm_response(response)
        assert len(boundaries) == 0
    
    def test_parse_llm_response_invalid(self, detector):
        """Test parsing invalid response."""
        response = "This is not valid JSON"
        
        boundaries = detector._parse_llm_response(response)
        assert len(boundaries) == 0
    
    def test_detect_boundaries_time_based(self, detector, sample_messages):
        """Test time-based boundary detection."""
        boundaries = detector._detect_boundaries_time_based(sample_messages)
        
        # Should detect boundary between message 4 and 5 (3 day gap)
        assert len(boundaries) == 1
        assert boundaries[0].after_message_index == 4
        assert "72 hours" in boundaries[0].reason
        assert boundaries[0].confidence == 0.7
    
    def test_detect_boundaries_time_based_no_gaps(self, detector):
        """Test time-based detection with no significant gaps."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        messages = []
        
        # Messages every 30 minutes for 10 messages
        for i in range(10):
            messages.append(ConversationMessage(
                message_id=i,
                user_id="user1",
                contents=f"Message {i}",
                is_from_me=i % 2 == 0,
                created_at=base_time + timedelta(minutes=i * 30)
            ))
        
        boundaries = detector._detect_boundaries_time_based(messages)
        assert len(boundaries) == 0
    
    def test_create_conversations_from_boundaries(self, detector, sample_messages):
        """Test creating conversations from boundaries."""
        boundaries = [
            ConversationBoundary(
                after_message_index=4,
                reason="Test boundary",
                confidence=0.9
            )
        ]
        
        conversations = detector._create_conversations_from_boundaries(
            chat_id=123,
            messages=sample_messages,
            boundaries=boundaries
        )
        
        assert len(conversations) == 2
        
        # First conversation
        conv1 = conversations[0]
        assert conv1.chat_id == 123
        assert conv1.start_message_id == 1
        assert conv1.end_message_id == 5
        assert conv1.message_count == 5
        assert len(conv1.messages) == 5
        
        # Second conversation
        conv2 = conversations[1]
        assert conv2.chat_id == 123
        assert conv2.start_message_id == 6
        assert conv2.end_message_id == 8
        assert conv2.message_count == 3
        assert len(conv2.messages) == 3
    
    def test_create_conversations_min_messages(self, detector):
        """Test minimum message requirement."""
        detector.min_messages = 3
        
        messages = [
            ConversationMessage(
                message_id=i,
                user_id="user1",
                contents=f"Message {i}",
                is_from_me=True,
                created_at=datetime(2024, 1, 1) + timedelta(hours=i)
            )
            for i in range(5)
        ]
        
        # Boundary after message 1 (only 2 messages in first conversation)
        boundaries = [
            ConversationBoundary(after_message_index=1, reason="Test", confidence=0.8)
        ]
        
        conversations = detector._create_conversations_from_boundaries(
            chat_id=123,
            messages=messages,
            boundaries=boundaries
        )
        
        # First conversation has only 2 messages, should be excluded
        assert len(conversations) == 1
        assert conversations[0].start_message_id == 2
        assert conversations[0].message_count == 3
    
    def test_detect_conversations_integration(self, detector, sample_messages):
        """Test full conversation detection flow."""
        conversations = detector.detect_conversations(
            chat_id=123,
            messages=sample_messages,
            use_llm=False  # Use time-based for predictable test
        )
        
        assert len(conversations) == 2
        assert conversations[0].message_count == 5
        assert conversations[1].message_count == 3
        assert conversations[0].duration_minutes() == 4.0
    
    def test_detect_conversations_empty(self, detector):
        """Test detection with empty message list."""
        conversations = detector.detect_conversations(
            chat_id=123,
            messages=[],
            use_llm=False
        )
        
        assert len(conversations) == 0
    
    def test_conversation_duration(self):
        """Test conversation duration calculation."""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 30, 0)
        
        conversation = Conversation(
            conversation_id=None,
            chat_id=123,
            start_message_id=1,
            end_message_id=5,
            message_count=5,
            start_time=start_time,
            end_time=end_time,
            title=None,
            messages=[]
        )
        
        assert conversation.duration_minutes() == 30.0