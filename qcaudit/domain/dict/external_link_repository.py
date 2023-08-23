#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.domainbase import DomainBase
from qcaudit.domain.repobase import RepositoryBase


class ExternalLink(DomainBase):

    TABLE_NAME = 'external_link'


class ExternalLinkRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = ExternalLink.getModel(app)

    def getList(self, session):
        data = []
        for row in session.query(self.model).all():
            data.append(row)
        return data
