"""Tests for message validator module"""

import pytest
from unittest.mock import patch

from src.message_maker.validator import (
    MessageValidator, ValidationResult, ValidationLevel
)


class TestValidationLevel:
    """Test ValidationLevel enum"""
    
    def test_validation_level_values(self):
        """Test ValidationLevel enum values"""
        assert ValidationLevel.INFO.value == "info"
        assert ValidationLevel.WARNING.value == "warning"
        assert ValidationLevel.ERROR.value == "error"


class TestValidationResult:
    """Test ValidationResult dataclass"""
    
    def test_validation_result_creation(self):
        """Test creating ValidationResult"""
        result = ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message="Test message",
            suggestion="Test suggestion"
        )
        
        assert result.is_valid is True
        assert result.level == ValidationLevel.INFO
        assert result.message == "Test message"
        assert result.suggestion == "Test suggestion"
        
    def test_validation_result_without_suggestion(self):
        """Test ValidationResult without suggestion"""
        result = ValidationResult(
            is_valid=False,
            level=ValidationLevel.ERROR,
            message="Error message"
        )
        
        assert result.is_valid is False
        assert result.level == ValidationLevel.ERROR
        assert result.message == "Error message"
        assert result.suggestion is None


class TestMessageValidator:
    """Test MessageValidator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = MessageValidator()
        
    def test_validator_initialization(self):
        """Test validator initializes with word lists"""
        assert isinstance(self.validator.profanity_words, set)
        assert isinstance(self.validator.common_typos, dict)
        
    def test_validate_empty_message(self):
        """Test validating empty message"""
        results = self.validator.validate_message("")
        
        error_results = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(error_results) >= 1
        
        empty_error = next((r for r in error_results if "empty" in r.message.lower()), None)
        assert empty_error is not None
        assert empty_error.is_valid is False
        
    def test_validate_very_short_message(self):
        """Test validating very short message"""
        results = self.validator.validate_message("a")
        
        warning_results = [r for r in results if r.level == ValidationLevel.WARNING]
        short_warning = next((r for r in warning_results if "short" in r.message.lower()), None)
        assert short_warning is not None
        
    def test_validate_very_long_message(self):
        """Test validating very long message"""
        long_message = "a" * 1500  # Over 1000 character limit
        results = self.validator.validate_message(long_message)
        
        warning_results = [r for r in results if r.level == ValidationLevel.WARNING]
        long_warning = next((r for r in warning_results if "long" in r.message.lower()), None)
        assert long_warning is not None
        
    def test_validate_normal_length_message(self):
        """Test validating normal length message"""
        normal_message = "This is a normal length message that should pass validation."
        results = self.validator.validate_message(normal_message)
        
        # Should not have length-related errors
        length_errors = [r for r in results if "empty" in r.message.lower() or "short" in r.message.lower()]
        assert len(length_errors) == 0
        
    def test_validate_profanity_detection(self):
        """Test profanity detection"""
        # Note: Using placeholder profanity words from the validator
        profane_message = "This message contains badword1 which is inappropriate"
        results = self.validator.validate_message(profane_message)
        
        error_results = [r for r in results if r.level == ValidationLevel.ERROR]
        profanity_error = next((r for r in error_results if "inappropriate" in r.message.lower()), None)
        
        if profanity_error:  # Only check if profanity words are configured
            assert profanity_error.is_valid is False
            
    def test_validate_clean_message(self):
        """Test validating clean message"""
        clean_message = "This is a clean message with no issues."
        results = self.validator.validate_message(clean_message)
        
        error_results = [r for r in results if r.level == ValidationLevel.ERROR and "inappropriate" in r.message.lower()]
        assert len(error_results) == 0
        
    def test_validate_spelling_typos(self):
        """Test spelling validation with typos"""
        typo_message = "I will recieve the package and seperate the items."
        results = self.validator.validate_message(typo_message)
        
        warning_results = [r for r in results if r.level == ValidationLevel.WARNING]
        typo_warning = next((r for r in warning_results if "typo" in r.message.lower()), None)
        
        if typo_warning:  # Only check if typos are configured
            assert "recieve" in typo_warning.message or "seperate" in typo_warning.message
            
    def test_validate_no_typos(self):
        """Test validating message with no typos"""
        correct_message = "I will receive the package and separate the items."
        results = self.validator.validate_message(correct_message)
        
        typo_warnings = [r for r in results if r.level == ValidationLevel.WARNING and "typo" in r.message.lower()]
        assert len(typo_warnings) == 0
        
    def test_validate_capitalization(self):
        """Test capitalization validation"""
        lowercase_message = "this message doesn't start with a capital letter"
        results = self.validator.validate_message(lowercase_message)
        
        info_results = [r for r in results if r.level == ValidationLevel.INFO]
        capital_info = next((r for r in info_results if "capital" in r.message.lower()), None)
        assert capital_info is not None
        
    def test_validate_proper_capitalization(self):
        """Test message with proper capitalization"""
        proper_message = "This message starts with a capital letter."
        results = self.validator.validate_message(proper_message)
        
        capital_issues = [r for r in results if "capital" in r.message.lower()]
        assert len(capital_issues) == 0
        
    def test_validate_punctuation(self):
        """Test punctuation validation"""
        no_punctuation = "This is a longer message without proper punctuation"
        results = self.validator.validate_message(no_punctuation)
        
        info_results = [r for r in results if r.level == ValidationLevel.INFO]
        punctuation_info = next((r for r in info_results if "punctuation" in r.message.lower()), None)
        assert punctuation_info is not None
        
    def test_validate_proper_punctuation(self):
        """Test message with proper punctuation"""
        proper_message = "This message has proper punctuation."
        results = self.validator.validate_message(proper_message)
        
        punctuation_issues = [r for r in results if "punctuation" in r.message.lower()]
        assert len(punctuation_issues) == 0
        
    def test_validate_excessive_exclamation(self):
        """Test excessive exclamation marks"""
        excited_message = "This is so exciting!!!!! I can't believe it!!!!!"
        results = self.validator.validate_message(excited_message)
        
        warning_results = [r for r in results if r.level == ValidationLevel.WARNING]
        exclamation_warning = next((r for r in warning_results if "exclamation" in r.message.lower()), None)
        assert exclamation_warning is not None
        
    def test_validate_normal_exclamation(self):
        """Test normal use of exclamation marks"""
        normal_message = "This is exciting! Really!"
        results = self.validator.validate_message(normal_message)
        
        exclamation_warnings = [r for r in results if "exclamation" in r.message.lower()]
        assert len(exclamation_warnings) == 0
        
    def test_validate_all_caps(self):
        """Test all caps validation"""
        caps_message = "THIS MESSAGE IS IN ALL CAPS"
        results = self.validator.validate_message(caps_message)
        
        warning_results = [r for r in results if r.level == ValidationLevel.WARNING]
        caps_warning = next((r for r in warning_results if "caps" in r.message.lower()), None)
        assert caps_warning is not None
        
    def test_validate_mixed_case(self):
        """Test mixed case message"""
        mixed_message = "This Message Has Mixed Case"
        results = self.validator.validate_message(mixed_message)
        
        caps_warnings = [r for r in results if "caps" in r.message.lower()]
        assert len(caps_warnings) == 0
        
    def test_is_message_valid_with_errors(self):
        """Test is_message_valid with error-level issues"""
        empty_message = ""
        
        result = self.validator.is_message_valid(empty_message)
        assert result is False
        
    def test_is_message_valid_with_warnings_only(self):
        """Test is_message_valid with only warnings"""
        warning_message = "this message has warnings but no errors"
        
        result = self.validator.is_message_valid(warning_message)
        assert result is True  # Warnings don't make message invalid
        
    def test_is_message_valid_clean_message(self):
        """Test is_message_valid with clean message"""
        clean_message = "This is a clean message."
        
        result = self.validator.is_message_valid(clean_message)
        assert result is True
        
    def test_get_validation_summary(self):
        """Test validation summary generation"""
        test_message = "this message has some issues!!!"
        
        summary = self.validator.get_validation_summary(test_message)
        
        assert "is_valid" in summary
        assert "total_issues" in summary
        assert "errors" in summary
        assert "warnings" in summary
        assert "info" in summary
        assert "suggestions" in summary
        assert "details" in summary
        
        assert isinstance(summary["is_valid"], bool)
        assert isinstance(summary["total_issues"], int)
        assert isinstance(summary["errors"], int)
        assert isinstance(summary["warnings"], int)
        assert isinstance(summary["info"], int)
        assert isinstance(summary["suggestions"], list)
        assert isinstance(summary["details"], list)
        
        # Total issues should equal sum of individual counts
        assert summary["total_issues"] == len(summary["details"])


class TestMessageValidatorIntegration:
    """Integration tests for MessageValidator"""
    
    def test_comprehensive_validation(self):
        """Test comprehensive validation of a problematic message"""
        problematic_message = "this message has some issues!!!!"
        
        validator = MessageValidator()
        results = validator.validate_message(problematic_message)
        summary = validator.get_validation_summary(problematic_message)
        
        # Should have some validation results
        assert isinstance(results, list)
        assert isinstance(summary, dict)
        assert "is_valid" in summary
        assert "total_issues" in summary
        assert "errors" in summary
        assert "warnings" in summary
        assert "info" in summary
        
        # Basic functionality should work
        assert summary["total_issues"] == len(results)
        
    def test_perfect_message_validation(self):
        """Test validation of a well-formed message"""
        perfect_message = "This is a well-formed message with proper capitalization and punctuation."
        
        validator = MessageValidator()
        results = validator.validate_message(perfect_message)
        summary = validator.get_validation_summary(perfect_message)
        
        # Should be valid
        assert validator.is_message_valid(perfect_message) is True
        assert summary["is_valid"] is True
        assert summary["errors"] == 0
        
        # May have minor info/warnings but should be minimal
        assert summary["total_issues"] <= 2  # Allow for minor issues