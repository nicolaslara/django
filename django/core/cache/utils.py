import hashlib
import inspect
from urllib.parse import quote

from asgiref.sync import sync_to_async

TEMPLATE_FRAGMENT_KEY_TEMPLATE = 'template.cache.%s.%s'


def make_template_fragment_key(fragment_name, vary_on=None):
    if vary_on is None:
        vary_on = ()
    key = ':'.join(quote(str(var)) for var in vary_on)
    args = hashlib.md5(key.encode())
    return TEMPLATE_FRAGMENT_KEY_TEMPLATE % (fragment_name, args.hexdigest())


def auto_async(func):
    def sync_wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    async def async_wrapper(*args, **kwargs):
        return await sync_to_async(func)(*args, **kwargs)

    def inner(*args, **kwargs):
        # Initial experiment with frame hacks. This needs to be expended for many possible use cases
        parent_frame = inspect.getouterframes(inspect.currentframe())[1]
        if parent_frame.frame.f_code.co_flags & (
            inspect.CO_COROUTINE | inspect.CO_ITERABLE_COROUTINE | inspect.CO_ASYNC_GENERATOR
        ):
            return async_wrapper(*args, **kwargs)
        return sync_wrapper(*args, **kwargs)

    return inner
