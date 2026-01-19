#!/usr/bin/env python3
"""
Gmail MCP Server
Manage Gmail: search, delete, star/flag emails, mark as read/unread.

Requires Google OAuth credentials from Google Cloud Console.
"""

import os
import logging
from typing import Any, List, Union
import asyncio
import json
from mcp import server, types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
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
                # Delete invalid token and require re-auth
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                raise RuntimeError(
                    "Token refresh failed. Please delete token.json and re-authenticate. "
                    "Make sure your OAuth app has the correct redirect URIs configured: "
                    "http://localhost:8080/, http://localhost:63228/, http://localhost/"
                )
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                # Try to use a fixed port first
                try:
                    creds = flow.run_local_server(port=8080, prompt='consent')
                except OSError:
                    # If port 8080 is busy, use random port
                    creds = flow.run_local_server(port=0, prompt='consent')
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                raise RuntimeError(
                    f"OAuth authentication failed: {e}\n\n"
                    "Please ensure:\n"
                    "1. Your OAuth client is configured as 'Desktop app'\n"
                    "2. Redirect URIs include: http://localhost:8080/, http://localhost:63228/, http://localhost/\n"
                    "3. Gmail API is enabled in your Google Cloud project\n\n"
                    "See README.md for detailed setup instructions."
                )

        # Save the credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    _gmail_service = build('gmail', 'v1', credentials=creds)
    logger.info("Gmail API service initialized")
    return _gmail_service


