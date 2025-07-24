# utils/decorators.py

import functools
import time
import logging


def retry_on_exception(exceptions, tries=3, delay=1, backoff=2):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, tries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logging.error(f"{func.__name__} failed on attempt {attempt}: {e}")
                    if attempt == tries:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper

    return decorator_retry
