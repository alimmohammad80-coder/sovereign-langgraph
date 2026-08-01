import asyncio, inspect

async def invoke_existing_source(func, *, query, limit, country_iso3=None, region=None, series_key=None):
    accepted = set(inspect.signature(func).parameters)
    candidates = {
        "query": query, "q": query, "search_query": query,
        "limit": limit, "max_results": limit,
        "country_iso3": country_iso3, "country": country_iso3,
        "region": region,
        "series_key": series_key, "series_id": series_key,
        "indicator": series_key, "indicator_code": series_key,
    }
    kwargs = {k: v for k, v in candidates.items() if k in accepted and v is not None}
    if inspect.iscoroutinefunction(func):
        return await func(**kwargs)
    return await asyncio.to_thread(func, **kwargs)
