"""Conversation Context Analyzer - Analyzes message threads for context and patterns"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.database.manager import DatabaseManager
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationContext:
    """Represents the context of a conversation thread"""
    
    handle_id: int
    recent_messages: List[Dict[str, Any]]
    conversation_length: int
    last_message_time: Optional[datetime]
    user_last_spoke: bool
    contact_last_spoke: bool
    time_since_last_message: Optional[timedelta]
    conversation_tone: str = "neutral"
    topic_keywords: List[str] = None
    
    def __post_init__(self):
        if self.topic_keywords is None:
            self.topic_keywords = []


class ConversationAnalyzer:
    """Analyzes conversation context from message threads"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager()
        
    def get_conversation_context(
        self, 
        handle_id: int, 
        limit: int = 20
    ) -> Optional[ConversationContext]:
        """
        Get conversation context for a specific contact
        
        Args:
            handle_id: Contact handle ID from messages database
            limit: Number of recent messages to analyze
            
        Returns:
            ConversationContext object or None if no conversation found
        """
        if not self.db_manager.copy_db_path.exists():
            logger.error("Database copy does not exist")
            return None
            
        try:
            conn = sqlite3.connect(str(self.db_manager.copy_db_path))
            cursor = conn.cursor()
            
            # Get recent messages for this contact
            query = """
                SELECT 
                    ROWID,
                    guid,
                    text,
                    attributedBody,
                    handle_id,
                    date,
                    date_read,
                    is_from_me,
                    service
                FROM message 
                WHERE handle_id = ?
                ORDER BY date DESC 
                LIMIT ?
            """
            
            cursor.execute(query, (handle_id, limit))
            raw_messages = cursor.fetchall()
            
            conn.close()
            
            if not raw_messages:
                logger.info(f"No messages found for handle_id {handle_id}")
                return None
                
            # Process messages with text extraction
            messages = []
            for row in raw_messages:
                (rowid, guid, text, attributed_body, handle_id_db, 
                 date, date_read, is_from_me, service) = row
                
                # Extract text from the message
                from src.messaging.decoder import extract_message_text
                extracted_text = extract_message_text(text, attributed_body)
                
                if extracted_text:  # Only include messages with readable text
                    message = {
                        "rowid": rowid,
                        "guid": guid,
                        "text": extracted_text,
                        "handle_id": handle_id_db,
                        "date": date,
                        "date_read": date_read,
                        "is_from_me": bool(is_from_me),
                        "service": service,
                        "timestamp": self._cocoa_timestamp_to_datetime(date)
                    }
                    messages.append(message)
            
            if not messages:
                logger.info(f"No readable messages found for handle_id {handle_id}")
                return None
                
            # Analyze conversation context
            return self._analyze_conversation_context(handle_id, messages)
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting conversation context: {e}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing conversation context: {e}")
            return None
    
    def _analyze_conversation_context(
        self, 
        handle_id: int, 
        messages: List[Dict[str, Any]]
    ) -> ConversationContext:
        """Analyze the conversation to extract context and patterns"""
        
        # Sort messages by date (oldest first for analysis)
        messages_sorted = sorted(messages, key=lambda m: m["date"])
        
        # Get the most recent message
        last_message = messages_sorted[-1] if messages_sorted else None
        last_message_time = last_message["timestamp"] if last_message else None
        
        # Calculate time since last message
        time_since_last = None
        if last_message_time:
            time_since_last = datetime.now() - last_message_time
            
        # Determine who spoke last
        user_last_spoke = last_message["is_from_me"] if last_message else False
        contact_last_spoke = not user_last_spoke if last_message else False
        
        # Analyze conversation tone (basic analysis)
        tone = self._analyze_conversation_tone(messages_sorted)
        
        # Extract topic keywords
        keywords = self._extract_topic_keywords(messages_sorted)
        
        return ConversationContext(
            handle_id=handle_id,
            recent_messages=messages_sorted,
            conversation_length=len(messages_sorted),
            last_message_time=last_message_time,
            user_last_spoke=user_last_spoke,
            contact_last_spoke=contact_last_spoke,
            time_since_last_message=time_since_last,
            conversation_tone=tone,
            topic_keywords=keywords
        )
    
    def _analyze_conversation_tone(self, messages: List[Dict[str, Any]]) -> str:
        """Analyze the tone of the conversation based on message content"""
        
        # Simple tone analysis based on keywords and patterns
        positive_indicators = [
            "thanks", "thank you", "great", "awesome", "good", "nice", 
            "love", "like", "happy", "excited", "yes", "yeah", "sure"
        ]
        
        negative_indicators = [
            "no", "not", "can't", "won't", "sorry", "problem", "issue",
            "bad", "terrible", "awful", "annoying", "frustrated"
        ]
        
        question_indicators = ["?", "what", "when", "where", "how", "why", "who"]
        
        positive_count = 0
        negative_count = 0
        question_count = 0
        
        for message in messages[-5:]:  # Analyze last 5 messages for tone
            text = message["text"].lower()
            
            for indicator in positive_indicators:
                if indicator in text:
                    positive_count += 1
                    
            for indicator in negative_indicators:
                if indicator in text:
                    negative_count += 1
                    
            for indicator in question_indicators:
                if indicator in text:
                    question_count += 1
        
        # Determine tone based on indicators
        if question_count > positive_count + negative_count:
            return "questioning"
        elif positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _extract_topic_keywords(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract key topics/keywords from recent conversation"""
        
        # Common stop words to filter out
        stop_words = {
            "i", "you", "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "is", "are", "was", "were", "be",
            "been", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "this", "that", "these",
            "those", "my", "your", "his", "her", "its", "our", "their", "me",
            "him", "her", "us", "them", "it", "what", "when", "where", "why",
            "how", "who", "which", "if", "then", "now", "just", "only", "also",
            "so", "very", "really", "much", "more", "most", "some", "any", "all"
        }
        
        word_counts = {}
        
        # Analyze last 10 messages for keywords
        for message in messages[-10:]:
            text = message["text"].lower()
            words = text.split()
            
            for word in words:
                # Clean word (remove punctuation)
                cleaned_word = ''.join(c for c in word if c.isalnum())
                
                if (cleaned_word and 
                    len(cleaned_word) > 2 and 
                    cleaned_word not in stop_words):
                    word_counts[cleaned_word] = word_counts.get(cleaned_word, 0) + 1
        
        # Return top keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:5] if count > 1]
    
    def _cocoa_timestamp_to_datetime(self, cocoa_timestamp: int) -> datetime:
        """Convert macOS Cocoa timestamp to Python datetime"""
        # Cocoa timestamps are nanoseconds since 2001-01-01 00:00:00 UTC
        cocoa_epoch = datetime(2001, 1, 1)
        timestamp_seconds = cocoa_timestamp / 1_000_000_000
        return cocoa_epoch + timedelta(seconds=timestamp_seconds)
    
    def get_conversation_summary(self, handle_id: int) -> Dict[str, Any]:
        """Get a summary of conversation statistics for a contact"""
        
        context = self.get_conversation_context(handle_id, limit=100)
        if not context:
            return {}
            
        # Count user vs contact messages
        user_messages = sum(1 for msg in context.recent_messages if msg["is_from_me"])
        contact_messages = len(context.recent_messages) - user_messages
        
        # Calculate average response time (simplified)
        response_times = []
        for i in range(1, len(context.recent_messages)):
            current_msg = context.recent_messages[i]
            prev_msg = context.recent_messages[i-1]
            
            # Only measure response time if speakers alternate
            if current_msg["is_from_me"] != prev_msg["is_from_me"]:
                time_diff = current_msg["date"] - prev_msg["date"]
                response_times.append(time_diff / 1_000_000_000)  # Convert to seconds
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "handle_id": handle_id,
            "total_messages": context.conversation_length,
            "user_messages": user_messages,
            "contact_messages": contact_messages,
            "conversation_tone": context.conversation_tone,
            "topic_keywords": context.topic_keywords,
            "last_message_time": context.last_message_time,
            "time_since_last_message": context.time_since_last_message,
            "user_last_spoke": context.user_last_spoke,
            "avg_response_time_seconds": round(avg_response_time, 2)
        }