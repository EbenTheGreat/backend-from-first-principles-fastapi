from uuid import uuid4
from datetime import datetime, UTC

# In-memory bookmarks store — same pattern as tasks_db from project 1
# Key: bookmark UUID string → Value: bookmark dict
bookmarks_db: dict = {}

# In-memory weather cache — same Cache Aside pattern from caching lecture
# Key: "city:country_code:units" (e.g. "london:GB:metric") → Value: {data, fetched_at}
weather_cache: dict = {}
