# Gmail MCP Server

Manage your Gmail inbox: search, delete, star, archive, and mark emails as read/unread.

## Status: Ready

This server provides safe, read-modify access to your Gmail account using Google's official Gmail API.

## Features

- **Search Emails**: Powerful Gmail query syntax support
- **Delete Emails**: Permanently delete emails (with safety limits)
- **Star/Unstar**: Flag important emails
- **Mark Read/Unread**: Manage email read status
- **Archive**: Remove emails from inbox
- **Email Details**: Get full details of specific emails

## Setup

### 1. Install Dependencies

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

Or from the project root:

```bash
pip install -r requirements.txt
```

### 2. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as application type
   - Download the JSON file
5. Rename the downloaded file to `credentials.json`
6. Place it in `servers/gmail/credentials.json`

### 3. Configure Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "gmail-cleaner": {
      "command": "python3",
      "args": ["/Users/yourusername/Desktop/repo/ClaudeMCP/servers/gmail/gmail_cleaner.py"]
    }
  }
}
```

### 4. First Run Authentication

The first time you use the server, it will:
1. Open your browser for Google OAuth
2. Ask you to authorize the app
3. Save a `token.json` file for future use

**Note**: The `token.json` file contains your access credentials - keep it secure and don't commit it to git!

## Available Tools

### `search_emails`
Search for emails using Gmail's query syntax.

**Parameters:**
- `query` (required): Gmail search query
- `max_results` (optional): Max results (default 20, max 100)
- `include_snippet` (optional): Include email previews (default true)

**Example queries:**
- `subject:Invoice` - Emails with "Invoice" in subject
- `from:example@gmail.com` - Emails from specific sender
- `is:unread older_than:30d` - Unread emails older than 30 days
- `has:attachment larger:5M` - Emails with attachments over 5MB

### `delete_emails`
Permanently delete emails (use with caution!).

**Parameters:**
- `query` (required): Gmail search query
- `max_delete` (optional): Safety limit (default 50, max 100)

### `star_emails` / `unstar_emails`
Add or remove stars from emails.

**Parameters:**
- `query` (required): Gmail search query

### `mark_as_read` / `mark_as_unread`
Change read status of emails.

**Parameters:**
- `query` (required): Gmail search query

### `archive_emails`
Remove emails from inbox (archives them).

**Parameters:**
- `query` (required): Gmail search query

### `get_email_details`
Get full details of a specific email.

**Parameters:**
- `email_id` (required): Gmail message ID (from search results)

## Usage Examples

Ask Claude things like:

- "Search my Gmail for all unread emails from last week"
- "Star all emails from my boss with 'urgent' in the subject"
- "Delete all promotional emails older than 60 days"
- "Mark all emails from newsletters@example.com as read"
- "Archive all emails in my inbox from before January 2024"
- "Show me emails with attachments larger than 10MB"

## Gmail Query Syntax

Common Gmail search operators:

- `from:sender@example.com` - From specific sender
- `to:recipient@example.com` - To specific recipient
- `subject:text` - Subject contains text
- `has:attachment` - Has attachments
- `is:unread` - Unread emails
- `is:starred` - Starred emails
- `is:important` - Important emails
- `in:inbox` - In inbox
- `label:labelname` - Has specific label
- `after:2024/01/01` - After date
- `before:2024/12/31` - Before date
- `older_than:30d` - Older than X days/months/years
- `newer_than:7d` - Newer than X days/months/years
- `larger:5M` - Size larger than X (K/M)
- `smaller:1M` - Size smaller than X (K/M)

Combine with AND/OR:
- `from:boss@company.com subject:urgent` (AND is implicit)
- `from:alice@example.com OR from:bob@example.com`
- `subject:(meeting OR call) after:2024/01/01`

## Security

- **OAuth Authentication**: Uses official Google OAuth flow
- **Read-Modify Access**: Can read and modify emails, but not send
- **Safety Limits**: Delete operations limited to prevent accidents
- **Token Storage**: Credentials stored locally in `token.json`
- **No API Keys**: No hardcoded credentials in code

## Files

- `gmail_cleaner.py` - Main MCP server implementation
- `credentials.json` - OAuth client credentials (you provide this)
- `token.json` - OAuth access token (auto-generated, keep private!)

## Important Notes

1. **Keep credentials.json private**: Contains your OAuth client ID/secret
2. **Don't commit token.json**: Contains your personal access credentials
3. **Review before deleting**: Delete operations are permanent
4. **API Quotas**: Free Gmail API has daily quotas (250 quota units/user/second, 1 billion/day)

## Troubleshooting

**"credentials.json not found"**
- Download OAuth credentials from Google Cloud Console
- Place in `servers/gmail/` directory

**"Invalid grant" error**
- Delete `token.json` and re-authenticate

**"Access blocked" during OAuth**
- Your app needs to be verified by Google for production use
- For personal use, click "Advanced" > "Go to [app name] (unsafe)"

**Rate limit errors**
- The Gmail API has quotas - wait a few seconds between large operations

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Gmail Search Operators](https://support.google.com/mail/answer/7190)
- [Google OAuth Setup](https://developers.google.com/gmail/api/quickstart/python)
