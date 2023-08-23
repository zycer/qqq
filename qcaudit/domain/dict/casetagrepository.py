#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.dict.casetag import CaseTag
from qcaudit.domain.repobase import RepositoryBase


class CaseTagRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = CaseTag.getModel(app)

    def getList(self, session, input=""):
        tags = []
        query = session.query(self.model).filter(self.model.is_deleted == 0)
        if input:
            query = query.filter(self.model.name.like('%%%s%%' % input))
        for row in query.order_by(self.model.orderNo, self.model.id):
            tags.append(CaseTag(row))
        return tags
