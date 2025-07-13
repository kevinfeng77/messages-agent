"""Tests for template manager module"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.message_maker.template_manager import (
    TemplateManager, MessageTemplate, MessageType, ToneType
)


class TestMessageType:
    """Test MessageType enum"""
    
    def test_message_type_values(self):
        """Test MessageType enum values"""
        assert MessageType.GREETING.value == "greeting"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.QUESTION.value == "question"
        assert MessageType.ACKNOWLEDGMENT.value == "acknowledgment"
        assert MessageType.FAREWELL.value == "farewell"
        assert MessageType.APOLOGY.value == "apology"
        assert MessageType.THANKS.value == "thanks"
        assert MessageType.CONFIRMATION.value == "confirmation"


class TestToneType:
    """Test ToneType enum"""
    
    def test_tone_type_values(self):
        """Test ToneType enum values"""
        assert ToneType.CASUAL.value == "casual"
        assert ToneType.FORMAL.value == "formal"
        assert ToneType.FRIENDLY.value == "friendly"
        assert ToneType.PROFESSIONAL.value == "professional"
        assert ToneType.HUMOROUS.value == "humorous"
        assert ToneType.SERIOUS.value == "serious"


class TestMessageTemplate:
    """Test MessageTemplate dataclass"""
    
    def test_template_creation(self):
        """Test creating a MessageTemplate"""
        template = MessageTemplate(
            template_id="test_template",
            message_type=MessageType.GREETING,
            tone=ToneType.CASUAL,
            pattern="Hello {name}!",
            variables=["name"],
            examples=["Hello John!", "Hello Sarah!"]
        )
        
        assert template.template_id == "test_template"
        assert template.message_type == MessageType.GREETING
        assert template.tone == ToneType.CASUAL
        assert template.pattern == "Hello {name}!"
        assert template.variables == ["name"]
        assert template.examples == ["Hello John!", "Hello Sarah!"]
        
    def test_fill_template_success(self):
        """Test successfully filling a template"""
        template = MessageTemplate(
            template_id="greeting",
            message_type=MessageType.GREETING,
            tone=ToneType.CASUAL,
            pattern="Hey {name}, how's {activity} going?",
            variables=["name", "activity"],
            examples=[]
        )
        
        result = template.fill_template(name="John", activity="work")
        assert result == "Hey John, how's work going?"
        
    def test_fill_template_missing_variable(self):
        """Test filling template with missing variable"""
        template = MessageTemplate(
            template_id="greeting",
            message_type=MessageType.GREETING,
            tone=ToneType.CASUAL,
            pattern="Hello {name}!",
            variables=["name"],
            examples=[]
        )
        
        with patch('src.message_maker.template_manager.logger') as mock_logger:
            result = template.fill_template()  # Missing 'name' variable
            
            assert result == "Hello {name}!"  # Returns original pattern
            mock_logger.error.assert_called_once()


class TestTemplateManager:
    """Test TemplateManager class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_path = Path(temp_dir)
            self.manager = TemplateManager(template_path=self.temp_path)
            
    def test_initialization_loads_defaults(self):
        """Test that initialization loads default templates"""
        manager = TemplateManager()
        
        assert len(manager.templates) > 0
        assert "casual_greeting" in manager.templates
        assert "formal_greeting" in manager.templates
        assert "casual_thanks" in manager.templates
        assert "confirmation_response" in manager.templates
        
    def test_get_existing_template(self):
        """Test getting an existing template"""
        manager = TemplateManager()
        
        template = manager.get_template("casual_greeting")
        
        assert template is not None
        assert template.template_id == "casual_greeting"
        assert template.message_type == MessageType.GREETING
        assert template.tone == ToneType.CASUAL
        
    def test_get_nonexistent_template(self):
        """Test getting a non-existent template"""
        manager = TemplateManager()
        
        template = manager.get_template("nonexistent_template")
        
        assert template is None
        
    def test_find_templates_by_type_and_tone(self):
        """Test finding templates by message type and tone"""
        manager = TemplateManager()
        
        greeting_casual = manager.find_templates(MessageType.GREETING, ToneType.CASUAL)
        greeting_formal = manager.find_templates(MessageType.GREETING, ToneType.FORMAL)
        
        assert len(greeting_casual) >= 1
        assert len(greeting_formal) >= 1
        assert all(t.message_type == MessageType.GREETING for t in greeting_casual)
        assert all(t.tone == ToneType.CASUAL for t in greeting_casual)
        
    def test_find_templates_no_matches(self):
        """Test finding templates with no matches"""
        manager = TemplateManager()
        
        # Should have no humorous apology templates by default
        templates = manager.find_templates(MessageType.APOLOGY, ToneType.HUMOROUS)
        
        assert len(templates) == 0
        
    def test_add_template(self):
        """Test adding a new template"""
        manager = TemplateManager()
        initial_count = len(manager.templates)
        
        new_template = MessageTemplate(
            template_id="custom_template",
            message_type=MessageType.THANKS,
            tone=ToneType.FORMAL,
            pattern="Thank you very much, {name}.",
            variables=["name"],
            examples=["Thank you very much, Mr. Smith."]
        )
        
        with patch('src.message_maker.template_manager.logger') as mock_logger:
            manager.add_template(new_template)
            
            assert len(manager.templates) == initial_count + 1
            assert "custom_template" in manager.templates
            assert manager.get_template("custom_template") == new_template
            mock_logger.info.assert_called_once_with("Added template: custom_template")
            
    def test_remove_existing_template(self):
        """Test removing an existing template"""
        manager = TemplateManager()
        
        # Add a template first
        test_template = MessageTemplate(
            template_id="removable_template",
            message_type=MessageType.GREETING,
            tone=ToneType.CASUAL,
            pattern="Hi there!",
            variables=[],
            examples=[]
        )
        manager.add_template(test_template)
        
        initial_count = len(manager.templates)
        
        with patch('src.message_maker.template_manager.logger') as mock_logger:
            result = manager.remove_template("removable_template")
            
            assert result is True
            assert len(manager.templates) == initial_count - 1
            assert "removable_template" not in manager.templates
            mock_logger.info.assert_called_once_with("Removed template: removable_template")
            
    def test_remove_nonexistent_template(self):
        """Test removing a non-existent template"""
        manager = TemplateManager()
        
        result = manager.remove_template("nonexistent_template")
        
        assert result is False
        
    def test_save_and_load_templates(self):
        """Test saving and loading templates"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = TemplateManager(template_path=temp_path)
            
            # Add a custom template
            custom_template = MessageTemplate(
                template_id="save_test_template",
                message_type=MessageType.QUESTION,
                tone=ToneType.FRIENDLY,
                pattern="How are you doing, {name}?",
                variables=["name"],
                examples=["How are you doing, friend?"]
            )
            manager.add_template(custom_template)
            
            # Save templates
            save_path = temp_path / "test_templates.json"
            manager.save_templates(save_path)
            
            assert save_path.exists()
            
            # Load templates in a new manager
            new_manager = TemplateManager(template_path=temp_path)
            new_manager.load_templates(save_path)
            
            # Verify the custom template was loaded
            loaded_template = new_manager.get_template("save_test_template")
            assert loaded_template is not None
            assert loaded_template.template_id == "save_test_template"
            assert loaded_template.pattern == "How are you doing, {name}?"
            
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = TemplateManager(template_path=temp_path)
            
            nonexistent_path = temp_path / "nonexistent.json"
            
            with patch('src.message_maker.template_manager.logger') as mock_logger:
                manager.load_templates(nonexistent_path)
                
                mock_logger.warning.assert_called_once()
                
    def test_load_invalid_json(self):
        """Test loading invalid JSON file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = TemplateManager(template_path=temp_path)
            
            # Create invalid JSON file
            invalid_json_path = temp_path / "invalid.json"
            with open(invalid_json_path, 'w') as f:
                f.write("{ invalid json content")
                
            with patch('src.message_maker.template_manager.logger') as mock_logger:
                manager.load_templates(invalid_json_path)
                
                mock_logger.error.assert_called_once()


class TestTemplateManagerIntegration:
    """Integration tests for TemplateManager"""
    
    def test_complete_template_workflow(self):
        """Test complete template management workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = TemplateManager(template_path=temp_path)
            
            # Find existing templates
            casual_greetings = manager.find_templates(MessageType.GREETING, ToneType.CASUAL)
            assert len(casual_greetings) > 0
            
            # Use a template
            template = casual_greetings[0]
            filled = template.fill_template(name="TestUser")
            assert "TestUser" in filled
            
            # Add custom template
            custom = MessageTemplate(
                template_id="integration_test",
                message_type=MessageType.FAREWELL,
                tone=ToneType.CASUAL,
                pattern="See you later, {name}!",
                variables=["name"],
                examples=["See you later, John!"]
            )
            manager.add_template(custom)
            
            # Save and reload
            save_path = temp_path / "integration_test.json"
            manager.save_templates(save_path)
            
            new_manager = TemplateManager(template_path=temp_path)
            new_manager.load_templates(save_path)
            
            # Verify everything works
            loaded_template = new_manager.get_template("integration_test")
            assert loaded_template is not None
            
            farewell_templates = new_manager.find_templates(MessageType.FAREWELL, ToneType.CASUAL)
            assert len(farewell_templates) >= 1