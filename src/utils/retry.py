import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Type

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    backoff_base: int = 2,
    retry_on: tuple[Type[Exception], ...] = (Exception,),
    on_401: Callable[[], Any] | None = None,
) -> Callable:
    """Decorator for async functions with exponential backoff retry.

    Args:
        max_attempts: Maximum number of attempts.
        backoff_base: Base for exponential backoff (seconds).
        retry_on: Tuple of exception types to retry on.
        on_401: Optional async callback invoked on HTTP 401 before retry.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as exc:
                    last_exception = exc
                    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)

                    if status == 401 and on_401 is not None:
                        logger.warning("Got 401, calling on_401 callback (attempt %d)", attempt)
                        callback_result = on_401()
                        if asyncio.iscoroutine(callback_result):
                            await callback_result

                    if attempt == max_attempts:
                        logger.error(
                            "Function %s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise

                    delay = backoff_base ** (attempt - 1)
                    logger.warning(
                        "Function %s attempt %d/%d failed: %s. Retrying in %ds",
                        func.__name__, attempt, max_attempts, exc, delay,
                    )
                    await asyncio.sleep(delay)

            raise last_exception  # type: ignore[misc]

        return wrapper
    return decorator
