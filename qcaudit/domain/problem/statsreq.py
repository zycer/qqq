#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import List

import arrow
from sqlalchemy import or_

from qcaudit.common.const import AUDIT_TYPE_HOSPITAL, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_EXPERT, AUDIT_TYPE_DEPARTMENT, \
    AUDIT_TYPE_ACTIVE
from qcaudit.domain.req import ListRequestBase


@dataclass
class GetProblemStatsRequest(ListRequestBase):
    branch: str = ''
    ward: str = ''
    department: str = ''
    attending: str = ''
    startTime: str = ''
    endTime: str = ''
    caseType: str = ''  # 病历类型，用在有抽查的环节 可选值：running：运行中，archived：归档，Final:终末
    deptType: str = ''

    emrName: str = ''  # 用质控点的报错文书，其实更准确的是问题绑定的文书对应的标准文书名称，关联表太多
    category: int = 0
    problem: str = ''  # 模糊查询
    qcItemsId: List[int] = field(default_factory=list)
    itemType: int = 0  # 1=通用质控点，2=专科，3=专病

    auditType: str = ''
    problemType: int = 0  # 问题类型 0=全部，1=ai，2=人工
    withTotal: bool = False

    # 权限字段
    pField: str = ""
    # 权限字段筛选列表
    pList: List[str] = field(default_factory=list)

    # 问题状态，现存=1，已解决=2
    fixed: int = 0

    def getDischargeEndTime(self):
        """出院截止时间是日期的, 补充时间部分
        """
        if self.endTime:
            if len(self.endTime) <= 10:
                return f'{self.endTime} 23:59:59'
            else:
                return self.endTime
        return None

    def applyFilter(self, query, connection):
        problemModel = connection['caseProblem']
        caseModel = connection['case']
        qcItemModel = connection['qcItem']

        query = query.filter(problemModel.is_deleted == 0)

        if self.branch:
            query = query.filter(
                caseModel.branch == self.branch
            )
        if self.ward:
            query = query.filter(
                caseModel.wardName == self.ward
            )

        if self.department:
            if self.caseType == "running" or self.auditType == AUDIT_TYPE_ACTIVE:
                query = query.filter(
                    caseModel.department == self.department
                )
            else:
                query = query.filter(
                    caseModel.outDeptName == self.department
                )

        # 根据用户数据权限过滤科室或者病区
        field_dict = {'dept': 'outDeptName', 'ward': 'wardName'}
        if self.pField and self.pField in field_dict:
            _field = field_dict.get(self.pField, None)
            if _field:
                query = query.filter(getattr(caseModel, _field).in_(self.pList))

        if self.attending:
            query = query.filter(
                caseModel.attendDoctor == self.attending
            )

        if self.caseType == "running" or self.auditType == AUDIT_TYPE_ACTIVE:
            query = self.applyDateRangeFilter(
                query,
                field='admitTime',
                start=self.startTime,
                end=self.getDischargeEndTime(),
                model=caseModel
            )
        else:
            query = self.applyDateRangeFilter(
                query,
                field='dischargeTime',
                start=self.startTime,
                end=self.getDischargeEndTime(),
                model=caseModel
            )
        # 质控点过滤
        if self.emrName:
            query = query.filter(qcItemModel.standard_emr == self.emrName)
        if self.qcItemsId:
            query = query.filter(qcItemModel.id.in_(self.qcItemsId))
        if self.category:
            query = query.filter(qcItemModel.category == self.category)
        if self.problem:
            query = self.applyLikeFilter(query, 'requirement', self.problem, qcItemModel)
        if self.itemType:
            query = query.filter(qcItemModel.type == self.itemType)

        # 问题过滤
        if self.problemType:
            if self.problemType == 1:
                query = query.filter(or_(problemModel.from_ai == 1, problemModel.from_ai == 2))
            elif self.problemType == 2:
                query = query.filter(problemModel.from_ai == 0)
        if self.auditType:
            if self.auditType == 'final':
                # 事后问题统计 auditType in ('hospital','department','firstpage','expert') 效率低于 auditType <> 'active'
                query = query.filter(problemModel.auditType != AUDIT_TYPE_ACTIVE)
            else:
                query = query.filter(problemModel.auditType == self.auditType)
        return query

    def getFilterSql(self):
        # 时间范围
        if self.caseType == "running" or self.auditType == AUDIT_TYPE_ACTIVE:
            where = f" `case`.admitTime between '{self.startTime}' and '{self.getDischargeEndTime()}'"
        else:
            where = f" `case`.dischargeTime between '{self.startTime}' and '{self.getDischargeEndTime()}'"

        # 院区过滤
        if self.branch:
            where += f" and `case`.branch = '{self.branch}'"
        # 病区过滤
        if self.ward:
            where += f" and `case`.wardName = '{self.ward}'"

        # 科室过滤
        dept_field = "outDeptName"
        if self.caseType == "running" or self.auditType == AUDIT_TYPE_ACTIVE:
            dept_field = "department"
        if self.department:
            where += f" and `case`.{dept_field} = '{self.department}'"

        # 根据用户数据权限过滤科室或者病区
        if self.pField and self.pField == "dept":
            tmp = ["'%s'" % dept for dept in self.pList]
            where += f" and `case`.{dept_field} in ({','.join(tmp)})"
        if self.pField and self.pField == "ward":
            tmp = ["'%s'" % dept for dept in self.pList]
            where += f" and `case`.wardName in ({','.join(tmp)})"

        # 责任医生
        if self.attending:
            where += f" and `case`.attendDoctor = '{self.attending}'"

        # 质控点过滤
        if self.emrName:
            where += f" and qcItem.standard_emr = '{self.emrName}'"
        if self.qcItemsId:
            where += f" and qcItem.id in ({','.join([str(item) for item in self.qcItemsId])})"
        if self.category:
            where += f" and qcItem.category = '{self.category}'"
        if self.problem:
            where += f" and qcItem.requirement like '%{self.problem}%'"
        if self.itemType:
            where += f" and qcItem.type = '{self.itemType}'"

        # 问题过滤
        if self.problemType:
            if self.problemType == 1:
                where += f" and caseProblem.from_ai > 0"
            elif self.problemType == 2:
                where += f" and caseProblem.from_ai = 0"
        if self.auditType:
            if self.auditType == 'final':
                # 事后问题统计 auditType in ('hospital','department','firstpage','expert') 效率低于 auditType <> 'active'
                where += f" and caseProblem.auditType <> 'active'"
            else:
                where += f" and caseProblem.auditType = '{self.auditType}'"
        return where
