#!/usr/bin/env python3
from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemylib.sqlalchemylib.connection import Base

from qcaudit.app import Application
from qcaudit.domain.repobase import RepositoryBase


class DeptStatis(Base):
    """归一科室"""
    __tablename__ = "dim_dept_statis"

    deptid = Column(String(50), primary_key=True)
    deptname = Column(String(300))
    statis_name = Column(String(100))
    sn = Column(INTEGER(11))
    kind = Column(String(20))


class DimDeptStatisRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = DeptStatis

    def getList(self, session, sug=''):
        data = []
        query = session.query(self.model)
        if sug:
            query = query.filter(self.model.deptname.like('%%%s%%' % sug))
        for row in query:
            data.append(row)
        return data
