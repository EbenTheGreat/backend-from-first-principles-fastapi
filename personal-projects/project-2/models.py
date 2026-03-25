import uuid
from pydantic import BaseModel, Field, field_validator, ConfigDict
from sqlmodel import SQLModel, Field as SQLField
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


# ─────────────────────────────────────────────
# DATABASE TABLE MODEL
# ─────────────────────────────────────────────

class Bookmark(SQLModel, table=True):
    """
    The actual database table. SQLModel maps this to the 'bookmark' table in SQLite.
    - id uses UUID (not integer) to prevent IDOR security attacks
    - created_at / updated_at auto-set via default_factory
    """
    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    city: str = SQLField(index=True, min_length=1, max_length=99)
    country_code: str = SQLField(index=True, min_length=2, max_length=2)
    notes: str | None = SQLField(default=None, max_length=999)
    units: Units = SQLField(default=Units.metric)
    temperature_threshold: float | None = SQLField(default=None)
    is_favourite: bool = SQLField(default=False)
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = SQLField(default_factory=lambda: datetime.now(UTC))


class WeatherHistory(SQLModel, table=True):
    """
    Stores historical weather snapshots linked to a specific bookmark.
    This allows you to query "What was the weather like at this location on Dec 15th?"
    """
    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    
    # Foreign Key: Links this record to a specific bookmark
    bookmark_id: uuid.UUID = SQLField(foreign_key="bookmark.id", index=True)
    
    # The Snapshot Data (Copied from WeatherResponse)
    city: str = SQLField(index=True)
    country_code: str = SQLField(index=True)
    temperature: float
    feels_like: float
    description: str
    humidity: int
    wind_speed: float
    units: Units
    
    # The Time of the Snapshot
    fetched_at: datetime = SQLField(index=True)



# ─────────────────────────────────────────────
# API INPUT / OUTPUT MODELS (Pydantic — no table=True)
# kept separate from DB model for security and flexibility
# ─────────────────────────────────────────────

class BookMarkBase(BaseModel):
    """Shared fields for API input/output models."""
    city: str = Field(..., min_length=1, max_length=99)
    notes: str | None = Field(None, max_length=999)
    units: Units = Units.metric
    temperature_threshold: float | None = Field(
        None,
        alias="temperatureThreshold",
        description="Alert threshold for temperature in degrees"
    )
    is_favourite: bool = Field(False, alias="isFavourite", description="Mark as favourite")

    @field_validator("temperature_threshold")
    @classmethod
    def validate_temperature_threshold(cls, v: float | None) -> float | None:
        if v is not None and (v < -100 or v > 100):
            raise ValueError("Temperature threshold must be between -100 and 100")
        return v

    model_config = ConfigDict(populate_by_name=True)


class BookMarkCreate(BookMarkBase):
    """What the client sends when creating a bookmark."""
    country_code: str = Field(..., alias="countryCode", min_length=2, max_length=2)

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        if not v.isalpha() or not v.isupper():
            raise ValueError("Country code must be 2 uppercase letters (e.g. GB, NG)")
        return v


class BookMarkResponse(BookMarkBase):
    """What the API returns — includes id and timestamps. Never exposes DB internals."""
    id: uuid.UUID
    country_code: str = Field(..., alias="countryCode", min_length=2, max_length=2)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    # from_attributes=True lets FastAPI construct this from a SQLModel ORM object (Bookmark)
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class BookMarkUpdate(BaseModel):
    """All fields optional — used for PATCH (partial updates)."""
    city: str | None = Field(None, min_length=1, max_length=99)
    notes: str | None = Field(None, max_length=999)
    country_code: str | None = Field(None, alias="countryCode", min_length=2, max_length=2)
    units: Units | None = None
    temperature_threshold: float | None = Field(None, alias="temperatureThreshold", description="Alert threshold for temperature in degrees")
    is_favourite: bool | None = Field(None, alias="isFavourite", description="Mark as favourite")

    model_config = ConfigDict(populate_by_name=True)


class BookMarkListResponse(BaseModel):
    data: list[BookMarkResponse]
    total: int
    page: int
    total_pages: int = Field(alias="totalPages")

    model_config = ConfigDict(populate_by_name=True)


class BookmarkAlertResponse(BaseModel):
    bookmark_id: str
    city: str
    threshold: float
    current_temperature: float
    message: str


class WeatherResponse(BaseModel):
    city: str
    country_code: str = Field(..., alias="countryCode")
    temperature: float
    feels_like: float = Field(..., alias="feelsLike")
    description: str
    humidity: int
    wind_speed: float = Field(..., alias="windSpeed")
    units: Units
    fetched_at: datetime = Field(..., alias="fetchedAt")
    cached: bool
    alert: str | None = None

    # populate_by_name=True → allows both snake_case (internal use in weather_services.py)
    # AND camelCase aliases (API responses) to work at the same time
    model_config = ConfigDict(populate_by_name=True)
