# Claude MCP Server Collection

A curated collection of Model Context Protocol (MCP) servers for Claude AI, providing real-time access to stocks, weather, news, databases, and more.

## 🌟 What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io) (MCP) is an open standard that enables AI assistants like Claude to securely connect to external data sources and tools. This repository provides ready-to-use MCP servers that extend Claude's capabilities.

## 📦 Available Servers

### 🔴 Live Servers

| Server | Description | Status | API Required |
|--------|-------------|--------|--------------|
| [**Stock Data**](servers/stock/) | Real-time stock quotes, company info, historical prices | ✅ Ready | Alpha Vantage (Free) |
| [**Weather Data**](servers/weather/) | Current weather, forecasts, air quality, alerts | ✅ Ready | OpenWeatherMap (Free) |
| [**News Data**](servers/news/) | Headlines, article search, news sources | ✅ Ready | NewsAPI (Free) |

### 🟡 Coming Soon

| Server | Description | API Required |
|--------|-------------|--------------|
| **Database** | Query PostgreSQL, MySQL, MongoDB | Database credentials |

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Claude Desktop App or compatible MCP client
- API keys for the services you want to use

### Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/HectorHernandez1/ClaudeMCP.git
   cd ClaudeMCP
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Configure Claude Desktop:**

   Add servers to your Claude Desktop config file:

   **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

   **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

   Example configuration:
   ```json
   {
     "mcpServers": {
       "stock-data": {
         "command": "python",
         "args": ["/absolute/path/to/ClaudeMCP/servers/stock/stock_data.py"],
         "env": {
           "ALPHA_VANTAGE_API_KEY": "your_api_key_here"
         }
       }
     }
   }
   ```

5. **Restart Claude Desktop**

## 📚 Server Documentation

### Stock Data Server

**Location:** `servers/stock/`

**Features:**
- Real-time stock quotes with price, volume, change
- Company fundamentals (P/E ratio, market cap, sector)
- Daily historical prices
- Symbol search by company name
- Portfolio view for multiple stocks

**Setup:**
1. Get free API key: [alphavantage.co](https://www.alphavantage.co/support/#api-key)
2. Add to `.env`: `ALPHA_VANTAGE_API_KEY=your_key`
3. Configure in Claude Desktop (see above)

**Available Tools:**
- `get_stock_quote` - Real-time quote for a symbol
- `get_company_overview` - Company fundamentals
- `get_daily_prices` - Historical daily prices
- `search_stocks` - Find symbols by company name
- `get_portfolio_summary` - Multi-symbol quotes

**Rate Limits:** 25 requests/day (free tier)

[📖 Full Documentation](servers/stock/README.md)

---

### Weather Data Server

**Location:** `servers/weather/`

**Features:**
- Current weather conditions for any location
- 5-day forecasts with 3-hour intervals
- Air quality index and pollutant levels
- Weather alerts and warnings (requires subscription)
- Location search/geocoding
- Multi-location weather comparison
- Metric and imperial unit support

**Setup:**
1. Get free API key: [openweathermap.org](https://openweathermap.org/api)
2. Add to `.env`: `OPENWEATHER_API_KEY=your_key`
3. Configure in Claude Desktop (see above)

**Available Tools:**
- `get_current_weather` - Current conditions for a location
- `get_forecast` - 5-day forecast with 3-hour intervals
- `get_air_quality` - Air quality index and pollutants
- `search_locations` - Find location coordinates
- `get_weather_alerts` - Active weather alerts
- `get_multi_location_weather` - Weather for multiple locations

**Rate Limits:** 60 calls/minute, 1M calls/month (free tier)

[📖 Full Documentation](servers/weather/README.md)

---

### News Data Server

**Location:** `servers/news/`

**Features:**
- Top headlines by country and category
- Full-text article search
- Browse news sources
- Category news across multiple countries
- Filter by language, date, source

**Setup:**
1. Get free API key: [newsapi.org](https://newsapi.org/register)
2. Add to `.env`: `NEWS_API_KEY=your_key`
3. Configure in Claude Desktop (see above)

**Available Tools:**
- `get_top_headlines` - Latest headlines by country/category
- `search_news` - Search articles by keyword
- `get_sources` - Browse available news sources
- `get_headlines_by_source` - Headlines from specific source
- `get_category_news` - Category news across countries

**Rate Limits:** 100 requests/day (free tier)

[📖 Full Documentation](servers/news/README.md)

---

### Database Server _(Coming Soon)_

**Location:** `servers/database/`

**Planned Features:**
- Query PostgreSQL, MySQL, MongoDB
- Execute safe read queries
- Schema inspection
- Connection pooling

## 🧪 Testing

Test any server using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector@latest
```

**Configuration:**
- **Arguments:** `run --with mcp mcp run ./servers/stock/stock_data.py`
- **Transport Type:** STDIO

## 🔒 Security Best Practices

1. **Never commit API keys:** All `.env` files are gitignored
2. **Use environment variables:** Store secrets in `.env` files
3. **Rotate keys regularly:** Generate new API keys periodically
4. **Review permissions:** Each server only accesses what it needs
5. **Monitor usage:** Check API usage to detect unauthorized access

## 🛠️ Development

### Adding a New Server

1. Create directory: `servers/your-server/`
2. Copy template from `servers/stock/stock_data.py`
3. Update README with server details
4. Add dependencies to `requirements.txt`
5. Update main README with server info
6. Submit pull request

### Project Structure

```
ClaudeMCP/
├── servers/           # MCP server implementations
│   ├── stock/        # Stock market data
│   ├── weather/      # Weather data
│   ├── news/         # News aggregation
│   └── database/     # Database tools
├── .env.example      # Environment variable template
├── .gitignore        # Security: prevents committing secrets
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## 📖 Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/anthropics/anthropic-mcp-python)
- [Claude Desktop](https://claude.ai/download)
- [MCP Inspector Tool](https://github.com/modelcontextprotocol/inspector)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built with [Model Context Protocol](https://modelcontextprotocol.io)
- Stock data powered by [Alpha Vantage](https://www.alphavantage.co)
- Weather data powered by [OpenWeatherMap](https://openweathermap.org)
- News data powered by [NewsAPI](https://newsapi.org)

## ⭐ Star History

If you find this useful, please star the repository!

---

**Need help?** [Open an issue](https://github.com/HectorHernandez1/ClaudeMCP/issues)
