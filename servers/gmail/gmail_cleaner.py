#!/usr/bin/env python3
"""
Gmail MCP Server
Manage Gmail: search, read, send, delete, star/flag emails, mark as read/unread.

Requires Google OAuth credentials from Google Cloud Console.
"""

import os
import logging
import base64
from typing import Any, List, Union
import asyncio
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from mcp import server, types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
# gmail.modify: read, compose, trash, label management
# gmail.send: send emails
# https://mail.google.com/: full access including permanent delete
SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.send',
]
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')

# Initialize MCP server
app = Server("gmail-cleaner")

# Gmail service will be initialized when needed
_gmail_service = None


def get_gmail_service():
    """Initialize Gmail API service with OAuth credentials."""
    global _gmail_service

    if _gmail_service is not None:
        return _gmail_service

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Gmail API libraries not installed. "
            "Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )

    if not os.path.exists(CLIENT_SECRETS_FILE):
        raise FileNotFoundError(
            f"credentials.json not found at {CLIENT_SECRETS_FILE}. "
            "Download it from Google Cloud Console: "
            "https://console.cloud.google.com/apis/credentials"
        )

    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                raise RuntimeError(
                    "Token refresh failed. Deleted token.json - please restart to re-authenticate."
                )
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                try:
                    creds = flow.run_local_server(port=8080, prompt='consent')
                except OSError:
                    creds = flow.run_local_server(port=0, prompt='consent')
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                raise RuntimeError(
                    f"OAuth authentication failed: {e}\n\n"
                    "Please ensure:\n"
                    "1. Your OAuth client is configured as 'Desktop app'\n"
                    "2. Gmail API is enabled in your Google Cloud project\n"
                    "3. You added yourself as a test user in OAuth consent screen\n\n"
                    "See README.md for detailed setup instructions."
                )

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    _gmail_service = build('gmail', 'v1', credentials=creds)
    logger.info("Gmail API service initialized")
    return _gmail_service


def _get_email_body(payload):
    """Extract plain text body from email payload, handling multipart messages."""
    body = ""

    if payload.get('mimeType') == 'text/plain' and payload.get('body', {}).get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    elif payload.get('mimeType', '').startswith('multipart/'):
        for part in payload.get('parts', []):
            if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                break
            elif part.get('mimeType', '').startswith('multipart/'):
                # Nested multipart
                body = _get_email_body(part)
                if body:
                    break

    return body


def _make_response(data):
    """Create a JSON text response."""
    return [types.TextContent(type="text", text=json.dumps(data, indent=2))]


def _search_messages(gmail, query, max_results=100):
    """Search for messages and return all IDs, handling pagination."""
    all_messages = []
    result = gmail.users().messages().list(
        userId='me', q=query, maxResults=min(max_results, 500)
    ).execute()

    all_messages.extend(result.get('messages', []))

    while 'nextPageToken' in result and len(all_messages) < max_results:
        result = gmail.users().messages().list(
            userId='me', q=query,
            maxResults=min(max_results - len(all_messages), 500),
            pageToken=result['nextPageToken']
        ).execute()
        all_messages.extend(result.get('messages', []))

    return all_messages[:max_results]


