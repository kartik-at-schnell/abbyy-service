import time
from functools import wraps
from typing import Callable


def retry(times: int = 3, delay: float = 0.5):
    def outer(fn: Callable):
        @wraps(fn)
        def inner(*args, **kwargs):
            last_exc = None
            for _ in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    time.sleep(delay)
            raise last_exc

        return inner

    return outer

