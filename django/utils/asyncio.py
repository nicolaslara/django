import asyncio
import functools
import inspect

from asgiref.sync import sync_to_async, async_to_sync
from django.core.exceptions import SynchronousOnlyOperation


def async_unsafe(message):
    """
    Decorator to mark functions as async-unsafe. Someone trying to access
    the function while in an async context will get an error message.

    Functions are considered async-unsafe if they are calling io operations
    from a sync context. CPU-bound functions are not considered async-unsafe here
    """
    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            # Detect a running event loop in this thread.
            try:
                event_loop = asyncio.get_event_loop()
            except RuntimeError:
                pass
            else:
                if event_loop.is_running():
                    raise SynchronousOnlyOperation(message)
            # Pass onwards.
            return func(*args, **kwargs)
        return inner
    # If the message is actually a function, then be a no-arguments decorator.
    if callable(message):
        func = message
        message = 'You cannot call this from an async context - use a thread or sync_to_async.'
        return decorator(func)
    else:
        return decorator


class AsyncHelper:
    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, item):
        original = getattr(self.parent, item)
        if asyncio.iscoroutinefunction(original):
            return original
        return sync_to_async(original)


class SyncHelper:
    def __init__(self, parent):
        self.parent = parent

    def __getattr__(self, item):
        original = getattr(self.parent, item)
        if asyncio.iscoroutinefunction(original):
            return async_to_sync(original)
        return original
