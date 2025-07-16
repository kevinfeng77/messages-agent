# Conversations Service

The conversations service is responsible for detecting, managing, and searching conversations within the Messages Agent system.

## Architecture Overview

The service is organized into the following modules:

### Core Modules

- **`models.py`** - Data models and types
  - `Conversation`: Represents a detected conversation
  - `ConversationMessage`: Individual message within a conversation
  - `EmbeddingData`: Embedding data for semantic search

- **`config.py`** - Configuration management
  - `ConversationsConfig`: Service configuration settings

### Functional Modules

- **`detector.py`** - Conversation detection logic
  - `ConversationDetector`: Identifies and extracts conversations from message streams

- **`embeddings.py`** - Embedding generation service
  - `EmbeddingService`: Generates vector embeddings for conversations

- **`manager.py`** - Conversation CRUD operations
  - `ConversationManager`: Handles create, read, update, delete operations

- **`search.py`** - Semantic search service
  - `SemanticSearchService`: Performs similarity search on conversations

- **`api.py`** - REST API endpoints
  - `ConversationAPI`: External API interface for the service

### Testing

Each module has a corresponding test file in the `tests/` directory:
- `test_detector.py`
- `test_embeddings.py`
- `test_manager.py`
- `test_search.py`
- `test_api.py`

## Integration Points

This service integrates with:
- Message database for retrieving message data
- AI/ML services for embedding generation
- Main application for conversation processing

## Usage

The conversations service can be imported and used as follows:

```python
from src.conversations.detector import ConversationDetector
from src.conversations.manager import ConversationManager
from src.conversations.search import SemanticSearchService
```

## Future Development

This is a stub implementation. Future development will include:
- Conversation detection algorithms
- Embedding generation using AI models
- Database schema for conversation storage
- RESTful API implementation
- Comprehensive test coverage