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


class Helper:
    ignore = []

    def __init__(self, parent):
        self.parent = parent

    def super(self):
        return self.parent.__class__.__mro__[1]

    def __getattr__(self, item):
        original = getattr(self.parent, item)

        if item in self.ignore:
            return original

        if asyncio.iscoroutinefunction(original):
            # Wrap the function to make it async
            return self.async_wrapper(original)

        # Wrap the function to make it sync
        return self.sync_wrapper(original)

    def sync_wrapper(self, f):
        return f

    def async_wrapper(self, f):
        return f


class AsyncHelper(Helper):
    def sync_wrapper(self, f):
        return sync_to_async(f)

    def x(self):
        return 'x'


class SyncHelper:
    def async_wrapper(self, f):
        return async_to_sync(f)
