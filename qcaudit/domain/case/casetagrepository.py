#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.case.casetag import CaseTag
from qcaudit.domain.repobase import RepositoryBase


class CaseTagRepository(RepositoryBase):

    def __init__(self, app: Application):
        super().__init__(app)
        self.model = CaseTag.getModel(app)

    def getList(self, session, tag=None):
        tags = []
        handler = session.query(self.model)
        if tag:
            handler = handler.filter(self.model.name.like('%{}%'.format(tag)))
        for row in handler.order_by(self.model.orderNo, self.model.id):
            tags.append(CaseTag(row))
        return tags
