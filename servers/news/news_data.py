#!/usr/bin/env python3
"""
News Data MCP Server using NewsAPI
Provides access to news headlines, article search, and source information
"""

import os
import logging
from typing import Any, Dict, List, Union
import aiohttp
import asyncio
import json
from datetime import datetime, timedelta
from mcp import server, types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from dotenv import load_dotenv

# Import Brotli to ensure aiohttp can use it for decompression
try:
    import brotli
except ImportError:
    pass  # Brotli is optional but recommended

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NewsAPI configuration
NEWSAPI_BASE_URL = "https://newsapi.org/v2"
API_KEY = os.getenv("NEWS_API_KEY", "")

# Initialize MCP server
app = Server("news-data")


class NewsDataProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(auto_decompress=True)

    async def _make_request(self, endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
        await self._ensure_session()

        headers = {
            "X-Api-Key": self.api_key
        }

        url = f"{NEWSAPI_BASE_URL}/{endpoint}"

        async with self.session.get(url, params=params, headers=headers) as response:
            data = await response.json()

            if response.status == 200:
                if data.get("status") == "error":
                    raise ValueError(f"API Error: {data.get('message', 'Unknown error')}")
                return data
            elif response.status == 401:
                raise ValueError("Invalid API key. Please check your NEWS_API_KEY.")
            elif response.status == 426:
                raise ValueError("Free tier limitation: This endpoint requires a paid plan.")
            elif response.status == 429:
                raise ValueError("API rate limit exceeded. Please try again later.")
            else:
                error_msg = data.get("message", f"HTTP Error {response.status}")
                raise ValueError(error_msg)

    async def close(self):
        if self.session:
            await self.session.close()


# Initialize the news data provider
news_provider = NewsDataProvider(API_KEY)


# Valid categories for NewsAPI
VALID_CATEGORIES = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

# Valid countries (subset of most common)
VALID_COUNTRIES = ["us", "gb", "ca", "au", "de", "fr", "it", "es", "nl", "no", "se", "jp", "kr", "cn", "in", "br", "mx", "ar"]

# Valid sort options
VALID_SORT_OPTIONS = ["relevancy", "popularity", "publishedAt"]


def format_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """Format an article response."""
    return {
        "title": article.get("title", ""),
        "description": article.get("description", ""),
        "author": article.get("author", ""),
        "source": article.get("source", {}).get("name", ""),
        "url": article.get("url", ""),
        "image_url": article.get("urlToImage", ""),
        "published_at": article.get("publishedAt", ""),
        "content": article.get("content", "")
    }


@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get_top_headlines",
            description="Get top news headlines by country, category, or source",
            inputSchema={
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": f"2-letter country code (e.g., 'us', 'gb', 'de'). Options: {', '.join(VALID_COUNTRIES)}",
                        "default": "us"
                    },
                    "category": {
                        "type": "string",
                        "description": f"News category. Options: {', '.join(VALID_CATEGORIES)}",
                        "enum": VALID_CATEGORIES
                    },
                    "query": {
                        "type": "string",
                        "description": "Keywords to search for in headlines"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return (max 100)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": []
            },
        ),
        types.Tool(
            name="search_news",
            description="Search for news articles by keyword across all sources",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or phrases to search for"
                    },
                    "search_in": {
                        "type": "string",
                        "description": "Where to search: 'title', 'description', 'content', or comma-separated combination",
                        "default": "title,description"
                    },
                    "sort_by": {
                        "type": "string",
                        "description": f"Sort order. Options: {', '.join(VALID_SORT_OPTIONS)}",
                        "enum": VALID_SORT_OPTIONS,
                        "default": "publishedAt"
                    },
                    "language": {
                        "type": "string",
                        "description": "2-letter language code (e.g., 'en', 'es', 'fr')",
                        "default": "en"
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Oldest article date (ISO 8601 format: YYYY-MM-DD)"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "Newest article date (ISO 8601 format: YYYY-MM-DD)"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return (max 100)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["query"]
            },
        ),
        types.Tool(
            name="get_sources",
            description="Get available news sources, optionally filtered by category, language, or country",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": f"Filter by category. Options: {', '.join(VALID_CATEGORIES)}",
                        "enum": VALID_CATEGORIES
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by language (e.g., 'en', 'es', 'fr')"
                    },
                    "country": {
                        "type": "string",
                        "description": f"Filter by country code. Options: {', '.join(VALID_COUNTRIES)}"
                    }
                },
                "required": []
            },
        ),
        types.Tool(
            name="get_headlines_by_source",
            description="Get top headlines from a specific news source",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "News source ID (e.g., 'bbc-news', 'cnn', 'the-verge'). Use get_sources to find valid IDs."
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return (max 100)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["source"]
            },
        ),
        types.Tool(
            name="get_category_news",
            description="Get news for a specific category across multiple countries",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": f"News category. Options: {', '.join(VALID_CATEGORIES)}",
                        "enum": VALID_CATEGORIES
                    },
                    "countries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": f"List of country codes. Options: {', '.join(VALID_COUNTRIES)}",
                        "default": ["us"]
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results per country (max 20)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["category"]
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: Union[dict, None]
) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
    """
    Handle tool execution requests.
    """
    if name == "get_top_headlines":
        country = arguments.get("country", "us") if arguments else "us"
        category = arguments.get("category") if arguments else None
        query = arguments.get("query") if arguments else None
        page_size = arguments.get("page_size", 10) if arguments else 10

        params = {
            "country": country,
            "pageSize": str(min(page_size, 100))
        }

        if category:
            params["category"] = category
        if query:
            params["q"] = query

        data = await news_provider._make_request("top-headlines", params)

        articles = [format_article(a) for a in data.get("articles", [])]

        result = {
            "total_results": data.get("totalResults", 0),
            "country": country,
            "category": category,
            "query": query,
            "article_count": len(articles),
            "articles": articles
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "search_news":
        query = arguments.get("query") if arguments else None

        if not query:
            raise ValueError("Query is required")

        search_in = arguments.get("search_in", "title,description") if arguments else "title,description"
        sort_by = arguments.get("sort_by", "publishedAt") if arguments else "publishedAt"
        language = arguments.get("language", "en") if arguments else "en"
        from_date = arguments.get("from_date") if arguments else None
        to_date = arguments.get("to_date") if arguments else None
        page_size = arguments.get("page_size", 10) if arguments else 10

        params = {
            "q": query,
            "searchIn": search_in,
            "sortBy": sort_by,
            "language": language,
            "pageSize": str(min(page_size, 100))
        }

        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        data = await news_provider._make_request("everything", params)

        articles = [format_article(a) for a in data.get("articles", [])]

        result = {
            "total_results": data.get("totalResults", 0),
            "query": query,
            "sort_by": sort_by,
            "language": language,
            "article_count": len(articles),
            "articles": articles
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_sources":
        category = arguments.get("category") if arguments else None
        language = arguments.get("language") if arguments else None
        country = arguments.get("country") if arguments else None

        params = {}
        if category:
            params["category"] = category
        if language:
            params["language"] = language
        if country:
            params["country"] = country

        data = await news_provider._make_request("top-headlines/sources", params)

        sources = []
        for source in data.get("sources", []):
            sources.append({
                "id": source.get("id", ""),
                "name": source.get("name", ""),
                "description": source.get("description", ""),
                "url": source.get("url", ""),
                "category": source.get("category", ""),
                "language": source.get("language", ""),
                "country": source.get("country", "")
            })

        result = {
            "source_count": len(sources),
            "filters": {
                "category": category,
                "language": language,
                "country": country
            },
            "sources": sources
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_headlines_by_source":
        source = arguments.get("source") if arguments else None
        page_size = arguments.get("page_size", 10) if arguments else 10

        if not source:
            raise ValueError("Source is required")

        params = {
            "sources": source,
            "pageSize": str(min(page_size, 100))
        }

        data = await news_provider._make_request("top-headlines", params)

        articles = [format_article(a) for a in data.get("articles", [])]

        result = {
            "total_results": data.get("totalResults", 0),
            "source": source,
            "article_count": len(articles),
            "articles": articles
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_category_news":
        category = arguments.get("category") if arguments else None
        countries = arguments.get("countries", ["us"]) if arguments else ["us"]
        page_size = arguments.get("page_size", 5) if arguments else 5

        if not category:
            raise ValueError("Category is required")

        all_news = []

        for country in countries[:5]:  # Limit to 5 countries to avoid rate limits
            try:
                params = {
                    "country": country,
                    "category": category,
                    "pageSize": str(min(page_size, 20))
                }

                data = await news_provider._make_request("top-headlines", params)

                country_articles = []
                for article in data.get("articles", []):
                    formatted = format_article(article)
                    formatted["country"] = country
                    country_articles.append(formatted)

                all_news.append({
                    "country": country,
                    "article_count": len(country_articles),
                    "articles": country_articles
                })
            except Exception as e:
                all_news.append({
                    "country": country,
                    "error": str(e)
                })

        result = {
            "category": category,
            "countries_count": len(countries),
            "news_by_country": all_news
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
                server_name="news-data",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logger.info("Starting News Data MCP Server...")
    logger.info(f"API Key configured: {'Yes' if API_KEY else 'No - please set NEWS_API_KEY'}")
    try:
        logger.info("Server is running and ready to accept requests")
        asyncio.run(main())
    finally:
        logger.info("Shutting down server...")
        asyncio.run(news_provider.close())
        logger.info("Server shutdown complete")
