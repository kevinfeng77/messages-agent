#!/usr/bin/env python3
"""Validation script for message maker service directory structure and functionality"""

import sys
import os
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def validate_directory_structure() -> Tuple[bool, List[str]]:
    """
    Validate that the message maker service directory structure is correct
    
    Returns:
        Tuple of (success, issues)
    """
    issues = []
    base_path = Path(__file__).parent.parent.parent / "src" / "message_maker"
    
    # Check main directory exists
    if not base_path.exists():
        issues.append("message_maker directory does not exist")
        return False, issues
        
    # Check required files
    required_files = [
        "__init__.py",
        "generator.py", 
        "template_manager.py",
        "validator.py",
        "service.py",
        "config.py"
    ]
    
    for file_name in required_files:
        file_path = base_path / file_name
        if not file_path.exists():
            issues.append(f"Required file missing: {file_name}")
        elif file_path.stat().st_size == 0:
            issues.append(f"Required file is empty: {file_name}")
            
    # Check tests directory
    tests_path = base_path / "tests"
    if not tests_path.exists():
        issues.append("tests directory does not exist")
    else:
        required_test_files = [
            "__init__.py",
            "test_generator.py",
            "test_template_manager.py", 
            "test_validator.py",
            "test_service.py",
            "test_config.py"
        ]
        
        for test_file in required_test_files:
            test_path = tests_path / test_file
            if not test_path.exists():
                issues.append(f"Required test file missing: {test_file}")
            elif test_path.stat().st_size == 0:
                issues.append(f"Required test file is empty: {test_file}")
                
    return len(issues) == 0, issues


def validate_imports() -> Tuple[bool, List[str]]:
    """
    Validate that all modules can be imported successfully
    
    Returns:
        Tuple of (success, issues)
    """
    issues = []
    modules_to_test = [
        "src.message_maker",
        "src.message_maker.generator",
        "src.message_maker.template_manager", 
        "src.message_maker.validator",
        "src.message_maker.service",
        "src.message_maker.config"
    ]
    
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            print(f"✓ Successfully imported {module_name}")
        except ImportError as e:
            issues.append(f"Failed to import {module_name}: {e}")
        except Exception as e:
            issues.append(f"Error importing {module_name}: {e}")
            
    return len(issues) == 0, issues


def validate_class_instantiation() -> Tuple[bool, List[str]]:
    """
    Validate that key classes can be instantiated
    
    Returns:
        Tuple of (success, issues)
    """
    issues = []
    
    try:
        # Test MessageGenerator
        from src.message_maker.generator import MessageGenerator, MessageContext
        generator = MessageGenerator()
        context = MessageContext(conversation_history=["test"])
        print("✓ MessageGenerator instantiated successfully")
        
        # Test TemplateManager
        from src.message_maker.template_manager import TemplateManager
        template_manager = TemplateManager()
        print("✓ TemplateManager instantiated successfully")
        
        # Test MessageValidator
        from src.message_maker.validator import MessageValidator
        validator = MessageValidator()
        print("✓ MessageValidator instantiated successfully")
        
        # Test MessageMakerService
        from src.message_maker.service import MessageMakerService
        service = MessageMakerService()
        print("✓ MessageMakerService instantiated successfully")
        
        # Test ConfigManager
        from src.message_maker.config import ConfigManager
        config_manager = ConfigManager()
        print("✓ ConfigManager instantiated successfully")
        
    except Exception as e:
        issues.append(f"Failed to instantiate classes: {e}")
        
    return len(issues) == 0, issues


