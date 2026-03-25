from fastapi import APIRouter, HTTPException, Query, status
from models import (
    Sort, SortBy, Units,
    Bookmark, BookMarkCreate, BookMarkResponse,
    BookMarkUpdate, BookmarkAlertResponse,
    BookMarkListResponse, WeatherResponse, WeatherHistory
)
from db import SessionDep
from sqlmodel import select, func, or_
import uuid
import math
from datetime import datetime, UTC
from weather_services import (
    get_from_cache, flush_cache, save_to_cache,
    get_weather, get_weather_for_bookmark,
    get_cache_stats, save_history, get_history
)
import asyncio
from typing import Any


v1 = APIRouter(prefix="/v1", tags=["bookmarks"])


@v1.post("/bookmarks", response_model=BookMarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(bookmark: BookMarkCreate, session: SessionDep):
    """
    Create a new bookmark entry.
    Returns 201 Created.
    """
    # Pre-verify that the city actually exists in OpenWeatherMap
    await get_weather_for_bookmark(
        city=bookmark.city,
        country_code=bookmark.country_code,
        units=bookmark.units
    )
    
    # Check if a bookmark for the same city and country already exists
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

    # Convert BookMarkCreate → Bookmark DB model
    # model_validate reads the snake_case attributes from the Pydantic object
    db_bookmark = Bookmark.model_validate(bookmark)
    session.add(db_bookmark)
    session.commit()
    session.refresh(db_bookmark)   # reload from DB so id/created_at are populated
    return db_bookmark


@v1.get("/bookmarks", response_model=BookMarkListResponse, status_code=status.HTTP_200_OK)
async def get_all_bookmarks(
    session: SessionDep,
    page: int = Query(1, ge=1, description="page number"),
    limit: int = Query(5, ge=1, le=100, description="items per page, Max=100"),
    country_code: str | None = Query(None, description="filter by country"),
    search: str | None = Query(None, description="search in city and notes"),
    sort_by: SortBy = Query(SortBy.created_at, description="field to use in sorting"),
    sort_order: Sort = Query(Sort.ascending, description="sort by asc or desc order"),
    favourite: bool | None = Query(None, description="filter by is_favourite")
) -> BookMarkListResponse:
    """
    Get all bookmarks with filtering, sorting, and pagination.
    Returns 200 OK.
    """
    # Build query — SQL handles equality filters efficiently
    statement = select(Bookmark)

    if country_code:
        statement = statement.where(Bookmark.country_code == country_code)
    if favourite is not None:
        statement = statement.where(Bookmark.is_favourite == favourite)

    # 2. SQL-Side Search using OR and LIKE (%search%)
    if search:
        search_lower = search.strip().lower()
        # This translates to: WHERE city LIKE '%search%' OR notes LIKE '%search%'
        statement = statement.where(
  or_(
                Bookmark.city.icontains(search_lower),
                Bookmark.notes.icontains(search_lower)
            )
        )

    # 3. Quick DB Lookup for the Total count (BEFORE pagination!)
    # We ask the DB "how many rows match these filters?" without downloading any rows
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    # 4. SQL-Side Sorting
    # We get the correct SQL column (e.g. Bookmark.created_at)
    sort_column = getattr(Bookmark, sort_by.value)
    if sort_order == Sort.descending:
        statement = statement.order_by(sort_column.desc())
    else:
        statement = statement.order_by(sort_column.asc())

    # 5. SQL-Side Pagination (Offset and Limit)
    start = (page - 1) * limit
    statement = statement.offset(start).limit(limit)

    # 6. Finally, execute the query! The DB only sends over exactly the 5 items we need.
    paginated = session.exec(statement).all()

    # Calculate total pages using the total count we grabbed in Step 3
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return BookMarkListResponse(
        data=paginated,
        total=total,
        page=page,
        totalPages=total_pages
    )


@v1.get("/bookmarks/{bookmark_id}", response_model=BookMarkResponse, status_code=status.HTTP_200_OK)
async def get_bookmark(bookmark_id: uuid.UUID, session: SessionDep):
    """
    Get a single bookmark by UUID.
    Returns 200 OK if found, 404 Not Found if missing.
    """
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bookmark {bookmark_id} not found"
        )
    return bookmark


@v1.patch("/bookmarks/{bookmark_id}", response_model=BookMarkResponse, status_code=status.HTTP_200_OK)
async def update_bookmark(bookmark_id: uuid.UUID, bookmark_update: BookMarkUpdate, session: SessionDep):
    """
    Partially update bookmark fields (PATCH).
    Only sends fields the client explicitly provided.
    """
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bookmark {bookmark_id} not found"
        )

    # exclude_unset=True → only include fields the client actually sent
    # by_alias=False → use snake_case field names to match Bookmark attributes
    update_data = bookmark_update.model_dump(exclude_unset=True, by_alias=False)
    bookmark.sqlmodel_update(update_data)
    bookmark.updated_at = datetime.now(UTC)

    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


