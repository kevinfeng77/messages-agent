"""
Query Manager for Graphiti Knowledge Graph

This module provides functionality for querying and searching the Graphiti knowledge graph.
Supports various search methods including basic search, center node search, and node search
with predefined recipes.
"""

import asyncio
import logging
import os
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
from graphiti_core.edges import Edge
from graphiti_core.nodes import Node

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class QueryManager:
    """Manages querying and searching the Graphiti knowledge graph."""

    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
    ):
        """
        Initialize the QueryManager with Neo4j connection parameters.

        Args:
            neo4j_uri: Neo4j connection URI (defaults to environment variable)
            neo4j_user: Neo4j username (defaults to environment variable)
            neo4j_password: Neo4j password (defaults to environment variable)
        """
        self.neo4j_uri = neo4j_uri or os.environ.get(
            "NEO4J_URI", "bolt://localhost:7687"
        )
        self.neo4j_user = neo4j_user or os.environ.get("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.environ.get(
            "NEO4J_PASSWORD", "password"
        )

        if not self.neo4j_uri or not self.neo4j_user or not self.neo4j_password:
            raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set")

        self.graphiti = None

    async def initialize(self):
        """Initialize the Graphiti connection."""
        self.graphiti = Graphiti(self.neo4j_uri, self.neo4j_user, self.neo4j_password)
        logger.info("Graphiti connection initialized")

    async def close(self):
        """Close the Graphiti connection."""
        if self.graphiti:
            await self.graphiti.close()
            logger.info("Graphiti connection closed")

    async def search(self, query: str, limit: int = 10) -> List[Edge]:
        """
        Perform a basic hybrid search combining semantic similarity and BM25 retrieval.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of Edge objects representing relationships/facts
        """
        if not self.graphiti:
            raise RuntimeError("QueryManager not initialized. Call initialize() first.")

        results = await self.graphiti.search(query, limit=limit)
        logger.info(f"Basic search for '{query}' returned {len(results)} results")
        return results

    async def search_with_center_node(
        self, query: str, center_node_uuid: str, limit: int = 10
    ) -> List[Edge]:
        """
        Perform a search reranked by graph distance from a center node.

        Args:
            query: Search query string
            center_node_uuid: UUID of the center node for reranking
            limit: Maximum number of results to return

        Returns:
            List of Edge objects reranked by graph distance
        """
        if not self.graphiti:
            raise RuntimeError("QueryManager not initialized. Call initialize() first.")

        results = await self.graphiti.search(
            query, center_node_uuid=center_node_uuid, limit=limit
        )
        logger.info(f"Center node search for '{query}' returned {len(results)} results")
        return results

    async def node_search(self, query: str, limit: int = 5) -> List[Node]:
        """
        Perform a node search using hybrid search to find entities directly.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of Node objects representing entities
        """
        if not self.graphiti:
            raise RuntimeError("QueryManager not initialized. Call initialize() first.")

        # Use predefined search configuration recipe
        node_search_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        node_search_config.limit = limit

        search_results = await self.graphiti._search(
            query=query, config=node_search_config
        )
        logger.info(
            f"Node search for '{query}' returned {len(search_results.nodes)} results"
        )
        return search_results.nodes

    async def get_auto_center_node_search(
        self, query: str, limit: int = 10
    ) -> List[Edge]:
        """
        Perform a search that automatically uses the top result as a center node for reranking.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of Edge objects reranked by the top result's source node
        """
        if not self.graphiti:
            raise RuntimeError("QueryManager not initialized. Call initialize() first.")

        # First get basic search results
        initial_results = await self.search(query, limit=1)

        if not initial_results:
            logger.warning(f"No initial results found for query: '{query}'")
            return []

        # Use the top result's source node as center for reranking
        center_node_uuid = initial_results[0].source_node_uuid
        reranked_results = await self.search_with_center_node(
            query, center_node_uuid, limit
        )

        logger.info(
            f"Auto center node search for '{query}' returned {len(reranked_results)} results"
        )
        return reranked_results

    def format_search_results(self, results: List[Edge]) -> List[Dict[str, Any]]:
        """
        Format search results into a readable dictionary format.

        Args:
            results: List of Edge objects from search

        Returns:
            List of dictionaries with formatted result data
        """
        formatted_results = []

        for result in results:
            formatted_result = {
                "uuid": result.uuid,
                "fact": result.fact,
                "source_node_uuid": result.source_node_uuid,
                "target_node_uuid": result.target_node_uuid,
                "created_at": result.created_at,
                "name": getattr(result, "name", None),
                "group_id": getattr(result, "group_id", None),
                "valid_at": getattr(result, "valid_at", None),
                "invalid_at": getattr(result, "invalid_at", None),
            }
            formatted_results.append(formatted_result)

        return formatted_results

    def format_node_results(self, nodes: List[Node]) -> List[Dict[str, Any]]:
        """
        Format node search results into a readable dictionary format.

        Args:
            nodes: List of Node objects from search

        Returns:
            List of dictionaries with formatted node data
        """
        formatted_nodes = []

        for node in nodes:
            formatted_node = {
                "uuid": node.uuid,
                "name": node.name,
                "summary": node.summary,
                "labels": node.labels,
                "created_at": node.created_at,
                "attributes": getattr(node, "attributes", {}),
            }
            formatted_nodes.append(formatted_node)

        return formatted_nodes

    def print_search_results(self, results: List[Edge], title: str = "Search Results"):
        """
        Print search results in a readable format.

        Args:
            results: List of Edge objects from search
            title: Title to display above results
        """
        print(f"\n{title}:")
        for result in results:
            print(f"UUID: {result.uuid}")
            print(f"Fact: {result.fact}")
            if hasattr(result, "valid_at") and result.valid_at:
                print(f"Valid from: {result.valid_at}")
            if hasattr(result, "invalid_at") and result.invalid_at:
                print(f"Valid until: {result.invalid_at}")
            print("---")

    def print_node_results(self, nodes: List[Node], title: str = "Node Search Results"):
        """
        Print node search results in a readable format.

        Args:
            nodes: List of Node objects from search
            title: Title to display above results
        """
        print(f"\n{title}:")
        for node in nodes:
            print(f"Node UUID: {node.uuid}")
            print(f"Node Name: {node.name}")
            node_summary = (
                node.summary[:100] + "..." if len(node.summary) > 100 else node.summary
            )
            print(f"Content Summary: {node_summary}")
            print(f'Node Labels: {", ".join(node.labels)}')
            print(f"Created At: {node.created_at}")
            if hasattr(node, "attributes") and node.attributes:
                print("Attributes:")
                for key, value in node.attributes.items():
                    print(f"  {key}: {value}")
            print("---")


async def example_usage():
    """Example usage of the QueryManager."""
    manager = QueryManager()

    try:
        await manager.initialize()

        # Basic search
        print("Performing basic search...")
        basic_results = await manager.search("California Attorney General")
        manager.print_search_results(basic_results, "Basic Search Results")

        # Node search
        print("\nPerforming node search...")
        node_results = await manager.node_search("California Governor")
        manager.print_node_results(node_results, "Node Search Results")

        # Auto center node search
        print("\nPerforming auto center node search...")
        center_results = await manager.get_auto_center_node_search(
            "California Attorney General"
        )
        manager.print_search_results(center_results, "Auto Center Node Search Results")

        # Format results as dictionaries
        print("\nFormatted basic search results:")
        formatted = manager.format_search_results(basic_results)
        for result in formatted:
            print(f"Fact: {result['fact']}")

    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
