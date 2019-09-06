"Dummy cache backend"

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.utils.asyncio import auto_async


class DummyCache(BaseCache):
    def __init__(self, host, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @auto_async
    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return True

    @auto_async
    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return default

    @auto_async
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

    @auto_async
    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        self.validate_key(key)
        return False

    @auto_async
    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

    @auto_async
    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return False

    @auto_async
    def clear(self):
        pass
