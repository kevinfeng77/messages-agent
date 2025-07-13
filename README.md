# Message Agent

An AI-powered communication assistant that analyzes message patterns, builds user profiles, and provides intelligent response suggestions. The system uses Graphiti for knowledge graph management and normalized database schemas for efficient data processing.

## 🚀 Key Features

- **Comprehensive Message Processing** - Extracts and processes messages from macOS Messages.app
- **Normalized Database Architecture** - Clean schema with users, chats, messages, and relationships
- **Privacy-First Design** - Works entirely offline with local data and encryption
- **Graphiti Integration** - Knowledge graph management for user profiling and pattern analysis  
- **Organized Codebase** - Modular structure with proper testing and validation
- **Simplified Setup** - One-command setup using Just task runner

## 🏗️ Project Architecture

The Message Agent system spans 4 main phases:

1. **Phase 1**: Data Preparation & Graphiti Integration
2. **Phase 2**: Data Ingestion Pipeline  
3. **Phase 3**: Intelligence Layer
4. **Phase 4**: Live Response System

### Technology Stack
- **Backend**: Python with SQLite database management
- **Database**: Normalized SQLite schema with proper indexing
- **AI/ML**: Graphiti for knowledge graphs, message text decoding
- **Infrastructure**: Organized script structure, comprehensive testing

## 🔧 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kevinfeng77/messages-agent.git
   cd messages-agent
   ```

2. **Create virtual environment and install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   pip install -r requirements.txt
   ```

3. **Install Just task runner:**
   ```bash
   # On macOS with Homebrew
   brew install just
   
   # Or follow installation instructions at https://github.com/casey/just
   ```

4. **Grant Full Disk Access** (Required for Messages database access):
   - Open System Preferences > Security & Privacy > Privacy > Full Disk Access
   - Add Terminal.app or your IDE (VS Code, PyCharm, etc.)
   - Restart your terminal/IDE after granting permissions

## 🎯 Usage

### Quick Setup
Run the complete setup with a single command:

```bash
# Activate virtual environment
source venv/bin/activate

# Complete setup from clean state
just setup
```

This command will:
1. Clean the data directory
2. Copy the Messages database safely
3. Create and populate the normalized messages.db

### Available Commands

```bash
# Setup and data management
just setup      # Complete setup from clean state
just copy       # Copy Messages database only  
just create     # Create and populate messages.db only
just clean      # Clean data directory

# Development and validation
just test       # Run all tests
just validate   # Run validation scripts
just lint       # Run code quality checks
just format     # Format code with black/isort
just stats      # Show database statistics
```

## 📊 Database Schema

The system uses a normalized database schema with four main tables:

### Users Table
```sql
CREATE TABLE users (
    user_id TEXT NOT NULL,
    first_name TEXT NOT NULL, 
    last_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT NOT NULL,
    handle_id INTEGER
);
```

### Chats Table  
```sql
CREATE TABLE chats (
    chat_id INTEGER NOT NULL PRIMARY KEY,
    display_name TEXT NOT NULL
);
```

### Messages Table
```sql
CREATE TABLE messages (
    message_id INTEGER NOT NULL PRIMARY KEY,
    user_id TEXT NOT NULL,
    contents TEXT NOT NULL,
    is_from_me BOOLEAN,
    created_at TIMESTAMP NOT NULL
);
```

### Junction Tables
```sql
-- Many-to-many: chats ↔ users
CREATE TABLE chat_users (
    chat_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);

-- Many-to-many: chats ↔ messages  
CREATE TABLE chat_messages (
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    message_date TIMESTAMP NOT NULL,
    PRIMARY KEY (chat_id, message_id)
);
```

### Example Queries

```sql
-- Get all messages in a chat with user details
SELECT m.contents, u.first_name, u.last_name, m.created_at
FROM messages m
JOIN users u ON m.user_id = u.user_id
JOIN chat_messages cm ON m.message_id = cm.message_id
WHERE cm.chat_id = 1
ORDER BY m.created_at;

-- Find all chats for a specific user
SELECT c.display_name, c.chat_id
FROM chats c
JOIN chat_users cu ON c.chat_id = cu.chat_id
WHERE cu.user_id = 'user123';
```

