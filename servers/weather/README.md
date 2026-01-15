# Weather MCP Server

Real-time weather data and forecasts powered by OpenWeatherMap API.

## Features

- Current weather conditions for any location worldwide
- 5-day weather forecasts with 3-hour intervals
- Air quality index and pollutant levels
- Weather alerts and warnings
- Location search/geocoding
- Multi-location weather comparison
- Support for metric (Celsius) and imperial (Fahrenheit) units

## Setup

### 1. Get an OpenWeatherMap API Key

1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Navigate to your API keys section
3. Copy your API key (free tier available)

**API Tiers:**
- **Free tier**: Current weather, 5-day forecast, geocoding, air pollution
- **One Call 3.0** (subscription required): Weather alerts, minute-by-minute forecasts

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
OPENWEATHER_API_KEY=your_api_key_here
```

Or set it in your Claude Desktop configuration (see below).

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Claude Desktop

Add the weather server to your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "weather-data": {
      "command": "python",
      "args": ["/path/to/ClaudeMCP/servers/weather/weather_data.py"],
      "env": {
        "OPENWEATHER_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Available Tools

### `get_current_weather`

Get current weather conditions for a location.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `location` | string | Yes | City name (e.g., "London", "New York,US") or coordinates as "lat,lon" |
| `units` | string | No | "metric" (Celsius) or "imperial" (Fahrenheit). Default: "metric" |

**Returns:**
```json
{
  "location": {
    "name": "London",
    "country": "GB",
    "coordinates": {"lat": 51.5074, "lon": -0.1278}
  },
  "weather": {
    "condition": "Clouds",
    "description": "overcast clouds",
    "icon": "04d"
  },
  "temperature": {
    "current": 12.5,
    "feels_like": 11.2,
    "min": 10.0,
    "max": 14.0,
    "unit": "°C"
  },
  "humidity": 76,
  "pressure": 1015,
  "visibility": 10000,
  "wind": {
    "speed": 5.2,
    "direction": "SW",
    "degrees": 225,
    "unit": "m/s"
  },
  "clouds": 90,
  "sunrise": 1699862400,
  "sunset": 1699896000
}
```

### `get_forecast`

Get 5-day weather forecast with 3-hour intervals.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `location` | string | Yes | City name or coordinates |
| `units` | string | No | "metric" or "imperial". Default: "metric" |

**Returns:**
```json
{
  "location": {
    "name": "Paris",
    "country": "FR",
    "coordinates": {"lat": 48.8566, "lon": 2.3522}
  },
  "forecast_count": 40,
  "forecasts": [
    {
      "datetime": "2024-01-15 12:00:00",
      "timestamp": 1705320000,
      "weather": {
        "condition": "Rain",
        "description": "light rain"
      },
      "temperature": {
        "current": 8.5,
        "feels_like": 6.2,
        "unit": "°C"
      },
      "humidity": 82,
      "wind": {
        "speed": 4.1,
        "direction": "W"
      },
      "precipitation_probability": 65
    }
  ]
}
```

### `get_air_quality`

Get air quality index and pollutant concentrations.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | number | Yes | Latitude of the location |
| `lon` | number | Yes | Longitude of the location |

**Returns:**
```json
{
  "coordinates": {"lat": 40.7128, "lon": -74.006},
  "air_quality_index": 2,
  "air_quality_description": "Fair",
  "components": {
    "co": 233.65,
    "no": 0.0,
    "no2": 15.68,
    "o3": 68.78,
    "so2": 1.81,
    "pm2_5": 8.5,
    "pm10": 12.3,
    "nh3": 0.52
  },
  "component_units": "μg/m³"
}
```

**AQI Scale:**
| Index | Description |
|-------|-------------|
| 1 | Good |
| 2 | Fair |
| 3 | Moderate |
| 4 | Poor |
| 5 | Very Poor |

### `search_locations`

Search for locations to get coordinates and details.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | City name or location to search |
| `limit` | integer | No | Max results (1-5). Default: 5 |

**Returns:**
```json
[
  {
    "name": "San Francisco",
    "lat": 37.7749,
    "lon": -122.4194,
    "country": "US",
    "state": "California"
  }
]
```

### `get_weather_alerts`

Get active weather alerts for a location.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | number | Yes | Latitude of the location |
| `lon` | number | Yes | Longitude of the location |

**Note:** Weather alerts require OpenWeatherMap One Call API 3.0 subscription.

**Returns:**
```json
{
  "coordinates": {"lat": 35.6762, "lon": 139.6503},
  "alert_count": 1,
  "alerts": [
    {
      "sender": "JMA",
      "event": "Heavy Rain Warning",
      "start": 1699862400,
      "end": 1699948800,
      "description": "Heavy rain expected in the region",
      "tags": ["Rain"]
    }
  ]
}
```

### `get_multi_location_weather`

Get current weather for multiple locations at once.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `locations` | array | Yes | List of city names or coordinates |
| `units` | string | No | "metric" or "imperial". Default: "metric" |

**Returns:**
```json
{
  "locations_count": 3,
  "weather_data": [
    {
      "location": {"name": "Tokyo", "country": "JP"},
      "weather": {"condition": "Clear", "description": "clear sky"},
      "temperature": {"current": 15.2, "feels_like": 14.1, "unit": "°C"},
      "humidity": 45,
      "wind": {"speed": 3.2, "unit": "m/s"}
    },
    {
      "location": {"name": "London", "country": "GB"},
      "weather": {"condition": "Clouds", "description": "broken clouds"},
      "temperature": {"current": 8.5, "feels_like": 6.8, "unit": "°C"},
      "humidity": 78,
      "wind": {"speed": 5.1, "unit": "m/s"}
    }
  ]
}
```

## Usage Examples

**Ask Claude:**

- "What's the weather like in Tokyo right now?"
- "Give me a 5-day forecast for San Francisco"
- "What's the air quality in Beijing?"
- "Compare the weather in London, Paris, and Berlin"
- "Are there any weather alerts for Miami?"
- "Find the coordinates for Sydney, Australia"
- "What's the weather in New York in Fahrenheit?"

## Rate Limits

**Free Tier:**
- 60 calls/minute
- 1,000,000 calls/month
- Current weather, 5-day forecast, geocoding, air pollution

**One Call 3.0 (Subscription):**
- 1,000 calls/day included
- Additional calls billed per 1,000
- Weather alerts, minute forecasts, historical data

## Troubleshooting

### "Invalid API key" Error
- Verify your API key is correct in `.env` or Claude Desktop config
- New API keys may take a few hours to activate
- Ensure no extra whitespace in the key

### "Location not found" Error
- Try using the full city name with country code (e.g., "Paris,FR")
- Use `search_locations` to find the correct location name
- Try using coordinates instead (lat,lon)

### Weather alerts returning empty
- Weather alerts require One Call API 3.0 subscription
- Free tier does not include alerts
- Visit https://openweathermap.org/api/one-call-3 for subscription

### Rate limit exceeded
- Wait a few minutes before trying again
- Consider upgrading your API plan for higher limits
- Cache frequently requested locations

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol
- `aiohttp>=3.8.0,<3.10.0` - Async HTTP client
- `python-dotenv>=0.19.0` - Environment variable loading
- `brotli>=1.0.0` - Compression support

## API Documentation

- [OpenWeatherMap API Docs](https://openweathermap.org/api)
- [Current Weather API](https://openweathermap.org/current)
- [5-Day Forecast API](https://openweathermap.org/forecast5)
- [Air Pollution API](https://openweathermap.org/api/air-pollution)
- [Geocoding API](https://openweathermap.org/api/geocoding-api)
- [One Call API 3.0](https://openweathermap.org/api/one-call-3)

---

**Status:** ✅ Ready | **API:** OpenWeatherMap | **Tier:** Free (with optional subscription features)
