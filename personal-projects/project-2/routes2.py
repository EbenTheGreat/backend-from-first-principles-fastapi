from fastapi import APIRouter, HTTPException, Query, status, Request, Response
from models import (
    Sort, SortBy, Units,
    Bookmark, BookMarkCreate, BookMarkResponse,
    BookMarkUpdate, BookmarkAlertResponse,
    BookMarkListResponse, WeatherResponse, WeatherHistory,
    WeatherCompareItem
)
from db import SessionDep
from sqlmodel import select, func, or_
import uuid
import math
from datetime import datetime, UTC
import asyncio
from typing import Any
import hashlib
import json

# ─────────────────────────────────────────────
# KEY CHANGE 1: Import the CLASSES, not bare functions
# Old: from weather_services import get_from_cache, get_weather_for_bookmark, ...
# New: Import the three service classes
# ─────────────────────────────────────────────
from weather_service_2 import WeatherCacheService, WeatherAPIService, WeatherHistoryService

# ─────────────────────────────────────────────
# KEY CHANGE 2: Instantiate the services at module level (singletons)
# These are created ONCE when the server starts, and reused across all requests.
# Note: api_service RECEIVES cache_service — this is "Dependency Injection"
# ─────────────────────────────────────────────
cache_service   = WeatherCacheService()
api_service     = WeatherAPIService(cache_service=cache_service)
history_service = WeatherHistoryService()


v1 = APIRouter(prefix="/v1", tags=["bookmarks"])


@v1.post("/bookmarks", response_model=BookMarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(bookmark: BookMarkCreate, session: SessionDep):
    """Create a new bookmark entry. Returns 201 Created."""
    # KEY CHANGE 3: Call the method ON the api_service instance, not a bare function
    # Old: await get_weather_for_bookmark(city=..., country_code=..., units=...)
    # New: await api_service.get_weather_for_bookmark(city=..., country_code=..., units=...)
    await api_service.get_weather_for_bookmark(
        city=bookmark.city,
        country_code=bookmark.country_code,
        units=bookmark.units
    )

    existing = session.exec(
        select(Bookmark).where(
            func.lower(Bookmark.city) == bookmark.city.lower(),
            func.lower(Bookmark.country_code) == bookmark.country_code.lower()
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bookmark for {bookmark.city}, {bookmark.country_code} already exists."
        )

    db_bookmark = Bookmark.model_validate(bookmark)
    session.add(db_bookmark)
    session.commit()
    session.refresh(db_bookmark)
    return db_bookmark


@v1.get("/bookmarks", response_model=BookMarkListResponse, status_code=status.HTTP_200_OK)
async def get_all_bookmarks(
    session: SessionDep,
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    country_code: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: SortBy = Query(SortBy.created_at),
    sort_order: Sort = Query(Sort.ascending),
    favourite: bool | None = Query(None)
) -> BookMarkListResponse:
    """Get all bookmarks with filtering, sorting, and pagination. Returns 200 OK."""
    # No service changes here — this route only talks to the database directly
    statement = select(Bookmark)

    if country_code:
        statement = statement.where(Bookmark.country_code == country_code)
    if favourite is not None:
        statement = statement.where(Bookmark.is_favourite == favourite)
    if search:
        search_lower = search.strip().lower()
        statement = statement.where(
            or_(
                Bookmark.city.icontains(search_lower),
                Bookmark.notes.icontains(search_lower)
            )
        )

    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    sort_column = getattr(Bookmark, sort_by.value)
    if sort_order == Sort.descending:
        statement = statement.order_by(sort_column.desc())
    else:
        statement = statement.order_by(sort_column.asc())

    start = (page - 1) * limit
    statement = statement.offset(start).limit(limit)
    paginated = session.exec(statement).all()

    total_pages = math.ceil(total / limit) if total > 0 else 1

    return BookMarkListResponse(
        data=paginated,
        total=total,
        page=page,
        totalPages=total_pages
    )


@v1.get("/bookmarks/{bookmark_id}", response_model=BookMarkResponse, status_code=status.HTTP_200_OK)
async def get_bookmark(bookmark_id: uuid.UUID, session: SessionDep, request: Request):
    """Get a single bookmark by UUID. Returns 200 OK, 304 if not modified, 404 if missing."""
    # No service changes here — this route only talks to the database directly
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bookmark {bookmark_id} not found")

    data = BookMarkResponse.model_validate(bookmark, from_attributes=True).model_dump(mode="json")
    content_str = json.dumps(data, sort_keys=True)
    etag = hashlib.sha256(content_str.encode("utf-8")).hexdigest()

    if_none_match = request.headers.get("If-None-Match")
    if if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})

    return Response(
        content=json.dumps(data),
        media_type="application/json",
        headers={"ETag": etag, "Cache-Control": "public, max-age=3600"}
    )


