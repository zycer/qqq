#!/usr/bin/env python
# coding=utf-8

import logging
import platform
import sys
from contextlib import contextmanager
from typing import Sequence

from alembic import autogenerate
from alembic.autogenerate import produce_migrations
from alembic.operations import MigrateOperation, Operations, ops
from alembic.operations.ops import DropIndexOp, DropTableOp, DropTableCommentOp, DropConstraintOp, ModifyTableOps, \
    DropColumnOp
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from sqlalchemy.sql.schema import MetaData
from sqlalchemy_utils import database_exists, create_database

class CharsetBase(object):
    __table_args__ = {
        "mysql_default_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }


Base = declarative_base(cls=CharsetBase)
metadata = Base.metadata

PYTHON_VERSION = platform.python_version()
is_python3 = PYTHON_VERSION.startswith('3')
if not is_python3:
    reload(sys)
    sys.setdefaultencoding('utf-8')
    import simplejson as json
else:
    import json

class Connection(object):

    def __init__(self, url, createIfNotExists=False, reflectTables=None, declareTables=None, poolSize=100,
                 autocommit=False, pool_pre_ping=True, automigrate=False, **kwargs):
        """

        Args:
            url (str): 对应的sqlalchemy url
            createIfNotExists (bool): 如果database不存在是否创建
            reflectTables (list):  要反射的数据库中已存在的表名, 指定其他项目中创建的表
            declareTables (list):  新定义的表, 指定当前项目管理的表, 需要继承本文件中定义的Base
        """
        reflectTables = reflectTables or []
        declareTables = declareTables or []
        self.url = url
        self.engine = create_engine(self.url, max_overflow=-1, pool_size=poolSize, pool_pre_ping=pool_pre_ping, **kwargs)
        if 'oracle' in self.url:
            logging.info('Ignore database check on oracle')
            self.engine.connect()
        elif createIfNotExists:
            if not database_exists(self.engine.url):
                logging.info('Database[%s] not exists, create it', url)
                create_database(self.engine.url)
                self.engine.connect()
            else:
                logging.info('Database[%s] is already existing', url)
                self.engine.connect()
        else:
            logging.info('Database[%s] is already existing', url)
            self.engine.connect()

        self._autocommit = autocommit
        self._Session = sessionmaker(bind=self.engine, autocommit=autocommit)
        self._tables = {}

        self.autoMapMetaData = MetaData()
        self.AutoMapBase = automap_base(metadata=self.autoMapMetaData)
        self.reflectTables(*reflectTables)

        for table in declareTables:
            #print(dir(table))
            if hasattr(table, '__tablename__'):
                self._tables[table.__tablename__] = table
            else:
                self._tables[table.name] = table

        if declareTables and automigrate:
            self.migrateTable(declareTables)
    
    def reflectTables(self, *tables):
        if not tables:
            return
        self.autoMapMetaData.reflect(self.engine, only=tables, views=True)
        self.AutoMapBase.prepare()
        for table_name in tables:
            try:
                tcls = getattr(self.AutoMapBase.classes, table_name)
                self._tables[table_name] = tcls
            except AttributeError:
                if self.autoMapMetaData.tables and table_name in self.autoMapMetaData.tables:
                    self._tables[table_name] = self.autoMapMetaData.tables[table_name]
                else:
                    logging.error('table %s not found', table_name)
        
    def __getitem__(self, tablename):
        """获得table对应的表
        """
        return self._tables[tablename]

    @contextmanager
    def session(self, autocommit=False):
        """
            单纯读的查询可以将autocommit设置为True, 以减少锁表的概率
        """
        # session = self._Session()
        Session = sessionmaker(bind=self.engine, autocommit=autocommit or self._autocommit)
        session = Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def createTable(self):
        """创建所有表
        """
        metadata.create_all(self.engine)

    def dropTable(self):
        metadata.drop_all(self.engine)

    def execute(self, sql, **kwargs):
        """执行sql语句"""
        if kwargs:
            sql = text(sql)
            rs = self.engine.execute(sql, **kwargs)
        else:
            rs = self.engine.execute(sql)
        return rs

    def iterResult(self, sql, lowerCase=True, **kwargs):
        """执行sql并将结果返回, 返回的结果是dict

        Args:
            sql (str): 可以是包含:param的格式, 但这种情况下必须提供kwargs. 如果不提供kwargs, 则当做普通sql执行

        Yields:
            dict: 每一行数据, 返回字典
        """
        rs = self.execute(sql, **kwargs)
        for row in rs:
            yield {
                column.lower() if lowerCase else column: value
                for column, value in row.items()
            }

    def first(self, sql, lowerCase=True, **kwargs):
        """执行sql并返回第一条结果, 如果没有结果则返回None
        Args:
            sql (str): 可以是包含:param的格式, 但这种情况下必须提供kwargs. 如果不提供kwargs, 则当做普通sql执行

        Returns:
            dict: 每一行数据, 返回字典
        """
        for item in self.iterResult(sql, lowerCase=lowerCase, **kwargs):
            return item
        return None

    def migrateTable(self, tables):
        """
        对比数据库连接和Base.metadata，自动生成迁移脚本 MigrationScript
        执行创建和修改的迁移操作
        """
        table_names = [table.__tablename__ if hasattr(table, '__tablename__') else table.name for table in tables]

        def include_object(object, name, type_, reflected, compare_to):
            """alembic 检测条件，只检测本项目涉及到的数据库表"""
            if type_ == "table" and object.name not in table_names:
                return False
            else:
                return True

        migration = produce_migrations(MigrationContext.configure(self.engine.connect(), opts={
            'compare_type': True,
            'compare_server_default': True,
            'include_object': include_object,
        }), Base.metadata)

        self._upgrade(self._getSafeUpgradeOps(migration.upgrade_ops.ops))

    def _getSafeUpgradeOps(self, upgrade_ops: Sequence[MigrateOperation] = ()):
        """判断操作的类型，去除 remove 操作，保留 add create alter
        """
        safe_operations = []
        for op in upgrade_ops:
            if hasattr(op, "ops"):
                safe_operations.extend(self._getSafeUpgradeOps(op.ops))
            elif not isinstance(op, (DropIndexOp, DropTableOp, DropColumnOp, DropTableCommentOp, DropConstraintOp)):
                safe_operations.append(op)
        return safe_operations

    def _upgrade(self, upgrade_ops):
        """执行数据库迁移操作
        invoke every migration_operation in operation_container
        参考 https://alembic.sqlalchemy.org/en/latest/cookbook.html#run-alembic-operation-objects-directly-as-in-from-autogenerate
        """
        if not isinstance(upgrade_ops, list):
            logging.info("operations is not list")
            return

        # 打印日志
        logging.info("QC Migration Operations:\n %s" % autogenerate.render_python_code(ops.UpgradeOps(ops=upgrade_ops)))

        stack = list(upgrade_ops)
        operations = Operations(MigrationContext.configure(self.engine.connect()))
        while stack:
            op_c = stack.pop(0)
            try:
                if isinstance(op_c, ModifyTableOps):
                    with operations.batch_alter_table(op_c.table_name, schema=op_c.schema) as batch_ops:
                        for mo in op_c.ops:
                            if hasattr(mo, "column"):
                                mo.column = mo.column.copy()
                            batch_ops.invoke(mo)
                elif hasattr(op_c, "ops"):
                    stack.extend(op_c.ops)
                else:
                    if hasattr(op_c, "column"):
                        op_c.column = op_c.column.copy()
                    operations.invoke(op_c)
            except Exception as e:
                logging.info("migration error occurred, operation: %s, err: %s" % (op_c, e))

    def getUrl(self, drivername=None, username=None, password=None, host=None, port=None, database=None):
        """获取一个新的url, 可以同时替换一些参数
        """
        url = make_url(self.url)
        if drivername:
            url.drivername = drivername
        if username:
            url.username = username
        if password:
            url.password = password
        if host:
            url.host = host
        if port:
            url.port = port
        if database:
            url.database = database
        return str(url) 

