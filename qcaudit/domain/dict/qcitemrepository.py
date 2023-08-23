#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.dict.qcitem import QcItem
from qcaudit.domain.repobase import RepositoryBase


class QcItemRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = QcItem.getModel(app)

    def getList(self, session, standardName='', sug='', withUnableItems=False):
        items = []
        handler = session.query(self.model)
        if standardName:
            handler = handler.filter_by(standard_emr=standardName)
        if sug:
            handler = handler.filter(self.model.instruction.like('%' + sug + '%'))
        if not withUnableItems:
            handler = handler.filter_by(enable=2)
        for row in handler.all():
            items.append(QcItem(row))
        return items

    def add(self, session, qcItem: QcItem):
        """添加质控点
        """
        session.add(qcItem.model)
