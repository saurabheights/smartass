import httpx
import pytest
import respx

from smartass.daemon.http import AsyncHttpClient


@pytest.mark.asyncio
async def test_get_json_returns_parsed_body():
    client = AsyncHttpClient(user_agent="smartass-test/0.1", timeout=2.0)
    try:
        with respx.mock(assert_all_called=True) as mock:
            mock.get("https://example.test/api").mock(
                return_value=httpx.Response(200, json={"ok": True, "n": 3})
            )
            data = await client.get_json("https://example.test/api")
            assert data == {"ok": True, "n": 3}
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_get_json_raises_on_5xx():
    client = AsyncHttpClient(user_agent="smartass-test/0.1", timeout=2.0)
    try:
        with respx.mock() as mock:
            mock.get("https://example.test/api").mock(
                return_value=httpx.Response(503, text="down")
            )
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_json("https://example.test/api")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_sets_user_agent_header():
    client = AsyncHttpClient(user_agent="smartass/0.1.0", timeout=2.0)
    try:
        with respx.mock() as mock:
            route = mock.get("https://example.test/").mock(
                return_value=httpx.Response(200, json={})
            )
            await client.get_json("https://example.test/")
            assert route.calls.last.request.headers["user-agent"] == "smartass/0.1.0"
    finally:
        await client.aclose()
