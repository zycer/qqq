# coding: utf-8
"""
公共的表，包括配置项表等
"""
from sqlalchemy import Column, DateTime, Index, JSON, String, BigInteger
from sqlalchemy.dialects.mysql import INTEGER, LONGTEXT

from sqlalchemylib.sqlalchemylib.connection import Base


class ConfigItem(Base):
    __tablename__ = 'configItem'

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(255))
    value = Column(String(1024))
    scope = Column(String(255))
    platform = Column(String(255))
    message = Column(String(255))
    name_ch = Column(String(255))
    default_value = Column(String(1024))
    type = Column(String(255))
    choice = Column(LONGTEXT)

    Index("configItem_name_uindex", name, unique=True)


class EmrParserResult(Base):
    __tablename__ = 'emrParserResult'

    id = Column(BigInteger, primary_key=True)
    caseId = Column(String(255), comment='caseId')
    docId = Column(String(255), comment='文书id')
    key = Column(String(255))
    field = Column(JSON, comment='解析字段')
    create_time = Column(DateTime, comment='创建时间')

    Index("emrParserResult_caseId_index", caseId, unique=False)
