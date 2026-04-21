"""Thin async HTTP client shared by plugins with the net.http permission."""

from __future__ import annotations

from typing import Any

import httpx


class AsyncHttpClient:
    def __init__(self, user_agent: str, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        resp = await self._client.get(url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()
