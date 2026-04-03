"""
PRACTICE EXERCISE: The Three-Box Architecture

INSTRUCTIONS:
1. Do NOT look at weather_service_2.py!
2. Write the 3 class definitions for our services from memory.
   (Hint: The Memory Box, The Internet Box, The Hard Drive Box)
3. Inside the classes, write the empty function signatures (def function_name(...):) that belong in each.
4. Inside each function, write what it does using # comments. 
   Bonus: Write out the Database Lifecycle Mantra or the Cache-Aside flow in the comments where applicable!

When you're done, compare this file with weather_service_2.py to see how you did.
"""

import httpx
import json
import time
import uuid
from datetime import datetime, UTC
from fastapi import HTTPException, status
import fakeredis
from sqlmodel import Session, select

# Helpful types you might need:
from models import WeatherResponse, Units, WeatherHistory, Bookmark
from config import settings

# ─────────────────────────────────────────────
# BOX 1: The Memory Box (Talking to Redis)
# ─────────────────────────────────────────────

# TODO: Write your Cache class here.
# What functions does it need to read/write cache and handle rate limiting?
class WeatherCacheService:
   """
   to handle 
   """
   CACHE_TTL = 600
   RATE_LIMIT_WINDOW_SECONDS= 60
   RATE_LIMIT_MAX_REQUESTS=10

   #first get the fakeredis module
   _redis_client = fakeredis.FakeRedis()

   #initialize the class
   def __init__(self):
      self.cache = self._redis_client

   def _cache_key(self, city: str, country_code: str, units: Units) -> str:
      """
      use this as a helper function to get the cache
      """
      return f"weather:{city}:{country_code}:{units}"

   
   def save_to_cache(self, city: str, country_code: str, units: Units, data:WeatherResponse)-> None:
      """
      save weather history to cache
      """
      key = self._cache_key(city, country_code, units)
      self.cache.setex(key, self.CACHE_TTL,data.model_dump_json())

   
   def get_from_cache(self, city: str, country_code: str, units: Units) -> WeatherResponse:
      """
      get weather response from cache
      """
      key = self._cache_key(city, country_code, units)
      cached_data= self.cache.get(key)

      if cached_data:
         #load the data with json
         data = json.loads(cached_data)
         data["cached"] = True
         return WeatherResponse(**data)
      return None

   def get_cache_stats(self) -> dict:
      """
      return the statistics in what is in the weather cache
      """
      keys = self.cache.scan_iter("weather:*")
      weather_keys = [k.decode("utf-8") for k in keys]
      return {
         "total_entries": len(weather_keys),
         "cached_locations": weather_keys
      }

   def flush_cache(self) -> None:
      """
      clear everything in the cache
      """
      self.cache.flushdb()

   def check_rate_limit(self, client_ip: str) -> None:
      """
      implement per IP rate limit
      """
      current_minute = int(time.time() / self.RATE_LIMIT_WINDOW_SECONDS)
      rate_key = f"rate_limit:{client_ip}:{current_minute}"

      count = self.cache.incr(rate_key)

      if count == 1:
         self.cache.expire(rate_key, self.RATE_LIMIT_WINDOW_SECONDS)

      if count > self.RATE_LIMIT_MAX_REQUESTS:
         ttl = self.cache.ttl(rate_key)
         ttl = ttl if ttl > 0 else self.RATE_LIMIT_WINDOW_SECONDS
         raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests, retry in {ttl}s"
         )

# ─────────────────────────────────────────────
# BOX 2: The Internet Box (Talking to OpenWeather)
# ─────────────────────────────────────────────

# TODO: Write your API class here. 
# It needs to fetch live data and orchestrate the Cache-Aside pattern.

class WeatherService:
   """
   Interacts with open weather URL and it utilizes the cache service
   """
   BaseUrl= "https://api.openweathermap.org/data/2.5/weather"

   def __init__(self, cache_service: WeatherCacheService):
      self.cache = cache_service
      self.api_key = settings.OPENWEATHER_API_KEY

   
   def get_weather(self, city: str, country_code: str, units: Units) -> WeatherResponse:
      """
      Get live weather data from OpenWeather Api
      """
      params = {
         "q":f"{self.city}: {self.country_code}",
         "units": self.units,
         "appid": self.api_key
      }

      async with httpx.AsyncClient() as client:
         try:
            response = await client.get(self.BaseUrl, params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

         except httpx.TimeoutException:
            raise HTTPException(
               status_code=status.HTTP_504_GATEWAY_TIMEOUT,
               detail="Weather API timeout"
            )

         except httpx.TimeoutException:
            raise HTTPException(
               status_code=response.status_code,
               detail=f"Weather API error: {e.response.status_code} {e.response.reason_phrase}"
            )
         
         except httpx.TimeoutException:
            raise HTTPException(
               status_code=status.HTTP_504_GATEWAY_TIMEOUT,
               detail="Weather API timeout"
            )

         return WeatherResponse(
        city=data["name"],
        country=data["sys"]["country"],
        temperature=data["main"]["temp"],
        feels_like=data["main"]["feels_like"],
        description=data["weather"][0]["description"],
        humidity=data["main"]["humidity"],
        wind_speed=data["wind"]["speed"],
        units=units,
        fetched_at=datetime.now(UTC),
        cached=False
      )




# ─────────────────────────────────────────────
# BOX 3: The Hard Drive Box (Talking to the Database)
# ─────────────────────────────────────────────

# TODO: Write your History/Database class here.
# It needs to save new records and read history using the Database Mantra.

