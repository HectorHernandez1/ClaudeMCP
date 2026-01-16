# News MCP Server

Access news headlines and articles from thousands of sources worldwide using NewsAPI.

## Features

- Top headlines by country, category, or source
- Full-text article search with filters
- Browse available news sources
- Category-based news across multiple countries
- Support for multiple languages

## Setup

### 1. Get a NewsAPI Key

1. Sign up at [NewsAPI.org](https://newsapi.org/register)
2. Copy your API key from the dashboard

**Free Tier Limitations:**
- 100 requests per day
- Headlines up to 1 month old
- Search limited to headlines/descriptions (not full content)
- For development/personal use only

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
NEWS_API_KEY=your_api_key_here
```

Or set it in your Claude Desktop configuration (see below).

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Claude Desktop

Add the news server to your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "news-data": {
      "command": "python",
      "args": ["/path/to/ClaudeMCP/servers/news/news_data.py"],
      "env": {
        "NEWS_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Available Tools

### `get_top_headlines`

Get top news headlines by country, category, or search query.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `country` | string | No | 2-letter country code (default: "us") |
| `category` | string | No | News category (business, entertainment, general, health, science, sports, technology) |
| `query` | string | No | Keywords to search for in headlines |
| `page_size` | integer | No | Number of results (1-100, default: 10) |

**Returns:**
```json
{
  "total_results": 38,
  "country": "us",
  "category": "technology",
  "article_count": 10,
  "articles": [
    {
      "title": "Apple Announces New Product Line",
      "description": "Apple unveiled its latest innovations...",
      "author": "John Smith",
      "source": "TechCrunch",
      "url": "https://example.com/article",
      "image_url": "https://example.com/image.jpg",
      "published_at": "2024-01-15T10:30:00Z",
      "content": "Full article content..."
    }
  ]
}
```

### `search_news`

Search for news articles across all sources.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Keywords or phrases to search for |
| `search_in` | string | No | Where to search: "title", "description", "content" (default: "title,description") |
| `sort_by` | string | No | Sort order: "relevancy", "popularity", "publishedAt" (default: "publishedAt") |
| `language` | string | No | 2-letter language code (default: "en") |
| `from_date` | string | No | Oldest date (YYYY-MM-DD) |
| `to_date` | string | No | Newest date (YYYY-MM-DD) |
| `page_size` | integer | No | Number of results (1-100, default: 10) |

**Returns:**
```json
{
  "total_results": 1250,
  "query": "artificial intelligence",
  "sort_by": "publishedAt",
  "language": "en",
  "article_count": 10,
  "articles": [...]
}
```

### `get_sources`

Get available news sources with optional filters.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by category |
| `language` | string | No | Filter by language code |
| `country` | string | No | Filter by country code |

**Returns:**
```json
{
  "source_count": 25,
  "filters": {
    "category": "technology",
    "language": "en",
    "country": null
  },
  "sources": [
    {
      "id": "techcrunch",
      "name": "TechCrunch",
      "description": "Breaking technology news and analysis",
      "url": "https://techcrunch.com",
      "category": "technology",
      "language": "en",
      "country": "us"
    }
  ]
}
```

### `get_headlines_by_source`

Get top headlines from a specific news source.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | string | Yes | Source ID (e.g., "bbc-news", "cnn", "the-verge") |
| `page_size` | integer | No | Number of results (1-100, default: 10) |

**Returns:**
```json
{
  "total_results": 10,
  "source": "bbc-news",
  "article_count": 10,
  "articles": [...]
}
```

### `get_category_news`

Get news for a category across multiple countries.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | Yes | News category |
| `countries` | array | No | List of country codes (default: ["us"]) |
| `page_size` | integer | No | Results per country (1-20, default: 5) |

**Returns:**
```json
{
  "category": "sports",
  "countries_count": 3,
  "news_by_country": [
    {
      "country": "us",
      "article_count": 5,
      "articles": [...]
    },
    {
      "country": "gb",
      "article_count": 5,
      "articles": [...]
    }
  ]
}
```

## Supported Values

### Categories
- `business`
- `entertainment`
- `general`
- `health`
- `science`
- `sports`
- `technology`

### Countries (Common)
`us`, `gb`, `ca`, `au`, `de`, `fr`, `it`, `es`, `nl`, `no`, `se`, `jp`, `kr`, `cn`, `in`, `br`, `mx`, `ar`

### Languages
`en`, `es`, `fr`, `de`, `it`, `pt`, `nl`, `no`, `se`, `ar`, `zh`, `he`, `ru`

### Sort Options
- `relevancy` - Most relevant to the search query
- `popularity` - Most popular sources first
- `publishedAt` - Newest articles first (default)

## Usage Examples

**Ask Claude:**

- "What are today's top headlines?"
- "Show me the latest technology news"
- "Search for news about climate change"
- "What are the top sports headlines in the UK?"
- "Find news sources for business news"
- "Get headlines from BBC News"
- "Compare tech news from US, UK, and Germany"

## Rate Limits

**Free Tier (Developer):**
- 100 requests per day
- Articles up to 1 month old
- Development/personal use only

**Paid Plans:**
- Business: 250,000 requests/month
- Enterprise: Custom limits
- Access to full content and older articles

## Troubleshooting

### "Invalid API key" Error
- Verify your API key is correct
- Check for extra whitespace in the key
- Ensure the key is active in your NewsAPI dashboard

### "Rate limit exceeded" Error
- Free tier allows 100 requests/day
- Wait until the next day or upgrade your plan
- Consider caching frequent queries

### "Upgrade required" Error
- Some features require a paid plan
- The `everything` endpoint has limitations on free tier
- Older articles (>1 month) require paid access

### Empty results
- Try broadening your search query
- Check that the country/language combination has sources
- Use `get_sources` to verify available sources

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol
- `aiohttp>=3.8.0,<3.10.0` - Async HTTP client
- `python-dotenv>=0.19.0` - Environment variable loading
- `brotli>=1.0.0` - Compression support

## API Documentation

- [NewsAPI Documentation](https://newsapi.org/docs)
- [Top Headlines Endpoint](https://newsapi.org/docs/endpoints/top-headlines)
- [Everything Endpoint](https://newsapi.org/docs/endpoints/everything)
- [Sources Endpoint](https://newsapi.org/docs/endpoints/sources)

---

**Status:** ✅ Ready | **API:** NewsAPI | **Tier:** Free (100 requests/day)