@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Gmail tools."""
    return [
        types.Tool(
            name="search_emails",
            description="Search for emails using Gmail query syntax",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query. Examples: 'subject:Invoice', 'from:example.com', 'is:unread older_than:30d', 'before:2020/01/01'",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default 20, max 100)",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="read_email",
            description="Read the full content of an email by ID (use search_emails first to find IDs)",
            inputSchema={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Gmail message ID from search results",
                    },
                },
                "required": ["email_id"],
            },
        ),
        types.Tool(
            name="send_email",
            description="Send an email from your Gmail account",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address (comma-separated for multiple)",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line",
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body text (plain text)",
                    },
                    "cc": {
                        "type": "string",
                        "description": "CC recipients (comma-separated, optional)",
                    },
                    "bcc": {
                        "type": "string",
                        "description": "BCC recipients (comma-separated, optional)",
                    },
                },
                "required": ["to", "subject", "body"],
            },
        ),
        types.Tool(
            name="reply_to_email",
            description="Reply to an existing email thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Gmail message ID to reply to",
                    },
                    "body": {
                        "type": "string",
                        "description": "Reply body text",
                    },
                },
                "required": ["email_id", "body"],
            },
        ),
        types.Tool(
            name="trash_emails",
            description="Move emails to trash (recoverable for 30 days)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query to find emails to trash",
                    },
                    "max_trash": {
                        "type": "integer",
                        "description": "Maximum number of emails to trash (default 50, max 500)",
                        "default": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="delete_emails",
            description="PERMANENTLY delete emails (cannot be recovered! Use trash_emails instead for safe deletion)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query to find emails to permanently delete",
                    },
                    "max_delete": {
                        "type": "integer",
                        "description": "Maximum number of emails to delete (default 50, max 500)",
                        "default": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="star_emails",
            description="Star/flag emails matching a search query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query to find emails to star",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="unstar_emails",
            description="Remove star from emails matching a search query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query to find emails to unstar",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="mark_as_read",
            description="Mark emails as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query to find emails to mark as read",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="mark_as_unread",
            description="Mark emails as unread",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query to find emails to mark as unread",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="archive_emails",
            description="Archive emails (remove from inbox)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query to find emails to archive",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: Union[dict, None]
) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
    """Handle tool execution requests."""

    args = arguments or {}

    try:
        gmail = get_gmail_service()

        # --- SEARCH ---
        if name == "search_emails":
            query = args.get("query", "")
            max_results = min(args.get("max_results", 20), 100)

            messages = _search_messages(gmail, query, max_results)

            if not messages:
                return _make_response({"query": query, "count": 0, "emails": []})

            email_details = []
            for msg in messages:
                full_msg = gmail.users().messages().get(
                    userId='me', id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'To', 'Subject', 'Date']
                ).execute()

                headers = {h['name']: h['value'] for h in full_msg.get('payload', {}).get('headers', [])}

                email_details.append({
                    "id": msg['id'],
                    "from": headers.get('From', 'Unknown'),
                    "to": headers.get('To', 'Unknown'),
                    "subject": headers.get('Subject', 'No Subject'),
                    "date": headers.get('Date', 'Unknown'),
                    "snippet": full_msg.get('snippet', ''),
                    "labels": full_msg.get('labelIds', [])
                })

            return _make_response({"query": query, "count": len(email_details), "emails": email_details})

        # --- READ ---
        elif name == "read_email":
            email_id = args.get("email_id", "")

            msg = gmail.users().messages().get(
                userId='me', id=email_id, format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
            body = _get_email_body(msg.get('payload', {}))

            # Get attachment info
            attachments = []
            for part in msg.get('payload', {}).get('parts', []):
                if part.get('filename'):
                    attachments.append({
                        "filename": part['filename'],
                        "mimeType": part.get('mimeType', 'unknown'),
                        "size": part.get('body', {}).get('size', 0)
                    })

            return _make_response({
                "id": msg['id'],
                "threadId": msg.get('threadId', ''),
                "from": headers.get('From', 'Unknown'),
                "to": headers.get('To', 'Unknown'),
                "cc": headers.get('Cc', ''),
                "subject": headers.get('Subject', 'No Subject'),
                "date": headers.get('Date', 'Unknown'),
                "body": body,
                "labels": msg.get('labelIds', []),
                "attachments": attachments
            })

        # --- SEND ---
        elif name == "send_email":
            to = args.get("to", "")
            subject = args.get("subject", "")
            body = args.get("body", "")
            cc = args.get("cc", "")
            bcc = args.get("bcc", "")

            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            sent = gmail.users().messages().send(
                userId='me', body={'raw': raw}
            ).execute()

            return _make_response({
                "sent": True,
                "messageId": sent['id'],
                "threadId": sent.get('threadId', ''),
                "to": to,
                "subject": subject
            })

        # --- REPLY ---
        elif name == "reply_to_email":
            email_id = args.get("email_id", "")
            body = args.get("body", "")

            # Get original message for headers
            original = gmail.users().messages().get(
                userId='me', id=email_id, format='metadata',
                metadataHeaders=['From', 'To', 'Subject', 'Message-ID']
            ).execute()

            headers = {h['name']: h['value'] for h in original.get('payload', {}).get('headers', [])}
            thread_id = original.get('threadId', '')

            subject = headers.get('Subject', '')
            if not subject.lower().startswith('re:'):
                subject = f"Re: {subject}"

            reply_to = headers.get('From', '')

            message = MIMEText(body)
            message['to'] = reply_to
            message['subject'] = subject
            message['In-Reply-To'] = headers.get('Message-ID', '')
            message['References'] = headers.get('Message-ID', '')

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            sent = gmail.users().messages().send(
                userId='me', body={'raw': raw, 'threadId': thread_id}
            ).execute()

            return _make_response({
                "sent": True,
                "messageId": sent['id'],
                "threadId": sent.get('threadId', ''),
                "to": reply_to,
                "subject": subject
            })

        # --- TRASH (safe delete) ---
        elif name == "trash_emails":
            query = args.get("query", "")
            max_trash = min(args.get("max_trash", 50), 500)

            messages = _search_messages(gmail, query, max_trash)

            if not messages:
                return _make_response({"found": 0, "trashed": 0, "query": query})

            trashed = 0
            failed = 0
            for msg in messages:
                try:
                    gmail.users().messages().trash(userId='me', id=msg['id']).execute()
                    trashed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to trash message {msg['id']}: {e}")

            return _make_response({
                "found": len(messages), "trashed": trashed, "failed": failed, "query": query
            })

        # --- DELETE (permanent) ---
        elif name == "delete_emails":
            query = args.get("query", "")
            max_delete = min(args.get("max_delete", 50), 500)

            messages = _search_messages(gmail, query, max_delete)

            if not messages:
                return _make_response({"found": 0, "deleted": 0, "query": query})

            # Use batchDelete for efficiency when deleting many messages
            message_ids = [msg['id'] for msg in messages]

            if len(message_ids) > 1:
                try:
                    gmail.users().messages().batchDelete(
                        userId='me', body={'ids': message_ids}
                    ).execute()
                    return _make_response({
                        "found": len(message_ids), "deleted": len(message_ids),
                        "failed": 0, "query": query
                    })
                except Exception as e:
                    logger.error(f"Batch delete failed: {e}, falling back to individual delete")

            # Fallback: delete one by one
            deleted = 0
            failed = 0
            for msg_id in message_ids:
                try:
                    gmail.users().messages().delete(userId='me', id=msg_id).execute()
                    deleted += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to delete message {msg_id}: {e}")

            return _make_response({
                "found": len(message_ids), "deleted": deleted, "failed": failed, "query": query
            })

        # --- STAR / UNSTAR ---
        elif name == "star_emails":
            query = args.get("query", "")
            messages = _search_messages(gmail, query)

            if not messages:
                return _make_response({"found": 0, "starred": 0, "query": query})

            count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me', id=msg['id'],
                        body={"addLabelIds": ["STARRED"]}
                    ).execute()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to star message {msg['id']}: {e}")

            return _make_response({"found": len(messages), "starred": count, "query": query})

        elif name == "unstar_emails":
            query = args.get("query", "")
            messages = _search_messages(gmail, query)

            if not messages:
                return _make_response({"found": 0, "unstarred": 0, "query": query})

            count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me', id=msg['id'],
                        body={"removeLabelIds": ["STARRED"]}
                    ).execute()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to unstar message {msg['id']}: {e}")

            return _make_response({"found": len(messages), "unstarred": count, "query": query})

        # --- READ STATUS ---
        elif name == "mark_as_read":
            query = args.get("query", "")
            messages = _search_messages(gmail, query)

            if not messages:
                return _make_response({"found": 0, "marked_read": 0, "query": query})

            count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me', id=msg['id'],
                        body={"removeLabelIds": ["UNREAD"]}
                    ).execute()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to mark as read {msg['id']}: {e}")

            return _make_response({"found": len(messages), "marked_read": count, "query": query})

        elif name == "mark_as_unread":
            query = args.get("query", "")
            messages = _search_messages(gmail, query)

            if not messages:
                return _make_response({"found": 0, "marked_unread": 0, "query": query})

            count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me', id=msg['id'],
                        body={"addLabelIds": ["UNREAD"]}
                    ).execute()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to mark as unread {msg['id']}: {e}")

            return _make_response({"found": len(messages), "marked_unread": count, "query": query})

        # --- ARCHIVE ---
        elif name == "archive_emails":
            query = args.get("query", "")
            messages = _search_messages(gmail, query)

            if not messages:
                return _make_response({"found": 0, "archived": 0, "query": query})

            count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me', id=msg['id'],
                        body={"removeLabelIds": ["INBOX"]}
                    ).execute()
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to archive message {msg['id']}: {e}")

            return _make_response({"found": len(messages), "archived": count, "query": query})

        else:
            return _make_response({"error": f"Unknown tool: {name}"})

    except FileNotFoundError as e:
        return _make_response({"error": "Setup required", "message": str(e), "hint": "See README.md for setup instructions"})
    except ImportError as e:
        return _make_response({"error": "Dependencies missing", "message": str(e)})
    except Exception as e:
        logger.error(f"Error executing {name}: {e}")
        return _make_response({"error": "Execution failed", "message": str(e)})


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gmail-cleaner",
                server_version="2.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logger.info("Starting Gmail MCP Server v2.0...")

    try:
        logger.info("Server is running and ready to accept requests")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        logger.info("Server shutdown complete")
