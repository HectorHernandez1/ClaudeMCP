#!/usr/bin/env python3
"""
Personal Finance Database MCP Server
Connects to the money_stuff PostgreSQL database for spending tracking.

Gracefully handles connection failures - if the database is unavailable
(e.g., you're away from home), the server returns helpful error messages
instead of crashing.
"""

import os
import logging
from typing import Any, Dict, List, Union, Optional
import asyncio
import json
from datetime import datetime, date
from decimal import Decimal
from mcp import server, types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration from environment
# SECURITY: Only localhost connections allowed - no remote database access
ALLOWED_HOST = "localhost"
DB_CONFIG = {
    "host": ALLOWED_HOST,  # Fixed to localhost for security
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "money_stuff"),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Schema for the personal finance database
SCHEMA = "budget_app"

# Initialize MCP server
app = Server("finance-database")


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for database types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class FinanceDatabaseProvider:
    """
    Async PostgreSQL database provider with graceful error handling.

    If the database is unavailable, methods return helpful error messages
    instead of crashing the MCP server.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
        self._connection_error: Optional[str] = None

    async def _ensure_pool(self) -> bool:
        """
        Ensure connection pool exists. Returns True if connected, False otherwise.
        Stores connection error for helpful user feedback.
        """
        if self.pool is not None:
            return True

        try:
            import asyncpg
        except ImportError:
            self._connection_error = (
                "asyncpg library not installed. "
                "Run: pip install asyncpg"
            )
            logger.error(self._connection_error)
            return False

        try:
            self.pool = await asyncpg.create_pool(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
            self._connection_error = None
            logger.info(f"Connected to database: {self.config['database']}")
            return True
        except asyncpg.InvalidCatalogNameError:
            self._connection_error = (
                f"Database '{self.config['database']}' does not exist. "
                "Please create it first with: createdb money_stuff"
            )
        except asyncpg.InvalidPasswordError:
            self._connection_error = (
                "Invalid database credentials. "
                "Check DB_USER and DB_PASSWORD in your .env file."
            )
        except OSError as e:
            if "Connection refused" in str(e) or "could not connect" in str(e).lower():
                self._connection_error = (
                    f"Cannot connect to PostgreSQL at {self.config['host']}:{self.config['port']}. "
                    "Is the database server running? If you're away from home, "
                    "the database may not be accessible - this is expected behavior."
                )
            else:
                self._connection_error = f"Connection error: {e}"
        except Exception as e:
            self._connection_error = f"Database connection failed: {e}"

        logger.warning(self._connection_error)
        return False

    def get_connection_error(self) -> Optional[str]:
        """Get the last connection error message."""
        return self._connection_error

    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a read-only query and return results."""
        if not await self._ensure_pool():
            raise ConnectionError(self._connection_error)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def execute_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return single result."""
        if not await self._ensure_pool():
            raise ConnectionError(self._connection_error)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def get_schema_tables(self) -> List[Dict[str, Any]]:
        """Get all tables in the budget_app schema."""
        query = """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = $1
            ORDER BY table_name
        """
        return await self.execute_query(query, SCHEMA)

    async def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
        """
        return await self.execute_query(query, SCHEMA, table_name)

    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection closed")


# Initialize the database provider
db_provider = FinanceDatabaseProvider(DB_CONFIG)


def format_error_response(error: str) -> List[types.TextContent]:
    """Format an error as a helpful response."""
    return [types.TextContent(
        type="text",
        text=json.dumps({
            "error": True,
            "message": error,
            "hint": "The database may be unavailable. This won't break Claude Code - other tools continue working normally."
        }, indent=2)
    )]


def format_success_response(data: Any) -> List[types.TextContent]:
    """Format successful data as JSON response."""
    return [types.TextContent(
        type="text",
        text=json.dumps(data, indent=2, cls=JSONEncoder)
    )]


