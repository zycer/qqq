#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 19:31:25

'''

from dataclasses import dataclass
import enum
from typing import Dict, Optional

from qcaudit.common.const import CASE_STATUS_REFUSED
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.domainbase import DomainBase
from qcaudit.domain.sample.samplerecorditem import SampleRecordItem

@dataclass
class CaseDoctor:

    # 医生编码
    code: str
    # 医生姓名
    name: str
    # 科室名称
    department: str = ''

class CaseType(enum.Enum):
    
    # 运行病历
    ACTIVE = 0
    # 归档病历
    ARCHIVE = 1
    # 快照
    SNAPSHOT = 2
    # 终末病历
    FINAL = 3
    

class Case(DomainBase):
    """
        TODO:
        增加origin_case_id, updated_at
    """
    
    def __init__(self, model, auditRecord=None, sampleRecordItem=None, firstPage=None, activeProblemNum=0, activeScore=0,
                 activeProblemAllNum=0, activeQcNum=0, active_record=None, activeAllProblemNum=0, activeAllScore=0, 
                 activeProblemNoFixNum=0, audit_record=None, fp_info=None):
        """

        Args:
            model ([type]): [description]
            auditRecord ([type], optional): 对应的审核记录. Defaults to None.
            sampleRecordItem ([type], optional): 对应的抽查分配信息. Defaults to None.
            firstPage ([type], optional): 对应的首页信息. Defaults to None.
            activeProblemNum: 事中质控人工问题现存数
            activeScore: 事中质控人工问题现存扣分总数
            activeProblemAllNum: 事中质控人工问题总数
            activeProblemNoFixNum: 事中质控人工问题未整改数
            activeQcNum: 事中质控保存次数
            active_record: 事中质控记录
            activeAllProblemNum: 事中质控 人工+AI 未删除、未整改、未忽略的所有问题数
            activeAllScore: 事中质控 100 - 人工+AI 未删除、未整改、未忽略的所有问题总扣分
            fp_info: 编码信息
        """
        super().__init__(model)
        self.auditRecord = auditRecord
        self.sampleRecordItem = sampleRecordItem
        self.firstPage = firstPage
        self._tags = []
        self._tagsModel = []
        self.activeProblemNum = activeProblemNum or 0
        self.activeProblemAllNum = activeProblemAllNum or 0
        self.activeQcNum = activeQcNum or 0
        self.activeScore = activeScore or 0
        self.active_record = active_record
        self.activeAllProblemNum = activeAllProblemNum or 0
        self.activeAllScore = activeAllScore or 0
        self.activeProblemNoFixNum = activeProblemNoFixNum or 0
        self.audit_record = audit_record
        self.fp_info = fp_info

    def getCaseType(self) -> CaseType:
        """获取病历类型

        Returns:
            CaseType: [description]
        """
        if self.originCaseId:
            return CaseType.SNAPSHOT
        if not self.dischargeTime:
            return CaseType.ACTIVE
        else:
            return CaseType.ARCHIVE
    
    def getAttendDoctor(self) -> Optional[CaseDoctor]:
        return CaseDoctor(
            code=self.attendCode,
            name=self.attendDoctor
        )
    
    def incRefuseCount(self):
        """增加退回次数
        """
        refuseCount = self.refuseCount + 1 if self.refuseCount else 1
        self.setModel(
                refuseCount=refuseCount
            )
    
    def refuse(self, operatorId, operatorName, refuseTime):
        """退回处理

        Args:
            operatorId ([type]): [description]
            operatorName ([type]): [description]
            refuseTime ([type]): [description]

        Returns:
            [type]: [description]
        """
        self.setModel(
                    reviewer=operatorName,
                    reviewerId=operatorId,
                    reviewTime=refuseTime,
                    refuseCount=(self.refuseCount or 0) + 1,
                    status=CASE_STATUS_REFUSED
                )

    
    @property
    def Tags(self):
        return self._tags

    @property
    def TagsModel(self):
        return self._tagsModel
    
    def convertTagToName(self, tagDict: Dict[str, str]):
        """将病历中的tag由id转换为名称

        Args:
            tagDict ([type]): [description]
        """
        self._tags = []
        if self.model.tags:
            self._tags = [
                tagDict[t] for t in self.model.tags
            ]

    def convertTagToModel(self, tagDict: Dict[str, object]):
        """将病历中的tag由id转换成caseTag对象

        Args:
            tagDict ([type]): [description]
        """
        self._tagsModel = []
        if self.model.tags:
            self._tagsModel = [
                tagDict[t] for t in self.model.tags if tagDict.get(t)
            ]
    
    def expunge(self, session):
        self.expungeInstance(
            session, self.model, self.auditRecord, self.sampleRecordItem, self.firstPage, 
            self.active_record, self.audit_record, self.fp_info
        )

    @property
    def DepartmentAuditStatus(self):
        """科室质控状态"""
        if self.auditRecord:
            return self.auditRecord.statusOfDepartment
        else:
            return None
    
    @property
    def HospitalAuditStatus(self):
        """全院质控状态"""
        if self.auditRecord:
            return self.auditRecord.statusOfHospital
        else:
            return None

    @property
    def ExpertAuditStatus(self):
        """专家质控状态"""
        if self.auditRecord:
            return self.auditRecord.statusOfExpert
        else:
            return None
    
    @property
    def FirstpageAuditStatus(self):
        """首页质控状态"""
        if self.auditRecord:
            return self.auditRecord.statusOfFirstpage
        else:
            return None

    def isSnapshot(self) -> bool:
        """当前病历是不是一个快照

        Returns:
            bool: [description]
        """
        return self.model.orgin_case_id is not None and self.model.origin_case_id != self.model.caseId

    def increaseRefuseCount(self):
        """增加驳回次数
        """
        self.model.refuseCount = self.model.refuseCount + 1
    
    def decreaseRefuseCount(self):
        """减少驳回次数
        """
        if self.model.refuseCount > 0:
            self.model.refuseCount = self.model.refuseCount - 1
    
    def getStatus(self, auditType):
        audit = AuditRecord(self.auditRecord)
        if audit:
            return audit.getStatus(auditType)
        return 0

    def setStatus(self, status):
        self.model.status = status
