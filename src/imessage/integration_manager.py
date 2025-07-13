"""iMessage Integration Manager - Main interface for iMessage smart response system"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.database.manager import DatabaseManager
from src.imessage.conversation_analyzer import ConversationAnalyzer, ConversationContext
from src.imessage.response_generator import ResponseGenerator, ResponseSuggestion
from src.user.handle_matcher import HandleMatcher
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class IMessageIntegrationManager:
    """Main interface for iMessage integration and smart response suggestions"""
    
    def __init__(self, data_dir: str = "./data"):
        self.db_manager = DatabaseManager(data_dir)
        self.conversation_analyzer = ConversationAnalyzer(self.db_manager)
        self.response_generator = ResponseGenerator(self.conversation_analyzer)
        # HandleMatcher expects a path, so we'll initialize it later after database setup
        self.handle_matcher = None
        
    def initialize(self) -> bool:
        """Initialize the iMessage integration system"""
        try:
            logger.info("Initializing iMessage Integration Manager...")
            
            # Verify database access
            if not self.db_manager.verify_source_database():
                logger.error("Cannot access Messages database")
                return False
            
            # Create working copy of database
            db_path = self.db_manager.create_safe_copy()
            if not db_path:
                logger.error("Failed to create database copy")
                return False
            
            # Initialize HandleMatcher with the database copy path
            self.handle_matcher = HandleMatcher(str(db_path))
            
            logger.info("iMessage Integration Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize iMessage Integration Manager: {e}")
            return False
    
    def get_response_suggestions_by_phone(
        self, 
        phone_number: str, 
        num_suggestions: int = 3
    ) -> List[ResponseSuggestion]:
        """
        Get response suggestions for a contact by phone number
        
        Args:
            phone_number: Contact's phone number
            num_suggestions: Number of suggestions to return
            
        Returns:
            List of ResponseSuggestion objects
        """
        try:
            # Check if handle_matcher is initialized
            if not self.handle_matcher:
                logger.warning("HandleMatcher not initialized")
                return self.response_generator._get_default_suggestions(num_suggestions)
            
            # Find handle_id for this phone number
            handle_id = self.handle_matcher.find_handle_by_phone(phone_number)
            if not handle_id:
                logger.warning(f"No handle found for phone number: {phone_number}")
                return self.response_generator._get_default_suggestions(num_suggestions)
            
            return self.response_generator.generate_suggestions(handle_id, num_suggestions)
            
        except Exception as e:
            logger.error(f"Error getting suggestions for phone {phone_number}: {e}")
            return []
    
    def get_response_suggestions_by_handle(
        self, 
        handle_id: int, 
        num_suggestions: int = 3
    ) -> List[ResponseSuggestion]:
        """
        Get response suggestions for a contact by handle ID
        
        Args:
            handle_id: Contact's handle ID from messages database
            num_suggestions: Number of suggestions to return
            
        Returns:
            List of ResponseSuggestion objects
        """
        try:
            return self.response_generator.generate_suggestions(handle_id, num_suggestions)
        except Exception as e:
            logger.error(f"Error getting suggestions for handle {handle_id}: {e}")
            return []
    
    def get_conversation_context_by_phone(self, phone_number: str) -> Optional[ConversationContext]:
        """Get conversation context for a contact by phone number"""
        try:
            if not self.handle_matcher:
                logger.warning("HandleMatcher not initialized")
                return None
                
            handle_id = self.handle_matcher.find_handle_by_phone(phone_number)
            if not handle_id:
                logger.warning(f"No handle found for phone number: {phone_number}")
                return None
            
            return self.conversation_analyzer.get_conversation_context(handle_id)
            
        except Exception as e:
            logger.error(f"Error getting context for phone {phone_number}: {e}")
            return None
    
    def get_conversation_summary_by_phone(self, phone_number: str) -> Dict[str, any]:
        """Get conversation summary for a contact by phone number"""
        try:
            if not self.handle_matcher:
                logger.warning("HandleMatcher not initialized")
                return {}
                
            handle_id = self.handle_matcher.find_handle_by_phone(phone_number)
            if not handle_id:
                logger.warning(f"No handle found for phone number: {phone_number}")
                return {}
            
            return self.conversation_analyzer.get_conversation_summary(handle_id)
            
        except Exception as e:
            logger.error(f"Error getting summary for phone {phone_number}: {e}")
            return {}
    
    def analyze_user_response_patterns_by_phone(self, phone_number: str) -> Dict[str, any]:
        """Analyze user's response patterns for a specific contact by phone number"""
        try:
            if not self.handle_matcher:
                logger.warning("HandleMatcher not initialized")
                return {}
                
            handle_id = self.handle_matcher.find_handle_by_phone(phone_number)
            if not handle_id:
                logger.warning(f"No handle found for phone number: {phone_number}")
                return {}
            
            return self.response_generator.analyze_user_response_patterns(handle_id)
            
        except Exception as e:
            logger.error(f"Error analyzing patterns for phone {phone_number}: {e}")
            return {}
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, any]]:
        """Get list of recent conversations with basic info"""
        try:
            if not self.db_manager.copy_db_path.exists():
                logger.error("Database copy does not exist")
                return []
            
            import sqlite3
            conn = sqlite3.connect(str(self.db_manager.copy_db_path))
            cursor = conn.cursor()
            
            # Get recent conversations (most recent message per handle)
            query = """
                SELECT 
                    handle_id,
                    MAX(date) as last_message_date,
                    COUNT(*) as message_count
                FROM message 
                WHERE handle_id IS NOT NULL
                GROUP BY handle_id
                ORDER BY last_message_date DESC
                LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            conn.close()
            
            conversations = []
            for handle_id, last_date, msg_count in results:
                # Try to get contact info if handle_matcher is available
                contact_info = None
                if self.handle_matcher:
                    try:
                        contact_info = self.handle_matcher.get_contact_info_by_handle(handle_id)
                    except Exception as e:
                        logger.warning(f"Could not get contact info for handle {handle_id}: {e}")
                
                conversation = {
                    "handle_id": handle_id,
                    "last_message_date": last_date,
                    "message_count": msg_count,
                    "contact_info": contact_info,
                    "phone_number": contact_info.get("phone_number") if contact_info else None,
                    "display_name": contact_info.get("display_name") if contact_info else f"Handle {handle_id}"
                }
                conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting recent conversations: {e}")
            return []
    
    def simulate_response_suggestions(
        self, 
        phone_number: str, 
        incoming_message: str
    ) -> Tuple[List[ResponseSuggestion], Dict[str, any]]:
        """
        Simulate getting response suggestions for a new incoming message
        
        Args:
            phone_number: Contact's phone number
            incoming_message: The new message text to respond to
            
        Returns:
            Tuple of (suggestions, context_info)
        """
        try:
            # Get current conversation context
            context = self.get_conversation_context_by_phone(phone_number)
            context_info = {}
            
            if context:
                context_info = {
                    "conversation_length": context.conversation_length,
                    "last_message_time": context.last_message_time,
                    "conversation_tone": context.conversation_tone,
                    "topic_keywords": context.topic_keywords,
                    "user_last_spoke": context.user_last_spoke
                }
            
            # Get suggestions based on current context
            suggestions = self.get_response_suggestions_by_phone(phone_number)
            
            # Enhance suggestions based on the new incoming message
            enhanced_suggestions = self._enhance_suggestions_for_message(
                suggestions, incoming_message
            )
            
            context_info["incoming_message"] = incoming_message
            context_info["simulation_time"] = datetime.now().isoformat()
            
            return enhanced_suggestions, context_info
            
        except Exception as e:
            logger.error(f"Error simulating response for {phone_number}: {e}")
            return [], {}
    
    def _enhance_suggestions_for_message(
        self, 
        base_suggestions: List[ResponseSuggestion], 
        incoming_message: str
    ) -> List[ResponseSuggestion]:
        """Enhance suggestions based on a specific incoming message"""
        
        enhanced = []
        incoming_lower = incoming_message.lower()
        
        # Boost confidence for relevant suggestions
        for suggestion in base_suggestions:
            new_confidence = suggestion.confidence
            
            # Boost confidence if suggestion matches message context
            if "?" in incoming_message and suggestion.category == "question_response":
                new_confidence += 0.2
            elif any(word in incoming_lower for word in ["thanks", "thank"]) and "welcome" in suggestion.text.lower():
                new_confidence += 0.3
            elif "sorry" in incoming_lower and "worry" in suggestion.text.lower():
                new_confidence += 0.3
            
            enhanced.append(ResponseSuggestion(
                text=suggestion.text,
                confidence=min(new_confidence, 1.0),  # Cap at 1.0
                category=suggestion.category,
                reasoning=f"{suggestion.reasoning} (enhanced for incoming message)"
            ))
        
        # Add message-specific suggestions
        if "when" in incoming_lower or "what time" in incoming_lower:
            enhanced.append(ResponseSuggestion(
                text="Let me check my schedule",
                confidence=0.8,
                category="time_specific",
                reasoning="Responding to time question"
            ))
        
        if "where" in incoming_lower:
            enhanced.append(ResponseSuggestion(
                text="Good question, where works for you?",
                confidence=0.8,
                category="location_specific", 
                reasoning="Responding to location question"
            ))
        
        # Sort by confidence and return
        return sorted(enhanced, key=lambda x: x.confidence, reverse=True)
    
    def get_system_status(self) -> Dict[str, any]:
        """Get status information about the iMessage integration system"""
        try:
            stats = self.db_manager.get_database_stats()
            recent_conversations = len(self.get_recent_conversations(50))
            
            return {
                "database_connected": self.db_manager.copy_db_path.exists(),
                "database_stats": stats,
                "recent_conversations_count": recent_conversations,
                "last_database_update": self.db_manager.get_last_modification_time(),
                "system_ready": True
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "database_connected": False,
                "system_ready": False,
                "error": str(e)
            }
    
    def cleanup(self):
        """Clean up resources and temporary files"""
        try:
            self.db_manager.cleanup_copies()
            logger.info("iMessage Integration Manager cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Convenience function for quick access
def create_imessage_integration(data_dir: str = "./data") -> IMessageIntegrationManager:
    """Create and initialize an iMessage integration manager"""
    manager = IMessageIntegrationManager(data_dir)
    if manager.initialize():
        return manager
    else:
        raise RuntimeError("Failed to initialize iMessage integration")