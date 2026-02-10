import pytest

from src.utils.retry import async_retry


class FakeHTTPError(Exception):
    def __init__(self, status: int):
        self.status = status
        super().__init__(f"HTTP {status}")


async def test_retry_succeeds_first_attempt():
    call_count = 0

    @async_retry(max_attempts=3, backoff_base=0)
    async def succeed():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await succeed()
    assert result == "ok"
    assert call_count == 1


async def test_retry_succeeds_after_failures():
    call_count = 0

    @async_retry(max_attempts=3, backoff_base=0, retry_on=(ValueError,))
    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("not yet")
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert call_count == 3


async def test_retry_exhausted_raises():
    @async_retry(max_attempts=2, backoff_base=0, retry_on=(ValueError,))
    async def always_fail():
        raise ValueError("always fails")

    with pytest.raises(ValueError, match="always fails"):
        await always_fail()


async def test_retry_on_401_calls_callback():
    callback_called = False

    async def refresh_token():
        nonlocal callback_called
        callback_called = True

    call_count = 0

    @async_retry(max_attempts=2, backoff_base=0, retry_on=(FakeHTTPError,), on_401=refresh_token)
    async def api_call():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise FakeHTTPError(401)
        return "ok"

    result = await api_call()
    assert result == "ok"
    assert callback_called


async def test_retry_does_not_catch_unrelated_exception():
    @async_retry(max_attempts=3, backoff_base=0, retry_on=(ValueError,))
    async def wrong_error():
        raise TypeError("wrong type")

    with pytest.raises(TypeError, match="wrong type"):
        await wrong_error()
