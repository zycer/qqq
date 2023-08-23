#!/usr/bin/env python3

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()
metadata = Base.metadata


class DebugLog(Base):
    # debug 日志
    __tablename__ = 'doctor_debug_log'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), index=True)
    doctor = Column(String(255))
    time = Column(String(255))
    url = Column(String(255))
    method = Column(String(255))
    apiName = Column(String(255))
    apiStatus = Column(String(255))
    fileName = Column(String(255))
    content = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
