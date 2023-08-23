# coding: utf-8
"""
邵逸夫医院版本的病历质控相关数据库表结构
"""

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.mysql import INTEGER

from sqlalchemylib.sqlalchemylib.connection import Base


class AuthStat(Base):
    __tablename__ = 'authStat'
    __table_args__ = {
        'comment': '常州二院接口登录token表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    lastAuthToken = Column(String(255))
    lastTokenTime = Column(DateTime)
    id = Column(INTEGER(11), primary_key=True)
