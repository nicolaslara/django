from django.core.exceptions import ImproperlyConfigured
from django.db.backends import utils
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


class AsyncCursorWrapper(utils.CursorWrapper):
    def __init__(self, cursor, db):
        super().__init__(cursor, db)
        self._obj = None

    def __await__(self):
        return self.cursor.__await__()

    def __next__(self):
        return self.cursor.send(None)

    def send(self, value):
        return self.cursor.send(value)

    def throw(self, typ, val=None, tb=None):
        if val is None:
            return self.cursor.throw(typ)
        elif tb is None:
            return self.cursor.throw(typ, val)
        else:
            return self.cursor.throw(typ, val, tb)

    async def __aenter__(self):
        self._obj = await self.cursor
        return self._obj

    async def __aexit__(self, exc_type, exc, tb):
        try:
            self.cursor.close()
            self._obj = None
        except self.db.Database.Error:
            pass


class AsyncDatabaseWrapper(AsyncHelper):
    ignore = [
        'check_settings',
        'settings_dict',
        'get_connection_params',
        'wrap_database_errors',
    ]

    def ensure_connection(self):
        """Guarantee that a connection to the database is established."""
        if self.connection is None:
            with self.wrap_database_errors:
                self.sync_wrapper(self.connect)()

    async def connect(self):
        # Calling the parent's parent, with the wrapped methods.
        self.super().connect(self)
        self.connection = await self.connection
        self.parent.connection = self.connection

    def get_new_connection(self, conn_params):
        #ToDo: This probably needs to be wrapped
        return aiopg.connect(**conn_params)
        #return asyncpg.connect(**conn_params)

    def create_cursor(self, name=None):
        # Simplifying this because *name*, *scrollable* and *withhold* parameters are not supported by psycopg in asynchronous mode.
        cursor = self.connection.cursor()
        return cursor

    def make_debug_cursor(self, cursor):
        return AsyncCursorWrapper(cursor, self)

    def make_cursor(self, cursor):
        return AsyncCursorWrapper(cursor, self)


    def set_autocommit(self, autocommit):
        # Autocommit is always true for async connections
        return

    def init_connection_state(self):
        # Nothing to do here. #ToDo: or is there?
        return

    def validate_thread_sharing(self):
        # Temporarily disable thread checks
        return

    ###
    #  Overrides that just make self be the wrapper
    #  This should probably be in the helper
    #

    def cursor(self):
        # Calling the parent's parent, with the wrapped methods.
        return self.super().cursor(self)

    def _cursor(self):
        # Calling the parent's parent, with the wrapped methods.
        return self.super()._cursor(self)

    def _prepare_cursor(self, cursor):
        # Calling the parent's parent, with the wrapped methods.
        return self.super()._prepare_cursor(self, cursor)
