"""
Episode Manager for Graphiti Knowledge Graph

This module provides functionality for adding episodes to the Graphiti knowledge graph.
Episodes can be text content or structured JSON data that will be processed to extract
entities and relationships.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Union, Dict, Any, Optional

from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class EpisodeManager:
    """Manages adding episodes to the Graphiti knowledge graph."""
    
    def __init__(self, neo4j_uri: Optional[str] = None, neo4j_user: Optional[str] = None, 
                 neo4j_password: Optional[str] = None):
        """
        Initialize the EpisodeManager with Neo4j connection parameters.
        
        Args:
            neo4j_uri: Neo4j connection URI (defaults to environment variable)
            neo4j_user: Neo4j username (defaults to environment variable)
            neo4j_password: Neo4j password (defaults to environment variable)
        """
        self.neo4j_uri = neo4j_uri or os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_user = neo4j_user or os.environ.get('NEO4J_USER', 'neo4j')
        self.neo4j_password = neo4j_password or os.environ.get('NEO4J_PASSWORD', 'password')
        
        if not self.neo4j_uri or not self.neo4j_user or not self.neo4j_password:
            raise ValueError('NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set')
        
        self.graphiti = None
    
    async def initialize(self):
        """Initialize the Graphiti connection and build indices."""
        self.graphiti = Graphiti(self.neo4j_uri, self.neo4j_user, self.neo4j_password)
        await self.graphiti.build_indices_and_constraints()
        logger.info("Graphiti initialized and indices built")
    
    async def close(self):
        """Close the Graphiti connection."""
        if self.graphiti:
            await self.graphiti.close()
            logger.info("Graphiti connection closed")
    
    async def add_text_episode(self, name: str, content: str, description: str = "text episode",
                              reference_time: Optional[datetime] = None) -> None:
        """
        Add a text episode to the knowledge graph.
        
        Args:
            name: Name/identifier for the episode
            content: Text content to be processed
            description: Description of the episode source
            reference_time: Timestamp for the episode (defaults to current time)
        """
        if not self.graphiti:
            raise RuntimeError("EpisodeManager not initialized. Call initialize() first.")
        
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)
        
        await self.graphiti.add_episode(
            name=name,
            episode_body=content,
            source=EpisodeType.text,
            source_description=description,
            reference_time=reference_time,
        )
        logger.info(f"Added text episode: {name}")
    
    async def add_json_episode(self, name: str, content: Dict[str, Any], description: str = "json episode",
                              reference_time: Optional[datetime] = None) -> None:
        """
        Add a JSON episode to the knowledge graph.
        
        Args:
            name: Name/identifier for the episode
            content: Structured data to be processed
            description: Description of the episode source
            reference_time: Timestamp for the episode (defaults to current time)
        """
        if not self.graphiti:
            raise RuntimeError("EpisodeManager not initialized. Call initialize() first.")
        
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)
        
        await self.graphiti.add_episode(
            name=name,
            episode_body=json.dumps(content),
            source=EpisodeType.json,
            source_description=description,
            reference_time=reference_time,
        )
        logger.info(f"Added JSON episode: {name}")
    
    async def add_episode(self, name: str, content: Union[str, Dict[str, Any]], 
                         episode_type: EpisodeType, description: str = "episode",
                         reference_time: Optional[datetime] = None) -> None:
        """
        Add an episode to the knowledge graph (auto-detects type if not specified).
        
        Args:
            name: Name/identifier for the episode
            content: Content to be processed (text or dict)
            episode_type: Type of episode (text or json)
            description: Description of the episode source
            reference_time: Timestamp for the episode (defaults to current time)
        """
        if not self.graphiti:
            raise RuntimeError("EpisodeManager not initialized. Call initialize() first.")
        
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)
        
        # Convert content to string if it's a dict
        episode_body = content if isinstance(content, str) else json.dumps(content)
        
        await self.graphiti.add_episode(
            name=name,
            episode_body=episode_body,
            source=episode_type,
            source_description=description,
            reference_time=reference_time,
        )
        logger.info(f"Added {episode_type.value} episode: {name}")
    
    async def add_multiple_episodes(self, episodes: list) -> None:
        """
        Add multiple episodes to the knowledge graph.
        
        Args:
            episodes: List of episode dictionaries with keys:
                     - name: Episode name
                     - content: Episode content (str or dict)
                     - type: EpisodeType (text or json)
                     - description: Optional description
                     - reference_time: Optional timestamp
        """
        if not self.graphiti:
            raise RuntimeError("EpisodeManager not initialized. Call initialize() first.")
        
        for episode in episodes:
            await self.add_episode(
                name=episode['name'],
                content=episode['content'],
                episode_type=episode['type'],
                description=episode.get('description', 'episode'),
                reference_time=episode.get('reference_time')
            )
        
        logger.info(f"Added {len(episodes)} episodes to the knowledge graph")


async def example_usage():
    """Example usage of the EpisodeManager."""
    manager = EpisodeManager()
    
    try:
        await manager.initialize()
        
        # Add a text episode
        await manager.add_text_episode(
            name="Sample Text Episode",
            content="This is sample text content that will be processed by Graphiti.",
            description="example text data"
        )
        
        # Add a JSON episode
        await manager.add_json_episode(
            name="Sample JSON Episode",
            content={"key": "value", "number": 42, "nested": {"data": "here"}},
            description="example structured data"
        )
        
        # Add multiple episodes
        episodes = [
            {
                'name': 'Episode 1',
                'content': 'Text content for episode 1',
                'type': EpisodeType.text,
                'description': 'batch episode 1'
            },
            {
                'name': 'Episode 2',
                'content': {'data': 'structured content'},
                'type': EpisodeType.json,
                'description': 'batch episode 2'
            }
        ]
        await manager.add_multiple_episodes(episodes)
        
    finally:
        await manager.close()


if __name__ == '__main__':
    asyncio.run(example_usage())