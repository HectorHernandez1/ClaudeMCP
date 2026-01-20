# Personal Finance Database MCP Server

Query your `money_stuff` PostgreSQL database for spending tracking and analysis.

## Status: Ready

This server connects to the PersonalFinanceHub database schema (`budget_app`) and provides read-only access to your financial data.

## Features

- **Localhost Only**: Connects only to localhost databases - cannot access remote servers for security
- **Graceful Connection Handling**: If the database is unavailable (e.g., you're away from home), the server returns helpful error messages instead of crashing. Claude Code continues working normally.
- **Read-Only**: Only SELECT queries allowed - your data is safe
- **Pre-built Financial Queries**: Spending summaries, category breakdowns, monthly totals
- **Custom Queries**: Execute your own SELECT queries for advanced analysis

## Available Tools

| Tool | Description |
|------|-------------|
| `get_spending_summary` | Spending by category for a date range |
| `get_recent_transactions` | Recent transactions with filters |
| `get_monthly_totals` | Total spending by month |
| `get_category_breakdown` | Detailed category analysis with percentages |
| `search_transactions` | Search by description text |
| `list_categories` | All spending categories |
| `list_persons` | All persons in database |
| `list_accounts` | All account types |
| `get_database_status` | Connection status and basic stats |
| `execute_select_query` | Custom SELECT queries (advanced) |

## Setup

### 1. Install Dependencies

```bash
pip install asyncpg
# Or install all project dependencies:
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Note: DB_HOST is hardcoded to localhost for security
DB_PORT=5432
DB_NAME=money_stuff
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
```

### 3. Add to Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "finance-database": {
      "command": "python",
      "args": ["/path/to/ClaudeMCP/servers/database/finance_db.py"],
      "env": {
        "DB_PORT": "5432",
        "DB_NAME": "money_stuff",
        "DB_USER": "your_username",
        "DB_PASSWORD": "your_password"
      }
    }
  }
}
```

## Database Schema

This server expects the `budget_app` schema from [PersonalFinanceHub](https://github.com/HectorHernandez1/PersonalFinanceHub):

- `budget_app.persons` - User identity records
- `budget_app.spending_categories` - Transaction categories
- `budget_app.account_type` - Card/account types
- `budget_app.transactions` - Primary transaction table

## What Happens When Database is Unavailable?

When you're away from home or the database server is down:

1. The MCP server **does not crash**
2. Tool calls return a helpful JSON error:
   ```json
   {
     "error": true,
     "message": "Cannot connect to PostgreSQL at localhost:5432...",
     "hint": "The database may be unavailable. This won't break Claude Code - other tools continue working normally."
   }
   ```
3. All other MCP servers (stock, weather, news) continue working
4. Claude can still help you with other tasks

## Example Usage

Ask Claude things like:

- "How much did I spend on groceries this month?"
- "Show me my top spending categories for 2024"
- "What were my largest transactions last week?"
- "Compare my monthly spending over the past 6 months"
- "Search for all Amazon transactions"

## Security

- **Localhost only**: Hard-coded to connect only to localhost - cannot access databases on other servers in the network
- **Read-only by default**: Only SELECT queries are allowed
- **SQL injection prevention**: Parameterized queries throughout
- **Dangerous keyword blocking**: INSERT, UPDATE, DELETE, DROP, etc. are blocked
- **Query timeout**: 30-second limit prevents runaway queries

## Files

- `finance_db.py` - Main MCP server implementation
- `README.md` - This documentation
