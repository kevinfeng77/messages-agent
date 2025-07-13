#!/usr/bin/env python3
"""
Validation script for the main API function implementation.

This script performs end-to-end validation of the message response generation
API function to ensure it meets all SERENE-59 requirements.
"""

import os
import sys
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.message_maker.api import generate_message_responses, MessageMakerService
from src.message_maker.types import MessageRequest, MessageResponse
from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class APIFunctionValidator:
    """Validator for the main API function implementation."""
    
    def __init__(self):
        """Initialize the validator."""
        self.results = {
            "validation_passed": True,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "error_details": []
        }
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log the result of a test."""
        self.results["tests_run"] += 1
        if passed:
            self.results["tests_passed"] += 1
            logger.info(f"✅ {test_name}: PASSED {details}")
        else:
            self.results["tests_failed"] += 1
            self.results["validation_passed"] = False
            error_msg = f"❌ {test_name}: FAILED {details}"
            logger.error(error_msg)
            self.results["error_details"].append(error_msg)
    
    def validate_function_signature(self) -> None:
        """Validate that the main API function has the correct signature."""
        test_name = "Function Signature Validation"
        
        try:
            # Check that the function exists and is callable
            assert callable(generate_message_responses), "generate_message_responses must be callable"
            
            # Check that MessageMakerService exists and has required method
            service = MessageMakerService()
            assert hasattr(service, 'generate_message_responses'), "MessageMakerService must have generate_message_responses method"
            assert callable(service.generate_message_responses), "MessageMakerService.generate_message_responses must be callable"
            
            self.log_test_result(test_name, True, "- Function exists and is callable")
            
        except Exception as e:
            self.log_test_result(test_name, False, f"- {str(e)}")
    
    def validate_input_validation(self) -> None:
        """Validate that input validation works correctly."""
        test_name = "Input Validation"
        
        try:
            # Test valid input
            valid_request = MessageRequest(
                chat_id=123,
                user_id="test_user",
                contents="Hello world"
            )
            valid_request.validate()  # Should not raise
            
            # Test invalid chat_id
            try:
                invalid_request = MessageRequest(chat_id=-1, user_id="test", contents="test")
                invalid_request.validate()
                raise AssertionError("Should have raised ValueError for negative chat_id")
            except ValueError:
                pass  # Expected
            
            # Test empty user_id
            try:
                invalid_request = MessageRequest(chat_id=1, user_id="", contents="test")
                invalid_request.validate()
                raise AssertionError("Should have raised ValueError for empty user_id")
            except ValueError:
                pass  # Expected
            
            # Test empty contents
            try:
                invalid_request = MessageRequest(chat_id=1, user_id="test", contents="")
                invalid_request.validate()
                raise AssertionError("Should have raised ValueError for empty contents")
            except ValueError:
                pass  # Expected
            
            self.log_test_result(test_name, True, "- All validation rules work correctly")
            
        except Exception as e:
            self.log_test_result(test_name, False, f"- {str(e)}")
    
    @patch('src.message_maker.api.get_chat_history_for_message_generation')
    @patch('src.message_maker.api.LLMClient')
    def validate_workflow_integration(self, mock_llm_client_class, mock_get_chat_history) -> None:
        """Validate that the workflow integrates all components correctly."""
        test_name = "Workflow Integration"
        
        try:
            # Setup mocks
            from src.message_maker.types import ChatMessage
            mock_chat_history = [
                ChatMessage(content="Hi", is_from_me=False, timestamp="2023-01-01 10:00:00"),
                ChatMessage(content="Hello", is_from_me=True, timestamp="2023-01-01 10:01:00")
            ]
            mock_get_chat_history.return_value = mock_chat_history
            
            mock_llm_client = Mock()
            mock_response = MessageResponse(
                response_1="Response 1",
                response_2="Response 2",
                response_3="Response 3"
            )
            mock_llm_client.generate_responses.return_value = mock_response
            mock_llm_client_class.return_value = mock_llm_client
            
            # Test the complete workflow
            request = MessageRequest(
                chat_id=456,
                user_id="integration_test",
                contents="Test message"
            )
            
            result = generate_message_responses(request)
            
            # Verify result structure
            assert isinstance(result, MessageResponse), "Result must be MessageResponse"
            assert hasattr(result, 'response_1'), "Result must have response_1"
            assert hasattr(result, 'response_2'), "Result must have response_2" 
            assert hasattr(result, 'response_3'), "Result must have response_3"
            assert result.response_1 == "Response 1", "response_1 content mismatch"
            assert result.response_2 == "Response 2", "response_2 content mismatch"
            assert result.response_3 == "Response 3", "response_3 content mismatch"
            
            # Verify chat history was retrieved
            mock_get_chat_history.assert_called_once_with(
                chat_id="456",
                user_id="integration_test"
            )
            
            # Verify LLM client was called
            mock_llm_client.generate_responses.assert_called_once()
            
            self.log_test_result(test_name, True, "- All workflow steps execute correctly")
            
        except Exception as e:
            self.log_test_result(test_name, False, f"- {str(e)}")
    
    def validate_error_handling(self) -> None:
        """Validate that error handling works correctly."""
        test_name = "Error Handling"
        
        try:
            service = MessageMakerService()
            
            # Test with invalid request
            invalid_request = MessageRequest(
                chat_id=-1,  # Invalid
                user_id="test",
                contents="test"
            )
            
            try:
                service.generate_message_responses(invalid_request)
                raise AssertionError("Should have raised ValueError for invalid request")
            except ValueError:
                pass  # Expected
            except Exception as e:
                raise AssertionError(f"Expected ValueError but got {type(e).__name__}: {e}")
            
            self.log_test_result(test_name, True, "- Error handling works correctly")
            
        except Exception as e:
            self.log_test_result(test_name, False, f"- {str(e)}")
    
    def validate_response_format(self) -> None:
        """Validate that the response format matches Notion specification."""
        test_name = "Response Format Compliance"
        
        try:
            # Test MessageResponse structure
            response = MessageResponse(
                response_1="Test response 1",
                response_2="Test response 2", 
                response_3="Test response 3"
            )
            
            # Verify to_dict matches expected format
            response_dict = response.to_dict()
            expected_keys = {"response_1", "response_2", "response_3"}
            actual_keys = set(response_dict.keys())
            
            assert actual_keys == expected_keys, f"Response keys mismatch. Expected: {expected_keys}, Got: {actual_keys}"
            
            # Verify JSON serialization works
            json_str = response.to_json()
            parsed = json.loads(json_str)
            assert "response_1" in parsed, "JSON must contain response_1"
            assert "response_2" in parsed, "JSON must contain response_2"
            assert "response_3" in parsed, "JSON must contain response_3"
            
            self.log_test_result(test_name, True, "- Response format matches specification")
            
        except Exception as e:
            self.log_test_result(test_name, False, f"- {str(e)}")
    
    def validate_service_initialization(self) -> None:
        """Validate that MessageMakerService initializes correctly."""
        test_name = "Service Initialization"
        
        try:
            # Test default initialization
            service1 = MessageMakerService()
            assert service1.db_path == "./data/messages.db", "Default db_path incorrect"
            assert service1.llm_client is not None, "LLM client not initialized"
            assert service1.logger is not None, "Logger not initialized"
            
            # Test custom initialization
            custom_path = "/custom/test/path.db"
            service2 = MessageMakerService(db_path=custom_path)
            assert service2.db_path == custom_path, "Custom db_path not set correctly"
            
            self.log_test_result(test_name, True, "- Service initializes correctly")
            
        except Exception as e:
            self.log_test_result(test_name, False, f"- {str(e)}")
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation tests."""
        logger.info("🚀 Starting API function validation...")
        
        # Run all validation tests
        self.validate_function_signature()
        self.validate_input_validation()
        self.validate_workflow_integration()
        self.validate_error_handling()
        self.validate_response_format()
        self.validate_service_initialization()
        
        # Print summary
        if self.results["validation_passed"]:
            logger.info(f"🎉 All validations passed! ({self.results['tests_passed']}/{self.results['tests_run']} tests)")
        else:
            logger.error(f"💥 Validation failed! ({self.results['tests_failed']}/{self.results['tests_run']} tests failed)")
            for error in self.results["error_details"]:
                logger.error(f"   {error}")
        
        return self.results


def main():
    """Main validation execution."""
    print("=" * 80)
    print("API Function Validation for SERENE-59")
    print("=" * 80)
    
    validator = APIFunctionValidator()
    results = validator.run_all_validations()
    
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {results['tests_run']}")
    print(f"Passed: {results['tests_passed']}")
    print(f"Failed: {results['tests_failed']}")
    print(f"Overall Result: {'✅ PASSED' if results['validation_passed'] else '❌ FAILED'}")
    
    if not results['validation_passed']:
        print("\nFailed Tests:")
        for error in results['error_details']:
            print(f"  - {error}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)