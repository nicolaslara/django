import os
import signal
import subprocess

from django.db.backends.base.client import BaseDatabaseClient


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'psql'

    @classmethod
    def runshell_db(cls, conn_params):
        # ToDo: This needs to be rewriten in aiopg
        raise NotImplementedError('This needs to be rewriten in aiopg')


    def runshell(self):
        DatabaseClient.runshell_db(self.connection.get_connection_params())
