# Gmail MCP Server

Manage your Gmail inbox: search, read, send, reply, delete, star, archive, and mark emails as read/unread.

## Status: Ready (v2.0)

Full Gmail management with read, write, send, and delete capabilities using Google's official Gmail API.

## Features

- **Search Emails**: Powerful Gmail query syntax support
- **Read Emails**: Full email body, headers, and attachment info
- **Send Emails**: Compose and send new emails with CC/BCC
- **Reply to Emails**: Reply within existing threads
- **Trash Emails**: Safe delete (recoverable for 30 days)
- **Delete Emails**: Permanent deletion with batch support
- **Star/Unstar**: Flag important emails
- **Mark Read/Unread**: Manage email read status
- **Archive**: Remove emails from inbox

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
4. Configure OAuth consent screen and test users:
   - Go to "OAuth consent screen" in the left sidebar
   - Configure app name, user support email, developer contact
   - Under "Test users", click "+ ADD USERS"
   - Add your Gmail address (the one you'll use with the MCP server)
   - Click "Save"
5. Create OAuth credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - **IMPORTANT**: Choose "Desktop app" as application type (NOT "Web application")
   - Click "Create"
   - Download the JSON file
6. Rename the downloaded file to `credentials.json`
7. Place it in `servers/gmail/credentials.json`

**Important**: You must add yourself as a test user (step 4) or you'll get a 403 error during OAuth!

### 3. Configure Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "gmail-cleaner": {
      "command": "python3",
      "args": ["/path/to/ClaudeMCP/servers/gmail/gmail_cleaner.py"]
    }
  }
}
```

### 4. First Run Authentication

The first time you use the server, it will:
1. Open your browser for Google OAuth
2. Ask you to authorize the app (full Gmail access + send)
3. Save a `token.json` file for future use

**Note**: The `token.json` file contains your access credentials - keep it secure and don't commit it to git!

## Available Tools

### `search_emails`
Search for emails using Gmail's query syntax.

**Parameters:**
- `query` (required): Gmail search query
- `max_results` (optional): Max results (default 20, max 100)

**Example queries:**
- `subject:Invoice` - Emails with "Invoice" in subject
- `from:example@gmail.com` - Emails from specific sender
- `is:unread older_than:30d` - Unread emails older than 30 days
- `has:attachment larger:5M` - Emails with attachments over 5MB
- `before:2020/01/01` - Emails before a specific date

### `read_email`
Read the full content of an email including body text and attachment info.

**Parameters:**
- `email_id` (required): Gmail message ID (from search results)

### `send_email`
Send a new email from your Gmail account.

**Parameters:**
- `to` (required): Recipient email (comma-separated for multiple)
- `subject` (required): Email subject line
- `body` (required): Email body (plain text)
- `cc` (optional): CC recipients (comma-separated)
- `bcc` (optional): BCC recipients (comma-separated)

### `reply_to_email`
Reply to an existing email thread.

**Parameters:**
- `email_id` (required): Gmail message ID to reply to
- `body` (required): Reply body text

### `trash_emails`
Move emails to trash (recoverable for 30 days).

**Parameters:**
- `query` (required): Gmail search query
- `max_trash` (optional): Safety limit (default 50, max 500)

### `delete_emails`
PERMANENTLY delete emails (cannot be recovered!).

**Parameters:**
- `query` (required): Gmail search query
- `max_delete` (optional): Safety limit (default 50, max 500)

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

## Usage Examples

Ask Claude things like:

- "Search my Gmail for all unread emails from last week"
- "Read the latest email from my boss"
- "Send an email to john@example.com about the meeting tomorrow"
- "Reply to the latest email from Sarah saying I'll be there"
- "Trash all promotional emails older than 60 days"
- "Permanently delete all emails before 2020"
- "Star all emails from my boss with 'urgent' in the subject"
- "Mark all emails from newsletters@example.com as read"
- "Archive all emails in my inbox from before January 2024"

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
- **Full Access Scope**: Required for permanent delete and send capabilities
- **Safety Limits**: Delete/trash operations limited to prevent accidents
- **Batch Operations**: Uses efficient batchDelete for bulk operations
- **Token Storage**: Credentials stored locally in `token.json`
- **No API Keys**: No hardcoded credentials in code

## Files

- `gmail_cleaner.py` - Main MCP server implementation
- `credentials.json` - OAuth client credentials (you provide this)
- `token.json` - OAuth access token (auto-generated, keep private!)

## Important Notes

1. **Keep credentials.json private**: Contains your OAuth client ID/secret
2. **Don't commit token.json**: Contains your personal access credentials
3. **Trash vs Delete**: Use `trash_emails` for safe deletion (30-day recovery), `delete_emails` for permanent
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

**"Error 403: access_denied" during OAuth**
- Most common cause: You haven't added yourself as a test user in the OAuth consent screen
- Go to OAuth consent screen > Test users > + ADD USERS
- Add your Gmail address and save
- Make sure your OAuth client type is "Desktop app" (not "Web application")
- Delete `token.json` and try again
- Restart Claude Desktop

**Emails not deleting (0 deleted)**
- The old `gmail.modify` scope doesn't support permanent delete
- Delete `token.json` to force re-authentication with the new full-access scope
- Restart Claude Desktop

**Rate limit errors**
- The Gmail API has quotas - wait a few seconds between large operations

## Changelog

### v2.0
- **Fixed**: Delete now works - upgraded scope from `gmail.modify` to full access (`https://mail.google.com/`)
- **Added**: `read_email` - Read full email body and attachments
- **Added**: `send_email` - Send new emails with CC/BCC support
- **Added**: `reply_to_email` - Reply within existing threads
- **Added**: `trash_emails` - Safe delete (recoverable for 30 days)
- **Added**: Batch delete for bulk operations
- **Added**: Pagination support for large result sets
- **Improved**: All responses now return structured JSON
- **Improved**: Consistent error handling across all tools

### v1.0
- Initial release with search, delete, star, mark read/unread, archive

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Gmail Search Operators](https://support.google.com/mail/answer/7190)
- [Google OAuth Setup](https://developers.google.com/gmail/api/quickstart/python)
