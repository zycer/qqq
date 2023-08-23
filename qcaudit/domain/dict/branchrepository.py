#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.dict.branch import Branch
from qcaudit.domain.repobase import RepositoryBase


class BranchRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = Branch.getModel(app)

    def getList(self, session):
        branches = []
        for row in session.query(self.model):
            branches.append(Branch(row))
        return branches
