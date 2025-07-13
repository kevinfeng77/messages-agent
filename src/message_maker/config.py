"""Configuration management for message maker service"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
from dataclasses import dataclass, asdict

from src.utils.logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for message generation"""
    
    max_response_length: int = 500
    min_response_length: int = 5
    default_tone: str = "casual"
    default_message_type: str = "response"
    enable_user_patterns: bool = True
    pattern_analysis_threshold: int = 10


@dataclass
class ValidationConfig:
    """Configuration for message validation"""
    
    enable_profanity_filter: bool = True
    enable_spell_check: bool = True
    enable_grammar_check: bool = True
    enable_tone_analysis: bool = True
    max_warning_threshold: int = 3
    auto_fix_typos: bool = False


@dataclass
class TemplateConfig:
    """Configuration for template management"""
    
    template_directory: str = "templates"
    auto_load_templates: bool = True
    enable_custom_templates: bool = True
    template_cache_size: int = 100


@dataclass
class ServiceConfig:
    """Main service configuration"""
    
    service_name: str = "Message Maker Service"
    version: str = "1.0.0"
    debug_mode: bool = False
    log_level: str = "INFO"
    generation: GenerationConfig = None
    validation: ValidationConfig = None
    templates: TemplateConfig = None
    
    def __post_init__(self):
        if self.generation is None:
            self.generation = GenerationConfig()
        if self.validation is None:
            self.validation = ValidationConfig()
        if self.templates is None:
            self.templates = TemplateConfig()


class ConfigManager:
    """Manages configuration for the message maker service"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent / "config.json"
        self.config = ServiceConfig()
        self._load_config()
        
    def _load_config(self):
        """Load configuration from file if it exists"""
        if not self.config_path.exists():
            logger.info(f"Config file not found at {self.config_path}, using defaults")
            self._save_default_config()
            return
            
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
                
            # Load main config
            self.config.service_name = config_data.get("service_name", self.config.service_name)
            self.config.version = config_data.get("version", self.config.version)
            self.config.debug_mode = config_data.get("debug_mode", self.config.debug_mode)
            self.config.log_level = config_data.get("log_level", self.config.log_level)
            
            # Load generation config
            if "generation" in config_data:
                gen_data = config_data["generation"]
                self.config.generation = GenerationConfig(
                    max_response_length=gen_data.get("max_response_length", 500),
                    min_response_length=gen_data.get("min_response_length", 5),
                    default_tone=gen_data.get("default_tone", "casual"),
                    default_message_type=gen_data.get("default_message_type", "response"),
                    enable_user_patterns=gen_data.get("enable_user_patterns", True),
                    pattern_analysis_threshold=gen_data.get("pattern_analysis_threshold", 10)
                )
                
            # Load validation config
            if "validation" in config_data:
                val_data = config_data["validation"]
                self.config.validation = ValidationConfig(
                    enable_profanity_filter=val_data.get("enable_profanity_filter", True),
                    enable_spell_check=val_data.get("enable_spell_check", True),
                    enable_grammar_check=val_data.get("enable_grammar_check", True),
                    enable_tone_analysis=val_data.get("enable_tone_analysis", True),
                    max_warning_threshold=val_data.get("max_warning_threshold", 3),
                    auto_fix_typos=val_data.get("auto_fix_typos", False)
                )
                
            # Load template config
            if "templates" in config_data:
                temp_data = config_data["templates"]
                self.config.templates = TemplateConfig(
                    template_directory=temp_data.get("template_directory", "templates"),
                    auto_load_templates=temp_data.get("auto_load_templates", True),
                    enable_custom_templates=temp_data.get("enable_custom_templates", True),
                    template_cache_size=temp_data.get("template_cache_size", 100)
                )
                
            logger.info(f"Loaded configuration from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}, using defaults")
            self.config = ServiceConfig()
            
    def _save_default_config(self):
        """Save default configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = {
                "service_name": self.config.service_name,
                "version": self.config.version,
                "debug_mode": self.config.debug_mode,
                "log_level": self.config.log_level,
                "generation": asdict(self.config.generation),
                "validation": asdict(self.config.validation),
                "templates": asdict(self.config.templates)
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
                
            logger.info(f"Saved default configuration to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving default configuration: {e}")
            
    def save_config(self):
        """Save current configuration to file"""
        self._save_default_config()
        
    def get_config(self) -> ServiceConfig:
        """Get current configuration"""
        return self.config
        
    def update_config(self, **kwargs):
        """
        Update configuration values
        
        Args:
            **kwargs: Configuration values to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated config: {key} = {value}")
            else:
                logger.warning(f"Unknown config key: {key}")
                
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config = ServiceConfig()
        self._save_default_config()
        logger.info("Configuration reset to defaults")
        
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate current configuration
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Validate generation config
        if self.config.generation.max_response_length <= self.config.generation.min_response_length:
            issues.append("max_response_length must be greater than min_response_length")
            
        if self.config.generation.pattern_analysis_threshold < 1:
            issues.append("pattern_analysis_threshold must be at least 1")
            
        # Validate validation config
        if self.config.validation.max_warning_threshold < 0:
            issues.append("max_warning_threshold must be non-negative")
            
        # Validate template config
        if self.config.templates.template_cache_size < 1:
            warnings.append("template_cache_size should be at least 1")
            
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }