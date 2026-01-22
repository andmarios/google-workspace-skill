"""Retry utilities for handling transient API errors."""

import time
from functools import wraps
from typing import Any, Callable, TypeVar

from googleapiclient.errors import HttpError

T = TypeVar("T")


def is_retryable_error(error: HttpError) -> bool:
    """Check if an HTTP error is retryable.

    Transient errors that should be retried:
    - 500 Internal Error
    - 502 Bad Gateway
    - 503 Service Unavailable
    - 429 Too Many Requests (rate limiting)
    """
    if error.resp is None:
        return False
    status = error.resp.status
    return status in (429, 500, 502, 503)


def retry_on_transient_error(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry functions on transient Google API errors.

    Args:
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for delay after each retry.

    Example:
        @retry_on_transient_error(max_retries=3)
        def upload_file(...):
            return self.service.files().create(...).execute()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_error: HttpError | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except HttpError as e:
                    if not is_retryable_error(e) or attempt >= max_retries:
                        raise
                    last_error = e
                    time.sleep(delay)
                    delay *= backoff_factor

            # This shouldn't be reached, but just in case
            if last_error:
                raise last_error
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


def execute_with_retry(
    request: Any,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Any:
    """Execute a Google API request with retry logic.

    This is useful when you can't easily use the decorator, e.g.,
    when the request is built dynamically.

    Args:
        request: A Google API request object (from .create(), .get(), etc.).
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for delay after each retry.

    Returns:
        The result of request.execute()

    Example:
        request = self.service.files().create(body=metadata, media_body=media)
        result = execute_with_retry(request)
    """
    delay = initial_delay
    last_error: HttpError | None = None

    for attempt in range(max_retries + 1):
        try:
            return request.execute()
        except HttpError as e:
            if not is_retryable_error(e) or attempt >= max_retries:
                raise
            last_error = e
            time.sleep(delay)
            delay *= backoff_factor

    if last_error:
        raise last_error
    raise RuntimeError("Unexpected retry loop exit")
