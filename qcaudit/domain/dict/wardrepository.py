#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.dict.ward import Ward
from qcaudit.domain.repobase import RepositoryBase


class WardRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = Ward.getModel(app)

    def getList(self, session, name=None, branch=None):
        wards = []
        query = session.query(self.model)
        if name:
            query = query.filter(self.model.name.like('%%%s%%' % name))
        if branch:
            query = query.filter(self.model.branch == branch)
        for row in query.order_by(self.model.sort_no):
            wards.append(Ward(row))
        return wards
