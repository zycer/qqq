#!/usr/bin/env python3
import logging

from qcaudit.app import Application
from qcaudit.domain.calendar.calendar import Calendar
from qcaudit.domain.repobase import RepositoryBase


class CalendarRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = Calendar

    def getList(self, session, start, end):
        calendar = []
        for row in session.query(self.model).filter(self.model.date >= start).filter(self.model.date <= end).all():
            calendar.append(row)
        return calendar

    def upsert(self, session, data):
        for item in data:
            date = item.get('date')
            isWorkday = item.get('isWorkday')
            row = session.query(self.model).filter(self.model.date == date).first()
            if row:
                row.isWorkday = isWorkday
            else:
                session.add(self.model(date=date, isWorkday=isWorkday))
        session.commit()

