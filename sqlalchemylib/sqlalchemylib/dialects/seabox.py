#!/usr/bin/env python3

from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.engine import reflection
from sqlalchemy.dialects.mysql.reflection import MySQLTableDefinitionParser, ReflectedState
import re
import sqlalchemy.util as util


class SeaboxDialect(PGDialect_psycopg2):
    
    def _get_server_version_info(self, connection):
        return (13, 1, 0)

    @classmethod
    def register(cls):
        from sqlalchemy.dialects import registry
        registry.register("seabox.psycopg2", "sqlalchemylib.dialects.seabox", "SeaboxDialect")