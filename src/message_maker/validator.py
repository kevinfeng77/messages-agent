"""Message validation utilities for ensuring quality and appropriateness"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels"""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of message validation"""
    
    is_valid: bool
    level: ValidationLevel
    message: str
    suggestion: Optional[str] = None


class MessageValidator:
    """Validates generated messages for quality, appropriateness, and correctness"""
    
    def __init__(self):
        self.profanity_words = set()
        self.common_typos = {}
        self._load_validation_rules()
        
    def _load_validation_rules(self):
        """Load validation rules and word lists"""
        logger.info("Loading message validation rules")
        
        # Basic profanity filter (expandable)
        self.profanity_words = {
            "badword1", "badword2"  # Placeholder - would load from external source
        }
        
        # Common typos and corrections
        self.common_typos = {
            "teh": "the",
            "recieve": "receive",
            "seperate": "separate",
            "definately": "definitely"
        }
        
    def validate_message(self, message: str) -> List[ValidationResult]:
        """
        Comprehensive validation of a message
        
        Args:
            message: Message text to validate
            
        Returns:
            List of validation results
        """
        logger.debug(f"Validating message: {message[:50]}...")
        
        results = []
        
        # Basic validations
        results.extend(self._validate_length(message))
        results.extend(self._validate_profanity(message))
        results.extend(self._validate_spelling(message))
        results.extend(self._validate_grammar(message))
        results.extend(self._validate_tone(message))
        
        return results
        
    def _validate_length(self, message: str) -> List[ValidationResult]:
        """Validate message length"""
        results = []
        
        if len(message) == 0:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Message is empty",
                suggestion="Provide a message with content"
            ))
        elif len(message) < 2:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Message is very short",
                suggestion="Consider adding more context"
            ))
        elif len(message) > 1000:
            results.append(ValidationResult(
                is_valid=True,
                level=ValidationLevel.WARNING,
                message="Message is quite long",
                suggestion="Consider breaking into multiple messages"
            ))
            
        return results
        
    def _validate_profanity(self, message: str) -> List[ValidationResult]:
        """Check for inappropriate content"""
        results = []
        
        words = message.lower().split()
        found_profanity = [word for word in words if word in self.profanity_words]
        
        if found_profanity:
            results.append(ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Inappropriate language detected: {', '.join(found_profanity)}",
                suggestion="Remove or replace inappropriate words"
            ))
            
        return results
        
    def _validate_spelling(self, message: str) -> List[ValidationResult]:
        """Check for common spelling errors"""
        results = []
        
        words = re.findall(r'\b\w+\b', message.lower())
        typos_found = []
        
        for word in words:
            if word in self.common_typos:
                typos_found.append((word, self.common_typos[word]))
                
        if typos_found:
            typo_list = [f"'{typo}' -> '{correct}'" for typo, correct in typos_found]
            results.append(ValidationResult(
                is_valid=True,
                level=ValidationLevel.WARNING,
                message=f"Possible typos detected: {', '.join(typo_list)}",
                suggestion="Consider spell checking"
            ))
            
        return results
        
    def _validate_grammar(self, message: str) -> List[ValidationResult]:
        """Basic grammar validation"""
        results = []
        
        # Check for sentence structure
        if message and not message[0].isupper():
            results.append(ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Message doesn't start with capital letter",
                suggestion="Consider capitalizing first letter"
            ))
            
        # Check for punctuation at end of sentences
        if len(message) > 10 and message[-1] not in '.!?':
            results.append(ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Message doesn't end with punctuation",
                suggestion="Consider adding appropriate punctuation"
            ))
            
        return results
        
    def _validate_tone(self, message: str) -> List[ValidationResult]:
        """Validate message tone appropriateness"""
        results = []
        
        # Check for excessive exclamation marks
        exclamation_count = message.count('!')
        if exclamation_count > 3:
            results.append(ValidationResult(
                is_valid=True,
                level=ValidationLevel.WARNING,
                message="Many exclamation marks detected",
                suggestion="Consider reducing emphasis for better tone"
            ))
            
        # Check for all caps (shouting)
        if message.isupper() and len(message) > 5:
            results.append(ValidationResult(
                is_valid=True,
                level=ValidationLevel.WARNING,
                message="Message is in all caps",
                suggestion="Consider using normal capitalization"
            ))
            
        return results
        
    def is_message_valid(self, message: str) -> bool:
        """
        Quick validation check
        
        Args:
            message: Message to validate
            
        Returns:
            True if message passes all validations, False otherwise
        """
        results = self.validate_message(message)
        return all(result.is_valid for result in results if result.level == ValidationLevel.ERROR)
        
    def get_validation_summary(self, message: str) -> Dict[str, Any]:
        """
        Get validation summary with counts and suggestions
        
        Args:
            message: Message to validate
            
        Returns:
            Dictionary with validation summary
        """
        results = self.validate_message(message)
        
        summary = {
            "is_valid": self.is_message_valid(message),
            "total_issues": len(results),
            "errors": len([r for r in results if r.level == ValidationLevel.ERROR]),
            "warnings": len([r for r in results if r.level == ValidationLevel.WARNING]),
            "info": len([r for r in results if r.level == ValidationLevel.INFO]),
            "suggestions": [r.suggestion for r in results if r.suggestion],
            "details": results
        }
        
        return summary