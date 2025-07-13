"""Tests for message maker service module"""

import pytest
from unittest.mock import patch, MagicMock

from src.message_maker.service import (
    MessageMakerService, MessageRequest, MessageResponse
)
from src.message_maker.generator import MessageContext
from src.message_maker.validator import ValidationResult, ValidationLevel


class TestMessageRequest:
    """Test MessageRequest dataclass"""
    
    def test_message_request_creation(self):
        """Test creating MessageRequest with required fields"""
        request = MessageRequest(
            conversation_history=["Hello", "Hi there"],
            user_id="user123"
        )
        
        assert request.conversation_history == ["Hello", "Hi there"]
        assert request.user_id == "user123"
        assert request.message_type == "response"
        assert request.tone == "casual"
        assert request.platform == "imessage"
        assert request.require_validation is True
        assert request.max_suggestions == 3
        
    def test_message_request_with_custom_values(self):
        """Test MessageRequest with custom values"""
        request = MessageRequest(
            conversation_history=["How are you?"],
            user_id="user456",
            message_type="greeting",
            tone="formal",
            platform="whatsapp",
            require_validation=False,
            max_suggestions=5
        )
        
        assert request.conversation_history == ["How are you?"]
        assert request.user_id == "user456"
        assert request.message_type == "greeting"
        assert request.tone == "formal"
        assert request.platform == "whatsapp"
        assert request.require_validation is False
        assert request.max_suggestions == 5


class TestMessageResponse:
    """Test MessageResponse dataclass"""
    
    def test_message_response_creation(self):
        """Test creating MessageResponse"""
        validation_result = ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message="Test validation"
        )
        
        response = MessageResponse(
            primary_message="Hello there!",
            suggestions=["Hi!", "Hey there!", "Greetings!"],
            validation_results=[validation_result],
            confidence_score=0.85,
            metadata={"method": "template", "time": 0.1}
        )
        
        assert response.primary_message == "Hello there!"
        assert response.suggestions == ["Hi!", "Hey there!", "Greetings!"]
        assert len(response.validation_results) == 1
        assert response.confidence_score == 0.85
        assert response.metadata["method"] == "template"