@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Gmail tools."""
    return [
        types.Tool(
            name="search_emails",
            description="Search for emails using Gmail query syntax (e.g., 'subject:Invoice from:sender@example.com')",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query. Examples: 'subject:Invoice', 'from:example.com', 'is:unread older_than:30d'",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 20, max 100)",
                        "default": 20,
                    },
                    "include_snippet": {
                        "type": "boolean",
                        "description": "Include email snippet/preview in results (default true)",
                        "default": True,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="delete_emails",
            description="Permanently delete emails matching a search query (use with caution!)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query to find emails to delete",
                    },
                    "max_delete": {
                        "type": "integer",
                        "description": "Maximum number of emails to delete (safety limit, default 50)",
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
            description="Remove star/flag from emails matching a search query",
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
            description="Archive emails (remove from inbox) matching a search query",
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
        types.Tool(
            name="get_email_details",
            description="Get full details of a specific email by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "Gmail message ID",
                    },
                },
                "required": ["email_id"],
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

        if name == "search_emails":
            query = args.get("query", "")
            max_results = min(args.get("max_results", 20), 100)
            include_snippet = args.get("include_snippet", True)

            result = gmail.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = result.get('messages', [])

            if not messages:
                return [types.TextContent(
                    type="text",
                    text=f"No emails found matching query: '{query}'"
                )]

            email_details = []
            for msg in messages:
                if include_snippet:
                    full_msg = gmail.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()

                    headers = {h['name']: h['value'] for h in full_msg.get('payload', {}).get('headers', [])}

                    email_details.append({
                        "id": msg['id'],
                        "from": headers.get('From', 'Unknown'),
                        "subject": headers.get('Subject', 'No Subject'),
                        "date": headers.get('Date', 'Unknown'),
                        "snippet": full_msg.get('snippet', '')
                    })
                else:
                    email_details.append({"id": msg['id']})

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "query": query,
                    "count": len(messages),
                    "emails": email_details
                }, indent=2)
            )]

        elif name == "delete_emails":
            query = args.get("query", "")
            max_delete = min(args.get("max_delete", 50), 100)

            logger.info(f"Searching for emails to delete with query: '{query}', max_delete: {max_delete}")

            result = gmail.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_delete
            ).execute()

            messages = result.get('messages', [])
            logger.info(f"Found {len(messages)} messages matching query")

            if not messages:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "found": 0,
                        "deleted": 0,
                        "query": query,
                        "message": "No emails found matching this query. Try using 'search_emails' first to verify emails exist.",
                        "hint": "For 5+ year old emails, try: 'before:2020/01/01' or 'older_than:1825d'"
                    }, indent=2)
                )]

            deleted_count = 0
            failed_count = 0
            for msg in messages:
                try:
                    gmail.users().messages().delete(userId='me', id=msg['id']).execute()
                    deleted_count += 1
                    logger.info(f"Deleted message {msg['id']}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to delete message {msg['id']}: {e}")

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "found": len(messages),
                    "deleted": deleted_count,
                    "failed": failed_count,
                    "query": query
                }, indent=2)
            )]

        elif name == "star_emails":
            query = args.get("query", "")

            result = gmail.users().messages().list(userId='me', q=query).execute()
            messages = result.get('messages', [])

            if not messages:
                return [types.TextContent(
                    type="text",
                    text=f"No emails found to star matching query: '{query}'"
                )]

            starred_count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me',
                        id=msg['id'],
                        body={"addLabelIds": ["STARRED"]}
                    ).execute()
                    starred_count += 1
                except Exception as e:
                    logger.error(f"Failed to star message {msg['id']}: {e}")

            return [types.TextContent(
                type="text",
                text=f"Successfully starred {starred_count} emails matching query: '{query}'"
            )]

        elif name == "unstar_emails":
            query = args.get("query", "")

            result = gmail.users().messages().list(userId='me', q=query).execute()
            messages = result.get('messages', [])

            if not messages:
                return [types.TextContent(
                    type="text",
                    text=f"No emails found to unstar matching query: '{query}'"
                )]

            unstarred_count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me',
                        id=msg['id'],
                        body={"removeLabelIds": ["STARRED"]}
                    ).execute()
                    unstarred_count += 1
                except Exception as e:
                    logger.error(f"Failed to unstar message {msg['id']}: {e}")

            return [types.TextContent(
                type="text",
                text=f"Successfully unstarred {unstarred_count} emails matching query: '{query}'"
            )]

        elif name == "mark_as_read":
            query = args.get("query", "")

            result = gmail.users().messages().list(userId='me', q=query).execute()
            messages = result.get('messages', [])

            if not messages:
                return [types.TextContent(
                    type="text",
                    text=f"No emails found to mark as read matching query: '{query}'"
                )]

            marked_count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me',
                        id=msg['id'],
                        body={"removeLabelIds": ["UNREAD"]}
                    ).execute()
                    marked_count += 1
                except Exception as e:
                    logger.error(f"Failed to mark message {msg['id']} as read: {e}")

            return [types.TextContent(
                type="text",
                text=f"Successfully marked {marked_count} emails as read matching query: '{query}'"
            )]

        elif name == "mark_as_unread":
            query = args.get("query", "")

            result = gmail.users().messages().list(userId='me', q=query).execute()
            messages = result.get('messages', [])

            if not messages:
                return [types.TextContent(
                    type="text",
                    text=f"No emails found to mark as unread matching query: '{query}'"
                )]

            marked_count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me',
                        id=msg['id'],
                        body={"addLabelIds": ["UNREAD"]}
                    ).execute()
                    marked_count += 1
                except Exception as e:
                    logger.error(f"Failed to mark message {msg['id']} as unread: {e}")

            return [types.TextContent(
                type="text",
                text=f"Successfully marked {marked_count} emails as unread matching query: '{query}'"
            )]

        elif name == "archive_emails":
            query = args.get("query", "")

            result = gmail.users().messages().list(userId='me', q=query).execute()
            messages = result.get('messages', [])

            if not messages:
                return [types.TextContent(
                    type="text",
                    text=f"No emails found to archive matching query: '{query}'"
                )]

            archived_count = 0
            for msg in messages:
                try:
                    gmail.users().messages().modify(
                        userId='me',
                        id=msg['id'],
                        body={"removeLabelIds": ["INBOX"]}
                    ).execute()
                    archived_count += 1
                except Exception as e:
                    logger.error(f"Failed to archive message {msg['id']}: {e}")

            return [types.TextContent(
                type="text",
                text=f"Successfully archived {archived_count} emails matching query: '{query}'"
            )]

        elif name == "get_email_details":
            email_id = args.get("email_id", "")

            msg = gmail.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}

            details = {
                "id": msg['id'],
                "threadId": msg.get('threadId', ''),
                "from": headers.get('From', 'Unknown'),
                "to": headers.get('To', 'Unknown'),
                "subject": headers.get('Subject', 'No Subject'),
                "date": headers.get('Date', 'Unknown'),
                "snippet": msg.get('snippet', ''),
                "labels": msg.get('labelIds', [])
            }

            return [types.TextContent(
                type="text",
                text=json.dumps(details, indent=2)
            )]

        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except FileNotFoundError as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": "Setup required",
                "message": str(e),
                "hint": "See README.md for setup instructions"
            }, indent=2)
        )]
    except ImportError as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": "Dependencies missing",
                "message": str(e)
            }, indent=2)
        )]
    except Exception as e:
        logger.error(f"Error executing {name}: {e}")
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": "Execution failed",
                "message": str(e)
            }, indent=2)
        )]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gmail-cleaner",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logger.info("Starting Gmail MCP Server...")

    try:
        logger.info("Server is running and ready to accept requests")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        logger.info("Server shutdown complete")