def validate_functionality() -> Tuple[bool, List[str]]:
    """
    Validate basic functionality of the service
    
    Returns:
        Tuple of (success, issues)
    """
    issues = []
    
    try:
        from src.message_maker.service import MessageMakerService, MessageRequest
        
        # Test basic service functionality
        service = MessageMakerService()
        
        # Test message generation
        request = MessageRequest(
            conversation_history=["Hello", "Hi there"],
            user_id="test_user"
        )
        
        response = service.generate_message(request)
        
        # Validate response structure
        if not hasattr(response, 'primary_message'):
            issues.append("Response missing primary_message attribute")
        elif not isinstance(response.primary_message, str):
            issues.append("primary_message is not a string")
            
        if not hasattr(response, 'suggestions'):
            issues.append("Response missing suggestions attribute")
        elif not isinstance(response.suggestions, list):
            issues.append("suggestions is not a list")
            
        if not hasattr(response, 'confidence_score'):
            issues.append("Response missing confidence_score attribute")
        elif not isinstance(response.confidence_score, (int, float)):
            issues.append("confidence_score is not numeric")
        elif not (0.0 <= response.confidence_score <= 1.0):
            issues.append("confidence_score not in valid range [0.0, 1.0]")
            
        print("✓ Basic message generation functionality validated")
        
        # Test service status
        status = service.get_service_status()
        if not isinstance(status, dict):
            issues.append("Service status is not a dictionary")
        elif "service_name" not in status:
            issues.append("Service status missing service_name")
            
        print("✓ Service status functionality validated")
        
    except Exception as e:
        issues.append(f"Functionality validation failed: {e}")
        
    return len(issues) == 0, issues


def validate_template_functionality() -> Tuple[bool, List[str]]:
    """
    Validate template management functionality
    
    Returns:
        Tuple of (success, issues)
    """
    issues = []
    
    try:
        from src.message_maker.template_manager import (
            TemplateManager, MessageTemplate, MessageType, ToneType
        )
        
        manager = TemplateManager()
        
        # Test default templates loaded
        if len(manager.templates) == 0:
            issues.append("No default templates loaded")
        else:
            print(f"✓ {len(manager.templates)} default templates loaded")
            
        # Test finding templates
        casual_greetings = manager.find_templates(MessageType.GREETING, ToneType.CASUAL)
        if len(casual_greetings) == 0:
            issues.append("No casual greeting templates found")
        else:
            print(f"✓ Found {len(casual_greetings)} casual greeting templates")
            
        # Test template filling
        if casual_greetings:
            template = casual_greetings[0]
            if "name" in template.variables:
                filled = template.fill_template(name="TestUser")
                if "TestUser" not in filled:
                    issues.append("Template filling did not work correctly")
                else:
                    print("✓ Template filling functionality validated")
                    
    except Exception as e:
        issues.append(f"Template functionality validation failed: {e}")
        
    return len(issues) == 0, issues


def validate_validation_functionality() -> Tuple[bool, List[str]]:
    """
    Validate message validation functionality
    
    Returns:
        Tuple of (success, issues)
    """
    issues = []
    
    try:
        from src.message_maker.validator import MessageValidator
        
        validator = MessageValidator()
        
        # Test empty message validation
        empty_results = validator.validate_message("")
        if len(empty_results) == 0:
            issues.append("Empty message validation returned no results")
        else:
            print("✓ Empty message validation working")
            
        # Test normal message validation
        normal_results = validator.validate_message("This is a normal message.")
        if not isinstance(normal_results, list):
            issues.append("Validation results not returned as list")
        else:
            print("✓ Normal message validation working")
            
        # Test validation summary
        summary = validator.get_validation_summary("Test message")
        required_keys = ["is_valid", "total_issues", "errors", "warnings", "info"]
        for key in required_keys:
            if key not in summary:
                issues.append(f"Validation summary missing key: {key}")
                
        if len(issues) == 0:
            print("✓ Validation summary functionality validated")
            
    except Exception as e:
        issues.append(f"Validation functionality validation failed: {e}")
        
    return len(issues) == 0, issues


def validate_config_functionality() -> Tuple[bool, List[str]]:
    """
    Validate configuration management functionality
    
    Returns:
        Tuple of (success, issues)
    """
    issues = []
    
    try:
        from src.message_maker.config import ConfigManager
        
        # Use a temporary path to avoid affecting real config
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            # Test config loading
            config = manager.get_config()
            if config.service_name != "Message Maker Service":
                issues.append("Default service name not set correctly")
            else:
                print("✓ Default configuration loaded correctly")
                
            # Test config validation
            validation_result = manager.validate_config()
            if not validation_result["is_valid"]:
                issues.append(f"Default configuration validation failed: {validation_result['issues']}")
            else:
                print("✓ Configuration validation working")
                
            # Test config updates
            manager.update_config(debug_mode=True)
            if not manager.config.debug_mode:
                issues.append("Configuration update failed")
            else:
                print("✓ Configuration update working")
                
    except Exception as e:
        issues.append(f"Configuration functionality validation failed: {e}")
        
    return len(issues) == 0, issues


