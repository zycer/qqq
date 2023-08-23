#!/usr/bin/env python
# coding=utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from sqlalchemylib.sqlalchemylib.connection import Base, metadata, Connection
from sqlalchemylib.sqlalchemylib.util import ModelUtil
from sqlalchemy import Column, Date, DateTime, Float, Index, JSON, LargeBinary, String, TIMESTAMP, Table, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT, VARCHAR, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from sqlalchemy.sql.sqltypes import BOOLEAN, Integer

# 定义新的表

class TestTable(Base):

    __tablename__ = 'test_table'

    id = Column(INTEGER(), primary_key=True)
    caseId = Column(String(255))
    patientId = Column(String(255))
    exeTime = Column(DateTime)

# 创建连接
connection = Connection(
    url='mysql+pymysql://root:rxthinkingmysql@192.168.100.40:49138/qcmanager_v2?charset=utf8mb4', 
    createIfNotExists=True,
    # 在本连接中维护的表, 如果不存在会自动创建 
    declareTables=[TestTable],
    # 在其他服务中维护的表, 使用反射自动生成model类 
    reflectTables=['case', 'emrInfo'])

model = connection['test_table']
with connection.session() as session:
    row = session.query(model).first()
    print type(row)
    # 获得json字符串
    print ModelUtil.asJson(row)
    # 获得字典
    print ModelUtil.asDict(row)
    

# 执行sql, 并迭代结果集
for row in connection.iterResult('select * from test_table where id != :id', id='xxx'):
    print row
