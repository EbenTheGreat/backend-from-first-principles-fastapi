from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from enum import Enum
from datetime import datetime, UTC

class Units(str, Enum):
    metric = "°C"
    imperal = "°F"


class BookMarkBase(BaseModel):
    id: UUID
    city: str = Field(..., min_length=1, max_length=99)
    country_code: str = Field(..., alias="countryCode" )
    notes: str | None = Field(None)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class WeatherBase(BaseModel):
    city: str	
    country_code: str
    temperature: float	
    feels_like: float	
    description: str
    humidity: int
    wind_speed: float	
    units: str
    fetched_at: datetime
    cached: bool 