## 📂 Project Structure

```
ai_text_agent/
├── src/                          # Core application modules
│   ├── database/                 # Database management
│   │   ├── manager.py           # Original Messages DB copying
│   │   ├── messages_db.py       # New normalized database
│   │   ├── migrator.py          # Migration utilities
│   │   └── tests/               # Database tests
│   ├── extractors/              # Data extraction modules
│   │   ├── addressbook_extractor.py  # Contact extraction
│   │   └── tests/
│   ├── graphiti/                # Knowledge graph integration
│   │   ├── episode_manager.py   # Graphiti episodes
│   │   ├── query_manager.py     # Graph queries
│   │   └── tests/
│   ├── messaging/               # Message processing
│   │   ├── decoder.py           # Text decoding from binary
│   │   └── tests/
│   ├── user/                    # User management
│   │   ├── user.py              # User model
│   │   ├── handle_matcher.py    # Handle-to-user mapping
│   │   └── tests/
│   └── utils/                   # Shared utilities
│       ├── logger_config.py     # Logging configuration
│       └── tests/
├── scripts/                     # Organized utility scripts
│   ├── copy_messages_database.py    # Copy Messages DB
│   ├── setup_messages_database.py  # Setup normalized DB
│   ├── migration/               # Database migrations
│   ├── validation/              # Validation scripts
│   └── debug/                   # Debug utilities
├── tests/                       # Integration tests
├── data/                        # Generated databases
│   ├── copy/                    # Messages database copy
│   └── messages.db              # Normalized database
├── logs/                        # Application logs
├── justfile                     # Task runner commands
├── CLAUDE.md                    # Project instructions for AI
└── requirements.txt             # Python dependencies
```

## 🔒 Security & Privacy

- **Never modifies** the original Messages database
- **Works with copies** in the `./data/` directory  
- **Processes data locally** - no external API calls
- **Respects user privacy** - all data stays on your machine
- **Organized access patterns** - controlled through normalized schema

## 🛠️ Development

### Code Quality
```bash
# Format code
just format

# Run linting
just lint

# Run tests  
just test

# Run validation
just validate
```

### Database Management
```bash
# View database statistics
just stats

# Clean and recreate databases
just clean setup
```

## 🚧 Requirements

- **macOS** (Messages.app and AddressBook required)
- **Python 3.7+**
- **Just task runner**
- **Full Disk Access** permission
- **Messages.app** with message history

## 🧪 Testing

The project includes comprehensive testing:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Database and cross-component testing  
- **Validation Scripts**: End-to-end workflow validation
- **Performance Tests**: Database operation efficiency

Run all tests with:
```bash
just test
just validate
```

## 🛠️ Troubleshooting

### "Permission Denied" Error
1. Grant Full Disk Access to Terminal/IDE in System Preferences
2. Restart Terminal/IDE after granting permissions
3. Ensure Messages.app has been opened at least once

### Setup Issues
- Verify Just is installed: `just --version`
- Check Python virtual environment is activated
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Database Issues
- Clean and recreate: `just clean setup`
- Check database file permissions in `./data/` directory
- View statistics: `just stats`

## 📈 Future Enhancements

This system is designed for:
- **AI Response Generation** - Contextual response suggestions using Graphiti
- **Conversation Analytics** - Advanced messaging pattern analysis
- **Real-time Processing** - Live message interception and processing
- **Multi-platform Support** - Extension to other messaging platforms
- **Advanced Privacy Controls** - Enhanced encryption and data protection

## 📄 License

This project is for educational and personal use only. Ensure you comply with all applicable laws and Apple's terms of service when accessing Messages data.

---

**Note:** This tool accesses your personal Messages data. Only use it on your own device and ensure you understand the privacy implications.