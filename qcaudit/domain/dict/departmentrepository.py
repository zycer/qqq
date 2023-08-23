#!/usr/bin/env python3

from qcaudit.app import Application
from qcaudit.domain.dict.department import Department
from qcaudit.domain.repobase import RepositoryBase


class DepartmentRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = Department.getModel(app)
        self._get_internal_department()
        self._get_surgery_department()

    DEPT_TYPE_DEPARTMENT = {}

    def getList(self, session, name=None, branch=None):
        departments = []
        query = session.query(self.model)
        if name:
            query = query.filter(self.model.name.like('%%%s%%' % name))
        if branch:
            query = query.filter(self.model.branch == branch)
        for row in query:
            departments.append(Department(row))
        return departments

    def getMzList(self, session, request):
        """
        获取门诊科室
        :return:
        """
        case_model = self.app.mysqlConnection["case"]
        query = session.query(case_model.department).distinct().filter(case_model.patientType == 1)
        if request.args.get("name"):
            query = query.filter(case_model.department.like("%{}%".format(request.args.get("name"))))
        res = []
        for item in query.all():
            if item.department:
                res.append(item.department)
        return res

    def _get_internal_department(self):
        """
        查询内科全部科室
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query = session.query(self.model).filter(self.model.deptType == 1)
            self.DEPT_TYPE_DEPARTMENT[1] = [item.name for item in query]

    def _get_surgery_department(self):
        """
        查询外科全部科室
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query = session.query(self.model).filter(self.model.deptType == 2)
            self.DEPT_TYPE_DEPARTMENT[2] = [item.name for item in query]

    def add(self, session, departments):
        """增加科室 支持批量"""
        # params = ['name', 'branch', 'deptType']
        # for dp in departments:
        #     item = self.model(
        #         **{c: getattr(dp, c) for c in params}
        #     )
        #     session.add(item)
        for dp in departments:
            item = self.model(**dp)
            session.add(item)

