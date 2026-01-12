#!/usr/bin/env python3
"""
Stock Data MCP Server using Alpha Vantage API
Provides real-time stock quotes, company info, and market data
"""

import os
import logging
from typing import Any, Dict, List, Union
import aiohttp
import asyncio
import json
from mcp import server, types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Alpha Vantage API configuration
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")

# Initialize MCP server
app = Server("stock-data")

class StockDataProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
    
    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        await self._ensure_session()
        params["apikey"] = self.api_key
        
        async with self.session.get(ALPHA_VANTAGE_BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if "Error Message" in data:
                    raise ValueError(f"API Error: {data['Error Message']}")
                if "Note" in data:
                    raise ValueError("API rate limit exceeded. Please try again later.")
                return data
            else:
                raise ValueError(f"HTTP Error: {response.status}")
    
    async def close(self):
        if self.session:
            await self.session.close()

# Initialize the stock data provider
stock_provider = StockDataProvider(API_KEY)


@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get_stock_quote",
            description="Get real-time stock quote for a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT, GOOGL)",
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get_company_overview",
            description="Get company overview and fundamental data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT, GOOGL)",
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get_daily_prices",
            description="Get daily historical stock prices",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT, GOOGL)",
                    },
                    "outputsize": {
                        "type": "string",
                        "description": "Amount of data to return (compact or full)",
                        "enum": ["compact", "full"],
                        "default": "compact"
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="search_stocks",
            description="Search for stock symbols by company name or keywords",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "Company name or keywords to search for",
                    },
                },
                "required": ["keywords"],
            },
        ),
        types.Tool(
            name="get_portfolio_summary",
            description="Get quotes for multiple stocks (portfolio view)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of stock symbols",
                    },
                },
                "required": ["symbols"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: Union[dict, None]
) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if name == "get_stock_quote":
        symbol = arguments.get("symbol") if arguments else None
        if not symbol:
            raise ValueError("Symbol is required")
        
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper()
        }
        
        data = await stock_provider._make_request(params)
        
        if "Global Quote" not in data:
            raise ValueError(f"No data found for symbol: {symbol}. Response: {data}")
        
        quote = data["Global Quote"]
        result = {
            "symbol": quote.get("01. symbol", ""),
            "price": float(quote.get("05. price", 0)),
            "change": float(quote.get("09. change", 0)),
            "change_percent": quote.get("10. change percent", ""),
            "volume": int(quote.get("06. volume", 0)),
            "latest_trading_day": quote.get("07. latest trading day", ""),
            "previous_close": float(quote.get("08. previous close", 0)),
            "open": float(quote.get("02. open", 0)),
            "high": float(quote.get("03. high", 0)),
            "low": float(quote.get("04. low", 0))
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_company_overview":
        symbol = arguments.get("symbol") if arguments else None
        if not symbol:
            raise ValueError("Symbol is required")
        
        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper()
        }
        
        data = await stock_provider._make_request(params)
        
        if not data or "Symbol" not in data:
            raise ValueError(f"No company data found for symbol: {symbol}")
        
        result = {
            "symbol": data.get("Symbol", ""),
            "name": data.get("Name", ""),
            "description": data.get("Description", ""),
            "sector": data.get("Sector", ""),
            "industry": data.get("Industry", ""),
            "market_cap": data.get("MarketCapitalization", ""),
            "pe_ratio": data.get("PERatio", ""),
            "dividend_yield": data.get("DividendYield", ""),
            "52_week_high": data.get("52WeekHigh", ""),
            "52_week_low": data.get("52WeekLow", ""),
            "beta": data.get("Beta", ""),
            "eps": data.get("EPS", "")
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_daily_prices":
        symbol = arguments.get("symbol") if arguments else None
        outputsize = arguments.get("outputsize", "compact") if arguments else "compact"
        
        if not symbol:
            raise ValueError("Symbol is required")
        
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol.upper(),
            "outputsize": outputsize
        }
        
        data = await stock_provider._make_request(params)
        
        if "Time Series (Daily)" not in data:
            raise ValueError(f"No daily data found for symbol: {symbol}")
        
        time_series = data["Time Series (Daily)"]
        
        # Convert to more readable format
        prices = []
        for date, values in list(time_series.items())[:10]:  # Last 10 days
            prices.append({
                "date": date,
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "adjusted_close": float(values["5. adjusted close"]),
                "volume": int(values["6. volume"])
            })
        
        result = {
            "symbol": symbol.upper(),
            "prices": prices,
            "metadata": data.get("Meta Data", {})
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "search_stocks":
        keywords = arguments.get("keywords") if arguments else None
        if not keywords:
            raise ValueError("Keywords are required")
        
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords
        }
        
        data = await stock_provider._make_request(params)
        
        if "bestMatches" not in data:
            return [types.TextContent(type="text", text="[]")]
        
        results = []
        for match in data["bestMatches"][:10]:  # Top 10 results
            results.append({
                "symbol": match.get("1. symbol", ""),
                "name": match.get("2. name", ""),
                "type": match.get("3. type", ""),
                "region": match.get("4. region", ""),
                "market_open": match.get("5. marketOpen", ""),
                "market_close": match.get("6. marketClose", ""),
                "timezone": match.get("7. timezone", ""),
                "currency": match.get("8. currency", ""),
                "match_score": match.get("9. matchScore", "")
            })
        
        return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
    
    elif name == "get_portfolio_summary":
        symbols = arguments.get("symbols") if arguments else None
        if not symbols:
            raise ValueError("At least one symbol is required")
        
        portfolio = []
        total_value = 0
        
        for symbol in symbols:
            try:
                # Get quote data for each symbol
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol.upper()
                }
                
                data = await stock_provider._make_request(params)
                
                if "Global Quote" in data:
                    quote = data["Global Quote"]
                    quote_data = {
                        "symbol": quote.get("01. symbol", ""),
                        "price": float(quote.get("05. price", 0)),
                        "change": float(quote.get("09. change", 0)),
                        "change_percent": quote.get("10. change percent", ""),
                        "volume": int(quote.get("06. volume", 0)),
                        "latest_trading_day": quote.get("07. latest trading day", ""),
                        "previous_close": float(quote.get("08. previous close", 0)),
                        "open": float(quote.get("02. open", 0)),
                        "high": float(quote.get("03. high", 0)),
                        "low": float(quote.get("04. low", 0))
                    }
                    portfolio.append(quote_data)
                    total_value += quote_data['price']
                else:
                    portfolio.append({
                        "symbol": symbol,
                        "error": f"No data found for symbol: {symbol}"
                    })
            except Exception as e:
                portfolio.append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        result = {
            "portfolio": portfolio,
            "total_value": total_value,
            "num_positions": len(symbols)
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="stock-data",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logger.info("Starting Stock Data MCP Server...")
    logger.info(f"API Key configured: {'Yes' if API_KEY != 'demo' else 'Using demo key'}")
    try:
        logger.info("Server is running and ready to accept requests")
        asyncio.run(main())
    finally:
        logger.info("Shutting down server...")
        # Cleanup on exit
        asyncio.run(stock_provider.close())
        logger.info("Server shutdown complete")