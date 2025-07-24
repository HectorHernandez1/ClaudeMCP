#!/usr/bin/env python3
"""
Stock Data MCP Server using Alpha Vantage API
Provides real-time stock quotes, company info, and market data
"""

import os
from typing import Any, Dict, List
import aiohttp
import asyncio
from mcp.server.fastmcp import FastMCP

# Alpha Vantage API configuration
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")

# Initialize FastMCP server
mcp = FastMCP("Stock Data MCP", port=8000, host="0.0.0.0")

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

@mcp.tool()
async def get_stock_quote(symbol: str) -> Dict[str, Any]:
    """
    Get real-time stock quote for a symbol
    
    Args:
        symbol (str): Stock symbol (e.g., AAPL, MSFT, GOOGL)
    
    Returns:
        Dict[str, Any]: Current stock quote data
    """
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol.upper()
    }
    
    data = await stock_provider._make_request(params)
    
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

@mcp.tool()
async def get_company_overview(symbol: str) -> Dict[str, Any]:
    """
    Get company overview and fundamental data
    
    Args:
        symbol (str): Stock symbol (e.g., AAPL, MSFT, GOOGL)
    
    Returns:
        Dict[str, Any]: Company overview data
    """
    params = {
        "function": "OVERVIEW",
        "symbol": symbol.upper()
    }
    
    data = await stock_provider._make_request(params)
    
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

@mcp.tool()
async def get_daily_prices(symbol: str, outputsize: str = "compact") -> Dict[str, Any]:
    """
    Get daily historical stock prices
    
    Args:
        symbol (str): Stock symbol (e.g., AAPL, MSFT, GOOGL)
        outputsize (str): Amount of data to return (compact or full)
    
    Returns:
        Dict[str, Any]: Historical price data
    """
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
    
    return {
        "symbol": symbol.upper(),
        "prices": prices,
        "metadata": data.get("Meta Data", {})
    }

@mcp.tool()
async def search_stocks(keywords: str) -> List[Dict[str, Any]]:
    """
    Search for stock symbols by company name or keywords
    
    Args:
        keywords (str): Company name or keywords to search for
    
    Returns:
        List[Dict[str, Any]]: List of matching stocks
    """
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": keywords
    }
    
    data = await stock_provider._make_request(params)
    
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

@mcp.tool()
async def get_portfolio_summary(symbols: List[str]) -> Dict[str, Any]:
    """
    Get quotes for multiple stocks (portfolio view)
    
    Args:
        symbols (List[str]): List of stock symbols
    
    Returns:
        Dict[str, Any]: Portfolio summary data
    """
    if not symbols:
        raise ValueError("At least one symbol is required")
    
    portfolio = []
    total_value = 0
    
    for symbol in symbols:
        try:
            quote_data = await get_stock_quote(symbol)
            portfolio.append(quote_data)
            total_value += quote_data['price']
        except Exception as e:
            portfolio.append({
                "symbol": symbol,
                "error": str(e)
            })
    
    return {
        "portfolio": portfolio,
        "total_value": total_value,
        "num_positions": len(symbols)
    }

if __name__ == "__main__":
    try:
        mcp.run(transport="stdio")
    finally:
        # Cleanup on exit
        asyncio.run(stock_provider.close())