class TestMessageMakerService:
    """Test MessageMakerService class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = MessageMakerService()
        
    def test_service_initialization(self):
        """Test service initializes with all components"""
        assert self.service.generator is not None
        assert self.service.template_manager is not None
        assert self.service.validator is not None
        
    @patch('src.message_maker.service.logger')
    def test_generate_message_basic(self, mock_logger):
        """Test basic message generation"""
        request = MessageRequest(
            conversation_history=["Hello"],
            user_id="test_user"
        )
        
        with patch.object(self.service.generator, 'generate_response') as mock_generate:
            with patch.object(self.service.generator, 'suggest_responses') as mock_suggest:
                with patch.object(self.service.validator, 'validate_message') as mock_validate:
                    
                    mock_generate.return_value = "Hi there!"
                    mock_suggest.return_value = ["Hey!", "Hello!", "Hi!"]
                    mock_validate.return_value = [ValidationResult(
                        is_valid=True,
                        level=ValidationLevel.INFO,
                        message="Good message"
                    )]
                    
                    response = self.service.generate_message(request)
                    
                    assert response.primary_message == "Hi there!"
                    assert len(response.suggestions) == 3
                    assert len(response.validation_results) >= 1
                    assert 0.0 <= response.confidence_score <= 1.0
                    assert "generation_method" in response.metadata
                    
    def test_generate_message_without_validation(self):
        """Test message generation without validation"""
        request = MessageRequest(
            conversation_history=["Hello"],
            user_id="test_user",
            require_validation=False
        )
        
        with patch.object(self.service.generator, 'generate_response') as mock_generate:
            with patch.object(self.service.generator, 'suggest_responses') as mock_suggest:
                
                mock_generate.return_value = "Hi there!"
                mock_suggest.return_value = ["Hey!", "Hello!"]
                
                response = self.service.generate_message(request)
                
                assert response.primary_message == "Hi there!"
                assert len(response.validation_results) == 0
                
    def test_generate_message_no_suggestions(self):
        """Test message generation without suggestions"""
        request = MessageRequest(
            conversation_history=["Hello"],
            user_id="test_user",
            max_suggestions=0
        )
        
        with patch.object(self.service.generator, 'generate_response') as mock_generate:
            
            mock_generate.return_value = "Hi there!"
            
            response = self.service.generate_message(request)
            
            assert response.primary_message == "Hi there!"
            assert len(response.suggestions) == 0
            
    def test_calculate_confidence_high_score(self):
        """Test confidence calculation with high score"""
        message = "Great message!"
        context = MessageContext(conversation_history=["Hello", "Hi"])
        validation_results = [ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message="Good"
        )]
        
        confidence = self.service._calculate_confidence(message, context, validation_results)
        
        assert confidence > 0.8  # Should be high due to good context and no errors
        
    def test_calculate_confidence_with_errors(self):
        """Test confidence calculation with validation errors"""
        message = "Bad message"
        context = MessageContext(conversation_history=["Hello"])
        validation_results = [
            ValidationResult(is_valid=False, level=ValidationLevel.ERROR, message="Error 1"),
            ValidationResult(is_valid=False, level=ValidationLevel.ERROR, message="Error 2")
        ]
        
        confidence = self.service._calculate_confidence(message, context, validation_results)
        
        assert confidence < 0.5  # Should be low due to errors
        
    def test_calculate_confidence_with_warnings(self):
        """Test confidence calculation with warnings"""
        message = "Okay message"
        context = MessageContext(conversation_history=["Hello"])
        validation_results = [
            ValidationResult(is_valid=True, level=ValidationLevel.WARNING, message="Warning 1"),
            ValidationResult(is_valid=True, level=ValidationLevel.WARNING, message="Warning 2")
        ]
        
        confidence = self.service._calculate_confidence(message, context, validation_results)
        
        assert 0.5 < confidence < 0.8  # Should be moderate due to warnings
        
    def test_calculate_confidence_bounds(self):
        """Test confidence calculation stays within bounds"""
        message = "Test message"
        context = MessageContext(conversation_history=[])
        
        # Test with many errors (should not go below 0)
        many_errors = [ValidationResult(is_valid=False, level=ValidationLevel.ERROR, message=f"Error {i}") for i in range(10)]
        confidence = self.service._calculate_confidence(message, context, many_errors)
        assert confidence >= 0.0
        
        # Test with perfect conditions (should not exceed 1)
        good_results = [ValidationResult(is_valid=True, level=ValidationLevel.INFO, message="Good")]
        good_context = MessageContext(conversation_history=["msg1", "msg2", "msg3"])
        confidence = self.service._calculate_confidence(message, good_context, good_results)
        assert confidence <= 1.0
        
    def test_update_user_patterns(self):
        """Test updating user patterns"""
        user_id = "test_user_123"
        messages = ["Hello", "How are you?", "Thanks!"]
        
        with patch.object(self.service.generator, 'analyze_message_patterns') as mock_analyze:
            mock_analyze.return_value = {"avg_length": 10}
            
            self.service.update_user_patterns(user_id, messages)
            
            mock_analyze.assert_called_once_with(user_id, messages)
            
    def test_add_custom_template_success(self):
        """Test adding custom template successfully"""
        template_data = {
            "template_id": "custom_test",
            "message_type": "greeting",
            "tone": "casual",
            "pattern": "Hey {name}!",
            "variables": ["name"],
            "examples": ["Hey John!"]
        }
        
        with patch.object(self.service.template_manager, 'add_template') as mock_add:
            self.service.add_custom_template(template_data)
            
            mock_add.assert_called_once()
            
    def test_add_custom_template_error(self):
        """Test adding custom template with error"""
        invalid_template_data = {
            "template_id": "invalid_test",
            # Missing required fields
        }
        
        with patch('src.message_maker.service.logger') as mock_logger:
            self.service.add_custom_template(invalid_template_data)
            
            mock_logger.error.assert_called_once()
            
    def test_get_service_status(self):
        """Test getting service status"""
        # Add some test data
        self.service.generator.user_patterns["user1"] = {"avg_length": 10}
        self.service.generator.user_patterns["user2"] = {"avg_length": 15}
        
        status = self.service.get_service_status()
        
        assert status["service_name"] == "Message Maker Service"
        assert status["status"] == "active"
        assert status["templates_loaded"] > 0  # Should have default templates
        assert status["users_with_patterns"] == 2
        assert status["validation_rules_active"] is True


class TestMessageMakerServiceIntegration:
    """Integration tests for MessageMakerService"""
    
    def test_complete_workflow(self):
        """Test complete message generation workflow"""
        service = MessageMakerService()
        
        # Create a realistic request
        request = MessageRequest(
            conversation_history=["Hey, how's your day going?", "Pretty good, thanks! How about you?"],
            user_id="integration_test_user",
            message_type="response",
            tone="casual",
            max_suggestions=2,
            require_validation=True
        )
        
        # Generate message
        response = service.generate_message(request)
        
        # Verify response structure
        assert isinstance(response.primary_message, str)
        assert len(response.primary_message) > 0
        assert len(response.suggestions) <= 2
        assert isinstance(response.confidence_score, float)
        assert 0.0 <= response.confidence_score <= 1.0
        assert isinstance(response.metadata, dict)
        
        # Verify validation was performed
        assert isinstance(response.validation_results, list)
        
        # Update user patterns
        service.update_user_patterns(request.user_id, request.conversation_history)
        
        # Verify patterns were stored
        status = service.get_service_status()
        assert status["users_with_patterns"] >= 1
        
    def test_service_with_custom_template(self):
        """Test service with custom template"""
        service = MessageMakerService()
        
        # Add custom template
        custom_template = {
            "template_id": "integration_custom",
            "message_type": "thanks",
            "tone": "casual",
            "pattern": "Thanks a bunch, {name}!",
            "variables": ["name"],
            "examples": ["Thanks a bunch, friend!"]
        }
        
        service.add_custom_template(custom_template)
        
        # Verify template was added
        template = service.template_manager.get_template("integration_custom")
        assert template is not None
        assert template.pattern == "Thanks a bunch, {name}!"
        
        # Test service status includes the new template
        status = service.get_service_status()
        assert status["templates_loaded"] > 4  # Default + custom template