@v1.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(bookmark_id: uuid.UUID, session: SessionDep):
    """
    Delete a bookmark permanently.
    Returns 204 No Content.
    """
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bookmark {bookmark_id} not found"
        )
    session.delete(bookmark)
    session.commit()
    return


@v1.get("/bookmarks/{bookmark_id}/weather", response_model=WeatherResponse, status_code=status.HTTP_200_OK)
async def get_bookmark_weather(
    bookmark_id: uuid.UUID,
    session: SessionDep,
    force_refresh: bool = Query(False, description="Bypass cache")
):
    """
    Get weather for a saved bookmark.
    Returns 200 OK, 404 if bookmark not found, 502/503/504 if weather API fails.
    """
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    weather = await get_weather_for_bookmark(
        city=bookmark.city,
        country_code=bookmark.country_code,
        units=bookmark.units,
        force_refresh=force_refresh
    )
    save_history(session, bookmark_id, weather)
    return weather


@v1.get("/weather", status_code=status.HTTP_200_OK, response_model=WeatherResponse)
async def quick_weather_lookup(
    city: str = Query(..., min_length=1, description="City name"),
    country_code: str = Query(..., min_length=2, max_length=2, description="Country code (e.g. GB, NG)"),
    units: Units = Query(Units.metric, description="Temperature units"),
    force_refresh: bool = Query(False, description="Bypass cache")
):
    """
    Quick weather lookup without needing a saved bookmark.
    Returns 200 OK, 502/503/504 if weather API fails.
    """
    return await get_weather_for_bookmark(city, country_code, units, force_refresh)


@v1.get("/bookmarks/{bookmark_id}/weather/history", response_model=list[WeatherHistory], status_code=status.HTTP_200_OK)
async def get_weather_history(bookmark_id: uuid.UUID, session: SessionDep):
    """
    Return all past weather fetches for a bookmark, oldest first.
    Returns 200 OK, 404 if bookmark not found.
    """
    bookmark = session.get(Bookmark, bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    return get_history(session, bookmark_id)


@v1.get("/bookmarks/alerts/temperature", response_model=list[BookmarkAlertResponse], status_code=status.HTTP_200_OK)
async def get_temperature_alerts(session: SessionDep):
    """
    Check all bookmarks with a set threshold.
    Returns those where current temperature exceeds the threshold.
    """
    # Only fetch bookmarks that actually have a threshold set — SQL handles the filter
    statement = select(Bookmark).where(Bookmark.temperature_threshold.is_not(None))
    bookmarks = session.exec(statement).all()

    # 1. Fire all weather requests to OpenWeather simultaneously
    fetch_tasks = [
        asyncio.create_task(get_weather_for_bookmark(
            city=b.city,
            country_code=b.country_code,
            units=b.units
        ))
        for b in bookmarks
    ]

    # 2. Wait for everything to finish at once, trapping exceptions
    weather_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    alerts = []
    # 3. Zip pairs the bookmark and the weather result together
    for bookmark, result in zip(bookmarks, weather_results):
        
        # Guard Clause: Skip if OpenWeather crashed/timed out for this specific city
        if isinstance(result, Exception):
            continue 

        # Build the alert if threshold is breached
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
    page: int = Query(1, ge=1, description="page number"),
    limit: int = Query(5, ge=5, le=100, description="items per page, max=100")
) -> dict[str, Any]:
    """
    Fetch weather for multiple bookmarks concurrently using asyncio.gather.
    """
    total = session.exec(select(func.count()).select_from(Bookmark)).one()
    
    start = (page - 1) * limit
    paginated = session.exec(select(Bookmark).offset(start).limit(limit)).all()

    fetch_tasks = [
        asyncio.create_task(get_weather_for_bookmark(
            city=b.city,
            country_code=b.country_code,
            units=b.units,
            force_refresh=True
        ))
        for b in paginated
    ]

    weather_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    results_list = []
    for b, w in zip(paginated, weather_results):
        if isinstance(w, Exception):
            results_list.append({
                "bookmark_id": str(b.id), 
                "city": b.city, 
                "weather": None,
                "error": str(w)
            })
        else:
            # If it succeeded, send the weather!
            results_list.append({
                "bookmark_id": str(b.id), 
                "city": b.city, 
                "weather": w
            })

            
    total_pages = math.ceil(total / limit) if total > 0 else 1
    return {"data": results_list, "total": total, "page": page, "totalPages": total_pages}


@v1.get("/cache/stats", status_code=status.HTTP_200_OK)
async def cache_stats():
    """Return how many items are in the weather cache and which locations are cached."""
    return get_cache_stats()


@v1.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache():
    """Clear all weather cache data."""
    flush_cache()
    return
