#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-28 16:24:18

'''
from dataclasses import dataclass
from qcaudit.domain.req import ListRequestBase
import arrow
from sqlalchemy import text, func
from sqlalchemy import and_, or_
import json

@dataclass
class GetSampleRecordRequest(ListRequestBase):

    id: int = 0
    startTime: str = ''
    endTime: str = ''
    auditType: str = ''
    operatorId: str = ''
    caseType: str = ''
    sampleId: str = ''

    def applyFilter(self, query, connection):
        model = connection['sample_record']
        if self.startTime:
            startTime = arrow.get(self.startTime).naive
            query = query.filter(
                model.createdAt > startTime
            )
        if self.endTime:
            endTime = arrow.get(self.endTime).naive
            query = query.filter(
                model.createdAt < endTime
            )
        if self.id:
            query = query.filter(
                model.id == self.id
            )
        if self.auditType:
            query = query.filter(
                model.auditType == self.auditType
            )
        if self.caseType:
            query = query.filter(
                model.caseType == self.caseType
            )
        if self.operatorId:
            query = query.filter(
                model.operatorId == self.operatorId
            )
        if self.sampleId:
            query = query.filter(
                model.id == self.sampleId
            )
        query = query.filter(model.submit_flag == 1)
        return query

    def applySort(self, query, connection):
        """应用排序规则"""
        query = query.order_by(text(f'createdAt DESC'))
        return query


@dataclass
class GetSampleDetailRequest(ListRequestBase):

    sampleId: int = 0
    auditType: str = ''
    branch: str = ''
    ward: str = ''
    department: str = ''
    attending: str = ''
    caseId: str = ''
    patientId: str = ''
    tag: str = ''
    is_export: int = 0  # 是否为导出(不分页)
    isExportDetail: int = 0  # 是否为导出明细
    doctorId: str = ''
    wardDoctor: list = None
    group: str = ""  # 诊疗组
    assignDoctor: str = ""

    def applyFilter(self, query, connection):
        model = connection['sample_record_item']
        caseModel = connection['case']
        # 仅查询住院患者
        query = query.filter(caseModel.patientType == 2)
        if self.sampleId:
            query = query.filter(
                model.recordId == self.sampleId
            )
        if self.auditType:
            query = query.filter(
                model.auditType == self.auditType
            )
        if self.branch:
            query = query.filter(
                caseModel.branch == self.branch
            )
        if self.department:
            dept = self.department.split(",")
            query = query.filter(
                or_(and_(caseModel.department.in_(dept), caseModel.outDeptName == None), caseModel.outDeptName.in_(dept))
            )
        if self.attending:
            query = query.filter(
                caseModel.attendDoctor.in_(self.attending.split(","))
            )
        if self.caseId:
            query = query.filter(
                caseModel.caseId == self.caseId
            )
        if self.patientId:
            query = query.filter(or_(caseModel.patientId == self.patientId, caseModel.name.like('%' + self.patientId + '%'), caseModel.inpNo == self.patientId))
        if self.tag:
            query = query.filter(
                func.json_contains(caseModel.tags, json.dumps(self.tag)) == 1
            )
        if self.ward:
            query = query.filter(
                caseModel.wardName.in_(self.ward.split(","))
            )
        if self.group:
            query = query.filter(
                caseModel.medicalGroupName.in_(self.group.split(","))
            )
        if self.assignDoctor:
            query = query.filter(
                model.expertName == self.assignDoctor
            )
        # print(query)
        return query