@v1.patch("/bookmarks/{bookmark_id}", response_model=BookMarkResponse, status_code=status.HTTP_200_OK)
async def update_bookmark(bookmark_id: uuid.UUID, bookmark_update: BookMarkUpdate, session: SessionDep):
    """Partially update bookmark fields (PATCH). Returns 200 OK, 404 if missing."""
    # No service changes here — this route only talks to the database directly
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bookmark {bookmark_id} not found")

    update_data = bookmark_update.model_dump(exclude_unset=True, by_alias=False)
    bookmark.sqlmodel_update(update_data)
    bookmark.updated_at = datetime.now(UTC)
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


@v1.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(bookmark_id: uuid.UUID, session: SessionDep):
    """Delete a bookmark permanently. Returns 204 No Content."""
    # No service changes here — this route only talks to the database directly
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bookmark {bookmark_id} not found")
    session.delete(bookmark)
    session.commit()
    return


@v1.get("/bookmarks/{bookmark_id}/weather", response_model=WeatherResponse, status_code=status.HTTP_200_OK)
async def get_bookmark_weather(
    bookmark_id: uuid.UUID,
    session: SessionDep,
    request: Request,
    force_refresh: bool = Query(False)
):
    """Get weather for a saved bookmark. Returns 200 OK, 404, 429, 502/503/504."""
    # Old: check_rate_limit(request.client.host)
    # New: call the method on the cache_service instance
    cache_service.check_rate_limit(request.client.host)

    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    # Old: weather = await get_weather_for_bookmark(city=..., ...)
    # New: call the method on the api_service instance
    weather = await api_service.get_weather_for_bookmark(
        city=bookmark.city,
        country_code=bookmark.country_code,
        units=bookmark.units,
        force_refresh=force_refresh
    )

    # Old: save_history(session, bookmark_id, weather)
    # New: call the method on the history_service instance
    history_service.save_history(session, bookmark_id, weather)
    return weather


@v1.get("/weather", status_code=status.HTTP_200_OK, response_model=WeatherResponse)
async def quick_weather_lookup(
    request: Request,
    city: str = Query(..., min_length=1),
    country_code: str = Query(..., min_length=2, max_length=2),
    units: Units = Query(Units.metric),
    force_refresh: bool = Query(False)
):
    """Quick weather lookup without needing a saved bookmark. Returns 200 OK, 429, 502/503/504."""
    # Old: check_rate_limit(request.client.host)
    # New: call the method on the cache_service instance
    cache_service.check_rate_limit(request.client.host)

    # Old: return await get_weather_for_bookmark(city, country_code, units, force_refresh)
    # New: call the method on the api_service instance
    return await api_service.get_weather_for_bookmark(city, country_code, units, force_refresh)


@v1.get("/bookmarks/{bookmark_id}/weather/history", response_model=list[WeatherHistory], status_code=status.HTTP_200_OK)
async def get_weather_history(bookmark_id: uuid.UUID, session: SessionDep):
    """Return all past weather fetches for a bookmark, oldest first. Returns 200 OK, 404."""
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    # Old: return get_history(session, bookmark_id)
    # New: call the method on the history_service instance
    return history_service.get_history(session, bookmark_id)


