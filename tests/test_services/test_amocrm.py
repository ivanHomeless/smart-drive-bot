"""Tests for AmoCRM client, auth, services, and mock."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.amocrm.auth import AmoCRMAuth, REFRESH_MARGIN_SECONDS
from src.services.amocrm.client import AmoCRMClient, AmoCRMError
from src.services.amocrm.contacts import ContactsService
from src.services.amocrm.leads import LeadsService
from src.services.amocrm.notes import NotesService
from src.services.amocrm.mock import MockAmoCRMClient


# ---------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------

class FakeTokenRow:
    def __init__(self, access, refresh, expires_at):
        self.access_token = access
        self.refresh_token = refresh
        self.expires_at = expires_at


@pytest.mark.asyncio
async def test_auth_returns_cached_token():
    """If token is valid and not near expiry, return cached."""
    auth = AmoCRMAuth(session_factory=MagicMock())
    auth._access_token = "cached_token"
    auth._refresh_token = "refresh_token"
    auth._expires_at = datetime.now(timezone.utc) + timedelta(hours=12)

    token = await auth.get_access_token()

    assert token == "cached_token"


@pytest.mark.asyncio
async def test_auth_refreshes_expired_token():
    """If token is near expiry, refresh it."""
    auth = AmoCRMAuth(session_factory=MagicMock())
    auth._access_token = "old_token"
    auth._refresh_token = "old_refresh"
    auth._expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)

    with patch.object(auth, "_refresh", new_callable=AsyncMock) as mock_refresh:
        async def side_effect():
            auth._access_token = "new_token"
            auth._expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_refresh.side_effect = side_effect

        token = await auth.get_access_token()

    assert token == "new_token"
    mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_auth_loads_from_db_when_no_memory():
    """If no token in memory, load from DB."""
    auth = AmoCRMAuth(session_factory=MagicMock())

    with patch.object(auth, "_load_from_db", new_callable=AsyncMock) as mock_load:
        async def load_side_effect():
            auth._access_token = "db_token"
            auth._refresh_token = "db_refresh"
            auth._expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
        mock_load.side_effect = load_side_effect

        token = await auth.get_access_token()

    assert token == "db_token"
    mock_load.assert_called_once()


@pytest.mark.asyncio
async def test_auth_handle_401_triggers_refresh():
    """handle_401 should force refresh."""
    auth = AmoCRMAuth(session_factory=MagicMock())
    auth._refresh_token = "some_refresh"

    with patch.object(auth, "_refresh", new_callable=AsyncMock) as mock_refresh:
        await auth.handle_401()

    mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_auth_raises_when_no_token():
    """If no token available at all, raise RuntimeError."""
    auth = AmoCRMAuth(session_factory=MagicMock())

    with patch.object(auth, "_load_from_db", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="No AmoCRM token"):
            await auth.get_access_token()


# ---------------------------------------------------------------
# Client tests (using get/post/patch wrapper methods)
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_successful_request():
    """Successful GET returns parsed JSON."""
    auth = MagicMock()
    auth.get_access_token = AsyncMock(return_value="test_token")
    auth.base_url = "https://test.amocrm.ru"

    client = AmoCRMClient(auth)

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"data": "value"}
        result = await client.get("/api/v4/contacts")

    assert result == {"data": "value"}
    mock_req.assert_called_once_with("GET", "/api/v4/contacts", params=None)


@pytest.mark.asyncio
async def test_client_post_passes_json():
    """POST passes json body correctly."""
    auth = MagicMock()
    auth.get_access_token = AsyncMock(return_value="test_token")
    auth.base_url = "https://test.amocrm.ru"

    client = AmoCRMClient(auth)

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"_embedded": {"leads": [{"id": 1}]}}
        result = await client.post("/api/v4/leads", json=[{"name": "test"}])

    assert result["_embedded"]["leads"][0]["id"] == 1
    mock_req.assert_called_once_with("POST", "/api/v4/leads", json=[{"name": "test"}])


@pytest.mark.asyncio
async def test_client_request_retries_on_429():
    """_request retries on 429 Too Many Requests."""
    auth = MagicMock()
    auth.get_access_token = AsyncMock(return_value="test_token")
    auth.base_url = "https://test.amocrm.ru"

    client = AmoCRMClient(auth)
    call_count = 0

    # Mock aiohttp at a lower level using a helper
    async def fake_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        if call_count == 1:
            resp.status = 429
            resp.text = AsyncMock(return_value="rate limited")
        else:
            resp.status = 200
            resp.json = AsyncMock(return_value={"ok": True})
        return resp

    with patch("aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        # Make request return an async context manager
        mock_session.request = MagicMock(side_effect=lambda *a, **kw: _acm(fake_request(*a, **kw)))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client._request("GET", "/api/v4/leads")

    assert result == {"ok": True}
    assert call_count == 2


@pytest.mark.asyncio
async def test_client_request_401_triggers_refresh():
    """_request calls auth.handle_401 on 401."""
    auth = MagicMock()
    auth.get_access_token = AsyncMock(return_value="test_token")
    auth.handle_401 = AsyncMock()
    auth.base_url = "https://test.amocrm.ru"

    client = AmoCRMClient(auth)
    call_count = 0

    async def fake_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        if call_count == 1:
            resp.status = 401
            resp.text = AsyncMock(return_value="unauthorized")
        else:
            resp.status = 200
            resp.json = AsyncMock(return_value={"ok": True})
        return resp

    with patch("aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session.request = MagicMock(side_effect=lambda *a, **kw: _acm(fake_request(*a, **kw)))

        result = await client._request("GET", "/api/v4/contacts")

    auth.handle_401.assert_called_once()
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_client_request_raises_on_persistent_500():
    """_request raises AmoCRMError after 3 retries of 500."""
    auth = MagicMock()
    auth.get_access_token = AsyncMock(return_value="test_token")
    auth.base_url = "https://test.amocrm.ru"

    client = AmoCRMClient(auth)

    async def fake_request(method, url, **kwargs):
        resp = MagicMock()
        resp.status = 500
        resp.text = AsyncMock(return_value="server error")
        return resp

    with patch("aiohttp.ClientSession") as mock_cls:
        mock_session = MagicMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session.request = MagicMock(side_effect=lambda *a, **kw: _acm(fake_request(*a, **kw)))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(AmoCRMError, match="500"):
                await client._request("GET", "/api/v4/leads")


class _acm:
    """Helper to wrap a coroutine as an async context manager."""

    def __init__(self, coro):
        self._coro = coro

    async def __aenter__(self):
        return await self._coro

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------
# Mock client tests
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_client_contacts_search_empty():
    mock = MockAmoCRMClient()
    result = await mock.get("/api/v4/contacts", params={"query": "+79991234567"})
    assert result["_embedded"]["contacts"] == []


@pytest.mark.asyncio
async def test_mock_client_create_contact():
    mock = MockAmoCRMClient()
    result = await mock.post("/api/v4/contacts", json=[{"name": "Test"}])
    assert "id" in result["_embedded"]["contacts"][0]


@pytest.mark.asyncio
async def test_mock_client_create_lead():
    mock = MockAmoCRMClient()
    result = await mock.post("/api/v4/leads", json=[{"name": "Test Lead"}])
    assert "id" in result["_embedded"]["leads"][0]


@pytest.mark.asyncio
async def test_mock_client_create_note():
    mock = MockAmoCRMClient()
    result = await mock.post(
        "/api/v4/leads/123/notes",
        json=[{"note_type": "common", "params": {"text": "test"}}],
    )
    note = result["_embedded"]["notes"][0]
    assert "id" in note
    assert note["entity_id"] == 123


# ---------------------------------------------------------------
# Services with mock client
# ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_contacts_service_find_by_phone_not_found():
    mock = MockAmoCRMClient()
    service = ContactsService(mock)
    result = await service.find_by_phone("+79991234567")
    assert result is None


@pytest.mark.asyncio
async def test_contacts_service_create():
    mock = MockAmoCRMClient()
    service = ContactsService(mock)
    contact_id = await service.create(
        name="Test", phone="+79991234567",
        telegram_id=123, telegram_username="testuser",
    )
    assert isinstance(contact_id, int)


@pytest.mark.asyncio
async def test_leads_service_create():
    mock = MockAmoCRMClient()
    service = LeadsService(mock)
    lead_id = await service.create(
        title="Продажа - BMW - Иван",
        contact_id=100,
        service_type="sell",
        data={"car_brand": "BMW", "year": "2023"},
    )
    assert isinstance(lead_id, int)


@pytest.mark.asyncio
async def test_notes_service_add():
    mock = MockAmoCRMClient()
    service = NotesService(mock)
    note_id = await service.add_to_lead(lead_id=100, text="Test note")
    assert isinstance(note_id, int)
