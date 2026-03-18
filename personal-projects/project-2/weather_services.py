import httpx
import json
from datetime import datetime, UTC
from fastapi import HTTPException, status
from config import settings
from models import WeatherResponse, Units
import fakeredis

cache = fakeredis.FakeRedis(decode_responses=True)

WEATHER_TTL = 600  # Cache weather data for 10 minutes


def _cache_key(city: str, country_code: str, units: Units) -> str:
    return f"weather:{city.lower()}:{country_code.lower()}:{units.value}"


def get_from_cache(city: str, country_code: str, units: Units) -> WeatherResponse | None:
    """Check fakeredis for a cached weather result."""
    key = _cache_key(city, country_code, units)
    cached_data = cache.get(key)
    if cached_data:
        data = json.loads(cached_data)
        data["cached"] = True
        return WeatherResponse(**data)
    return None


def save_to_cache(city: str, country_code: str, units: Units, data: WeatherResponse):
    """Store a WeatherResponse in fakeredis with a TTL."""
    key = _cache_key(city, country_code, units)
    # setex = SET with EXpiry (TTL in seconds)
    cache.setex(key, WEATHER_TTL, data.model_dump_json())


async def get_weather(city: str, country_code: str, units: Units) -> WeatherResponse:
    """Fetch live weather from OpenWeather API."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": f"{city},{country_code}",
        "units": units.value,
        "appid": settings.OPENWEATHER_API_KEY
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Weather API timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Weather API error: {e}")
        except httpx.RequestException as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Weather API unavailable: {e}")

        return WeatherResponse(
            city=data["name"],
            country_code=data["sys"]["country"],
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            description=data["weather"][0]["description"],
            humidity=data["main"]["humidity"],
            wind_speed=data["wind"]["speed"],
            units=units,
            fetched_at=datetime.now(UTC),
            cached=False
        )


async def get_weather_for_bookmark(city: str, country_code: str, units: Units) -> WeatherResponse:
    """
    Full Cache Aside flow:
    1. Check cache
    2. Miss → call API
    3. Transform response (done inside get_weather)
    4. Store in cache with TTL
    5. Return data
    """
    # Step 1: Check cache
    if not force_refresh:
        cached = get_from_cache(city, country_code, units)
        if cached:
            return cached  

    # Step 2 & 3: Cache miss → call API + transform
    weather = await get_weather(city, country_code, units)

    
    # Step 4: Store with TTL
    save_to_cache(city, country_code, units, weather)

    # Step 5: Return
    return weather


def get_cache_stats() -> dict:
    """Return statistics about what's currently in the weather cache."""
    keys = cache.keys("weather:*")  # all weather cache keys
    return {
        "total_entries": len(keys),
        "cached_locations": list(keys)
    }


def flush_cache() -> None:
    """Clear cache data"""
    cache.flushdb()
    return


def save_history(bookmark_id: str, weather: WeatherResponse) -> None:
    """Append a WeatherResponse to the history list for this bookmark."""
    cache.rpush(f"history:{bookmark_id}", weather.model_dump_json())


def get_history(bookmark_id: str) -> list[WeatherResponse]:
    """Return all past weather fetches for this bookmark, oldest first."""
    entries = cache.lrange(f"history:{bookmark_id}", 0, -1)
    return [WeatherResponse(**json.loads(entry)) for entry in entries]


def set_treshold(bookmark_id: str, treshold: int) -> None:
    """Set the treshold for temperature alert."""
    cache.set(f"treshold:{bookmark_id}", treshold)
    return


