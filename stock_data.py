#!/usr/bin/env python3
"""
Stock Data MCP Server using Alpha Vantage API
Provides real-time stock quotes, company info, and market data
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
import aiohttp
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Alpha Vantage API configuration
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")  # Get free key from alphavantage.co

app = Server("stock-data-mcp")

class StockDataProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
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
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time stock quote"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper()
        }
        
        data = await self._make_request(params)
        
        if "Global Quote" not in data:
            raise ValueError(f"No data found for symbol: {symbol}")
        
        quote = data["Global Quote"]
        return {
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
    
    async def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """Get company overview and fundamental data"""
        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper()
        }
        
        data = await self._make_request(params)
        
        if not data or "Symbol" not in data:
            raise ValueError(f"No company data found for symbol: {symbol}")
        
        return {
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
    
    async def get_daily_prices(self, symbol: str, outputsize: str = "compact") -> Dict[str, Any]:
        """Get daily historical prices (compact = last 100 days, full = 20+ years)"""
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol.upper(),
            "outputsize": outputsize
        }
        
        data = await self._make_request(params)
        
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
        
        return {
            "symbol": symbol.upper(),
            "prices": prices,
            "metadata": data.get("Meta Data", {})
        }
    
    async def search_symbol(self, keywords: str) -> List[Dict[str, Any]]:
        """Search for stock symbols by company name or keywords"""
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords
        }
        
        data = await self._make_request(params)
        
        if "bestMatches" not in data:
            return []
        
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
        
        return results
    
    async def close(self):
        if self.session:
            await self.session.close()

# Initialize the stock data provider
stock_provider = StockDataProvider(API_KEY)

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available stock data tools"""
    return [
        types.Tool(
            name="get_stock_quote",
            description="Get real-time stock quote for a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT, GOOGL)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_company_overview",
            description="Get company overview and fundamental data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT, GOOGL)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_daily_prices",
            description="Get daily historical stock prices",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT, GOOGL)"
                    },
                    "outputsize": {
                        "type": "string",
                        "description": "Amount of data to return",
                        "enum": ["compact", "full"],
                        "default": "compact"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="search_stocks",
            description="Search for stock symbols by company name or keywords",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "Company name or keywords to search for"
                    }
                },
                "required": ["keywords"]
            }
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
                        "description": "List of stock symbols"
                    }
                },
                "required": ["symbols"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls for stock data operations"""
    
    try:
        if name == "get_stock_quote":
            symbol = arguments.get("symbol")
            if not symbol:
                raise ValueError("Symbol is required")
            
            quote = await stock_provider.get_quote(symbol)
            
            result = f"""📈 **{quote['symbol']} Stock Quote**

**Current Price:** ${quote['price']:.2f}
**Change:** ${quote['change']:.2f} ({quote['change_percent']})
**Volume:** {quote['volume']:,}

**Daily Range:**
- Open: ${quote['open']:.2f}
- High: ${quote['high']:.2f}
- Low: ${quote['low']:.2f}
- Previous Close: ${quote['previous_close']:.2f}

**Latest Trading Day:** {quote['latest_trading_day']}"""
            
            return [types.TextContent(type="text", text=result)]
        
        elif name == "get_company_overview":
            symbol = arguments.get("symbol")
            if not symbol:
                raise ValueError("Symbol is required")
            
            overview = await stock_provider.get_company_overview(symbol)
            
            result = f"""🏢 **{overview['name']} ({overview['symbol']})**

**Sector:** {overview['sector']}
**Industry:** {overview['industry']}

**Key Metrics:**
- Market Cap: {overview['market_cap']}
- P/E Ratio: {overview['pe_ratio']}
- EPS: {overview['eps']}
- Beta: {overview['beta']}
- Dividend Yield: {overview['dividend_yield']}

**52-Week Range:** ${overview['52_week_low']} - ${overview['52_week_high']}

**Description:**
{overview['description'][:300]}..."""
            
            return [types.TextContent(type="text", text=result)]
        
        elif name == "get_daily_prices":
            symbol = arguments.get("symbol")
            outputsize = arguments.get("outputsize", "compact")
            
            if not symbol:
                raise ValueError("Symbol is required")
            
            prices_data = await stock_provider.get_daily_prices(symbol, outputsize)
            
            result = f"📊 **{prices_data['symbol']} - Recent Daily Prices**\n\n"
            
            for price in prices_data['prices']:
                change = price['close'] - price['open']
                change_pct = (change / price['open']) * 100 if price['open'] != 0 else 0
                direction = "📈" if change >= 0 else "📉"
                
                result += f"**{price['date']}** {direction}\n"
                result += f"  Close: ${price['close']:.2f} | Change: {change:+.2f} ({change_pct:+.1f}%)\n"
                result += f"  Range: ${price['low']:.2f} - ${price['high']:.2f} | Volume: {price['volume']:,}\n\n"
            
            return [types.TextContent(type="text", text=result)]
        
        elif name == "search_stocks":
            keywords = arguments.get("keywords")
            if not keywords:
                raise ValueError("Keywords are required")
            
            results = await stock_provider.search_symbol(keywords)
            
            if not results:
                return [types.TextContent(type="text", text=f"No stocks found matching '{keywords}'")]
            
            result = f"🔍 **Search Results for '{keywords}'**\n\n"
            
            for stock in results:
                result += f"**{stock['symbol']}** - {stock['name']}\n"
                result += f"  Type: {stock['type']} | Region: {stock['region']}\n"
                result += f"  Currency: {stock['currency']} | Match Score: {stock['match_score']}\n\n"
            
            return [types.TextContent(type="text", text=result)]
        
        elif name == "get_portfolio_summary":
            symbols = arguments.get("symbols", [])
            if not symbols:
                raise ValueError("At least one symbol is required")
            
            result = "💼 **Portfolio Summary**\n\n"
            total_value = 0
            
            for symbol in symbols:
                try:
                    quote = await stock_provider.get_quote(symbol)
                    change_color = "🟢" if quote['change'] >= 0 else "🔴"
                    
                    result += f"{change_color} **{quote['symbol']}**: ${quote['price']:.2f} "
                    result += f"({quote['change']:+.2f} | {quote['change_percent']})\n"
                    
                    total_value += quote['price']
                    
                except Exception as e:
                    result += f"❌ **{symbol}**: Error - {str(e)}\n"
            
            result += f"\n**Portfolio Metrics:**\n"
            result += f"- Total Current Value: ${total_value:.2f}\n"
            result += f"- Number of Positions: {len(symbols)}\n"
            
            return [types.TextContent(type="text", text=result)]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]

async def main():
    # Read command-line arguments for transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="stock-data-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

# Cleanup on exit
async def cleanup():
    await stock_provider.close()

if __name__ == "__main__":
    import atexit
    atexit.register(lambda: asyncio.run(cleanup()))
    asyncio.run(main())