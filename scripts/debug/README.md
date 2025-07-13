# Debug Scripts

This folder contains debugging and diagnostic scripts for troubleshooting issues with the Message Agent system.

## Scripts

### `debug_addressbook_data.py`
Analyzes and debugs AddressBook database issues:
- Shows database paths and accessibility
- Extracts and displays contact records
- Helps diagnose contact extraction problems

### `debug_binary.py`  
Debugs binary message decoding issues:
- Analyzes message text encoding problems
- Helps with character encoding and binary data issues

### `analyze_nsdictionary.py`
Analyzes NSDictionary parsing failures in MessageDecoder:
- Examines binary structure of NSAttributedString data
- Helps debug messages that return "NSDictionary" instead of text
- Provides hex dumps and pattern analysis for troubleshooting

## Usage

Run debug scripts from the project root:

```bash
# Debug address book issues
python scripts/debug/debug_addressbook_data.py

# Debug binary encoding issues  
python scripts/debug/debug_binary.py

# Analyze NSDictionary parsing issues
python scripts/debug/analyze_nsdictionary.py
```

## When to Use

- **Contact Extraction Issues**: Use `debug_addressbook_data.py` when users aren't being extracted properly from the address book
- **Message Encoding Problems**: Use `debug_binary.py` when seeing garbled text or encoding errors in messages
- **NSDictionary Parsing Issues**: Use `analyze_nsdictionary.py` when messages decode as "NSDictionary" instead of actual text
- **Database Access Issues**: Use these scripts to verify database accessibility and data integrity