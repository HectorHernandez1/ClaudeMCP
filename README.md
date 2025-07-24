# Stock Data MCP Server

A Model Context Protocol (MCP) server that provides real-time stock market data using the Alpha Vantage API. This server enables AI assistants to fetch stock quotes, company information, historical prices, and search for stock symbols.

## Features

- **Real-time Stock Quotes**: Get current stock prices, changes, and trading volume
- **Company Overview**: Access fundamental data including market cap, P/E ratio, sector info
- **Historical Data**: Retrieve daily stock prices with adjustable time ranges
- **Symbol Search**: Find stock symbols by company name or keywords
- **Portfolio View**: Get quotes for multiple stocks simultaneously

## Setup

### Prerequisites

- Python 3.7+
- Alpha Vantage API key (get free key at [alphavantage.co](https://www.alphavantage.co/support/#api-key))

### Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   ```bash
   cp example.config.json config.json
   # Edit config.json with your actual file path and API key
   ```

4. Create a `.env` file with your API key:
   ```
   ALPHA_VANTAGE_API_KEY=your_api_key_here
   ```

## Usage

### Running the MCP Server

```bash
python stock_data.py
```

### Available Tools

The server provides these tools for AI assistants:

- `get_stock_quote` - Get real-time stock quote for a symbol
- `get_company_overview` - Get company overview and fundamental data  
- `get_daily_prices` - Get daily historical stock prices
- `search_stocks` - Search for stock symbols by company name
- `get_portfolio_summary` - Get quotes for multiple stocks


### use for testing 
npx @modelcontextprotocol/inspector@latest


### Configuration

Update your MCP client configuration to include this server:

```json
{
  "mcpServers": {
    "stock-data": {
      "command": "python",
      "args": ["/path/to/stock_data.py"],
      "env": {
        "ALPHA_VANTAGE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## API Rate Limits

- Alpha Vantage free tier: 25 requests per day
- Consider upgrading for higher limits if needed

## License

This project is open source and available under the MIT License.