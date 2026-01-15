#!/usr/bin/env python3
"""
Weather Data MCP Server using OpenWeatherMap API
Provides real-time weather data, forecasts, and weather alerts
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

# Import Brotli to ensure aiohttp can use it for decompression
try:
    import brotli
except ImportError:
    pass  # Brotli is optional but recommended

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenWeatherMap API configuration
OPENWEATHER_BASE_URL = "https://api.openweathermap.org"
API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# Initialize MCP server
app = Server("weather-data")


class WeatherDataProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(auto_decompress=True)

    async def _make_request(self, endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
        await self._ensure_session()
        params["appid"] = self.api_key

        url = f"{OPENWEATHER_BASE_URL}{endpoint}"

        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data
            elif response.status == 401:
                raise ValueError("Invalid API key. Please check your OPENWEATHER_API_KEY.")
            elif response.status == 404:
                raise ValueError("Location not found. Please check the location name or coordinates.")
            elif response.status == 429:
                raise ValueError("API rate limit exceeded. Please try again later.")
            else:
                error_text = await response.text()
                raise ValueError(f"HTTP Error {response.status}: {error_text}")

    async def close(self):
        if self.session:
            await self.session.close()


# Initialize the weather data provider
weather_provider = WeatherDataProvider(API_KEY)


def format_temperature(kelvin: float, units: str = "metric") -> float:
    """Convert Kelvin to Celsius or Fahrenheit."""
    if units == "metric":
        return round(kelvin - 273.15, 1)
    elif units == "imperial":
        return round((kelvin - 273.15) * 9/5 + 32, 1)
    return round(kelvin, 1)


def format_wind_speed(mps: float, units: str = "metric") -> float:
    """Convert m/s to appropriate unit."""
    if units == "imperial":
        return round(mps * 2.237, 1)  # m/s to mph
    return round(mps, 1)  # m/s for metric


def get_wind_direction(degrees: float) -> str:
    """Convert wind degrees to cardinal direction."""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(degrees / 22.5) % 16
    return directions[idx]


@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get_current_weather",
            description="Get current weather conditions for a location by city name or coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name (e.g., 'London', 'New York,US', 'Paris,FR') or coordinates as 'lat,lon'",
                    },
                    "units": {
                        "type": "string",
                        "description": "Temperature units: 'metric' (Celsius) or 'imperial' (Fahrenheit)",
                        "enum": ["metric", "imperial"],
                        "default": "metric"
                    },
                },
                "required": ["location"],
            },
        ),
        types.Tool(
            name="get_forecast",
            description="Get 5-day weather forecast with 3-hour intervals for a location",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name (e.g., 'London', 'New York,US') or coordinates as 'lat,lon'",
                    },
                    "units": {
                        "type": "string",
                        "description": "Temperature units: 'metric' (Celsius) or 'imperial' (Fahrenheit)",
                        "enum": ["metric", "imperial"],
                        "default": "metric"
                    },
                },
                "required": ["location"],
            },
        ),
        types.Tool(
            name="get_air_quality",
            description="Get current air quality index and pollutant levels for a location",
            inputSchema={
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Latitude of the location",
                    },
                    "lon": {
                        "type": "number",
                        "description": "Longitude of the location",
                    },
                },
                "required": ["lat", "lon"],
            },
        ),
        types.Tool(
            name="search_locations",
            description="Search for locations by name to get coordinates and location details",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "City name or location to search for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 5
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_weather_alerts",
            description="Get weather alerts and warnings for a location (requires coordinates)",
            inputSchema={
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Latitude of the location",
                    },
                    "lon": {
                        "type": "number",
                        "description": "Longitude of the location",
                    },
                },
                "required": ["lat", "lon"],
            },
        ),
        types.Tool(
            name="get_multi_location_weather",
            description="Get current weather for multiple locations at once",
            inputSchema={
                "type": "object",
                "properties": {
                    "locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of city names or coordinates",
                    },
                    "units": {
                        "type": "string",
                        "description": "Temperature units: 'metric' (Celsius) or 'imperial' (Fahrenheit)",
                        "enum": ["metric", "imperial"],
                        "default": "metric"
                    },
                },
                "required": ["locations"],
            },
        ),
    ]


async def get_coordinates(location: str) -> tuple:
    """Parse location string to get coordinates or geocode city name."""
    # Check if location is already coordinates
    if ',' in location:
        parts = location.split(',')
        try:
            # Try parsing as lat,lon
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, None
        except ValueError:
            pass  # Not coordinates, treat as city,country

    # Geocode the location
    params = {
        "q": location,
        "limit": 1
    }
    data = await weather_provider._make_request("/geo/1.0/direct", params)

    if not data:
        raise ValueError(f"Location not found: {location}")

    return data[0]["lat"], data[0]["lon"], data[0].get("name", location)


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: Union[dict, None]
) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
    """
    Handle tool execution requests.
    """
    if name == "get_current_weather":
        location = arguments.get("location") if arguments else None
        units = arguments.get("units", "metric") if arguments else "metric"

        if not location:
            raise ValueError("Location is required")

        lat, lon, resolved_name = await get_coordinates(location)

        params = {
            "lat": str(lat),
            "lon": str(lon),
        }

        data = await weather_provider._make_request("/data/2.5/weather", params)

        result = {
            "location": {
                "name": data.get("name", resolved_name or location),
                "country": data.get("sys", {}).get("country", ""),
                "coordinates": {"lat": lat, "lon": lon}
            },
            "weather": {
                "condition": data.get("weather", [{}])[0].get("main", ""),
                "description": data.get("weather", [{}])[0].get("description", ""),
                "icon": data.get("weather", [{}])[0].get("icon", "")
            },
            "temperature": {
                "current": format_temperature(data.get("main", {}).get("temp", 0), units),
                "feels_like": format_temperature(data.get("main", {}).get("feels_like", 0), units),
                "min": format_temperature(data.get("main", {}).get("temp_min", 0), units),
                "max": format_temperature(data.get("main", {}).get("temp_max", 0), units),
                "unit": "°C" if units == "metric" else "°F"
            },
            "humidity": data.get("main", {}).get("humidity", 0),
            "pressure": data.get("main", {}).get("pressure", 0),
            "visibility": data.get("visibility", 0),
            "wind": {
                "speed": format_wind_speed(data.get("wind", {}).get("speed", 0), units),
                "direction": get_wind_direction(data.get("wind", {}).get("deg", 0)),
                "degrees": data.get("wind", {}).get("deg", 0),
                "unit": "mph" if units == "imperial" else "m/s"
            },
            "clouds": data.get("clouds", {}).get("all", 0),
            "sunrise": data.get("sys", {}).get("sunrise", 0),
            "sunset": data.get("sys", {}).get("sunset", 0),
            "timezone": data.get("timezone", 0)
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_forecast":
        location = arguments.get("location") if arguments else None
        units = arguments.get("units", "metric") if arguments else "metric"

        if not location:
            raise ValueError("Location is required")

        lat, lon, resolved_name = await get_coordinates(location)

        params = {
            "lat": str(lat),
            "lon": str(lon),
        }

        data = await weather_provider._make_request("/data/2.5/forecast", params)

        forecasts = []
        for item in data.get("list", []):
            forecasts.append({
                "datetime": item.get("dt_txt", ""),
                "timestamp": item.get("dt", 0),
                "weather": {
                    "condition": item.get("weather", [{}])[0].get("main", ""),
                    "description": item.get("weather", [{}])[0].get("description", ""),
                    "icon": item.get("weather", [{}])[0].get("icon", "")
                },
                "temperature": {
                    "current": format_temperature(item.get("main", {}).get("temp", 0), units),
                    "feels_like": format_temperature(item.get("main", {}).get("feels_like", 0), units),
                    "min": format_temperature(item.get("main", {}).get("temp_min", 0), units),
                    "max": format_temperature(item.get("main", {}).get("temp_max", 0), units),
                    "unit": "°C" if units == "metric" else "°F"
                },
                "humidity": item.get("main", {}).get("humidity", 0),
                "pressure": item.get("main", {}).get("pressure", 0),
                "wind": {
                    "speed": format_wind_speed(item.get("wind", {}).get("speed", 0), units),
                    "direction": get_wind_direction(item.get("wind", {}).get("deg", 0)),
                    "unit": "mph" if units == "imperial" else "m/s"
                },
                "clouds": item.get("clouds", {}).get("all", 0),
                "precipitation_probability": item.get("pop", 0) * 100
            })

        result = {
            "location": {
                "name": data.get("city", {}).get("name", resolved_name or location),
                "country": data.get("city", {}).get("country", ""),
                "coordinates": {"lat": lat, "lon": lon}
            },
            "forecast_count": len(forecasts),
            "forecasts": forecasts
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_air_quality":
        lat = arguments.get("lat") if arguments else None
        lon = arguments.get("lon") if arguments else None

        if lat is None or lon is None:
            raise ValueError("Both lat and lon are required")

        params = {
            "lat": str(lat),
            "lon": str(lon),
        }

        data = await weather_provider._make_request("/data/2.5/air_pollution", params)

        aqi_descriptions = {
            1: "Good",
            2: "Fair",
            3: "Moderate",
            4: "Poor",
            5: "Very Poor"
        }

        aqi_data = data.get("list", [{}])[0]
        aqi = aqi_data.get("main", {}).get("aqi", 0)

        result = {
            "coordinates": {"lat": lat, "lon": lon},
            "air_quality_index": aqi,
            "air_quality_description": aqi_descriptions.get(aqi, "Unknown"),
            "components": {
                "co": aqi_data.get("components", {}).get("co", 0),
                "no": aqi_data.get("components", {}).get("no", 0),
                "no2": aqi_data.get("components", {}).get("no2", 0),
                "o3": aqi_data.get("components", {}).get("o3", 0),
                "so2": aqi_data.get("components", {}).get("so2", 0),
                "pm2_5": aqi_data.get("components", {}).get("pm2_5", 0),
                "pm10": aqi_data.get("components", {}).get("pm10", 0),
                "nh3": aqi_data.get("components", {}).get("nh3", 0)
            },
            "component_units": "μg/m³",
            "timestamp": aqi_data.get("dt", 0)
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "search_locations":
        query = arguments.get("query") if arguments else None
        limit = arguments.get("limit", 5) if arguments else 5

        if not query:
            raise ValueError("Query is required")

        params = {
            "q": query,
            "limit": str(min(max(limit, 1), 5))
        }

        data = await weather_provider._make_request("/geo/1.0/direct", params)

        results = []
        for loc in data:
            results.append({
                "name": loc.get("name", ""),
                "local_names": loc.get("local_names", {}),
                "lat": loc.get("lat", 0),
                "lon": loc.get("lon", 0),
                "country": loc.get("country", ""),
                "state": loc.get("state", "")
            })

        return [types.TextContent(type="text", text=json.dumps(results, indent=2))]

    elif name == "get_weather_alerts":
        lat = arguments.get("lat") if arguments else None
        lon = arguments.get("lon") if arguments else None

        if lat is None or lon is None:
            raise ValueError("Both lat and lon are required")

        # Use One Call API 3.0 for alerts (requires subscription)
        # Fallback to basic weather check if alerts not available
        params = {
            "lat": str(lat),
            "lon": str(lon),
            "exclude": "minutely,hourly,daily"
        }

        try:
            data = await weather_provider._make_request("/data/3.0/onecall", params)

            alerts = []
            for alert in data.get("alerts", []):
                alerts.append({
                    "sender": alert.get("sender_name", ""),
                    "event": alert.get("event", ""),
                    "start": alert.get("start", 0),
                    "end": alert.get("end", 0),
                    "description": alert.get("description", ""),
                    "tags": alert.get("tags", [])
                })

            result = {
                "coordinates": {"lat": lat, "lon": lon},
                "alert_count": len(alerts),
                "alerts": alerts
            }
        except ValueError as e:
            # One Call 3.0 requires subscription, provide helpful message
            if "401" in str(e) or "requires" in str(e).lower():
                result = {
                    "coordinates": {"lat": lat, "lon": lon},
                    "alert_count": 0,
                    "alerts": [],
                    "note": "Weather alerts require OpenWeatherMap One Call API 3.0 subscription. Visit https://openweathermap.org/api/one-call-3 for more information."
                }
            else:
                raise

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_multi_location_weather":
        locations = arguments.get("locations") if arguments else None
        units = arguments.get("units", "metric") if arguments else "metric"

        if not locations:
            raise ValueError("At least one location is required")

        weather_data = []

        for location in locations:
            try:
                lat, lon, resolved_name = await get_coordinates(location)

                params = {
                    "lat": str(lat),
                    "lon": str(lon),
                }

                data = await weather_provider._make_request("/data/2.5/weather", params)

                weather_data.append({
                    "location": {
                        "name": data.get("name", resolved_name or location),
                        "country": data.get("sys", {}).get("country", ""),
                        "coordinates": {"lat": lat, "lon": lon}
                    },
                    "weather": {
                        "condition": data.get("weather", [{}])[0].get("main", ""),
                        "description": data.get("weather", [{}])[0].get("description", "")
                    },
                    "temperature": {
                        "current": format_temperature(data.get("main", {}).get("temp", 0), units),
                        "feels_like": format_temperature(data.get("main", {}).get("feels_like", 0), units),
                        "unit": "°C" if units == "metric" else "°F"
                    },
                    "humidity": data.get("main", {}).get("humidity", 0),
                    "wind": {
                        "speed": format_wind_speed(data.get("wind", {}).get("speed", 0), units),
                        "unit": "mph" if units == "imperial" else "m/s"
                    }
                })
            except Exception as e:
                weather_data.append({
                    "location": {"name": location},
                    "error": str(e)
                })

        result = {
            "locations_count": len(locations),
            "weather_data": weather_data
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
                server_name="weather-data",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logger.info("Starting Weather Data MCP Server...")
    logger.info(f"API Key configured: {'Yes' if API_KEY else 'No - please set OPENWEATHER_API_KEY'}")
    try:
        logger.info("Server is running and ready to accept requests")
        asyncio.run(main())
    finally:
        logger.info("Shutting down server...")
        asyncio.run(weather_provider.close())
        logger.info("Server shutdown complete")
