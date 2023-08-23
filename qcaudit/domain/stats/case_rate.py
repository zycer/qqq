#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: case_rate.py
@time: 2022/8/10 16:17
@desc:
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import  Column,Integer,String,DateTime, Float
Base = declarative_base()


class CaseRate(Base):

    __tablename__ = 'case_rate'

    caseid = Column(String(255), primary_key=True)
    name = Column(String(255))
    admittime = Column(DateTime)
    outdeptname = Column(String(255))
    attendDoctor = Column(String(255))
    status = Column(Integer)
    dischargetime = Column(DateTime)
    branch = Column(String(255))
    score = Column(Float)
    outhosward = Column(String(255))
    medicalgroupname = Column(String(255))
    is_standard = Column(String(255))

