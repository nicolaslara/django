import asyncio
import functools
import inspect
import types

from asgiref.sync import sync_to_async, async_to_sync
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
        self.as_defined = f
        if asyncio.iscoroutinefunction(f):
            self.as_async = f
            self.as_sync = async_to_sync(f)
        else:
            self.as_async = sync_to_async(f)
            self.as_sync = f

    def __call__(self, *args, **kwargs):
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
            return self.as_async(*args, **kwargs)
        try:
            parent_frame = outer_frames[1]
            if parent_frame.frame.f_code.co_flags & (
                inspect.CO_COROUTINE |
                inspect.CO_ITERABLE_COROUTINE |
                inspect.CO_ASYNC_GENERATOR):
                return self.as_async(*args, **kwargs)
        except IndexError:
            pass  # No outer frames

        return self.as_sync(*args, **kwargs)

    def __get__(self, instance, owner):
        from functools import partial
        bound = functools.wraps(self.as_defined)(partial(self.__call__, instance))
        bound.as_sync = functools.wraps(self.as_defined)(partial(self.as_sync, instance))
        bound.as_async = functools.wraps(self.as_defined)(partial(self.as_async, instance))
        return bound

    def async_function(self, func):
        self.as_async = func
        return func

    def sync_function(self, func):
        self.as_sync = func
        return func


def auto_async(func):
    return functools.wraps(func)(AutoAsync(func))
