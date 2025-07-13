"""Template management for message generation patterns"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import json
from pathlib import Path

from src.utils.logger_config import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """Enumeration of supported message types"""
    
    GREETING = "greeting"
    RESPONSE = "response"
    QUESTION = "question"
    ACKNOWLEDGMENT = "acknowledgment"
    FAREWELL = "farewell"
    APOLOGY = "apology"
    THANKS = "thanks"
    CONFIRMATION = "confirmation"


class ToneType(Enum):
    """Enumeration of message tone types"""
    
    CASUAL = "casual"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    HUMOROUS = "humorous"
    SERIOUS = "serious"


@dataclass
class MessageTemplate:
    """Template for generating messages"""
    
    template_id: str
    message_type: MessageType
    tone: ToneType
    pattern: str
    variables: List[str]
    examples: List[str]
    
    def fill_template(self, **kwargs) -> str:
        """
        Fill template pattern with provided variables
        
        Args:
            **kwargs: Variable values to substitute in pattern
            
        Returns:
            Filled template string
        """
        try:
            return self.pattern.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return self.pattern


class TemplateManager:
    """Manages message templates for different contexts and user preferences"""
    
    def __init__(self, template_path: Optional[Path] = None):
        self.templates: Dict[str, MessageTemplate] = {}
        self.template_path = template_path or Path(__file__).parent / "templates"
        self._load_default_templates()
        
    def _load_default_templates(self):
        """Load default message templates"""
        logger.info("Loading default message templates")
        
        default_templates = [
            MessageTemplate(
                template_id="casual_greeting",
                message_type=MessageType.GREETING,
                tone=ToneType.CASUAL,
                pattern="Hey {name}! How's it going?",
                variables=["name"],
                examples=["Hey John! How's it going?", "Hey Sarah! How's it going?"]
            ),
            MessageTemplate(
                template_id="formal_greeting",
                message_type=MessageType.GREETING,
                tone=ToneType.FORMAL,
                pattern="Hello {name}, I hope you are doing well.",
                variables=["name"],
                examples=["Hello Mr. Smith, I hope you are doing well."]
            ),
            MessageTemplate(
                template_id="casual_thanks",
                message_type=MessageType.THANKS,
                tone=ToneType.CASUAL,
                pattern="Thanks! {additional_message}",
                variables=["additional_message"],
                examples=["Thanks! Really appreciate it", "Thanks! You're the best"]
            ),
            MessageTemplate(
                template_id="confirmation_response",
                message_type=MessageType.CONFIRMATION,
                tone=ToneType.CASUAL,
                pattern="Got it! {confirmation_details}",
                variables=["confirmation_details"],
                examples=["Got it! I'll be there at 3pm", "Got it! Thanks for letting me know"]
            )
        ]
        
        for template in default_templates:
            self.templates[template.template_id] = template
            
        logger.info(f"Loaded {len(default_templates)} default templates")
    
    def get_template(self, template_id: str) -> Optional[MessageTemplate]:
        """
        Get template by ID
        
        Args:
            template_id: Unique identifier for the template
            
        Returns:
            MessageTemplate if found, None otherwise
        """
        return self.templates.get(template_id)
    
    def find_templates(self, message_type: MessageType, tone: ToneType) -> List[MessageTemplate]:
        """
        Find templates matching message type and tone
        
        Args:
            message_type: Type of message to generate
            tone: Desired tone for the message
            
        Returns:
            List of matching templates
        """
        matching = []
        for template in self.templates.values():
            if template.message_type == message_type and template.tone == tone:
                matching.append(template)
                
        logger.debug(f"Found {len(matching)} templates for {message_type.value}/{tone.value}")
        return matching
    
    def add_template(self, template: MessageTemplate):
        """
        Add a new template
        
        Args:
            template: MessageTemplate to add
        """
        self.templates[template.template_id] = template
        logger.info(f"Added template: {template.template_id}")
    
    def remove_template(self, template_id: str) -> bool:
        """
        Remove template by ID
        
        Args:
            template_id: ID of template to remove
            
        Returns:
            True if removed, False if not found
        """
        if template_id in self.templates:
            del self.templates[template_id]
            logger.info(f"Removed template: {template_id}")
            return True
        return False
    
    def save_templates(self, filepath: Optional[Path] = None):
        """
        Save templates to JSON file
        
        Args:
            filepath: Optional path to save templates
        """
        save_path = filepath or self.template_path / "templates.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        template_data = {}
        for template_id, template in self.templates.items():
            template_data[template_id] = {
                "message_type": template.message_type.value,
                "tone": template.tone.value,
                "pattern": template.pattern,
                "variables": template.variables,
                "examples": template.examples
            }
            
        with open(save_path, 'w') as f:
            json.dump(template_data, f, indent=2)
            
        logger.info(f"Saved {len(self.templates)} templates to {save_path}")
    
    def load_templates(self, filepath: Optional[Path] = None):
        """
        Load templates from JSON file
        
        Args:
            filepath: Optional path to load templates from
        """
        load_path = filepath or self.template_path / "templates.json"
        
        if not load_path.exists():
            logger.warning(f"Template file not found: {load_path}")
            return
            
        try:
            with open(load_path, 'r') as f:
                template_data = json.load(f)
                
            for template_id, data in template_data.items():
                template = MessageTemplate(
                    template_id=template_id,
                    message_type=MessageType(data["message_type"]),
                    tone=ToneType(data["tone"]),
                    pattern=data["pattern"],
                    variables=data["variables"],
                    examples=data["examples"]
                )
                self.templates[template_id] = template
                
            logger.info(f"Loaded {len(template_data)} templates from {load_path}")
            
        except Exception as e:
            logger.error(f"Error loading templates: {e}")