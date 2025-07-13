"""Tests for message maker configuration module"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.message_maker.config import (
    ConfigManager, ServiceConfig, GenerationConfig, ValidationConfig, TemplateConfig
)


class TestGenerationConfig:
    """Test GenerationConfig dataclass"""
    
    def test_generation_config_defaults(self):
        """Test GenerationConfig default values"""
        config = GenerationConfig()
        
        assert config.max_response_length == 500
        assert config.min_response_length == 5
        assert config.default_tone == "casual"
        assert config.default_message_type == "response"
        assert config.enable_user_patterns is True
        assert config.pattern_analysis_threshold == 10
        
    def test_generation_config_custom_values(self):
        """Test GenerationConfig with custom values"""
        config = GenerationConfig(
            max_response_length=1000,
            min_response_length=10,
            default_tone="formal",
            default_message_type="greeting",
            enable_user_patterns=False,
            pattern_analysis_threshold=20
        )
        
        assert config.max_response_length == 1000
        assert config.min_response_length == 10
        assert config.default_tone == "formal"
        assert config.default_message_type == "greeting"
        assert config.enable_user_patterns is False
        assert config.pattern_analysis_threshold == 20


class TestValidationConfig:
    """Test ValidationConfig dataclass"""
    
    def test_validation_config_defaults(self):
        """Test ValidationConfig default values"""
        config = ValidationConfig()
        
        assert config.enable_profanity_filter is True
        assert config.enable_spell_check is True
        assert config.enable_grammar_check is True
        assert config.enable_tone_analysis is True
        assert config.max_warning_threshold == 3
        assert config.auto_fix_typos is False
        
    def test_validation_config_custom_values(self):
        """Test ValidationConfig with custom values"""
        config = ValidationConfig(
            enable_profanity_filter=False,
            enable_spell_check=False,
            enable_grammar_check=False,
            enable_tone_analysis=False,
            max_warning_threshold=5,
            auto_fix_typos=True
        )
        
        assert config.enable_profanity_filter is False
        assert config.enable_spell_check is False
        assert config.enable_grammar_check is False
        assert config.enable_tone_analysis is False
        assert config.max_warning_threshold == 5
        assert config.auto_fix_typos is True


class TestTemplateConfig:
    """Test TemplateConfig dataclass"""
    
    def test_template_config_defaults(self):
        """Test TemplateConfig default values"""
        config = TemplateConfig()
        
        assert config.template_directory == "templates"
        assert config.auto_load_templates is True
        assert config.enable_custom_templates is True
        assert config.template_cache_size == 100
        
    def test_template_config_custom_values(self):
        """Test TemplateConfig with custom values"""
        config = TemplateConfig(
            template_directory="custom_templates",
            auto_load_templates=False,
            enable_custom_templates=False,
            template_cache_size=50
        )
        
        assert config.template_directory == "custom_templates"
        assert config.auto_load_templates is False
        assert config.enable_custom_templates is False
        assert config.template_cache_size == 50


class TestServiceConfig:
    """Test ServiceConfig dataclass"""
    
    def test_service_config_defaults(self):
        """Test ServiceConfig default values and post_init"""
        config = ServiceConfig()
        
        assert config.service_name == "Message Maker Service"
        assert config.version == "1.0.0"
        assert config.debug_mode is False
        assert config.log_level == "INFO"
        assert isinstance(config.generation, GenerationConfig)
        assert isinstance(config.validation, ValidationConfig)
        assert isinstance(config.templates, TemplateConfig)
        
    def test_service_config_with_custom_sub_configs(self):
        """Test ServiceConfig with custom sub-configurations"""
        generation = GenerationConfig(max_response_length=1000)
        validation = ValidationConfig(enable_profanity_filter=False)
        templates = TemplateConfig(template_cache_size=200)
        
        config = ServiceConfig(
            service_name="Custom Service",
            version="2.0.0",
            debug_mode=True,
            log_level="DEBUG",
            generation=generation,
            validation=validation,
            templates=templates
        )
        
        assert config.service_name == "Custom Service"
        assert config.version == "2.0.0"
        assert config.debug_mode is True
        assert config.log_level == "DEBUG"
        assert config.generation.max_response_length == 1000
        assert config.validation.enable_profanity_filter is False
        assert config.templates.template_cache_size == 200


class TestConfigManager:
    """Test ConfigManager class"""
    
    def test_config_manager_initialization_no_file(self):
        """Test ConfigManager initialization without existing config file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            
            with patch('src.message_maker.config.logger') as mock_logger:
                manager = ConfigManager(config_path)
                
                assert isinstance(manager.config, ServiceConfig)
                assert config_path.exists()  # Should create default config
                mock_logger.info.assert_called()
                
    def test_config_manager_load_existing_config(self):
        """Test ConfigManager loading existing config file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "existing_config.json"
            
            # Create test config file
            test_config = {
                "service_name": "Test Service",
                "version": "3.0.0",
                "debug_mode": True,
                "log_level": "DEBUG",
                "generation": {
                    "max_response_length": 750,
                    "default_tone": "formal"
                },
                "validation": {
                    "enable_profanity_filter": False,
                    "max_warning_threshold": 5
                },
                "templates": {
                    "template_directory": "custom_templates",
                    "template_cache_size": 150
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(test_config, f)
                
            manager = ConfigManager(config_path)
            
            assert manager.config.service_name == "Test Service"
            assert manager.config.version == "3.0.0"
            assert manager.config.debug_mode is True
            assert manager.config.log_level == "DEBUG"
            assert manager.config.generation.max_response_length == 750
            assert manager.config.generation.default_tone == "formal"
            assert manager.config.validation.enable_profanity_filter is False
            assert manager.config.validation.max_warning_threshold == 5
            assert manager.config.templates.template_directory == "custom_templates"
            assert manager.config.templates.template_cache_size == 150
            
    def test_config_manager_load_partial_config(self):
        """Test ConfigManager loading partial config file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "partial_config.json"
            
            # Create partial config file
            partial_config = {
                "service_name": "Partial Service",
                "generation": {
                    "max_response_length": 600
                }
                # Missing validation and templates sections
            }
            
            with open(config_path, 'w') as f:
                json.dump(partial_config, f)
                
            manager = ConfigManager(config_path)
            
            # Should use custom values where provided
            assert manager.config.service_name == "Partial Service"
            assert manager.config.generation.max_response_length == 600
            
            # Should use defaults for missing sections
            assert manager.config.generation.min_response_length == 5  # Default
            assert isinstance(manager.config.validation, ValidationConfig)
            assert isinstance(manager.config.templates, TemplateConfig)
            
    def test_config_manager_load_invalid_json(self):
        """Test ConfigManager handling invalid JSON"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "invalid_config.json"
            
            # Create invalid JSON file
            with open(config_path, 'w') as f:
                f.write("{ invalid json content")
                
            with patch('src.message_maker.config.logger') as mock_logger:
                manager = ConfigManager(config_path)
                
                # Should fall back to defaults
                assert isinstance(manager.config, ServiceConfig)
                assert manager.config.service_name == "Message Maker Service"
                mock_logger.error.assert_called_once()
                
    def test_get_config(self):
        """Test getting current configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            config = manager.get_config()
            
            assert isinstance(config, ServiceConfig)
            assert config == manager.config
            
    def test_update_config(self):
        """Test updating configuration values"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            with patch('src.message_maker.config.logger') as mock_logger:
                manager.update_config(service_name="Updated Service", debug_mode=True)
                
                assert manager.config.service_name == "Updated Service"
                assert manager.config.debug_mode is True
                assert mock_logger.info.call_count == 2  # Two updates
                
    def test_update_config_invalid_key(self):
        """Test updating configuration with invalid key"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            with patch('src.message_maker.config.logger') as mock_logger:
                manager.update_config(invalid_key="invalid_value")
                
                mock_logger.warning.assert_called_once_with("Unknown config key: invalid_key")
                
    def test_save_config(self):
        """Test saving configuration to file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            # Update config
            manager.config.service_name = "Saved Service"
            
            # Save config
            manager.save_config()
            
            # Verify file was updated
            with open(config_path, 'r') as f:
                saved_data = json.load(f)
                
            assert saved_data["service_name"] == "Saved Service"
            
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            # Modify config
            manager.config.service_name = "Modified Service"
            manager.config.debug_mode = True
            
            with patch('src.message_maker.config.logger') as mock_logger:
                manager.reset_to_defaults()
                
                # Should be back to defaults
                assert manager.config.service_name == "Message Maker Service"
                assert manager.config.debug_mode is False
                mock_logger.info.assert_called_with("Configuration reset to defaults")
                
    def test_validate_config_valid(self):
        """Test validating valid configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            validation_result = manager.validate_config()
            
            assert validation_result["is_valid"] is True
            assert len(validation_result["issues"]) == 0
            assert isinstance(validation_result["warnings"], list)
            
    def test_validate_config_invalid_length_bounds(self):
        """Test validating config with invalid length bounds"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            # Set invalid bounds
            manager.config.generation.max_response_length = 5
            manager.config.generation.min_response_length = 10
            
            validation_result = manager.validate_config()
            
            assert validation_result["is_valid"] is False
            assert len(validation_result["issues"]) > 0
            assert any("max_response_length" in issue for issue in validation_result["issues"])
            
    def test_validate_config_invalid_threshold(self):
        """Test validating config with invalid threshold"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            # Set invalid threshold
            manager.config.generation.pattern_analysis_threshold = 0
            
            validation_result = manager.validate_config()
            
            assert validation_result["is_valid"] is False
            assert any("pattern_analysis_threshold" in issue for issue in validation_result["issues"])
            
    def test_validate_config_warnings(self):
        """Test validating config that generates warnings"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ConfigManager(config_path)
            
            # Set value that generates warning
            manager.config.templates.template_cache_size = 0
            
            validation_result = manager.validate_config()
            
            assert validation_result["is_valid"] is True  # Warnings don't invalidate
            assert len(validation_result["warnings"]) > 0
            assert any("template_cache_size" in warning for warning in validation_result["warnings"])


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager"""
    
    def test_complete_config_workflow(self):
        """Test complete configuration workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "workflow_config.json"
            
            # Initialize manager
            manager = ConfigManager(config_path)
            
            # Verify defaults
            assert manager.config.service_name == "Message Maker Service"
            
            # Update config
            manager.update_config(
                service_name="Workflow Test Service",
                debug_mode=True,
                log_level="DEBUG"
            )
            
            # Validate config
            validation = manager.validate_config()
            assert validation["is_valid"] is True
            
            # Save config
            manager.save_config()
            
            # Create new manager and verify persistence
            new_manager = ConfigManager(config_path)
            assert new_manager.config.service_name == "Workflow Test Service"
            assert new_manager.config.debug_mode is True
            assert new_manager.config.log_level == "DEBUG"
            
            # Reset and verify
            new_manager.reset_to_defaults()
            assert new_manager.config.service_name == "Message Maker Service"
            assert new_manager.config.debug_mode is False