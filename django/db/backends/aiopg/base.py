"""
PostgreSQL database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""

import asyncio
import threading
import warnings

import aiopg
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.postgresql import base as psql_backend
from django.db.backends.utils import (
    CursorDebugWrapper as BaseCursorDebugWrapper,
)
from django.db.utils import DatabaseError as WrappedDatabaseError
from django.utils.asyncio import async_unsafe
from django.utils.functional import cached_property
from django.utils.safestring import SafeString
from django.utils.version import get_version_tuple

try:
    import aiopg as Database
except ImportError as e:
    raise ImproperlyConfigured("Error loading aiopg module: %s" % e)

# Some of these import psycopg2, so import them after checking if it's installed.
from .client import DatabaseClient                          # NOQA isort:skip

# ToDo: A lot of these things use cursors, etc... so they may need to be
#  rewriten

from ..postgresql.creation import DatabaseCreation            # NOQA isort:skip
from ..postgresql.features import DatabaseFeatures            # NOQA isort:skip
from ..postgresql.introspection import DatabaseIntrospection  # NOQA isort:skip
from ..postgresql.operations import DatabaseOperations        # NOQA isort:skip
from ..postgresql.schema import DatabaseSchemaEditor          # NOQA isort:skip
from ..postgresql.utils import utc_tzinfo_factory             # NOQA isort:skip


class DatabaseWrapper(psql_backend.DatabaseWrapper):
    Database = Database
    SchemaEditorClass = DatabaseSchemaEditor
    # Classes instantiated in __init__().
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    async def get_new_connection(self, conn_params):

        # TODO: REWRITE THIS
        print(conn_params)

        connection = await aiopg.connect(**conn_params)

        return connection
        # self.isolation_level must be set:
        # - after connecting to the database in order to obtain the database's
        #   default when no value is explicitly specified in options.
        # - before calling _set_autocommit() because if autocommit is on, that
        #   will set connection.isolation_level to ISOLATION_LEVEL_AUTOCOMMIT.
        options = self.settings_dict['OPTIONS']
        try:
            self.isolation_level = options['isolation_level']
        except KeyError:
            self.isolation_level = connection.isolation_level
        else:
            # Set the isolation level to the value from OPTIONS.
            pass
            # FIXME: This is currently not working.set_session() only works form a sync context
            #if self.isolation_level != connection.isolation_level:
            #    await connection.set_session(isolation_level=self.isolation_level)

        return connection

    async def ensure_timezone(self):

        # TODO: REVIEW THIS FOR ASYNC COMPATIBILITY

        if self.connection is None:
            return False
        conn_timezone_name = await self.connection.get_parameter_status('TimeZone')
        timezone_name = self.timezone_name
        if timezone_name and conn_timezone_name != timezone_name:
            async with self.connection.cursor() as cursor:
                await cursor.execute(self.ops.set_time_zone_sql(), [timezone_name])
            return True
        return False

    async def init_connection_state(self):

        # TODO: Adapt to aiopg

        # FIXME: This cannot be used in an async context
        #self.connection.set_client_encoding('UTF8')

        timezone_changed = await self.ensure_timezone()
        if timezone_changed:
            # Commit after setting the time zone (see #17062)
            pass
            # Psycopg in async mode doesn't allow commit
            #if not self.get_autocommit():
            #    await self.connection.commit()

    def get_autocommit(self):
        return False

    @async_unsafe
    def create_cursor(self, name=None):

        # TODO: Adapt to aiopg

        if name:
            # In autocommit mode, the cursor will be used outside of a
            # transaction, hence use a holdable cursor.
            cursor = self.connection.cursor(name, scrollable=False, withhold=self.connection.autocommit)
        else:
            cursor = self.connection.cursor()
        cursor.tzinfo_factory = utc_tzinfo_factory if settings.USE_TZ else None
        return cursor

    @async_unsafe
    def chunked_cursor(self):
        self._named_cursor_idx += 1
        # Get the current async task
        # Note that right now this is behind @async_unsafe, so this is
        # unreachable, but in future we'll start loosening this restriction.
        # For now, it's here so that every use of "threading" is
        # also async-compatible.
        try:
            if hasattr(asyncio, 'current_task'):
                # Python 3.7 and up
                current_task = asyncio.current_task()
            else:
                # Python 3.6
                current_task = asyncio.Task.current_task()
        except RuntimeError:
            current_task = None
        # Current task can be none even if the current_task call didn't error
        if current_task:
            task_ident = str(id(current_task))
        else:
            task_ident = 'sync'
        # Use that and the thread ident to get a unique name
        return self._cursor(
            name='_django_curs_%d_%s_%d' % (
                # Avoid reusing name in other threads / tasks
                threading.current_thread().ident,
                task_ident,
                self._named_cursor_idx,
            )
        )

    async def _set_autocommit(self, autocommit):
        # ToDO: Fix wrap_database_errors for async
        #with self.wrap_database_errors:
        pass

    def check_constraints(self, table_names=None):
        """
        Check constraints by setting them to immediate. Return them to deferred
        afterward.
        """
        self.cursor().execute('SET CONSTRAINTS ALL IMMEDIATE')
        self.cursor().execute('SET CONSTRAINTS ALL DEFERRED')

    def is_usable(self):
        try:
            # Use a psycopg cursor directly, bypassing Django's utilities.
            self.connection.cursor().execute("SELECT 1")
        except Database.Error:
            return False
        else:
            return True

    @property
    def _nodb_connection(self):

        # ToDo:  What is this?

        nodb_connection = super()._nodb_connection
        try:
            nodb_connection.ensure_connection()
        except (Database.DatabaseError, WrappedDatabaseError):
            warnings.warn(
                "Normally Django will use a connection to the 'postgres' database "
                "to avoid running initialization queries against the production "
                "database when it's not needed (for example, when running tests). "
                "Django was unable to create a connection to the 'postgres' database "
                "and will use the first PostgreSQL database instead.",
                RuntimeWarning
            )
            for connection in connections.all():
                if connection.vendor == 'postgresql' and connection.settings_dict['NAME'] != 'postgres':
                    return self.__class__(
                        {**self.settings_dict, 'NAME': connection.settings_dict['NAME']},
                        alias=self.alias,
                    )
        return nodb_connection

    @cached_property
    def pg_version(self):

        # ToDo: adapt

        with self.temporary_connection():
            return self.connection.server_version

    def make_debug_cursor(self, cursor):

        # Ignore debug cursor for now

        return psql_backend.CursorDebugWrapper(cursor, self)


