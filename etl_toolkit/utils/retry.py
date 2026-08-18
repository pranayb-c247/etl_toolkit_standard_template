"""
retry.py
--------
Simple retry decorator with exponential backoff - for flaky API calls
(e.g. HappyEndpoint/RapidAPI rate limits, StubHub OAuth token refresh).
"""

import time
import logging
import functools

logger = logging.getLogger("etl_toolkit.utils")


def retry(max_attempts: int = 3, base_delay_sec: float = 2.0, exceptions=(Exception,)):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            attempt = 1
            while True:
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    if attempt >= max_attempts:
                        logger.error("retry: %s failed after %d attempts: %s", fn.__name__, attempt, e)
                        raise
                    delay = base_delay_sec * (2 ** (attempt - 1))
                    logger.warning("retry: %s failed (attempt %d/%d): %s. Retrying in %.1fs",
                                   fn.__name__, attempt, max_attempts, e, delay)
                    time.sleep(delay)
                    attempt += 1
        return wrapper
    return decorator
