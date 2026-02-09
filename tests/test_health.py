import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient, TestServer

from src.main import health_check


@pytest.mark.asyncio
async def test_health_check_returns_200():
    app = web.Application()
    app.router.add_get("/health", health_check)

    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/health")
        assert resp.status == 200
        text = await resp.text()
        assert text == "ok"
