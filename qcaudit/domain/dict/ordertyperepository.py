#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.dict.ordertype import OrderType
from qcaudit.domain.repobase import RepositoryBase


class OrderTypeRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = OrderType.getModel(app)

    def getList(self, session):
        result = []
        for row in session.query(self.model):
            result.append(OrderType(row))
        return result
