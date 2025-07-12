# Messages Agent

A Python tool that safely extracts messages from macOS Messages.app and maps them to real contact names from AddressBook for AI agent integration.

## 🚀 Key Features

- **Safe Messages Database Access** - Never modifies original Messages database
- **Complete Contact Mapping** - Maps phone numbers/emails to real contact names (94.2% success rate)
- **Multi-Source Contact Search** - Searches iCloud, Google, Yahoo AddressBook sources
- **Optimized Database Schema** - Single table with joined message + contact data
- **Privacy-First Design** - Works entirely offline with local data

## 📊 Results

- **223,951** total messages processed
- **211,012** messages (94.2%) mapped to contact names
- **110** distinct contacts identified
- **Comprehensive contact data** from all AddressBook sources

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

3. **Grant Full Disk Access** (Required for Messages database access):
   - Open System Preferences > Security & Privacy > Privacy > Full Disk Access
   - Add Terminal.app or your IDE (VS Code, PyCharm, etc.)
   - Restart your terminal/IDE after granting permissions

## 🎯 Usage

### Quick Migration
Run the complete migration to create a database with contact names:

```bash
# Activate virtual environment
source venv/bin/activate

# Run migration
python migrate_database.py
```

This creates `data/messages_complete_contacts.db` with the complete dataset.

### Database Schema

The resulting database contains a single optimized table:

```sql
CREATE TABLE messages_with_contacts (
    -- Message data
    message_id INTEGER,
    text TEXT,
    date INTEGER,
    is_from_me INTEGER,
    service TEXT,
    
    -- Contact data
    phone_email TEXT,
    contact_first_name TEXT,
    contact_last_name TEXT,
    contact_full_name TEXT,
    
    -- Metadata
    created_at TIMESTAMP
);
```

### Example Queries

```sql
-- Top contacts by message count
SELECT contact_full_name, COUNT(*) as message_count 
FROM messages_with_contacts 
WHERE contact_full_name IS NOT NULL 
GROUP BY contact_full_name 
ORDER BY message_count DESC;

-- Recent messages with contact names
SELECT contact_full_name, text, datetime(date/1000000000 + 978307200, 'unixepoch') as date
FROM messages_with_contacts 
WHERE contact_full_name IS NOT NULL 
ORDER BY date DESC 
LIMIT 10;
```

## 📱 Database Viewing

Use [TablePlus](https://tableplus.com/) or any SQLite browser to explore the data:
- **Database Path:** `./data/messages_complete_contacts.db`
- **Type:** SQLite

## 🏗️ Project Structure

```
messages-agent/
├── src/
│   ├── database_manager.py      # Safe Messages DB copying
│   ├── database_migrator.py     # Contact name mapping
│   └── logger_config.py         # Logging system
├── migrate_database.py          # Main migration script
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

## 🔒 Security & Privacy

- **Never modifies** the original Messages database
- **Works with copies** in the `./data/` directory  
- **Processes data locally** - no external API calls
- **Respects user privacy** - all data stays on your machine

## 🔧 Technical Details

### Contact Mapping Process
1. **Extracts** all contacts from multiple AddressBook sources
2. **Normalizes** phone numbers for consistent matching
3. **Maps** Messages handles to real contact names
4. **Creates** optimized database with joined data

### AddressBook Sources Searched
- **iCloud Contacts** - `/Library/Application Support/AddressBook/Sources/[iCloud-ID]/`
- **Google Contacts** - `/Library/Application Support/AddressBook/Sources/[Google-ID]/`
- **Yahoo Contacts** - `/Library/Application Support/AddressBook/Sources/[Yahoo-ID]/`

## 🚧 Requirements

- **macOS** (Messages.app and AddressBook required)
- **Python 3.7+**
- **Full Disk Access** permission
- **Messages.app** with message history

## 🛠️ Troubleshooting

### "Permission Denied" Error
1. Grant Full Disk Access to Terminal/IDE in System Preferences
2. Restart Terminal/IDE after granting permissions
3. Ensure Messages.app has been opened at least once

### Low Contact Matching Rate
- Check that contacts exist in AddressBook/Contacts.app
- Verify phone numbers are properly formatted in contacts
- Try running migration again after updating contacts

## 📈 Future Enhancements

This database is ready for:
- **AI Response Generation** - Use contact names for personalized responses
- **Conversation Analytics** - Analyze messaging patterns by contact
- **Smart Notifications** - Context-aware message handling
- **Message Search** - Enhanced search with contact names

## 📄 License

This project is for educational and personal use only. Ensure you comply with all applicable laws and Apple's terms of service when accessing Messages data.

---

**Note:** This tool accesses your personal Messages data. Only use it on your own device and ensure you understand the privacy implications.