#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 11:57:24

'''

from typing import Any, Dict, Optional
from qcaudit.application.auditapplication import AuditApplication, DepartmentAuditApplication, HospitalAuditApplication, \
    FirstpageAuditApplication, ExpertAuditApplication, ActiveAuditApplication
from qcaudit.application.caseapplication import CaseApplication, DepartmentCaseApplication, HospitalCaseApplication, \
    FirstpageCaseApplication, ExpertCaseApplication, ActiveCaseApplication
from qcaudit.application.ruleapplication import RuleApplication

from qcaudit.application.sampleapplication import ExpertSampleApplication, DepartmentSampleApplication, HospitalSampleApplication, FirstpageSampleApplication, SampleApplication
from qcaudit.application.firstpage_application import FirstPageApplication
from qcaudit.application.diagnosis_application import DiagnosisApplication
from qcaudit.application.operation_application import OperationApplication
from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL, \
    ALL_AUDIT_TYPE, AUDIT_TYPE_ACTIVE
from qcaudit.domain import audit
from qcaudit.domain.audit.auditrecordrepository import AuditRecordRepository

from qcaudit.domain.case import CaseFactory
from qcaudit.domain.audit import AuditFactory
from qcaudit.domain.dict import DictFactory
from qcaudit.domain.problem import ProblemFactory
from qcaudit.domain.sample import SampleFactory
from qcaudit.domain.user import UserFactory
from qcaudit.domain.message import MessageFactory


class Context(object):
    """Repository/application/DomainService的工厂类, 所有实例都在这里创建, 当医院需要定制时只要继承此类修改初始化的工厂函数
    """

    def __init__(self, app):
        self.app = app
        self._auditApps = {}
        self._caseApps = {}
        self._sampleApps = {}
        self._messageApps = {}
        # 由于初始化有先后顺序, 为保证在各个类的构造函数中引用context不会出错, 需要遵守一下原则
        # 1. 按照 repository/DomainService/Application的顺序去初始化
        # 2. 同类之间相互不会引用(repository不会引用其他repository, domainservice不会引用其他domainservice, application不会引用其他application), 必须引用请通过函数方式获取, 不要在构造函数中获取
        self.initDoctorRepository()
        self.initBranchRepository()
        self.initWardRepository()
        self.initDepartmentRepository()
        self.initCaseTagRepository()
        self.initDocumentsRepository()
        self.initDiseaseRepository()
        self.initDiagnosisRepository()
        self.initOperationRepository()
        self.initQcItemRepository()
        self.initQcGroupRepository()
        self.initOrderTypeRepository()
        self.initAuditRepository()
        self.initCheckHistoryRepository()
        self.initRefuseHistoryRepository()
        self.initRefuseDetailRepository()
        self.initCaseRepository()
        self.initEmrRepository()
        self.initOrderRepository()
        self.initProblemRepository()
        self.initSampleRecordRepository()
        self.initExpertUserRepository()
        self.initUserRepository()
        self.initMessageRepository()
        self.initCalendarRepository()
        
        # domain svc
        self.initSampleServices()
    
        # application
        self.initAuditApplication()
        self.initCaseApplication()
        self.initSampleApplication()
        self.firstpage_application = FirstPageApplication(self.app)
        self.diagnosis_application = DiagnosisApplication(self.app)
        self.operation_application = OperationApplication(self.app)

    def initAuditRepository(self):
        self._auditRepos: Dict[str, AuditRecordRepository] = self.initAll(AuditFactory.getAuditRecordRepository)
    
    def initCheckHistoryRepository(self):
        self._checkHistoryRepos = self.initAll(AuditFactory.getCheckHistoryRepository)
    
    def initRefuseHistoryRepository(self):
        self._refuseHistoryRepos = self.initAll(AuditFactory.getRefuseHistoryRepository)

    def initRefuseDetailRepository(self):
        self._refuseDetailRepos = self.initAll(AuditFactory.getRefuseDetailRepository)
        
    def initCaseRepository(self):
        self._caseRepos = self.initAll(CaseFactory.getCaseRepository)
    
    def initEmrRepository(self):
        self._emrRepos = self.initAll(CaseFactory.getEmrRepository)
    
    def initOrderRepository(self):
        self._orderRepos = self.initAll(CaseFactory.getOrderRepository)
              
    def initProblemRepository(self):
        self._problemRepos = self.initAll(ProblemFactory.getProblemRespository)
    
    def initSampleRecordRepository(self):
        self._sampleRecordRepos = self.initAll(SampleFactory.getSampleRecordRepository)    
        
    def initSampleServices(self):
        self._sampleSvcs = self.initAll(SampleFactory.getSampleRecordService)
    
    def initExpertUserRepository(self):
        self._expertRepos = self.initAll(SampleFactory.getExpertUserRepository)
    
    def initUserRepository(self):
        self._userRepos = self.initAll(UserFactory.getUserRepository)

    def initBranchRepository(self):
        self._branchRepos = self.initAll(DictFactory.getBranchRepository)

    def initWardRepository(self):
        self._wardRepos = self.initAll(DictFactory.getWardRepository)

    def initDepartmentRepository(self):
        self._departmentRepos = self.initAll(DictFactory.getDepartmentRepository)

    def initCaseTagRepository(self):
        self._casetagRepos = self.initAll(DictFactory.getCaseTagRepository)

    def initDocumentsRepository(self):
        self._documentsRepos = self.initAll(DictFactory.getDocumentsRepository)

    def initDiseaseRepository(self):
        self._diseaseRepos = self.initAll(DictFactory.getDiseaseRepository)

    def initDiagnosisRepository(self):
        self._diagnosisRepos = self.initAll(DictFactory.getDiagnosisRepository)

    def initOperationRepository(self):
        self._operationRepos = self.initAll(DictFactory.getOperationRepository)

    def initQcGroupRepository(self):
        self._qcGroupRepos = self.initAll(DictFactory.getQcGroupRepository)

    def initQcItemRepository(self):
        self._qcItemRepos = self.initAll(DictFactory.getQcItemRepository)

    def initOrderTypeRepository(self):
        self._orderTypeRepos = self.initAll(DictFactory.getOrderTypeRepository)

    def initCalendarRepository(self):
        self._calendarRepos = self.initAll(DictFactory.getCalendarRepository)
    
    def initAll(self, factory) -> Dict[str, Any]:
        # TODO: 将self.app改成self, 这样所有的类内部都不需要再初始化repository等对象, 而是通过context获取
        return {
            auditType: factory(self.app, auditType)
            for auditType in ALL_AUDIT_TYPE
        }
    
    def initDoctorRepository(self):
        self._doctorRepos = self.initAll(DictFactory.getDoctorRepository)

    def initMessageRepository(self):
        self._messsageRepository = self.initAll(MessageFactory.getMessageRepository)
    
    def initAuditApplication(self):
        self._auditApps = {
            AUDIT_TYPE_DEPARTMENT: DepartmentAuditApplication(self.app),
            AUDIT_TYPE_EXPERT: ExpertAuditApplication(self.app),
            AUDIT_TYPE_FIRSTPAGE: FirstpageAuditApplication(self.app),
            AUDIT_TYPE_HOSPITAL: HospitalAuditApplication(self.app),
            AUDIT_TYPE_ACTIVE: ActiveAuditApplication(self.app),
        }
    
    def initSampleApplication(self):
        self._sampleApps = {
            AUDIT_TYPE_DEPARTMENT: DepartmentSampleApplication(self.app),
            AUDIT_TYPE_EXPERT: ExpertSampleApplication(self.app),
            AUDIT_TYPE_FIRSTPAGE: FirstpageSampleApplication(self.app),
            AUDIT_TYPE_HOSPITAL: HospitalSampleApplication(self.app)
        }
    def initCaseApplication(self):
        self._caseApps = {
            AUDIT_TYPE_DEPARTMENT: DepartmentCaseApplication(self.app),
            AUDIT_TYPE_EXPERT: ExpertCaseApplication(self.app),
            AUDIT_TYPE_FIRSTPAGE: FirstpageCaseApplication(self.app),
            AUDIT_TYPE_HOSPITAL: HospitalCaseApplication(self.app),
            AUDIT_TYPE_ACTIVE: ActiveCaseApplication(self.app),
        }

    def getCaseApplication(self, auditType) -> Optional[CaseApplication]:
        return self._caseApps.get(auditType)
    
    def getAuditApplication(self, auditType) -> Optional[AuditApplication]:
        return self._auditApps.get(auditType)

    def getSampleApplication(self, auditType) -> Optional[SampleApplication]:
        return self._sampleApps.get(auditType)

    def getRuleApplication(self):
        return RuleApplication(self.app)
    
    def getCaseRepository(self, auditType):
        return self._caseRepos[auditType]
    
    def getDoctorRepository(self, auditType):
        return self._doctorRepos[auditType]

    def getBranchRepository(self, auditType):
        return self._branchRepos[auditType]

    def getWardRepository(self, auditType):
        return self._wardRepos[auditType]

    def getDepartmentRepository(self, auditType):
        return self._departmentRepos[auditType]

    def getCaseTagRepository(self, auditType):
        return self._casetagRepos[auditType]

    def getDocumentsRepository(self, auditType):
        return self._documentsRepos[auditType]

    def getDiseaseRepository(self, auditType):
        return self._diseaseRepos[auditType]

    def getDiagnosisRepository(self, auditType):
        return self._diagnosisRepos[auditType]

    def getOperationRepository(self, auditType):
        return self._operationRepos[auditType]

    def getQcGroupRepository(self, auditType):
        return self._qcGroupRepos[auditType]

    def getQcItemRepository(self, auditType):
        return self._qcItemRepos[auditType]

    def getOrderTypeRepository(self, auditType):
        return self._orderTypeRepos[auditType]
    
    def getAuditRepository(self, auditType):
        return self._auditRepos[auditType]
    
    def getCheckHistoryRepository(self, auditType):
        return self._checkHistoryRepos[auditType]
    
    def getRefuseHistoryRepository(self, auditType):
        return self._refuseHistoryRepos[auditType]

    def getRefuseDetailRepository(self, auditType):
        return self._refuseDetailRepos[auditType]
   
    def getEmrRepository(self, auditType):
        return self._emrRepos[auditType]
    
    def getProblemRepository(self, auditType):
        return self._problemRepos[auditType]
    
    def getSampleRecordRepository(self, auditType):
        return self._sampleRecordRepos[auditType]
    
    def getExpertUserRepository(self, auditType):
        return self._expertRepos[auditType] 
    
    def getExpertRecordRepository(self, auditType):
        return self._expertRepos[auditType]
    
    def getUserRepository(self, auditType):
        return self._userRepos[auditType]

    def getOrderRepository(self, auditType):
        return self._orderRepos[auditType]
    
    def getSampleService(self, auditType):
        return self._sampleSvcs[auditType]

    def getCalendarRepository(self, auditType):
        return self._calendarRepos[auditType]
    
    def GetFirstpageApplication(self):
        return self.firstpage_application

    def GetDiagnosisApplication(self):
        return self.diagnosis_application

    def GetOperationApplication(self):
        return self.operation_application
