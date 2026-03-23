from pydantic import BaseModel, Field, field_validator, ConfigDict
from uuid import UUID, uuid4
from enum import Enum
from datetime import datetime, UTC

class Units(str, Enum):
    metric = "metric"
    imperial = "imperial"

class Sort(str, Enum):
    ascending = "ascending"
    descending = "descending"

class SortBy(str, Enum):
    created_at = "created_at"
    updated_at = "updated_at"
    city = "city"


class BookMarkBase(BaseModel):
    city: str = Field(..., min_length=1, max_length=99)
    notes: str | None = Field(None, max_length=999)
    units: Units = Units.metric
    temperature_threshold: float | None = Field(None, alias="temperatureThreshold", description="Alert treshold for temperature in degrees")
    is_favourite: bool = Field(False, alias="isFavourite", description="Mark as favourite")
    
    @field_validator("temperature_threshold")
    @classmethod
    def validate_temperature_threshold(cls, v: float | None) -> float | None:
        if v is not None and v < -100 or v > 100:
            raise ValueError("Temperature threshold must be between -100 and 100")
        return v
    model_config= ConfigDict(populate_by_name=True)


class BookMarkCreate(BookMarkBase):
    country_code: str = Field(..., alias="countryCode", min_length=2, max_length=2 )

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        if not v.isalpha() or not v.isupper():
            raise ValueError("Country code must be 2 uppercase letters (e.g. GB, NG)")
        return v


class BookMarkResponse(BookMarkBase):
    id: UUID
    country_code: str = Field(..., alias="countryCode", min_length=2, max_length=2 )
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

class BookMarkUpdate(BaseModel):
    city: str | None = Field(None, min_length=1, max_length=99)
    notes: str | None = Field(None, max_length=999)
    country_code: str | None = Field(None, alias="countryCode", min_length=2, max_length=2 )
    units: Units | None = None
    temperature_threshold: float | None = Field(None, description="Alert treshold for temperature in degrees")
    is_favourite: bool | None = Field(None, alias="isFavourite", description="Mark as favourite")

    model_config= ConfigDict(populate_by_name=True)

class BookMarkListResponse(BaseModel):
    data: list[BookMarkResponse]
    total: int
    page: int
    total_pages: int=Field(alias="totalPages")

    model_config = ConfigDict(populate_by_name=True)


class BookmarkAlertResponse(BaseModel):
    bookmark_id: str
    city: str
    threshold: float
    current_temperature: float
    message: str
    


class WeatherResponse(BaseModel):
    city: str	
    country_code: str
    temperature: float	
    feels_like: float	
    description: str
    humidity: int
    wind_speed: float	
    units: Units
    fetched_at: datetime
    cached: bool 
    alert: str | None = None
    







