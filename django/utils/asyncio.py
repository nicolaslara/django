import asyncio
import functools
import inspect
import types

from asgiref.sync import sync_to_async
from django.core.exceptions import SynchronousOnlyOperation


def async_unsafe(message):
    """
    Decorator to mark functions as async-unsafe. Someone trying to access
    the function while in an async context will get an error message.
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

class AutoAsync(object):
    def __init__(self, f):
        self.func = f

    def sync_wrapper(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    async def async_wrapper(self, *args, **kwargs):
        return await sync_to_async(self.func)(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.sync_wrapper(*args, **kwargs)

    def __get__(self, instance, owner):
        from functools import partial

        self.bound = functools.wraps(self.func)(partial(self.__call__, instance))
        self.bound.sync = functools.wraps(self.func)(partial(self.__call__, instance))
        return self.bound



def auto_async(func):
    """
    Decorator to automatically convert a sync function to async depending on
    the calling context.
    """

    def sync_wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    async def async_wrapper(*args, **kwargs):
        return await sync_to_async(func)(*args, **kwargs)

    @functools.wraps(func)
    def inner(*args, **kwargs):
        # Initial experiment with frame hacks.
        # This needs to be expended for other possible use cases.
        #
        # This may also break easily. What happens if the parent wants a
        # coroutine to later pass it around?
        try:
            outer_frames = inspect.getouterframes(inspect.currentframe())
        except IndexError:
            # I'm not sure if this only happens on ipython, but for now
            # forcing async here helps me debug
            # ToDo: Review this.
            return async_wrapper(*args, **kwargs)
        try:
            parent_frame = outer_frames[1]
            if parent_frame.frame.f_code.co_flags & (
                inspect.CO_COROUTINE |
                inspect.CO_ITERABLE_COROUTINE |
                inspect.CO_ASYNC_GENERATOR):
                return async_wrapper(*args, **kwargs)
        except IndexError:
            pass  # No outer frames

        return sync_wrapper(*args, **kwargs)

    inner.sync = sync_wrapper
    inner.async_ = async_wrapper

    #inspect.ismethod

    return inner
