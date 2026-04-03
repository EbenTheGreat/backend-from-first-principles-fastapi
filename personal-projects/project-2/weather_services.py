import httpx
import json
from datetime import datetime, UTC
from fastapi import HTTPException, status
from config import settings
from models import WeatherResponse, Units
import fakeredis
from sqlmodel import Session, select
from models import WeatherHistory
import uuid


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
            raise HTTPException(status_code=e.response.status_code, detail=f"Weather API error: {e.response.status_code} {e.response.reason_phrase}")
        except httpx.RequestException:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Weather API unavailable")

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


async def get_weather_for_bookmark(city: str, country_code: str, units: Units, force_refresh: bool = False) -> WeatherResponse:
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


# ─────────────────────────────────────────────
# RATE LIMITING  (caching_complete.py Section 5)
# ─────────────────────────────────────────────

RATE_LIMIT = 10          # max requests per window
RATE_WINDOW = 60         # window size in seconds (1 minute)

def check_rate_limit(client_ip: str) -> None:
    """
    Enforce a per-IP rate limit using fakeredis atomic INCR.

    Pattern (identical to caching_complete.py Section 5):
    1. Build key:  rate:{ip}:{current_minute}
    2. INCR counter atomically — thread-safe, no race conditions
    3. On first hit in this window, set TTL so counter auto-expires
    4. If count > limit → raise 429 Too Many Requests with Retry-After header
    """
    import time
    current_minute = int(time.time() / RATE_WINDOW)
    rate_key = f"rate:{client_ip}:{current_minute}"

    count = cache.incr(rate_key)           # atomic: returns new value after increment

    if count == 1:
        cache.expire(rate_key, RATE_WINDOW)  # set TTL only on the very first hit

    if count > RATE_LIMIT:
        ttl = cache.ttl(rate_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({RATE_LIMIT} requests/min). Retry in {ttl}s.",
            headers={"Retry-After": str(ttl)}
        )



def save_history(session: Session, bookmark_id: uuid.UUID, weather: WeatherResponse) -> None:
    """Append a WeatherResponse to the history list for this bookmark."""
    history_record = WeatherHistory(
        bookmark_id=bookmark_id,
        city=weather.city,
        country_code=weather.country_code,
        temperature=weather.temperature,
        feels_like=weather.feels_like,
        description=weather.description,
        humidity=weather.humidity,
        wind_speed=weather.wind_speed,
        units=weather.units,
        fetched_at=weather.fetched_at
    )
    session.add(history_record)
    session.commit()
    session.refresh(history_record)
    return history_record


def get_history(session: Session, bookmark_id: uuid.UUID) -> list[WeatherResponse]:
    """Return all past weather fetches for this bookmark, oldest first."""
    statement = select(WeatherHistory).where(WeatherHistory.bookmark_id == bookmark_id).order_by(WeatherHistory.fetched_at.asc())
    results = session.exec(statement)
    return results.all()


def set_treshold(session: Session, bookmark_id: uuid.UUID, treshold: float) -> Bookmark:
    """Set the treshold for temperature alert."""
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bookmark {bookmark_id} not found"
        )
    bookmark.temperature_threshold = treshold
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