@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available database tools."""
    return [
        types.Tool(
            name="get_spending_summary",
            description="Get a summary of spending by category for a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD). Defaults to first day of current month.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD). Defaults to today.",
                    },
                    "person_id": {
                        "type": "integer",
                        "description": "Filter by person ID (optional)",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_recent_transactions",
            description="Get recent transactions with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of transactions to return (default 20, max 100)",
                        "default": 20,
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by spending category name",
                    },
                    "person_id": {
                        "type": "integer",
                        "description": "Filter by person ID",
                    },
                    "min_amount": {
                        "type": "number",
                        "description": "Minimum transaction amount",
                    },
                    "max_amount": {
                        "type": "number",
                        "description": "Maximum transaction amount",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_monthly_totals",
            description="Get total spending by month for the past year",
            inputSchema={
                "type": "object",
                "properties": {
                    "months": {
                        "type": "integer",
                        "description": "Number of months to include (default 12)",
                        "default": 12,
                    },
                    "person_id": {
                        "type": "integer",
                        "description": "Filter by person ID (optional)",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_category_breakdown",
            description="Get detailed breakdown of spending by category",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Year to analyze (defaults to current year)",
                    },
                    "month": {
                        "type": "integer",
                        "description": "Month to analyze (1-12, optional)",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="search_transactions",
            description="Search transactions by description",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Text to search for in transaction descriptions",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default 20)",
                        "default": 20,
                    },
                },
                "required": ["search_term"],
            },
        ),
        types.Tool(
            name="list_categories",
            description="List all available spending categories",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="list_persons",
            description="List all persons in the database",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="list_accounts",
            description="List all account types (credit cards, etc.)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_database_status",
            description="Check database connection status and basic stats",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="execute_select_query",
            description="Execute a custom SELECT query (read-only, advanced users)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query to execute. Must start with SELECT.",
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
        if name == "get_database_status":
            # Special case: check connection without failing
            connected = await db_provider._ensure_pool()
            if connected:
                # Get some basic stats
                try:
                    stats = await db_provider.execute_one(f"""
                        SELECT
                            (SELECT COUNT(*) FROM {SCHEMA}.transactions) as total_transactions,
                            (SELECT COUNT(*) FROM {SCHEMA}.persons) as total_persons,
                            (SELECT COUNT(*) FROM {SCHEMA}.spending_categories) as total_categories
                    """)
                    return format_success_response({
                        "connected": True,
                        "database": DB_CONFIG["database"],
                        "host": DB_CONFIG["host"],
                        "schema": SCHEMA,
                        "stats": stats
                    })
                except Exception as e:
                    return format_success_response({
                        "connected": True,
                        "database": DB_CONFIG["database"],
                        "host": DB_CONFIG["host"],
                        "schema": SCHEMA,
                        "stats_error": str(e)
                    })
            else:
                return format_success_response({
                    "connected": False,
                    "error": db_provider.get_connection_error(),
                    "hint": "Database unavailable. Other Claude tools still work normally."
                })

        elif name == "get_spending_summary":
            start_date = args.get("start_date")
            end_date = args.get("end_date")
            person_id = args.get("person_id")

            # Build query with optional filters
            query = f"""
                SELECT
                    sc.category_name,
                    COUNT(*) as transaction_count,
                    SUM(t.amount) as total_amount,
                    AVG(t.amount) as avg_amount,
                    MIN(t.amount) as min_amount,
                    MAX(t.amount) as max_amount
                FROM {SCHEMA}.transactions t
                JOIN {SCHEMA}.spending_categories sc ON t.category_id = sc.id
                WHERE 1=1
            """
            params = []
            param_idx = 1

            if start_date:
                query += f" AND t.transaction_date >= ${param_idx}"
                params.append(start_date)
                param_idx += 1

            if end_date:
                query += f" AND t.transaction_date <= ${param_idx}"
                params.append(end_date)
                param_idx += 1

            if person_id:
                query += f" AND t.person_id = ${param_idx}"
                params.append(person_id)
                param_idx += 1

            query += """
                GROUP BY sc.category_name
                ORDER BY total_amount DESC
            """

            results = await db_provider.execute_query(query, *params)

            # Calculate grand total
            grand_total = sum(r["total_amount"] or 0 for r in results)

            return format_success_response({
                "summary": results,
                "grand_total": grand_total,
                "filters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "person_id": person_id
                }
            })

        elif name == "get_recent_transactions":
            limit = min(args.get("limit", 20), 100)
            category = args.get("category")
            person_id = args.get("person_id")
            min_amount = args.get("min_amount")
            max_amount = args.get("max_amount")

            query = f"""
                SELECT
                    t.id,
                    t.transaction_date,
                    t.description,
                    t.amount,
                    sc.category_name,
                    p.name as person_name,
                    at.account_name
                FROM {SCHEMA}.transactions t
                JOIN {SCHEMA}.spending_categories sc ON t.category_id = sc.id
                JOIN {SCHEMA}.persons p ON t.person_id = p.id
                JOIN {SCHEMA}.account_type at ON t.account_type_id = at.id
                WHERE 1=1
            """
            params = []
            param_idx = 1

            if category:
                query += f" AND LOWER(sc.category_name) = LOWER(${param_idx})"
                params.append(category)
                param_idx += 1

            if person_id:
                query += f" AND t.person_id = ${param_idx}"
                params.append(person_id)
                param_idx += 1

            if min_amount is not None:
                query += f" AND t.amount >= ${param_idx}"
                params.append(min_amount)
                param_idx += 1

            if max_amount is not None:
                query += f" AND t.amount <= ${param_idx}"
                params.append(max_amount)
                param_idx += 1

            query += f" ORDER BY t.transaction_date DESC LIMIT ${param_idx}"
            params.append(limit)

            results = await db_provider.execute_query(query, *params)
            return format_success_response({
                "transactions": results,
                "count": len(results)
            })

        elif name == "get_monthly_totals":
            months = args.get("months", 12)
            person_id = args.get("person_id")

            query = f"""
                SELECT
                    DATE_TRUNC('month', t.transaction_date) as month,
                    SUM(t.amount) as total_amount,
                    COUNT(*) as transaction_count
                FROM {SCHEMA}.transactions t
                WHERE t.transaction_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '{months} months'
            """
            params = []
            param_idx = 1

            if person_id:
                query += f" AND t.person_id = ${param_idx}"
                params.append(person_id)

            query += """
                GROUP BY DATE_TRUNC('month', t.transaction_date)
                ORDER BY month DESC
            """

            results = await db_provider.execute_query(query, *params)
            return format_success_response({
                "monthly_totals": results,
                "months_included": months
            })

        elif name == "get_category_breakdown":
            year = args.get("year", datetime.now().year)
            month = args.get("month")

            query = f"""
                SELECT
                    sc.category_name,
                    SUM(t.amount) as total_amount,
                    COUNT(*) as transaction_count,
                    ROUND(100.0 * SUM(t.amount) / SUM(SUM(t.amount)) OVER (), 2) as percentage
                FROM {SCHEMA}.transactions t
                JOIN {SCHEMA}.spending_categories sc ON t.category_id = sc.id
                WHERE EXTRACT(YEAR FROM t.transaction_date) = $1
            """
            params = [year]

            if month:
                query += " AND EXTRACT(MONTH FROM t.transaction_date) = $2"
                params.append(month)

            query += """
                GROUP BY sc.category_name
                ORDER BY total_amount DESC
            """

            results = await db_provider.execute_query(query, *params)
            grand_total = sum(r["total_amount"] or 0 for r in results)

            return format_success_response({
                "breakdown": results,
                "grand_total": grand_total,
                "year": year,
                "month": month
            })

        elif name == "search_transactions":
            search_term = args.get("search_term", "")
            limit = min(args.get("limit", 20), 100)

            if not search_term:
                return format_error_response("search_term is required")

            query = f"""
                SELECT
                    t.id,
                    t.transaction_date,
                    t.description,
                    t.amount,
                    sc.category_name,
                    p.name as person_name
                FROM {SCHEMA}.transactions t
                JOIN {SCHEMA}.spending_categories sc ON t.category_id = sc.id
                JOIN {SCHEMA}.persons p ON t.person_id = p.id
                WHERE LOWER(t.description) LIKE LOWER($1)
                ORDER BY t.transaction_date DESC
                LIMIT $2
            """

            results = await db_provider.execute_query(query, f"%{search_term}%", limit)
            return format_success_response({
                "search_term": search_term,
                "results": results,
                "count": len(results)
            })

        elif name == "list_categories":
            query = f"""
                SELECT id, category_name
                FROM {SCHEMA}.spending_categories
                ORDER BY category_name
            """
            results = await db_provider.execute_query(query)
            return format_success_response({"categories": results})

        elif name == "list_persons":
            query = f"""
                SELECT id, name
                FROM {SCHEMA}.persons
                ORDER BY name
            """
            results = await db_provider.execute_query(query)
            return format_success_response({"persons": results})

        elif name == "list_accounts":
            query = f"""
                SELECT id, account_name
                FROM {SCHEMA}.account_type
                ORDER BY account_name
            """
            results = await db_provider.execute_query(query)
            return format_success_response({"accounts": results})

        elif name == "execute_select_query":
            query = args.get("query", "").strip()

            if not query:
                return format_error_response("Query is required")

            # Security: Only allow SELECT queries
            if not query.upper().startswith("SELECT"):
                return format_error_response(
                    "Only SELECT queries are allowed for safety. "
                    "This server is read-only."
                )

            # Block dangerous keywords
            dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
            query_upper = query.upper()
            for keyword in dangerous:
                if keyword in query_upper:
                    return format_error_response(
                        f"Query contains forbidden keyword: {keyword}. "
                        "Only read-only SELECT queries are allowed."
                    )

            results = await db_provider.execute_query(query)
            return format_success_response({
                "query": query,
                "results": results,
                "row_count": len(results)
            })

        else:
            return format_error_response(f"Unknown tool: {name}")

    except ConnectionError as e:
        return format_error_response(str(e))
    except Exception as e:
        logger.error(f"Error executing {name}: {e}")
        return format_error_response(f"Error: {e}")


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="finance-database",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logger.info("Starting Personal Finance Database MCP Server...")
    logger.info(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")

    if not DB_CONFIG["user"]:
        logger.warning("DB_USER not set in environment. Set it in your .env file.")

    try:
        logger.info("Server is running and ready to accept requests")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        logger.info("Shutting down server...")
        asyncio.run(db_provider.close())
        logger.info("Server shutdown complete")
