#!/usr/bin/env python3

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()
metadata = Base.metadata


class IpRule(Base):
    # ip 黑名单
    __tablename__ = 'ip_rule'

    id = Column(INTEGER(11), primary_key=True)
    ip = Column(String(255), index=True)
    rule = Column(INTEGER, default=0)  # 默认=0，1=黑名单，2=白名单
    created_at = Column(DateTime, default=datetime.now)

