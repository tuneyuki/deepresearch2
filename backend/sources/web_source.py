from __future__ import annotations

import httpx

from sources.base import ResearchSource, SearchResult


class WebSource(ResearchSource):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.firecrawl.dev/v1"

    async def search(self, query: str) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"query": query, "limit": 5},
                )
                resp.raise_for_status()
                data = resp.json()
                results = []
                for item in data.get("data", []):
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("description", item.get("snippet", "")),
                        )
                    )
                return results
        except Exception:
            return []

    async def fetch_content(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/scrape",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"url": url, "formats": ["markdown"]},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", {}).get("markdown", "")
        except Exception:
            return ""
