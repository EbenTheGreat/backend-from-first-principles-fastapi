from fastapi import APIRouter, HTTPException, Query, status
from models import Sort, SortBy,Units, BookMarkCreate, BookMarkResponse, BookMarkUpdate,BookmarkAlertResponse, BookMarkListResponse, WeatherResponse
from db import bookmarks_db
from uuid import uuid4
from datetime import datetime, UTC
import math
from weather_services import get_from_cache, flush_cache, save_to_cache, get_weather, get_weather_for_bookmark, get_cache_stats, save_history, get_history
import asyncio
from typing import Any


v1 = APIRouter(prefix="/v1", tags=["bookmarks"])


@v1.post("/bookmarks", response_model=BookMarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(bookmark: BookMarkCreate):
    """
    create a new bookmark entry
    Returns 201 Created
    """
    new_id = str(uuid4())
    new_bookmark = {
        "id": new_id,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **bookmark.model_dump(by_alias=False)
    }

    bookmarks_db[new_id] = new_bookmark

    return new_bookmark


@v1.get("/bookmarks", response_model=BookMarkListResponse, status_code=status.HTTP_200_OK)
async def get_all_bookmarks(
    page: int = Query(1, ge=1, description="page number"),
    limit: int = Query(5, ge=1, le=100, description="items per page, Max=100"),
    country_code: str | None = Query(None, description="filter by country"),
    search: str | None= Query(None, description="search in city and notes"),
    sort_by: SortBy = Query(SortBy.created_at, description="field to use in sorting"),
    sort_order: Sort = Query(Sort.ascending, description="sort by asc or desc order"),
    favourite: bool | None = Query(None, description="filter by is_favourite")
) -> BookMarkListResponse: 

    """
    Get all bookmarks
    Returns 200 Ok
    """

    bookmarks = list(bookmarks_db.values())

    if search:
        search_lower = search.strip().lower()
        bookmarks = [t for t in bookmarks if search_lower in t["city"].lower() or search_lower in t["notes"].lower()]

    if country_code:
        bookmarks = [t for t in bookmarks if country_code == t["country_code"]]
    
    if favourite is True:
        bookmarks = [t for t in bookmarks if t["is_favourite"] == True]
    elif favourite is False:
        bookmarks = [t for t in bookmarks if t["is_favourite"] == False]

    bookmarks = sorted(bookmarks,
    key= lambda t: t.get(sort_by, ""),
    reverse=sort_order == Sort.descending)

    total = len(bookmarks)
    start = (page-1) * limit
    end = start + limit
    paginated_bookmarks = bookmarks[start:end]
    total_pages = math.ceil(total / limit) if total > 0 else 1


    return {
        "data": paginated_bookmarks,
        "total": total,
        "page": page,
        "totalPages": total_pages
    }


@v1.get("/bookmarks/{bookmark_id}", response_model=BookMarkResponse, status_code=status.HTTP_200_OK)
async def get_bookmark(bookmark_id: str):
    """
    get single Bookmark
    Returns 200 OK if found, 404 Not Found if missing
    """
    if bookmark_id not in bookmarks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bookmark with {bookmark_id} not found")
    
    bookmark = bookmarks_db[bookmark_id]
    return bookmark

@v1.patch("/bookmarks/{bookmark_id}", response_model=BookMarkResponse, status_code=status.HTTP_200_OK)
async def update_bookmark(bookmark_id: str, bookmark_update: BookMarkUpdate):
    """
    update bookmark fields
    """
    if bookmark_id not in bookmarks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bookmark with {bookmark_id} not found")
    
    updated_data= bookmark_update.model_dump(exclude_unset=True)

    bookmark = bookmarks_db[bookmark_id]

    for field, value in updated_data.items():
        bookmark[field] = value

    bookmark["updated_at"] = datetime.now(UTC)

    return bookmark


@v1.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(bookmark_id: str):
    """
    delete bookmark
    """
    if bookmark_id not in bookmarks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Bookmark with {bookmark_id} not found")
    del bookmarks_db[bookmark_id]
    return


@v1.get("/bookmarks/{bookmark_id}/weather", response_model=WeatherResponse, status_code=status.HTTP_200_OK)
async def get_bookmark_weather(bookmark_id: str, force_refresh: bool = Query(False, description="Bypass cache")):
    """
    Get weather for a saved bookmark.
    Returns 200 OK, 404 if bookmark not found, 502/503/504 if weather API fails.
    """
    if bookmark_id not in bookmarks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    bookmark = bookmarks_db[bookmark_id]

    weather = await get_weather_for_bookmark(
        city=bookmark["city"],
        country_code=bookmark["country_code"],
        units=bookmark["units"],
        force_refresh=force_refresh
    )
    save_history(bookmark_id, weather)
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
    return await get_weather_for_bookmark(city, country_code, units)


@v1.get("/bookmarks/{bookmark_id}/weather/history", response_model=list[WeatherResponse], status_code=status.HTTP_200_OK)
async def get_weather_history(bookmark_id: str):
    """
    Return all past weather fetches for a bookmark, oldest first.
    Returns 200 OK, 404 if bookmark not found.
    """
    if bookmark_id not in bookmarks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    return get_history(bookmark_id)


@v1.get("bookmarks/alerts/temperature", response_model=list[BookmarkAlertResponse], status_code=status.HTTP_200_OK)
async def get_temperature_alerts():
    """
    Checks all bookmarks with a set treshold and returns those where the current 
    temperature exceeds the current threshold
    """
    alerts = []
    for bookmark_id, bookmark in bookmarks_db.items():
        threshold = bookmark.get("temperature_threshold")

        if threshold is not None:
            weather = await get_weather_for_bookmark(city=bookmark["city"],
            country_code=bookmark["country_code"],
            units=bookmark["units"])

            if weather.temperature >=threshold:
                alerts.append(BookmarkAlertResponse(
                    bookmark_id= bookmark_id,
                    city=bookmark["city"],
                    threshold=threshold,
                    current_temperature=weather.temperature,
                message=f"Alert! current temperature ({weather.temperature}°) is above your threshold of {threshold}°"
                ))

    return alerts


@v1.post("/bookmarks/weather/bulk", status_code=status.HTTP_201_CREATED)
async def fetch_weather_for_all_bookmarks(
    page: int = Query(1, ge= 1,description="page number"),
    limit: int = Query(5, ge=5, le=100, description="items per page, max=100")
) -> dict[str, Any]:
    """
    fetches weather for multiple bookmarks concurrently
    """
    bookmarks = list(bookmarks_db.values())

    total = len(bookmarks)
    start = (page-1) * limit
    end = start + limit
    paginated_bookmarks = bookmarks[start:end]

    fetch_tasks = []
    for bookmark in paginated_bookmarks:
        task = asyncio.create_task(get_weather_for_bookmark(
                city=bookmark["city"],
                country_code=bookmark["country_code"],
                units=bookmark["units"],
                force_refresh=True
            ))
        
        fetch_tasks.append(task)

    weather_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    results_list = []
    for bookmark, weather in zip(paginated_bookmarks, weather_results):
        results_list.append({
            "bookmark_id": bookmark["id"],
            "city": bookmark["city"],
            "weather": weather
        })
            
    total_pages = math.ceil(total / limit) if total > 0 else 1


    return {
        "data": results_list,
        "total": total,
        "page": page,
        "totalPages": total_pages
    } 





@v1.get("/cache/stats", status_code=status.HTTP_200_OK)
async def cache_stats():
    """
    Return how many items are in the weather cache and which locations are cached.
    """
    return get_cache_stats()


@v1.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache():
    """
    clear cache data
    """
    flush_cache()
    return

