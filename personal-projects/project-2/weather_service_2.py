import httpx
import json
import time
import uuid
from datetime import datetime, UTC
from fastapi import HTTPException, status
from config import settings
from models import WeatherResponse, Units, WeatherHistory, Bookmark
import fakeredis
from sqlmodel import Session, select


# ─────────────────────────────────────────────
# CACHE SERVICE
# ─────────────────────────────────────────────

class WeatherCacheService:
    """
    Handles all fakeredis interactions:
      - weather result caching (Cache-Aside pattern)
      - per-IP rate limiting (atomic INCR pattern)
      - cache introspection and flushing
    """

    WEATHER_TTL = 600   # Cache weather data for 10 minutes
    RATE_LIMIT  = 10    # max requests per window
    RATE_WINDOW = 60    # window size in seconds (1 minute)

    def __init__(self):
        self.cache = fakeredis.FakeRedis(decode_responses=True)

    # ── helpers ──────────────────────────────

    def _cache_key(self, city: str, country_code: str, units: Units) -> str:
        return f"weather:{city.lower()}:{country_code.lower()}:{units.value}"

    # ── weather caching ───────────────────────

    def get_from_cache(self, city: str, country_code: str, units: Units) -> WeatherResponse | None:
        """Check fakeredis for a cached weather result."""
        key = self._cache_key(city, country_code, units)
        cached_data = self.cache.get(key)
        if cached_data:
            data = json.loads(cached_data)
            data["cached"] = True
            return WeatherResponse(**data)
        return None

    def save_to_cache(self, city: str, country_code: str, units: Units, data: WeatherResponse) -> None:
        """Store a WeatherResponse in fakeredis with a TTL."""
        key = self._cache_key(city, country_code, units)
        # setex = SET with EXpiry (TTL in seconds)
        self.cache.setex(key, self.WEATHER_TTL, data.model_dump_json())

    def get_cache_stats(self) -> dict:
        """Return statistics about what's currently in the weather cache."""
        # scan_iter asks for keys in small batches instead of locking up the database
        weather_keys = list(self.cache.scan_iter("weather:*"))
        return {
            "total_entries": len(weather_keys),
            "cached_locations": weather_keys
        }

    def flush_cache(self) -> None:
        """Clear all cache data."""
        self.cache.flushdb()

    # ── rate limiting ─────────────────────────

    def check_rate_limit(self, client_ip: str) -> None:
        """
        Enforce a per-IP rate limit using fakeredis atomic INCR.

        Pattern (identical to caching_complete.py Section 5):
        1. Build key:  rate:{ip}:{current_minute}
        2. INCR counter atomically — thread-safe, no race conditions
        3. On first hit in this window, set TTL so counter auto-expires
        4. If count > limit → raise 429 Too Many Requests with Retry-After header
        """
        current_minute = int(time.time() / self.RATE_WINDOW)
        rate_key = f"rate:{client_ip}:{current_minute}"

        count = self.cache.incr(rate_key)           # atomic: returns new value after increment

        if count == 1:
            self.cache.expire(rate_key, self.RATE_WINDOW)  # set TTL only on the very first hit

        if count > self.RATE_LIMIT:
            ttl = self.cache.ttl(rate_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({self.RATE_LIMIT} requests/min). Retry in {ttl}s.",
                headers={"Retry-After": str(ttl)}
            )


# ─────────────────────────────────────────────
# API SERVICE
# ─────────────────────────────────────────────

class WeatherAPIService:
    """
    Handles all communication with the OpenWeather HTTP API and
    orchestrates the Cache-Aside flow via WeatherCacheService.
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self, cache_service: WeatherCacheService):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.cache   = cache_service

    # ── raw fetch ─────────────────────────────

    async def get_weather(self, city: str, country_code: str, units: Units) -> WeatherResponse:
        """Fetch live weather from OpenWeather API."""
        params = {
            "q": f"{city},{country_code}",
            "units": units.value,
            "appid": self.api_key
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.BASE_URL, params=params, timeout=10.0)
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

    # ── cache-aside flow ──────────────────────

    async def get_weather_for_bookmark(
        self,
        city: str,
        country_code: str,
        units: Units,
        force_refresh: bool = False
    ) -> WeatherResponse:
        """
        Full Cache-Aside flow:
        1. Check cache
        2. Miss → call API
        3. Transform response (done inside get_weather)
        4. Store in cache with TTL
        5. Return data
        """
        # Step 1: Check cache
        if not force_refresh:
            cached = self.cache.get_from_cache(city, country_code, units)
            if cached:
                return cached

        # Step 2 & 3: Cache miss → call API + transform
        weather = await self.get_weather(city, country_code, units)

        # Step 4: Store with TTL
        self.cache.save_to_cache(city, country_code, units, weather)

        # Step 5: Return
        return weather


# ─────────────────────────────────────────────
# HISTORY SERVICE
# ─────────────────────────────────────────────

class WeatherHistoryService:
    """
    Handles all database interactions for weather history
    and bookmark temperature thresholds.
    """

    def save_history(self, session: Session, bookmark_id: uuid.UUID, weather: WeatherResponse) -> WeatherHistory:
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

    def get_history(self, session: Session, bookmark_id: uuid.UUID, cursor: datetime | None = None, limit: int = 20) -> list[WeatherHistory]:
        """
        Return a slice of weather history for this bookmark using cursor pagination.
        Fetches 'limit + 1' items to easily determine if there is a next page.
        """
        statement = (
            select(WeatherHistory)
            .where(WeatherHistory.bookmark_id == bookmark_id)
        )

        if cursor:
            # Only return records fetched strictly AFTER our marker
            statement = statement.where(WeatherHistory.fetched_at > cursor)

        # Order by time (oldest first) and limit results
        statement = statement.order_by(WeatherHistory.fetched_at.asc()).limit(limit + 1)
        
        results = session.exec(statement).all()
        return results

    def set_threshold(self, session: Session, bookmark_id: uuid.UUID, threshold: float) -> Bookmark:
        """Set the temperature alert threshold for a bookmark.
        
        Raises HTTP 404 if the bookmark doesn't exist, so the router
        always knows whether the update actually succeeded.
        """
        bookmark = session.get(Bookmark, bookmark_id)
        if not bookmark:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bookmark {bookmark_id} not found"
            )
        bookmark.temperature_threshold = threshold
        session.add(bookmark)
        session.commit()
        session.refresh(bookmark)
        return bookmark
