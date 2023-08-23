# coding: utf-8
"""
qcetl 相关的表结构

"""
from sqlalchemy import Column, DateTime, JSON, String, TIMESTAMP, Text
from sqlalchemy.dialects.mysql import INTEGER, LONGTEXT

from sqlalchemylib.sqlalchemylib.connection import Base


class Dbinfo(Base):
    __tablename__ = 'dbinfo'

    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    url = Column(String(255))


class EtlConfig(Base):
    __tablename__ = 'etl_config'

    name = Column(String(255), primary_key=True, nullable=False)
    key = Column(String(255))
    dbid = Column(String(255), primary_key=True, nullable=False)
    sql = Column(Text)
    type = Column(String(64))
    caseId = Column(String(255))
    is_system = Column(Text)
    rule = Column(LONGTEXT)


class MessageHistory(Base):
    __tablename__ = 'message_history'

    id = Column(INTEGER(11), primary_key=True)
    type = Column(String(255))
    patientId = Column(String(255))
    caseId = Column(String(255), index=True)
    created_at = Column(DateTime)
    success = Column(INTEGER(11))
    body = Column(JSON)


class SyncTime(Base):
    __tablename__ = 'syncTime'

    lastSyncTime = Column(DateTime)
    id = Column(INTEGER(11), primary_key=True)


class SyncError(Base):
    __tablename__ = 'sync_error'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255))
    message = Column(String(255))
    created_at = Column(TIMESTAMP)
