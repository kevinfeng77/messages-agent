# Message Maker Service

AI-powered chat response generation using conversation history and context.

## Overview

The Message Maker Service generates contextually appropriate response suggestions by analyzing chat history with LLM processing. It takes a new incoming message and produces three response variations based on conversation patterns and user communication style.

## Quick Start

### Prerequisites

1. **API Key**: Set your Anthropic API key
   ```bash
   export ANTHROPIC_API_KEY="your_api_key_here"
   ```

2. **Database**: Ensure messages database exists at `./data/messages.db`
   ```bash
   # Run migration if needed
   python scripts/migration/migrate_messages_table.py
   ```

### Simple Test

Use the provided test script to generate responses for any chat:

```bash
# Basic usage
python test_message_maker.py "Display Name" "message content"

# With custom context limit (default: 500 messages)
python test_message_maker.py "Nick Kim" "how have you been" 200
```

**Example:**
```bash
python test_message_maker.py "Nick Kim" "how have you been"
```

Output:
```
>ê Testing Message Generation
Chat: Nick Kim
Message: how have you been
Context Limit: 500 messages
============================================================
1. Looking up chat...
    Found chat_id: 42, user_id: user-123
2. Creating request...
    Request created
3. Generating responses...
    Responses generated

=ñ Generated Responses:
============================================================

Option 1:
  I've been doing really well! Just been busy with work and some personal projects. How about you?

Option 2:
  Pretty good! Thanks for asking. Been keeping busy. What's new with you?

Option 3:
  I've been great! Life's been pretty hectic but in a good way. How have you been doing?

 Test completed successfully!
```

## API Usage

### Basic API Call

```python
from src.message_maker.api import generate_message_responses
from src.message_maker.types import MessageRequest

# Create request
request = MessageRequest(
    chat_id=123,
    user_id="user-456", 
    contents="Hey, how's your day going?"
)

# Generate responses (default: 2000 messages context)
response = generate_message_responses(request)

# Or with custom context limit
response = generate_message_responses(request, max_context_messages=500)

# Access responses
print("Response 1:", response.response_1)
print("Response 2:", response.response_2)
print("Response 3:", response.response_3)
```

### Service Class

```python
from src.message_maker.api import MessageMakerService

# Initialize service
service = MessageMakerService(db_path="./data/messages.db")

# Generate with custom context
response = service.generate_message_responses(request, max_context_messages=1000)
```

## Database Schema

The service uses the following key tables:

- **`chats`**: Chat metadata with display names
- **`messages`**: Individual message contents and metadata  
- **`chat_messages`**: Junction table linking chats to messages
- **`users`**: User information and IDs

### Finding Chats by Display Name

The test script automatically maps display names to chat IDs:

```python
from src.database.messages_db import MessagesDatabase

db = MessagesDatabase()
chats = db.get_chats_by_display_name("Nick Kim")
```

## Configuration

### Context Limits

- **Default**: 2000 messages for API calls
- **Test Script Default**: 500 messages for faster testing
- **Customizable**: Pass `max_context_messages` parameter

### Environment Variables

- **`ANTHROPIC_API_KEY`**: Required for LLM functionality
- **`DATABASE_PATH`**: Optional, defaults to `./data/messages.db`

## Architecture

### Components

1. **`api.py`**: Main orchestration and service class
2. **`types.py`**: Data models (MessageRequest, MessageResponse, etc.)
3. **`chat_history.py`**: Database query logic for retrieving conversation history
4. **`llm_client.py`**: Anthropic Claude integration for response generation

### Workflow

1. **Input Validation**: Validate request data
2. **Chat Lookup**: Find chat by display name ’ chat_id
3. **History Retrieval**: Get recent messages (limited by context parameter)
4. **LLM Processing**: Generate 3 response variations using chat context
5. **Response Return**: Return structured response with options

## Error Handling

Common error scenarios:

- **Display name not found**: `ValueError: No chat found with display name 'Name'`
- **Multiple matches**: `ValueError: Multiple chats found with display name 'Name'`
- **Missing API key**: `Error: ANTHROPIC_API_KEY environment variable is required`
- **Database not found**: `Error: Database file not found at ./data/messages.db`

## Performance

### Context Limits

- **500 messages**: ~5 seconds, good for testing
- **1000 messages**: ~8 seconds, balanced performance
- **2000 messages**: ~15 seconds, maximum context

### Cost Optimization

- Use smaller context limits for frequent testing
- Default limits are optimized for quality vs. cost balance
- Monitor token usage for production deployments

## Testing

### Test Script Features

- Display name to chat_id mapping
- Configurable context limits
- Error handling and validation
- Clear output formatting

### Manual Testing

```bash
# Test with minimal context
python test_message_maker.py "Contact Name" "test message" 50

# Test with large context  
python test_message_maker.py "Contact Name" "test message" 1500
```

## Troubleshooting

1. **Import errors**: Ensure you're in the project root directory
2. **Database errors**: Run migration scripts to set up tables
3. **API errors**: Verify ANTHROPIC_API_KEY is set correctly
4. **No responses**: Check that chat has sufficient message history

## Development

### Adding Features

- Modify `api.py` for workflow changes
- Update `types.py` for new data structures  
- Extend `llm_client.py` for prompt improvements
- Add validation in test script

### Code Style

- Follow existing patterns in the codebase
- Include type hints and docstrings
- Add error handling for edge cases
- Test with real conversation data

## Next Steps

The Message Maker Service is ready for:

1. **Integration**: Embed in larger messaging applications
2. **API Server**: Wrap in FastAPI/Flask for HTTP endpoints
3. **Batch Processing**: Process multiple requests concurrently
4. **Caching**: Add response caching for repeated contexts
5. **Monitoring**: Add metrics and logging for production use