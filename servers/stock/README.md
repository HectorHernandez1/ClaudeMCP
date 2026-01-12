# Stock Data MCP Server

Real-time stock market data server using the Alpha Vantage API. Provides stock quotes, company fundamentals, historical prices, and symbol search capabilities.

## Features

- **Real-time Stock Quotes** - Current price, volume, change, and trading data
- **Company Overview** - Fundamentals including market cap, P/E ratio, sector, industry
- **Historical Data** - Daily stock prices with adjustable time ranges
- **Symbol Search** - Find stock symbols by company name or keywords
- **Portfolio View** - Get quotes for multiple stocks simultaneously

## Setup

### 1. Get API Key

Get a free Alpha Vantage API key:
- Visit: https://www.alphavantage.co/support/#api-key
- Enter your email
- Copy your API key

### 2. Configure Environment

Add your API key to `.env` in the project root:

```bash
ALPHA_VANTAGE_API_KEY=your_key_here
```

### 3. Configure Claude Desktop

Add to your Claude Desktop config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "stock-data": {
      "command": "python",
      "args": ["/absolute/path/to/ClaudeMCP/servers/stock/stock_data.py"],
      "env": {
        "ALPHA_VANTAGE_API_KEY": "your_key_here"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

## Available Tools

### `get_stock_quote`

Get real-time stock quote for a symbol.

**Parameters:**
- `symbol` (string, required) - Stock symbol (e.g., "AAPL", "MSFT", "GOOGL")

**Returns:**
```json
{
  "symbol": "AAPL",
  "price": 178.25,
  "change": 2.50,
  "change_percent": "1.42%",
  "volume": 54321000,
  "latest_trading_day": "2024-01-12",
  "previous_close": 175.75,
  "open": 176.00,
  "high": 179.50,
  "low": 175.00
}
```

### `get_company_overview`

Get company fundamentals and overview data.

**Parameters:**
- `symbol` (string, required) - Stock symbol

**Returns:**
```json
{
  "symbol": "AAPL",
  "name": "Apple Inc",
  "description": "Apple Inc. designs, manufactures...",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap": "2800000000000",
  "pe_ratio": "28.5",
  "dividend_yield": "0.52%",
  "52_week_high": "198.23",
  "52_week_low": "164.08",
  "beta": "1.24",
  "eps": "6.15"
}
```

### `get_daily_prices`

Get daily historical stock prices.

**Parameters:**
- `symbol` (string, required) - Stock symbol
- `outputsize` (string, optional) - "compact" (100 days) or "full" (20+ years), default: "compact"

**Returns:**
```json
{
  "symbol": "AAPL",
  "prices": [
    {
      "date": "2024-01-12",
      "open": 176.00,
      "high": 179.50,
      "low": 175.00,
      "close": 178.25,
      "adjusted_close": 178.25,
      "volume": 54321000
    }
  ],
  "metadata": {...}
}
```

### `search_stocks`

Search for stock symbols by company name or keywords.

**Parameters:**
- `keywords` (string, required) - Company name or search keywords

**Returns:**
```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc",
    "type": "Equity",
    "region": "United States",
    "market_open": "09:30",
    "market_close": "16:00",
    "timezone": "UTC-04",
    "currency": "USD",
    "match_score": "1.0000"
  }
]
```

### `get_portfolio_summary`

Get quotes for multiple stocks at once.

**Parameters:**
- `symbols` (array of strings, required) - List of stock symbols

**Returns:**
```json
{
  "portfolio": [
    {
      "symbol": "AAPL",
      "price": 178.25,
      "change": 2.50,
      ...
    },
    {
      "symbol": "MSFT",
      "price": 395.60,
      "change": -1.20,
      ...
    }
  ],
  "total_value": 573.85,
  "num_positions": 2
}
```

## Usage Examples

### In Claude Desktop

Once configured, you can ask Claude:

- "What's the current stock price of Apple?"
- "Get me company information for Tesla"
- "Show me the last 10 days of Microsoft stock prices"
- "Search for stocks related to renewable energy"
- "Give me a portfolio summary for AAPL, MSFT, and GOOGL"

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector@latest
```

**Configuration:**
- **Arguments:** `run --with mcp mcp run ./servers/stock/stock_data.py`
- **Transport Type:** STDIO

Then test tools directly in the inspector interface.

## API Rate Limits

**Free Tier:**
- 25 API requests per day
- 5 API requests per minute

**Premium Tiers:**
- 75 requests/minute ($49.99/month)
- 150 requests/minute ($149.99/month)
- 300 requests/minute ($249.99/month)
- 600 requests/minute ($499.99/month)
- 1200 requests/minute ($999.99/month)

See: https://www.alphavantage.co/premium/

## Error Handling

The server handles common errors:

- **Invalid symbol:** Returns error message
- **Rate limit exceeded:** Returns "API rate limit exceeded" message
- **API errors:** Returns descriptive error messages
- **Network issues:** Handles connection failures gracefully

## Dependencies

```
mcp>=1.0.0
aiohttp>=3.8.0
python-dotenv>=0.19.0
```

## Troubleshooting

**"API rate limit exceeded"**
- You've hit the 25 requests/day limit
- Wait until tomorrow or upgrade to premium
- Consider caching responses for repeated queries

**"No data found for symbol"**
- Check that the symbol is valid (use `search_stocks` first)
- Verify the symbol is a US stock (Alpha Vantage focuses on US markets)

**"demo key" being used**
- Your API key isn't being loaded
- Check `.env` file exists and contains `ALPHA_VANTAGE_API_KEY`
- Verify Claude Desktop config includes the env variable

## Contributing

Found a bug or want to add a feature? Please open an issue or submit a pull request!

## License

MIT License - See main repository LICENSE file

## Resources

- [Alpha Vantage Documentation](https://www.alphavantage.co/documentation/)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/anthropics/anthropic-mcp-python)
