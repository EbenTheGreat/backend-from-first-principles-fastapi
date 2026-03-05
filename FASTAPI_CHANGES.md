# FastAPI Documentation Changes — What's New

> **As of:** February 28, 2026 | **Latest version:** FastAPI 0.134.0  
> **Source:** [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/)

This document covers the major changes FastAPI has made to their framework and official documentation. These are the changes the FastAPI team made — **not** specific to our project.

---

## 1. Python 3.10 is Now the Minimum (v0.129.0)

FastAPI **dropped support for Python 3.9**. Python 3.10 is now the minimum required version.

**What changed in the docs:**
- All official documentation examples were rewritten from Python 3.9 to Python 3.10 syntax
- The docs no longer show the old `Union[X, None]` style — they use `X | None` everywhere
- The docs no longer show `List[str]` — they use `list[str]` everywhere
- No more `from typing import Optional, List, Union` in any example

**Before (old docs):**
```python
from typing import Optional, List, Union

@app.get("/items")
def get_items(q: Optional[str] = None) -> List[Item]:
    ...
```

**After (current docs):**
```python
@app.get("/items")
def get_items(q: str | None = None) -> list[Item]:
    ...
```

> This is the biggest visual change across the entire documentation. Every single tutorial page was updated.

---

## 2. Pydantic v2 is Now Required (v0.128.0)

FastAPI **dropped support for `pydantic.v1`** — the backward-compatibility layer. You can no longer use Pydantic v1 APIs, even through the compatibility import.

**What this means:**
- `.dict()` is officially gone → use `.model_dump()`
- `.from_orm()` is officially gone → use `.model_validate()`
- `class Config:` / `schema_extra` is gone → use `model_config` / `json_schema_extra`
- `@validator` is gone → use `@field_validator`
- `@root_validator` is gone → use `@model_validator`

**Original Pydantic v2 migration happened in FastAPI 0.100.0**, but they kept backward compatibility with `pydantic.v1` for a long time. That safety net is now removed.

---

## 3. 2x JSON Performance (v0.130.0)

FastAPI now **serializes JSON responses using Pydantic's Rust-based serializer** when you have a Pydantic return type or `response_model`.

**What this means for you:**
- JSON responses are **2x faster** (or more) automatically
- No code changes needed — just having `response_model=YourModel` or a Pydantic return type triggers this
- Third-party JSON libraries (`orjson`, `ujson`) are no longer needed for speed

**New docs:** [Custom Response – JSON Performance](https://fastapi.tiangolo.com/advanced/custom-response/#json-performance)

---

## 4. ORJSONResponse & UJSONResponse Deprecated (v0.131.0)

Since Pydantic's Rust serializer is now faster than `orjson` and `ujson`, FastAPI **deprecated** both custom response classes:

- `ORJSONResponse` — deprecated
- `UJSONResponse` — deprecated

**What to use instead:** Just use the default `JSONResponse` — it's now powered by Pydantic's Rust serializer and is faster than both alternatives.

---

## 5. Strict Content-Type Checking (v0.132.0) ⚠️ Breaking

FastAPI now **checks the `Content-Type` header** on incoming JSON requests by default. If a client sends a POST/PUT/PATCH with JSON data but **without** a proper `Content-Type: application/json` header, FastAPI will reject it.

**Why this matters:** Some HTTP clients (like older JavaScript `fetch` calls or `curl` without `-H`) might not send the correct header.

**If your clients break, add this:**
```python
app = FastAPI(strict_content_type=False)
```

**New docs:** [Strict Content-Type Checking](https://fastapi.tiangolo.com/advanced/strict-content-type/)

---

## 6. Streaming JSON Lines with `yield` (v0.134.0)

FastAPI added native support for **streaming responses using `yield`**. You can now stream JSON Lines (newline-delimited JSON) or binary data directly from route functions.

```python
@app.get("/stream")
def stream_data():
    for item in get_items():
        yield item  # Each item is sent as a JSON line
```

**Why this matters:** This is essential for AI/LLM applications where you want to stream tokens or results incrementally instead of waiting for the full response.

**New docs:**
- [Stream JSON Lines](https://fastapi.tiangolo.com/tutorial/stream-json-lines/)
- [Stream Data (Advanced)](https://fastapi.tiangolo.com/advanced/stream-data/)

---

## 7. Documentation Structure Changes

The FastAPI docs website itself was reorganized:

| Section | What's New |
|---|---|
| **Tutorial** | New page: "Stream JSON Lines" |
| **Advanced** | New page: "Stream Data" |
| **Advanced** | New page: "Strict Content-Type Checking" |
| **Advanced** | Updated "Custom Response" with JSON Performance section |
| **All pages** | All code examples updated from Python 3.9 → 3.10 syntax |
| **All pages** | `Union[X, None]` replaced with `X \| None` throughout |

---

## Summary Timeline

| Version | Change | Type |
|---|---|---|
| **0.100.0** | Added Pydantic v2 support (kept v1 compatibility) | Feature |
| **0.128.0** | Dropped `pydantic.v1` compatibility — Pydantic v2 only | ⚠️ Breaking |
| **0.129.0** | Dropped Python 3.9 — minimum is now 3.10 | ⚠️ Breaking |
| **0.130.0** | 2x JSON performance via Pydantic Rust serializer | Performance |
| **0.131.0** | Deprecated `ORJSONResponse` and `UJSONResponse` | Deprecation |
| **0.132.0** | Strict `Content-Type` checking for JSON requests | ⚠️ Breaking |
| **0.133.0** | Starlette 1.0.0+ support | Upgrade |
| **0.134.0** | Streaming JSON Lines & binary data with `yield` | Feature |

---

## What Does This Mean For Your Learning?

1. **Everything you learned still applies** — the concepts (routing, validation, dependencies, auth, caching, architecture) are unchanged
2. **Only the syntax changed** — and it got simpler (`X | None` instead of `Optional[X]`)
3. **You're already up to date** — we updated all your code to the current patterns
4. **When reading old tutorials/YouTube videos** — they might use `Optional`, `.dict()`, `.from_orm()` — now you know the modern equivalents
