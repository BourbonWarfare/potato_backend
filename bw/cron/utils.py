import asyncio
import functools
import random


def backoff(delay=2, retries=3, max_delay=float('inf')):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_retry = 0
            current_delay = delay
            while current_retry < retries:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    current_retry += 1
                    if current_retry >= retries:
                        raise e
                    await asyncio.sleep(current_delay + random.random() * delay)
                    current_delay *= 2
                    current_delay = min(current_delay, max_delay)

        return wrapper

    return decorator
