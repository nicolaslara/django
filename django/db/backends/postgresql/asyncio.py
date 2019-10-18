from django.core.exceptions import ImproperlyConfigured
from django.utils.asyncio import AsyncHelper

# ToDO: Only do this import conditionally
try:
    import asyncpg
except ImportError as e:
    raise ImproperlyConfigured("Error loading asyncpg module: %s" % e)

try:
    import aiopg
except ImportError as e:
    raise ImproperlyConfigured("Error loading asyncpg module: %s" % e)


class AsyncDatabaseWrapper(AsyncHelper):
    ignore = [
        'check_settings',
        'settings_dict',
        'get_connection_params',
    ]

    async def connect(self):
        # Calling the parent's parent, with the wrapped methods.
        self.super().connect(self)
        self.connection = await self.connection
        self.parent.connection = self.connection

    def get_new_connection(self, conn_params):
        #ToDo: This probably needs to be wrapped
        return aiopg.connect(**conn_params)

    def get_connection_params(self):
        params = self.parent.get_connection_params()
        return params

    def set_autocommit(self, autocommit):
        # Autocommit is always true for async connections
        return

    def init_connection_state(self):
        # Nothing to do here. #ToDo: or is there?
        return
