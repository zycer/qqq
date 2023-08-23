# coding: utf-8
"""
专家质控项目相关的表结构
"""

from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import INTEGER

from sqlalchemylib.sqlalchemylib.connection import Base


class ExpertDept(Base):
    __tablename__ = 'expertDept'

    id = Column(INTEGER(11), primary_key=True)
    department = Column(String(256))
    category = Column(String(256))
    departmentCode = Column(String(256))
