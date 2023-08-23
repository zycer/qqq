#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.dict.disease import Disease
from qcaudit.domain.repobase import RepositoryBase


class DiseaseRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = Disease.getModel(app)

    def getList(self, session, sug=''):
        data = []
        query = session.query(self.model)
        if sug:
            query = query.filter(self.model.name.like('%%%s%%' % sug))
        for row in query:
            data.append(Disease(row))
        return data
