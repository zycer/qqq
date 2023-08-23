#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 23:07:19

'''

import logging
from typing import Optional
from qcaudit.domain.case.case import Case, CaseDoctor
from qcaudit.domain.domainbase import DomainBase
from datetime import datetime
from qcaudit.domain.case.emr import EmrDocument


class Problem(DomainBase):

    TABLE_NAME = 'caseProblem'

    def __init__(self, model, qcItemModel=None, emrInfoModel=None):
        super().__init__(model)
        self.qcItemModel = qcItemModel
        self.emrInfoModel = emrInfoModel
    
    @property
    def EmrInfo(self) -> Optional[EmrDocument]:
        if not self.emrInfoModel:
            return None
        return EmrDocument(self.emrInfoModel)
    
    def expunge(self, session):
        self.expungeInstance(session, self.model, self.qcItemModel, self.emrInfoModel)
    
    def fromAi(self):
        """是否来自ai
        """
        return True if self.model.from_ai == 1 or self.model.from_ai == 2 else False

    def isFix(self):
        """
        是否整改完成
        :return:
        """
        return True if self.model.is_fix == 1 else False

    def deduct(self, session, id, deductFlag, operatorId, operatorName):
        """设置问题是否扣分

        Args:
            session ([type]): [description]
            id ([type]): [description]
            deductFlag ([type]): [description]
            operatorId ([type]): [description]
            operatorName ([type]): [description]
        """
        raise NotImplementedError()
    
    def refuse(self, refuseTime: datetime):
        """问题退回处理

        Args:
            refuseTime (datetime): [description]
            doc (EmrDocument, optional): [description]. Defaults to None.
        """
        self.setModel(
            refuseFlag=1,
            refuseTime=refuseTime.strftime('%Y-%m-%d %H:%M:%S'),
            refuseCount=(self.refuseCount if self.refuseCount else 0) + 1
        )

    def addRefuse(self, refuseTime, doctor):
        """
        问题追加退回处理
        :param refuseTime:
        :param doctor:
        :return:
        """
        self.setModel(
            refuseFlag=1,
            refuseTime=refuseTime.strftime('%Y-%m-%d %H:%M:%S'),
            refuseCount=(self.refuseCount if self.refuseCount else 0) + 1,
            status=1,
            doctorCode=doctor,
        )
    
    def cancelRefuse(self):
        """撤销退回

        Returns:
            [type]: [description]
        """
        if self.refuseFlag != 1:
            logging.error(f'problem {self.id} is not refused')
            return 
        self.setModel(
            refuseFlag=0,
            refuseCount=int(self.refuseCount - 1)
        )
        
    @property
    def Doctor(self) -> CaseDoctor:
        return CaseDoctor(
            code=self.model.doctorCode,
            name=''
        )

    def getQcItemId(self):
        return self.model.qcItemId

    def getDeductFlag(self):
        return self.model.deduct_flag

    def setDeductFlag(self, deduct_flag):
        self.model.deduct_flag = deduct_flag

    def getScore(self):
        if not self.model.deduct_flag:
            return 0
        if self.model.problem_count > 1:
            return self.model.problem_count * float(self.model.score)
        return self.model.score or 0

    def setTitle(self, title):
        self.model.title = title

    def getReason(self):
        return self.model.reason

    def getDocId(self):
        return self.model.docId or ""

    def getSingleScore(self):
        return float(self.model.score) or 0

    def getProblemCount(self):
        return self.model.problem_count or 0

    def getCreateTime(self):
        if not self.model.created_at:
            return ""
        return self.model.created_at.strftime('%Y-%m-%d %H:%M:%S')

    def getOperatorName(self):
        return self.model.operator_name or ""

    def validate(self) -> bool:
        if not isinstance(self.model.qcItemId, int):
            return False
        if self.model.qcItemId <= 0:
            return False
        if not self.model.caseId:
            return False
        if not self.model.docId:
            return False
        if not self.model.auditType:
            return False
        if not self.model.reason:
            return False
        return True

    def getTags(self):
        """问题标签
        """
        tags = []
        if self.fromAi():
            tags.append('AI')
        else:
            tags.append('人工')
        if self.isFix():
            tags.append("整改完成")
        return tags

    def checkProblemStatus(self):
        # 检查问题状态 质控问题返回1 质控提示返回0
        if not self.qcItemModel:
            return 1
        elif self.qcItemModel.enableType != 1 and not self.model.status:
            return 0
        else:
            return 1

class ProblemSumTags:
    def __init__(self):
        self.tags = {
            "AI": {"name": "AI", "index": 1},
            "人工": {"name": "人工", "index": 2},
            "否决": {"name": "单项否决", "index": 3},
            "单病种": {"name": "单病种", "index": 4},
            "编码": {"name": "编码", "index": 5},
            "强控": {"name": "强控", "index": 6},
            "专科": {"name": "专科", "index": 7},
            "专病": {"name": "专病", "index": 8},
            "整改完成": {"name": "整改完成", "index": 9},
        }
        self.sum_tags = [{"name": "全部问题", "value": "all", "count": 0}]
        # python3.8 字典是有序的
        self.sum_tags.extend([{"name": tv.get('name'), "value": tk, "count": 0} for tk, tv in self.tags.items()])

    def add_sum_tags(self, count, tags):
        """问题输入"""
        self.sum_tags[0]['count'] += count
        for tag in tags * count:
            if self.tags.get(tag) and self.tags.get(tag).get('index'):
                self.sum_tags[self.tags[tag]['index']]['count'] += 1

    def get_sum_tags(self) -> list:
        return self.sum_tags


class ProblemRecord:

    def __init__(self, reason, qcItemId, standard_emr, category, is_deleted, auditType, cp_audit_id, c_audit_id):
        self.reason = reason
        self.qcItemId = qcItemId
        self.standard_emr = standard_emr
        self.category = category
        self.is_deleted = is_deleted
        self.auditType = auditType
        self.cp_audit_id = cp_audit_id
        self.c_audit_id = c_audit_id
