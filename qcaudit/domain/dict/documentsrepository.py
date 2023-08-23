#!/usr/bin/env python3
"""
文书对照关系
"""
from qcaudit.app import Application
from qcaudit.domain.dict.documents import Documents
from qcaudit.domain.repobase import RepositoryBase


class DocumentsRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = Documents.getModel(app)

    def getList(self, session):
        documents = []
        for row in session.query(self.model):
            documents.append(Documents(row))
        return documents

    def getDistinctStandardName(self, session):
        names = []
        for row in session.query(self.model.standard_name).group_by(self.model.standard_name):
            names.append(row.standard_name)
        return names

    def get(self, session, name):
        row = session.query(self.model).filter_by(name=name.strip()).first()
        if row:
            return Documents(row)
        else:
            return None

    def getByStandardName(self, session, nameList):
        documents = []
        for row in session.query(self.model).filter(self.model.standard_name.in_(nameList)).all():
            documents.append(Documents(row))
        return documents

    def getByName(self, session, names):
        documents = []
        names = [name.strip() for name in names]
        for row in session.query(self.model).filter(self.model.name.in_(names)).all():
            documents.append(Documents(row))
        return documents
