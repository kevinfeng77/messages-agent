"""Main message maker service orchestrating generation, templates, and validation"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .generator import MessageGenerator, MessageContext
from .template_manager import TemplateManager, MessageType, ToneType
from .validator import MessageValidator, ValidationResult
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class MessageRequest:
    """Request for message generation"""
    
    conversation_history: List[str]
    user_id: str
    message_type: str = "response"
    tone: str = "casual"
    platform: str = "imessage"
    require_validation: bool = True
    max_suggestions: int = 3


@dataclass
class MessageResponse:
    """Response containing generated messages and validation results"""
    
    primary_message: str
    suggestions: List[str]
    validation_results: List[ValidationResult]
    confidence_score: float
    metadata: Dict[str, Any]


class MessageMakerService:
    """
    Main service for intelligent message generation
    
    Orchestrates message generation, template management, and validation
    to provide high-quality, contextually appropriate message responses.
    """
    
    def __init__(self):
        self.generator = MessageGenerator()
        self.template_manager = TemplateManager()
        self.validator = MessageValidator()
        logger.info("Message Maker Service initialized")
        
    def generate_message(self, request: MessageRequest) -> MessageResponse:
        """
        Generate a message response based on the request
        
        Args:
            request: MessageRequest containing context and preferences
            
        Returns:
            MessageResponse with generated content and validation
        """
        logger.info(f"Processing message request for user {request.user_id}")
        
        # Create message context
        context = MessageContext(
            conversation_history=request.conversation_history,
            message_type=request.message_type,
            platform=request.platform,
            tone=request.tone
        )
        
        # Generate primary message
        primary_message = self.generator.generate_response(context)
        
        # Generate additional suggestions
        suggestions = []
        if request.max_suggestions > 0:
            suggestions = self.generator.suggest_responses(context, request.max_suggestions)
            
        # Validate messages
        validation_results = []
        if request.require_validation:
            validation_results.extend(self.validator.validate_message(primary_message))
            for suggestion in suggestions:
                validation_results.extend(self.validator.validate_message(suggestion))
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            primary_message, 
            context, 
            validation_results
        )
        
        # Prepare metadata
        metadata = {
            "generation_method": "template_based",
            "template_used": None,
            "user_patterns_applied": request.user_id in self.generator.user_patterns,
            "validation_passed": all(r.is_valid for r in validation_results),
            "processing_time": 0.0  # Would be calculated in real implementation
        }
        
        response = MessageResponse(
            primary_message=primary_message,
            suggestions=suggestions,
            validation_results=validation_results,
            confidence_score=confidence_score,
            metadata=metadata
        )
        
        logger.info(f"Generated message response with confidence {confidence_score:.2f}")
        return response
        
    def _calculate_confidence(
        self, 
        message: str, 
        context: MessageContext, 
        validation_results: List[ValidationResult]
    ) -> float:
        """
        Calculate confidence score for generated message
        
        Args:
            message: Generated message
            context: Original context
            validation_results: Validation results
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_score = 0.8  # Base confidence for successful generation
        
        # Reduce confidence for validation issues
        error_count = sum(1 for r in validation_results if not r.is_valid)
        warning_count = sum(1 for r in validation_results if r.level.value == "warning")
        
        confidence = base_score - (error_count * 0.3) - (warning_count * 0.1)
        
        # Increase confidence if we have conversation history
        if context.conversation_history and len(context.conversation_history) > 1:
            confidence += 0.1
            
        # Ensure confidence is in valid range
        return max(0.0, min(1.0, confidence))
        
    def update_user_patterns(self, user_id: str, messages: List[str]):
        """
        Update user-specific message patterns
        
        Args:
            user_id: Unique identifier for the user
            messages: List of user's recent messages for pattern analysis
        """
        logger.info(f"Updating patterns for user {user_id}")
        self.generator.analyze_message_patterns(user_id, messages)
        
    def add_custom_template(self, template_data: Dict[str, Any]):
        """
        Add a custom message template
        
        Args:
            template_data: Dictionary containing template information
        """
        try:
            from .template_manager import MessageTemplate
            
            template = MessageTemplate(
                template_id=template_data["template_id"],
                message_type=MessageType(template_data["message_type"]),
                tone=ToneType(template_data["tone"]),
                pattern=template_data["pattern"],
                variables=template_data.get("variables", []),
                examples=template_data.get("examples", [])
            )
            
            self.template_manager.add_template(template)
            logger.info(f"Added custom template: {template.template_id}")
            
        except Exception as e:
            logger.error(f"Error adding custom template: {e}")
            
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get current service status and statistics
        
        Returns:
            Dictionary with service status information
        """
        return {
            "service_name": "Message Maker Service",
            "status": "active",
            "templates_loaded": len(self.template_manager.templates),
            "users_with_patterns": len(self.generator.user_patterns),
            "validation_rules_active": True
        }