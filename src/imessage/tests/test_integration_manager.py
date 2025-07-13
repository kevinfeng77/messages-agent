"""Tests for IMessageIntegrationManager"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.imessage.integration_manager import IMessageIntegrationManager, create_imessage_integration
from src.imessage.response_generator import ResponseSuggestion
from src.imessage.conversation_analyzer import ConversationContext
from src.database.manager import DatabaseManager


class TestIMessageIntegrationManager(unittest.TestCase):
    """Test IMessageIntegrationManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock all dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_conversation_analyzer = Mock()
        self.mock_response_generator = Mock()
        self.mock_handle_matcher = Mock()
        
        # Create manager with mocked dependencies
        self.manager = IMessageIntegrationManager("test_data")
        self.manager.db_manager = self.mock_db_manager
        self.manager.conversation_analyzer = self.mock_conversation_analyzer
        self.manager.response_generator = self.mock_response_generator
        self.manager.handle_matcher = self.mock_handle_matcher
    
    def test_initialization_success(self):
        """Test successful initialization"""
        self.mock_db_manager.verify_source_database.return_value = True
        self.mock_db_manager.create_safe_copy.return_value = "test.db"
        
        result = self.manager.initialize()
        
        self.assertTrue(result)
        self.mock_db_manager.verify_source_database.assert_called_once()
        self.mock_db_manager.create_safe_copy.assert_called_once()
    
    def test_initialization_no_database(self):
        """Test initialization failure when database not accessible"""
        self.mock_db_manager.verify_source_database.return_value = False
        
        result = self.manager.initialize()
        
        self.assertFalse(result)
    
    def test_initialization_copy_failure(self):
        """Test initialization failure when database copy fails"""
        self.mock_db_manager.verify_source_database.return_value = True
        self.mock_db_manager.create_safe_copy.return_value = None
        
        result = self.manager.initialize()
        
        self.assertFalse(result)
    
    def test_get_response_suggestions_by_phone_success(self):
        """Test getting suggestions by phone number"""
        phone = "+1234567890"
        handle_id = 123
        suggestions = [
            ResponseSuggestion("Thanks!", 0.8, "acknowledgment"),
            ResponseSuggestion("Sounds good", 0.7, "agreement")
        ]
        
        self.mock_handle_matcher.find_handle_by_phone.return_value = handle_id
        self.mock_response_generator.generate_suggestions.return_value = suggestions
        
        result = self.manager.get_response_suggestions_by_phone(phone, 2)
        
        self.assertEqual(result, suggestions)
        self.mock_handle_matcher.find_handle_by_phone.assert_called_once_with(phone)
        self.mock_response_generator.generate_suggestions.assert_called_once_with(handle_id, 2)
    
    def test_get_response_suggestions_by_phone_no_handle(self):
        """Test getting suggestions when handle not found"""
        phone = "+1234567890"
        default_suggestions = [ResponseSuggestion("Hey!", 0.3, "default")]
        
        self.mock_handle_matcher.find_handle_by_phone.return_value = None
        self.mock_response_generator._get_default_suggestions.return_value = default_suggestions
        
        result = self.manager.get_response_suggestions_by_phone(phone, 3)
        
        self.assertEqual(result, default_suggestions)
        self.mock_response_generator._get_default_suggestions.assert_called_once_with(3)
    
    def test_get_response_suggestions_by_handle(self):
        """Test getting suggestions by handle ID"""
        handle_id = 123
        suggestions = [ResponseSuggestion("Great!", 0.9, "positive")]
        
        self.mock_response_generator.generate_suggestions.return_value = suggestions
        
        result = self.manager.get_response_suggestions_by_handle(handle_id, 1)
        
        self.assertEqual(result, suggestions)
        self.mock_response_generator.generate_suggestions.assert_called_once_with(handle_id, 1)
    
    def test_get_conversation_context_by_phone(self):
        """Test getting conversation context by phone"""
        phone = "+1234567890"
        handle_id = 123
        mock_context = Mock(spec=ConversationContext)
        
        self.mock_handle_matcher.find_handle_by_phone.return_value = handle_id
        self.mock_conversation_analyzer.get_conversation_context.return_value = mock_context
        
        result = self.manager.get_conversation_context_by_phone(phone)
        
        self.assertEqual(result, mock_context)
        self.mock_conversation_analyzer.get_conversation_context.assert_called_once_with(handle_id)
    
    def test_get_conversation_summary_by_phone(self):
        """Test getting conversation summary by phone"""
        phone = "+1234567890"
        handle_id = 123
        summary = {"total_messages": 10, "conversation_tone": "positive"}
        
        self.mock_handle_matcher.find_handle_by_phone.return_value = handle_id
        self.mock_conversation_analyzer.get_conversation_summary.return_value = summary
        
        result = self.manager.get_conversation_summary_by_phone(phone)
        
        self.assertEqual(result, summary)
        self.mock_conversation_analyzer.get_conversation_summary.assert_called_once_with(handle_id)
    
    def test_analyze_user_response_patterns_by_phone(self):
        """Test analyzing user response patterns by phone"""
        phone = "+1234567890"
        handle_id = 123
        patterns = {"avg_response_length": 5.2, "typical_response_style": "brief"}
        
        self.mock_handle_matcher.find_handle_by_phone.return_value = handle_id
        self.mock_response_generator.analyze_user_response_patterns.return_value = patterns
        
        result = self.manager.analyze_user_response_patterns_by_phone(phone)
        
        self.assertEqual(result, patterns)
        self.mock_response_generator.analyze_user_response_patterns.assert_called_once_with(handle_id)
    
    @patch('sqlite3.connect')
    def test_get_recent_conversations(self, mock_connect):
        """Test getting recent conversations"""
        self.mock_db_manager.copy_db_path.exists.return_value = True
        self.mock_db_manager.copy_db_path = "test.db"
        
        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (123, 1000000000, 15),
            (456, 2000000000, 8)
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Mock contact info
        self.mock_handle_matcher.get_contact_info_by_handle.side_effect = [
            {"phone_number": "+1234567890", "display_name": "John Doe"},
            {"phone_number": "+0987654321", "display_name": "Jane Smith"}
        ]
        
        result = self.manager.get_recent_conversations(2)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["handle_id"], 123)
        self.assertEqual(result[0]["message_count"], 15)
        self.assertEqual(result[0]["display_name"], "John Doe")
        self.assertEqual(result[1]["handle_id"], 456)
        self.assertEqual(result[1]["message_count"], 8)
        self.assertEqual(result[1]["display_name"], "Jane Smith")
    
    def test_simulate_response_suggestions(self):
        """Test simulating response suggestions for incoming message"""
        phone = "+1234567890"
        incoming_message = "Thanks for your help!"
        
        # Mock context
        mock_context = ConversationContext(
            handle_id=123,
            recent_messages=[],
            conversation_length=5,
            last_message_time=datetime.now(),
            user_last_spoke=False,
            contact_last_spoke=True,
            time_since_last_message=timedelta(minutes=2),
            conversation_tone="positive",
            topic_keywords=["help", "project"]
        )
        
        base_suggestions = [
            ResponseSuggestion("You're welcome", 0.7, "acknowledgment"),
            ResponseSuggestion("No problem", 0.6, "acknowledgment")
        ]
        
        # Mock method calls
        with patch.object(self.manager, 'get_conversation_context_by_phone', return_value=mock_context):
            with patch.object(self.manager, 'get_response_suggestions_by_phone', return_value=base_suggestions):
                suggestions, context_info = self.manager.simulate_response_suggestions(phone, incoming_message)
        
        # Check suggestions were enhanced
        self.assertGreater(len(suggestions), 0)
        
        # Check context info
        self.assertEqual(context_info["conversation_length"], 5)
        self.assertEqual(context_info["conversation_tone"], "positive")
        self.assertEqual(context_info["incoming_message"], incoming_message)
        self.assertIn("simulation_time", context_info)
    
    def test_enhance_suggestions_for_message_thanks(self):
        """Test enhancing suggestions for thank you message"""
        base_suggestions = [
            ResponseSuggestion("You're welcome", 0.5, "acknowledgment"),
            ResponseSuggestion("Great!", 0.4, "positive")
        ]
        incoming_message = "Thanks so much!"
        
        enhanced = self.manager._enhance_suggestions_for_message(base_suggestions, incoming_message)
        
        # "You're welcome" should get boosted confidence for thanks message
        welcome_suggestion = next((s for s in enhanced if "welcome" in s.text.lower()), None)
        self.assertIsNotNone(welcome_suggestion)
        self.assertGreater(welcome_suggestion.confidence, 0.5)
    
    def test_enhance_suggestions_for_message_question(self):
        """Test enhancing suggestions for question message"""
        base_suggestions = [
            ResponseSuggestion("What do you think?", 0.5, "question_response"),
            ResponseSuggestion("Thanks!", 0.4, "acknowledgment")
        ]
        incoming_message = "What time should we meet?"
        
        enhanced = self.manager._enhance_suggestions_for_message(base_suggestions, incoming_message)
        
        # Should add time-specific suggestion
        time_suggestions = [s for s in enhanced if "schedule" in s.text.lower() or "time" in s.reasoning.lower()]
        self.assertGreater(len(time_suggestions), 0)
    
    def test_get_system_status_success(self):
        """Test getting system status when everything is working"""
        mock_stats = {"message_count": 1000, "contact_count": 50}
        
        self.mock_db_manager.copy_db_path.exists.return_value = True
        self.mock_db_manager.get_database_stats.return_value = mock_stats
        self.mock_db_manager.get_last_modification_time.return_value = datetime.now()
        
        with patch.object(self.manager, 'get_recent_conversations', return_value=[{"handle_id": 123}]):
            status = self.manager.get_system_status()
        
        self.assertTrue(status["database_connected"])
        self.assertTrue(status["system_ready"])
        self.assertEqual(status["database_stats"], mock_stats)
        self.assertEqual(status["recent_conversations_count"], 1)
    
    def test_get_system_status_error(self):
        """Test getting system status when there's an error"""
        self.mock_db_manager.copy_db_path.exists.side_effect = Exception("Database error")
        
        status = self.manager.get_system_status()
        
        self.assertFalse(status["database_connected"])
        self.assertFalse(status["system_ready"])
        self.assertIn("error", status)
    
    def test_cleanup(self):
        """Test cleanup method"""
        self.manager.cleanup()
        self.mock_db_manager.cleanup_copies.assert_called_once()


class TestCreateIMessageIntegration(unittest.TestCase):
    """Test the convenience function for creating integration manager"""
    
    @patch('src.imessage.integration_manager.IMessageIntegrationManager')
    def test_create_imessage_integration_success(self, mock_manager_class):
        """Test successful creation of integration manager"""
        mock_manager = Mock()
        mock_manager.initialize.return_value = True
        mock_manager_class.return_value = mock_manager
        
        result = create_imessage_integration("test_data")
        
        self.assertEqual(result, mock_manager)
        mock_manager_class.assert_called_once_with("test_data")
        mock_manager.initialize.assert_called_once()
    
    @patch('src.imessage.integration_manager.IMessageIntegrationManager')
    def test_create_imessage_integration_failure(self, mock_manager_class):
        """Test failure to create integration manager"""
        mock_manager = Mock()
        mock_manager.initialize.return_value = False
        mock_manager_class.return_value = mock_manager
        
        with self.assertRaises(RuntimeError):
            create_imessage_integration("test_data")


if __name__ == '__main__':
    unittest.main()