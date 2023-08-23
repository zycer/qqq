#!/usr/bin/env python3
# coding=utf-8
'''
doris dialect,  使用方法

from sqlalchemylib.sqlalchemylib.doris import DorisDialect

DorisDialect.register()

'''

from sqlalchemy.dialects.mysql.pymysql import MySQLDialect_pymysql
from sqlalchemy.engine import reflection
from sqlalchemy.dialects.mysql.base import MySQLIdentifierPreparer
from sqlalchemy.dialects.mysql.reflection import MySQLTableDefinitionParser, ReflectedState
import re
import sqlalchemy.util as util


class DorisIdentifierPreparer(MySQLIdentifierPreparer):
    reserved_words = MySQLIdentifierPreparer.reserved_words | {'costs'}


class DorisTableDefinitionParser(MySQLTableDefinitionParser):

    def parse(self, show_create, charset):
        state = ReflectedState()
        state.charset = charset
        # print(show_create)
        for line in re.split(r"\r?\n", show_create):
            if line.startswith("  " + self.preparer.initial_quote):
                self._parse_column(line, state)
            # a regular table options line
            # elif line.startswith(") "):
            #    self._parse_table_options(line, state)
            # an ANSI-mode table options line
            elif line.startswith(")"):
                pass
            elif line.startswith("CREATE TABLE"):
                self._parse_table_name(line, state)
            # Not present in real reflection, but may be if
            # loading from a file.
            elif not line:
                pass
            elif line.startswith('CREATE') or line.startswith('COMMENT') or line.startswith('DISTRIBUTED') or (
                    line.startswith('PROPERTIES') or line.startswith('"') or line.startswith('  INDEX ')
            ):
                pass
            else:
                type_, spec = self._parse_constraints(line)
                if type_ is None:
                    util.warn("Unknown schema content: %r" % line)
                elif type_ == "key":
                    state.keys.append(spec)
                elif type_ == "fk_constraint":
                    state.fk_constraints.append(spec)
                elif type_ == "ck_constraint":
                    state.ck_constraints.append(spec)
                else:
                    pass
        return state

    def _prep_regexes(self):
        MySQLTableDefinitionParser._prep_regexes(self)
        _final = self.preparer.final_quote

        quotes = dict(
            zip(
                ("iq", "fq", "esc_fq"),
                [
                    re.escape(s)
                    for s in (
                    self.preparer.initial_quote,
                    _final,
                    self.preparer._escape_identifier(_final),
                )
                ],
            )
        )
        # (AGGREGATE|UNIQUE|DUPLICATE) INDEX `name` (USING (BTREE|HASH))?
        # (`col` (ASC|DESC)?, `col` (ASC|DESC)?)
        # KEY_BLOCK_SIZE size | WITH PARSER name  /*!50100 WITH PARSER name */
        self._re_key = re.compile(r"(?:(?P<type>\S+) )?KEY"
                                  r"(?: +%(iq)s(?P<name>(?:%(esc_fq)s|[^%(fq)s])+)%(fq)s)?"
                                  r"(?: +USING +(?P<using_pre>\S+))?"
                                  r" *\((?P<columns>.+?)\)"
                                  r"(?: +USING +(?P<using_post>\S+))?"
                                  r"(?: +KEY_BLOCK_SIZE *[ =]? *(?P<keyblock>\S+))?"
                                  r"(?: +WITH PARSER +(?P<parser>\S+))?"
                                  r"(?: +COMMENT +(?P<comment>(\x27\x27|\x27([^\x27])*?\x27)+))?"
                                  r"(?: +/\*(?P<version_sql>.+)\*/ *)?"
                                  r",?$" % quotes,
                                  re.I | re.UNICODE
                                  )
        self._re_column = self._re_column_loose


class DorisDialect(MySQLDialect_pymysql):
    name = 'doris'

    preparer = DorisIdentifierPreparer

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        parsed_state = self._parsed_state_or_create(
            connection, table_name, schema, **kw
        )
        # print(parsed_state.keys)
        for key in parsed_state.keys:
            if key["type"] == "AGGREGATE":
                # There can be only one.
                cols = [s[0] for s in key["columns"]]
                return {"constrained_columns": cols, "name": None}
        return {"constrained_columns": [], "name": None}

    @util.memoized_property
    def _tabledef_parser(self):
        """return the MySQLTableDefinitionParser, generate if needed.

        The deferred creation ensures that the dialect has
        retrieved server version information first.

        """
        preparer = self.identifier_preparer
        return DorisTableDefinitionParser(self, preparer)

    @classmethod
    def register(cls):
        from sqlalchemy.dialects import registry
        registry.register("doris.pymysql", "sqlalchemylib.dialects.doris", "DorisDialect")