def run_all_validations() -> Dict[str, Any]:
    """
    Run all validation tests and return results
    
    Returns:
        Dictionary with validation results
    """
    print("=" * 60)
    print("MESSAGE MAKER SERVICE VALIDATION")
    print("=" * 60)
    
    results = {}
    all_issues = []
    
    # Directory structure validation
    print("\n1. Validating directory structure...")
    structure_success, structure_issues = validate_directory_structure()
    results["directory_structure"] = {
        "success": structure_success,
        "issues": structure_issues
    }
    all_issues.extend(structure_issues)
    
    if structure_success:
        print("✓ Directory structure validation passed")
    else:
        print("✗ Directory structure validation failed")
        for issue in structure_issues:
            print(f"  - {issue}")
    
    # Import validation
    print("\n2. Validating imports...")
    import_success, import_issues = validate_imports()
    results["imports"] = {
        "success": import_success,
        "issues": import_issues
    }
    all_issues.extend(import_issues)
    
    if not import_success:
        print("✗ Import validation failed")
        for issue in import_issues:
            print(f"  - {issue}")
    
    # Only proceed with functional tests if imports work
    if import_success:
        # Class instantiation validation
        print("\n3. Validating class instantiation...")
        instantiation_success, instantiation_issues = validate_class_instantiation()
        results["instantiation"] = {
            "success": instantiation_success,
            "issues": instantiation_issues
        }
        all_issues.extend(instantiation_issues)
        
        if not instantiation_success:
            print("✗ Class instantiation validation failed")
            for issue in instantiation_issues:
                print(f"  - {issue}")
        
        # Functionality validation
        print("\n4. Validating basic functionality...")
        functionality_success, functionality_issues = validate_functionality()
        results["functionality"] = {
            "success": functionality_success,
            "issues": functionality_issues
        }
        all_issues.extend(functionality_issues)
        
        if not functionality_success:
            print("✗ Functionality validation failed")
            for issue in functionality_issues:
                print(f"  - {issue}")
        
        # Template functionality validation
        print("\n5. Validating template functionality...")
        template_success, template_issues = validate_template_functionality()
        results["templates"] = {
            "success": template_success,
            "issues": template_issues
        }
        all_issues.extend(template_issues)
        
        if not template_success:
            print("✗ Template functionality validation failed")
            for issue in template_issues:
                print(f"  - {issue}")
        
        # Validation functionality validation
        print("\n6. Validating validation functionality...")
        validation_success, validation_issues = validate_validation_functionality()
        results["validation"] = {
            "success": validation_success,
            "issues": validation_issues
        }
        all_issues.extend(validation_issues)
        
        if not validation_success:
            print("✗ Validation functionality validation failed")
            for issue in validation_issues:
                print(f"  - {issue}")
        
        # Config functionality validation
        print("\n7. Validating configuration functionality...")
        config_success, config_issues = validate_config_functionality()
        results["config"] = {
            "success": config_success,
            "issues": config_issues
        }
        all_issues.extend(config_issues)
        
        if not config_success:
            print("✗ Configuration functionality validation failed")
            for issue in config_issues:
                print(f"  - {issue}")
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r["success"])
    
    print(f"Tests run: {total_tests}")
    print(f"Tests passed: {successful_tests}")
    print(f"Tests failed: {total_tests - successful_tests}")
    print(f"Total issues found: {len(all_issues)}")
    
    overall_success = len(all_issues) == 0
    
    if overall_success:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("Message Maker Service is ready for use.")
    else:
        print("\n❌ VALIDATION FAILED")
        print("Please address the issues above before using the service.")
    
    results["overall"] = {
        "success": overall_success,
        "total_tests": total_tests,
        "passed_tests": successful_tests,
        "failed_tests": total_tests - successful_tests,
        "total_issues": len(all_issues),
        "all_issues": all_issues
    }
    
    return results


if __name__ == "__main__":
    # Run validation and exit with appropriate code
    validation_results = run_all_validations()
    
    if validation_results["overall"]["success"]:
        sys.exit(0)
    else:
        sys.exit(1)