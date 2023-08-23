#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-18 09:43:27

'''
from qcaudit.domain.calendar.calendar_repository import CalendarRepository
from qcaudit.domain.dict.branchrepository import BranchRepository
from qcaudit.domain.dict.casetagrepository import CaseTagRepository
from qcaudit.domain.dict.departmentrepository import DepartmentRepository
from qcaudit.domain.dict.diagnosis_repository import DiagnosisRepository
from qcaudit.domain.dict.disease_repository import DiseaseRepository
from qcaudit.domain.dict.doctorrepository import DoctorRepository
from qcaudit.domain.dict.documentsrepository import DocumentsRepository
from qcaudit.domain.dict.operation_repository import OperationRepository
from qcaudit.domain.dict.ordertyperepository import OrderTypeRepository
from qcaudit.domain.dict.wardrepository import WardRepository
from qcaudit.domain.qcgroup.qcgrouprepository import QcGroupRepository
from qcaudit.domain.qcgroup.qcitem_repository import QcItemRepository


class DictFactory(object):
    
    @classmethod
    def getDoctorRepository(cls, context, auditType) -> DoctorRepository:
        return DoctorRepository(context, auditType)

    @classmethod
    def getBranchRepository(cls, context, auditType) -> BranchRepository:
        return BranchRepository(context, auditType)

    @classmethod
    def getWardRepository(cls, context, auditType) -> WardRepository:
        return WardRepository(context, auditType)

    @classmethod
    def getDepartmentRepository(cls, context, auditType) -> DepartmentRepository:
        return DepartmentRepository(context, auditType)

    @classmethod
    def getCaseTagRepository(cls, context, auditType) -> CaseTagRepository:
        return CaseTagRepository(context, auditType)

    @classmethod
    def getDocumentsRepository(cls, context, auditType) -> DocumentsRepository:
        return DocumentsRepository(context, auditType)

    @classmethod
    def getDiseaseRepository(cls, context, auditType) -> DiseaseRepository:
        return DiseaseRepository(context, auditType)

    @classmethod
    def getDiagnosisRepository(cls, context, auditType) -> DiagnosisRepository:
        return DiagnosisRepository(context, auditType)

    @classmethod
    def getOperationRepository(cls, context, auditType) -> OperationRepository:
        return OperationRepository(context, auditType)

    @classmethod
    def getQcGroupRepository(cls, context, auditType) -> QcGroupRepository:
        return QcGroupRepository(context, auditType)

    @classmethod
    def getQcItemRepository(cls, context, auditType) -> QcItemRepository:
        return QcItemRepository(context, auditType)

    @classmethod
    def getOrderTypeRepository(cls, context, auditType) -> OrderTypeRepository:
        return OrderTypeRepository(context, auditType)

    @classmethod
    def getCalendarRepository(cls, context, auditType) -> CalendarRepository:
        return CalendarRepository(context, auditType)

