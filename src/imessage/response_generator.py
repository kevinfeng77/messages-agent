"""Response Generator - Generates contextual response suggestions for iMessage"""

import logging
import random
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.imessage.conversation_analyzer import ConversationAnalyzer, ConversationContext
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class ResponseSuggestion:
    """Represents a suggested response"""
    
    text: str
    confidence: float
    category: str
    reasoning: str = ""


class ResponseGenerator:
    """Generates contextual response suggestions based on conversation analysis"""
    
    def __init__(self, analyzer: Optional[ConversationAnalyzer] = None):
        self.analyzer = analyzer or ConversationAnalyzer()
        self._initialize_response_templates()
    
    def _initialize_response_templates(self):
        """Initialize response templates categorized by context"""
        
        self.response_templates = {
            "acknowledgment": [
                "Got it!",
                "Thanks!",
                "Perfect",
                "Sounds good",
                "Great, thanks",
                "Understood",
                "👍",
                "Awesome"
            ],
            "affirmative": [
                "Yes",
                "Yeah",
                "For sure",
                "Absolutely",
                "Definitely",
                "Of course",
                "Sure thing",
                "Yep"
            ],
            "negative": [
                "No thanks",
                "Not right now",
                "Maybe later",
                "I can't",
                "Sorry, no",
                "Not today",
                "Pass"
            ],
            "question_response": [
                "What do you think?",
                "How about you?",
                "What's your plan?",
                "When works for you?",
                "Where should we meet?",
                "Sounds good to you?"
            ],
            "greeting": [
                "Hey!",
                "Hi there",
                "Good morning",
                "Good afternoon",
                "Hello",
                "Hey, how's it going?",
                "What's up?"
            ],
            "casual": [
                "lol",
                "haha",
                "nice",
                "cool",
                "interesting",
                "wow",
                "oh nice",
                "that's funny"
            ],
            "time_based": [
                "Running late",
                "On my way",
                "Almost there",
                "Give me 5 minutes",
                "Just left",
                "Traffic is crazy"
            ],
            "planning": [
                "Let me check my calendar",
                "What time works?",
                "I'm free after 3",
                "Tomorrow works better",
                "Let's figure it out",
                "What did you have in mind?"
            ]
        }
        
        # Response patterns based on message content analysis
        self.content_patterns = {
            r"\b(thanks?|thx|thank you)\b": ["You're welcome", "No problem", "Anytime", "👍"],
            r"\b(sorry|my bad|oops)\b": ["No worries", "It's all good", "Don't worry about it", "No big deal"],
            r"\b(when|what time)\b": ["Let me check", "How about 3pm?", "Flexible on timing", "Whatever works"],
            r"\b(where|location|place)\b": ["Good question", "Your choice", "Somewhere central?", "The usual place?"],
            r"\b(how about|what about)\b": ["Sounds good", "That works", "I'm in", "Let's do it"],
            r"\b(can you|could you|would you)\b": ["Sure", "Happy to help", "Of course", "Let me see"],
            r"\b(lunch|dinner|food|eat)\b": ["I'm hungry too", "Good idea", "Where were you thinking?", "I'm in"],
            r"\b(meeting|work|call)\b": ["Sounds professional", "Got it", "When?", "I'll be there"],
            r"\?": ["Good question", "Let me think", "Not sure", "What do you think?"],
            r"!": ["Exciting!", "Nice!", "Wow", "That's great!"]
        }
    
    def generate_suggestions(
        self, 
        handle_id: int, 
        num_suggestions: int = 3
    ) -> List[ResponseSuggestion]:
        """
        Generate response suggestions for a conversation
        
        Args:
            handle_id: Contact handle ID
            num_suggestions: Number of suggestions to generate
            
        Returns:
            List of ResponseSuggestion objects
        """
        context = self.analyzer.get_conversation_context(handle_id)
        if not context:
            logger.warning(f"No conversation context found for handle_id {handle_id}")
            return self._get_default_suggestions(num_suggestions)
        
        suggestions = []
        
        # Get suggestions based on different strategies
        context_suggestions = self._get_context_based_suggestions(context)
        pattern_suggestions = self._get_pattern_based_suggestions(context)
        tone_suggestions = self._get_tone_based_suggestions(context)
        timing_suggestions = self._get_timing_based_suggestions(context)
        
        # Combine and score all suggestions
        all_suggestions = (
            context_suggestions + 
            pattern_suggestions + 
            tone_suggestions + 
            timing_suggestions
        )
        
        # Remove duplicates and sort by confidence
        unique_suggestions = {}
        for suggestion in all_suggestions:
            if suggestion.text not in unique_suggestions:
                unique_suggestions[suggestion.text] = suggestion
            else:
                # Keep the one with higher confidence
                if suggestion.confidence > unique_suggestions[suggestion.text].confidence:
                    unique_suggestions[suggestion.text] = suggestion
        
        # Sort by confidence and return top suggestions
        sorted_suggestions = sorted(
            unique_suggestions.values(), 
            key=lambda x: x.confidence, 
            reverse=True
        )
        
        return sorted_suggestions[:num_suggestions]
    
    def _get_context_based_suggestions(self, context: ConversationContext) -> List[ResponseSuggestion]:
        """Generate suggestions based on conversation context"""
        suggestions = []
        
        if not context.recent_messages:
            return suggestions
        
        last_message = context.recent_messages[-1]
        last_text = last_message["text"].lower()
        
        # If contact asked a question
        if "?" in last_text and not last_message["is_from_me"]:
            for response in self.response_templates["question_response"]:
                suggestions.append(ResponseSuggestion(
                    text=response,
                    confidence=0.8,
                    category="question_response",
                    reasoning="Responding to question"
                ))
        
        # If contact said thanks
        if any(word in last_text for word in ["thanks", "thank you", "thx"]):
            for response in ["You're welcome", "No problem", "Anytime"]:
                suggestions.append(ResponseSuggestion(
                    text=response,
                    confidence=0.9,
                    category="acknowledgment",
                    reasoning="Responding to thanks"
                ))
        
        # If contact is planning something
        if any(word in last_text for word in ["meet", "plan", "when", "where", "time"]):
            for response in self.response_templates["planning"]:
                suggestions.append(ResponseSuggestion(
                    text=response,
                    confidence=0.7,
                    category="planning",
                    reasoning="Responding to planning discussion"
                ))
        
        return suggestions
    
    def _get_pattern_based_suggestions(self, context: ConversationContext) -> List[ResponseSuggestion]:
        """Generate suggestions based on message content patterns"""
        suggestions = []
        
        if not context.recent_messages:
            return suggestions
        
        last_message = context.recent_messages[-1]
        last_text = last_message["text"]
        
        # Check each pattern
        for pattern, responses in self.content_patterns.items():
            if re.search(pattern, last_text, re.IGNORECASE):
                for response in responses:
                    suggestions.append(ResponseSuggestion(
                        text=response,
                        confidence=0.6,
                        category="pattern_match",
                        reasoning=f"Matched pattern: {pattern}"
                    ))
        
        return suggestions
    
    def _get_tone_based_suggestions(self, context: ConversationContext) -> List[ResponseSuggestion]:
        """Generate suggestions based on conversation tone"""
        suggestions = []
        
        tone = context.conversation_tone
        
        if tone == "positive":
            for response in self.response_templates["acknowledgment"]:
                suggestions.append(ResponseSuggestion(
                    text=response,
                    confidence=0.5,
                    category="tone_positive",
                    reasoning="Matching positive tone"
                ))
        
        elif tone == "questioning":
            for response in self.response_templates["question_response"]:
                suggestions.append(ResponseSuggestion(
                    text=response,
                    confidence=0.5,
                    category="tone_questioning",
                    reasoning="Responding to questioning tone"
                ))
        
        elif tone == "casual":
            for response in self.response_templates["casual"]:
                suggestions.append(ResponseSuggestion(
                    text=response,
                    confidence=0.4,
                    category="tone_casual",
                    reasoning="Matching casual tone"
                ))
        
        return suggestions
    
    def _get_timing_based_suggestions(self, context: ConversationContext) -> List[ResponseSuggestion]:
        """Generate suggestions based on timing and conversation flow"""
        suggestions = []
        
        # If user hasn't responded in a while
        if (context.time_since_last_message and 
            context.time_since_last_message.total_seconds() > 3600 and  # > 1 hour
            context.contact_last_spoke):
            
            for response in ["Sorry for the late reply", "Just saw this", "Hey!"]:
                suggestions.append(ResponseSuggestion(
                    text=response,
                    confidence=0.6,
                    category="timing_late",
                    reasoning="Late response acknowledgment"
                ))
        
        # If it's a quick back-and-forth conversation
        elif (context.time_since_last_message and 
              context.time_since_last_message.total_seconds() < 300):  # < 5 minutes
            
            for response in self.response_templates["casual"]:
                suggestions.append(ResponseSuggestion(
                    text=response,
                    confidence=0.4,
                    category="timing_quick",
                    reasoning="Quick conversation flow"
                ))
        
        return suggestions
    
    def _get_default_suggestions(self, num_suggestions: int) -> List[ResponseSuggestion]:
        """Get default suggestions when no context is available"""
        default_responses = [
            ResponseSuggestion("Hey!", 0.3, "default", "Default greeting"),
            ResponseSuggestion("What's up?", 0.3, "default", "Default casual"),
            ResponseSuggestion("Thanks!", 0.3, "default", "Default acknowledgment"),
            ResponseSuggestion("Sounds good", 0.3, "default", "Default agreement"),
            ResponseSuggestion("Let me check", 0.3, "default", "Default response")
        ]
        return default_responses[:num_suggestions]
    
    def analyze_user_response_patterns(self, handle_id: int) -> Dict[str, any]:
        """Analyze how the user typically responds in conversations"""
        context = self.analyzer.get_conversation_context(handle_id, limit=50)
        if not context:
            return {}
        
        user_messages = [msg for msg in context.recent_messages if msg["is_from_me"]]
        
        # Analyze response patterns
        response_lengths = [len(msg["text"].split()) for msg in user_messages]
        common_words = {}
        
        for message in user_messages:
            words = message["text"].lower().split()
            for word in words:
                common_words[word] = common_words.get(word, 0) + 1
        
        # Get most common words (excluding stop words)
        sorted_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "avg_response_length": sum(response_lengths) / len(response_lengths) if response_lengths else 0,
            "total_user_messages": len(user_messages),
            "common_words": sorted_words[:10],
            "typical_response_style": self._determine_response_style(user_messages)
        }
    
    def _determine_response_style(self, user_messages: List[Dict[str, any]]) -> str:
        """Determine the user's typical response style"""
        if not user_messages:
            return "unknown"
        
        avg_length = sum(len(msg["text"].split()) for msg in user_messages) / len(user_messages)
        
        emoji_count = sum(1 for msg in user_messages if any(ord(char) > 127 for char in msg["text"]))
        emoji_rate = emoji_count / len(user_messages)
        
        question_count = sum(1 for msg in user_messages if "?" in msg["text"])
        question_rate = question_count / len(user_messages)
        
        if avg_length < 3:
            return "brief"
        elif avg_length > 10:
            return "detailed"
        elif emoji_rate > 0.3:
            return "expressive"
        elif question_rate > 0.2:
            return "inquisitive"
        else:
            return "conversational"