@v1.get("/bookmarks/alerts/temperature", response_model=list[BookmarkAlertResponse], status_code=status.HTTP_200_OK)
async def get_temperature_alerts(session: SessionDep):
    """Check all bookmarks with a set threshold. Returns those where temperature exceeds it."""
    statement = select(Bookmark).where(Bookmark.temperature_threshold.is_not(None))
    bookmarks = session.exec(statement).all()

    fetch_tasks = [
        asyncio.create_task(
            # Old: get_weather_for_bookmark(city=b.city, ...)
            # New: call the method on the api_service instance
            api_service.get_weather_for_bookmark(
                city=b.city,
                country_code=b.country_code,
                units=b.units
            )
        )
        for b in bookmarks
    ]

    weather_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    alerts = []
    for bookmark, result in zip(bookmarks, weather_results):
        if isinstance(result, Exception):
            continue
        if result.temperature >= bookmark.temperature_threshold:
            alerts.append(BookmarkAlertResponse(
                bookmark_id=str(bookmark.id),
                city=bookmark.city,
                threshold=bookmark.temperature_threshold,
                current_temperature=result.temperature,
                message=f"Alert! current temperature ({result.temperature}°) is above your threshold of {bookmark.temperature_threshold}°"
            ))

    return alerts


@v1.post("/bookmarks/weather/bulk", status_code=status.HTTP_200_OK)
async def fetch_weather_for_all_bookmarks(
    session: SessionDep,
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=5, le=100)
) -> dict[str, Any]:
    """Fetch weather for multiple bookmarks concurrently using asyncio.gather."""
    total = session.exec(select(func.count()).select_from(Bookmark)).one()

    start = (page - 1) * limit
    paginated = session.exec(select(Bookmark).offset(start).limit(limit)).all()

    fetch_tasks = [
        asyncio.create_task(
            # Old: get_weather_for_bookmark(city=b.city, ..., force_refresh=True)
            # New: call the method on the api_service instance
            api_service.get_weather_for_bookmark(
                city=b.city,
                country_code=b.country_code,
                units=b.units,
                force_refresh=True
            )
        )
        for b in paginated
    ]

    weather_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    results_list = []
    for b, w in zip(paginated, weather_results):
        if isinstance(w, Exception):
            results_list.append({"bookmark_id": str(b.id), "city": b.city, "weather": None, "error": str(w)})
        else:
            results_list.append({"bookmark_id": str(b.id), "city": b.city, "weather": w})

    total_pages = math.ceil(total / limit) if total > 0 else 1
    return {"data": results_list, "total": total, "page": page, "totalPages": total_pages}


@v1.get("/weather/compare", response_model=list[WeatherCompareItem], status_code=status.HTTP_200_OK)
async def compare_weather(
    session: SessionDep,
    ids: str = Query(description="comma-separated bookmark UUIDs to compare")
):
    """Fetch and compare weather for multiple bookmarks side by side."""
    try:
        parsed_ids = [uuid.UUID(i.strip()) for i in ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="One or more IDs are not valid UUIDs")

    if not parsed_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No IDs provided")

    bookmarks = session.exec(select(Bookmark).where(Bookmark.id.in_(parsed_ids))).all()
    found = {b.id: b for b in bookmarks}

    tasks = [
        asyncio.create_task(
            # Old: get_weather_for_bookmark(city=b.city, ...)
            # New: call the method on the api_service instance
            api_service.get_weather_for_bookmark(
                city=b.city,
                country_code=b.country_code,
                units=b.units
            )
        )
        for b in bookmarks
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    comparison = []
    for b, result in zip(bookmarks, results):
        if isinstance(result, Exception):
            comparison.append(WeatherCompareItem(bookmark_id=str(b.id), city=b.city, country_code=b.country_code, weather=None, error=str(result)))
        else:
            comparison.append(WeatherCompareItem(bookmark_id=str(b.id), city=b.city, country_code=b.country_code, weather=result))

    for pid in parsed_ids:
        if pid not in found:
            comparison.append(WeatherCompareItem(bookmark_id=str(pid), city="unknown", country_code="??", weather=None, error="Bookmark not found"))

    return comparison


# ─────────────────────────────────────────────
# CACHE ROUTES
# ─────────────────────────────────────────────

@v1.get("/cache/stats", status_code=status.HTTP_200_OK)
async def cache_stats():
    """Return how many items are in the weather cache and which locations are cached."""
    # Old: return get_cache_stats()
    # New: call the method on the cache_service instance
    return cache_service.get_cache_stats()


@v1.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache():
    """Clear all weather cache data."""
    # Old: flush_cache()
    # New: call the method on the cache_service instance
    cache_service.flush_cache()
    return
