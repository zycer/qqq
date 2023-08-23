#!/usr/bin/env python3

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Date, String, INTEGER

Base = declarative_base()


class Calendar(Base):

    __tablename__ = 'calendar'

    id = Column(INTEGER, primary_key=True)
    date = Column(Date)
    isWorkday = Column(INTEGER)
    comment = Column(String)
