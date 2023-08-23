#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.dict.diagnosis import Diagnosis
from qcaudit.domain.repobase import RepositoryBase
from sqlalchemy import or_


class DiagnosisRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = Diagnosis.getModel(app)

    def getList(self, session, sug=''):
        data = []
        query = session.query(self.model)
        if sug:
            query = query.filter(or_(self.model.name.like('%%%s%%' % sug), self.model.initials.like('%%%s%%' % sug.lower())))
        if not sug:
            query = query.limit(50)
        for row in query:
            data.append(Diagnosis(row))
        return data
