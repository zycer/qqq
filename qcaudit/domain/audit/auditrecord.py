#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 19:27:15

'''
import json
from collections import namedtuple
from datetime import datetime
from typing import List, Tuple
from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL
from qcaudit.domain.domainbase import DomainBase
from dataclasses import dataclass

import arrow

@dataclass
class AuditHistoryItem:

    # 审核通过
    ACTION_APPROVE = '质控完成'
    ACTION_CANCEL_APPROVE_END = '撤销质控完成'
    ACTION_ARCHIVED = '归档完成'  # 各个医院不同点审核通过算归档需记录

    ACTION_REFUSE = '退回返修'
    ACTION_CANCEL_REFUSE = '撤销退回'
    ACTION_RECHECK_REFUSE = '退回重新质控'

    ACTION_RECHECK_APPROVE = '审核通过'
    ACTION_CANCEL_APPROVE = '撤销审核通过'
    ACTION_ADD_REFUSE = "追加退回"

    ActionType = {
        ACTION_APPROVE: 'pass',
        ACTION_ARCHIVED: 'pass',
        ACTION_RECHECK_APPROVE: 'pass',
        ACTION_REFUSE: 'refuse',
        ACTION_RECHECK_REFUSE: 'refuse',
        ACTION_ADD_REFUSE: 'refuse',
        '申请归档': 'apply',
        '提交申请': 'apply',
        '病案签收': 'apply',
        '驳回': 'refuse',
    }

    auditId: int
    auditType: str
    action: str
    time: str = '未知'
    doctor: str = '未知'
    message: str = ''
    refuseId: int = 0  # 退回记录id refuseHistory.id

    def asDict(self):
        return {
            'action': self.action,
            'doctor': self.doctor,
            'time': self.time,
            'auditType': self.auditType,
            'refuseId': self.refuseId
        }

# 由于不同审核环节要用不同的字段来记录一些信息, 这里用来表示对应的字段
OperatorField = namedtuple(
    'OperatorField',
    [
        'reviewerNameField',  # 审核人姓名
        'reviewerIdField',    # 审核人id
        'reviewTimeField',    # 审核时间
        'statusField',        # 审核状态
        'scoreField',         # 病历评分
        'firstpageScoreField',  # 首页评分
        'problemCountField',    # 问题数量
        'refuseMessageField',   # 退回重新质控备注
        ]
    )

class AuditRecord(DomainBase):

    # 未申请, 默认状态, 抽查未抽中的始终处于此状态
    STATUS_PENDING = 5
    # 待审核
    STATUS_APPLIED = 1
    # 审核通过
    STATUS_APPROVED = 3
    # 审核不通过
    STATUS_REFUSED = 4
    # 复审通过
    STATUS_RECHECK_APPROVED = 6
    # 复审不通过, 退回给初审专家重新审核.
    STATUS_RECHECK_REFUSED = 7

    TABLE_NAME = 'audit_record'

    def __init__(self, model):
        super().__init__(model)

    @classmethod
    def getOperatorFields(cls, auditType, isFinal=False) -> OperatorField:
        """获取审核对应的审核人/审核人id/审核时间/审核状态所属字段
        Args:
            auditType : [description]
            isFinal (bool, optional): [description]. Defaults to False.
        """
        return OperatorField._make({
            AUDIT_TYPE_DEPARTMENT: {
                False: (
                    'deptReviewerName', 'deptReviewerId', 'deptReviewTime', 'deptStatus', 'deptScore', 'deptFirstpageScore', 'deptProblemCount', 'deptFinalRefuseMessage'),
                True: (
                    'deptFinalReviewerName', 'deptFinalReviewerId', 'deptFinalReviewTime', 'deptStatus', 'deptScore', 'deptFirstpageScore', 'deptProblemCount', 'deptFinalRefuseMessage')
            },
            AUDIT_TYPE_HOSPITAL: {
                False: (
                    'reviewerName', 'reviewerId', 'reviewTime', 'status', 'score', 'firstpageScore', 'problemCount', 'finalRefuseMessage'),
                True: (
                    'finalReviewerName', 'finalReviewerId', 'finalReviewTime', 'status', 'score', 'firstpageScore', 'problemCount', 'finalRefuseMessage')
            },
            AUDIT_TYPE_FIRSTPAGE: {
                False: (
                    'fpReviewerName', 'fpReviewerId', 'fpReviewTime', 'fpStatus', 'fpScore', 'fpFirstpageScore', 'fpProblemCount', 'fpFinalRefuseMessage'),
                True: (
                    'fpFinalReviewerName', 'fpFinalReviewerId', 'fpFinalReviewTime', 'fpStatus', 'fpScore', 'fpFirstpageScore', 'fpProblemCount', 'fpFinalRefuseMessage')
            },
            AUDIT_TYPE_EXPERT: {
                False: (
                    'expertReviewerName', 'expertReviewerId', 'expertReviewTime', 'expertStatus', 'expertScore', 'expertFirstpageScore', 'expertProblemCount', 'expertFinalRefuseMessage'),
                True: (
                    'expertFinalReviewerName', 'expertFinalReviewerId', 'expertFinalReviewTime', 'expertStatus', 'expertScore', 'expertFirstpageScore', 'expertProblemCount', 'expertFinalRefuseMessage')
            }
        }.get(auditType).get(isFinal, ()))

    def getStatus(self, auditType, isFinal=False) -> int:
        """审核状态

        Args:
            auditType ([type]): [description]
            isFinal (bool, optional): [description]. Defaults to False.

        Returns:
            int: [description]
        """
        field = self.getOperatorFields(auditType, isFinal)
        return getattr(self.model, field.statusField)

    def getReviewer(self, auditType, isFinal=False) -> Tuple[str, str]:
        """审核人

        Args:
            auditType ([type]): [description]
            isFinal (bool, optional): [description]. Defaults to False.

        Returns:
            Tuple[str, str]: [description]
        """
        field = self.getOperatorFields(auditType, isFinal)
        return (
            getattr(self.model, field.reviewerIdField),
            getattr(self.model, field.reviewerNameField)
        )

    def getReviewTime(self, auditType, isFinal=False) -> datetime:
        """审核时间

        Args:
            auditType ([type]): [description]
            isFinal (bool, optional): [description]. Defaults to False.

        Returns:
            datetime: [description]
        """
        field = self.getOperatorFields(auditType, isFinal)
        return getattr(self.model, field.reviewTimeField)

    def getProblemCount(self, auditType) -> int:
        """获取问题数量
        """
        field = self.getOperatorFields(auditType)
        return getattr(self.model, field.problemCountField) or 0

    def setProblemCount(self, auditType, count):
        """设置问题数量

        Args:
            auditType ([type]): [description]
            count ([type]): [description]
        """
        field = self.getOperatorFields(auditType)
        self.setModel(
            **{field.problemCountField: count}
        )

    def getTimeline(self) -> List[AuditHistoryItem]:
        """获取审核历史
        """
        if not self.timeline:
            return []
        result = []
        for item in self.timeline:
            result.append(
                AuditHistoryItem(
                    auditId=self.id,
                    auditType=item.get('auditType', ''),
                    time=item.get('time', ''),
                    doctor=item.get('doctor', '未知'),
                    action=item.get('action', ''),
                    message=item.get('message', '')
                )
            )
        return result

    def updateStatus(self, auditType, operatorId: str, operatorName: str, status: int, isFinal=False):
        """更新状态

        Args:
            auditType ([type]): [description]
            operatorId (str): [description]
            operatorName (str): [description]
        """
        field = self.getOperatorFields(auditType, isFinal)
        self.setModel(
            **{
                field.statusField: status,
                field.reviewerIdField: operatorId,
                field.reviewerNameField: operatorName,
                field.reviewTimeField: arrow.utcnow().to('+08:00').naive
            }
        )

    def approve(self, auditType, operatorId: str, operatorName: str, archiveFlag: bool = False, completeAuditType=None):
        """审核通过
        Args:
            auditType ([type]): 审核类型
            operatorId ([str]):
            operatorName ([str]):
            archiveFlag ([bool]):
            completeAuditType ([str]): 质控完成节点
        """
        self.updateStatus(auditType, operatorId, operatorName, self.STATUS_APPROVED)
        action = AuditHistoryItem.ACTION_APPROVE if not archiveFlag else AuditHistoryItem.ACTION_ARCHIVED
        self.appendTimeline(auditType, action=action, doctor=operatorName)
        isComplete = False
        for complete in completeAuditType.split(","):
            # 配置质控完成节点, 可能存在多个, 当所有节点的状态都是3时, 更新质控完成标记为1
            if int(self.getStatus(complete) or 0) == self.STATUS_APPROVED:
                isComplete = True
            else:
                isComplete = False
        if isComplete:
            self.setModel(**{"qcCompleteFlag": 1})

    def refuse(self, auditType, operatorId: str, operatorName: str, atTime: str = None, refuseId: int = 0):
        """审核不通过
        """
        self.updateStatus(auditType, operatorId, operatorName, self.STATUS_REFUSED)
        self.appendTimeline(auditType, action=AuditHistoryItem.ACTION_REFUSE, doctor=operatorName,
                            actionTime=atTime, refuseId=refuseId)

    def cancelApprove(self, auditType, operatorId: str, operatorName: str):
        """取消审核通过

        Args:
            auditType (str): [description]
            operatorId (str): [description]
            operatorName (str): [description]
        """
        self.updateStatus(auditType, operatorId, operatorName, self.STATUS_APPROVED)
        self.appendTimeline(auditType, action=AuditHistoryItem.ACTION_CANCEL_APPROVE, doctor=operatorName)

    def cancelAudit(self, auditType, operatorId: str, operatorName: str):
        """取消质控完成

        Args:
            auditType (str): [description]
            operatorId (str): [description]
            operatorName (str): [description]
        """
        self.updateStatus(auditType, operatorId, operatorName, self.STATUS_APPLIED)
        self.appendTimeline(auditType, action=AuditHistoryItem.ACTION_CANCEL_APPROVE_END, doctor=operatorName)

    def cancelRefuse(self, auditType, operatorId: str, operatorName: str, isFinal=False):
        """取消审核不通过

        Args:
            caseId (str): [description]
            operatorId (str): [description]
            operatorName (str): [description]
        """
        if isFinal:
            self.updateStatus(auditType, operatorId, operatorName, self.STATUS_APPROVED)
        else:
            self.updateStatus(auditType, operatorId, operatorName, self.STATUS_APPLIED)
        self.appendTimeline(auditType, action=AuditHistoryItem.ACTION_CANCEL_REFUSE, doctor=operatorName)
        self.resetAuditQcCompleteFlag()
        self.resetUrgeFlag()

    def resetAuditQcCompleteFlag(self):
        """
        重置质控完成标记
        :return:
        """
        self.setModel(**{"qcCompleteFlag": 0})

    def recheckApprove(self, auditType, operatorId: str, operatorName: str):
        """复审通过

        Args:
            auditType ([type]): [description]
            operatorId (str): [description]
            operatorName (str): [description]
        """
        self.updateStatus(auditType, operatorId, operatorName, self.STATUS_RECHECK_APPROVED, isFinal=True)
        self.appendTimeline(auditType, action=AuditHistoryItem.ACTION_RECHECK_APPROVE, doctor=operatorName)

    def recheckRefuse(self, auditType, operatorId: str, operatorName: str, comment: str = ''):
        """复审不通过, 退回初审重新审核

        Args:
            auditType ([type]): [description]
            operatorId (str): [description]
            operatorName (str): [description]
            comment (str): [退回重新质控备注]
        """
        self.updateStatus(auditType, operatorId, operatorName, self.STATUS_RECHECK_REFUSED, isFinal=True)
        self.setRefuseMessage(auditType, comment)
        self.appendTimeline(auditType, action=AuditHistoryItem.ACTION_RECHECK_REFUSE, doctor=operatorName)

    def appendTimeline(self, auditType, action, doctor, actionTime=None, refuseId=None):
        """增加一条审核历史

        Args:
            actionTime (str): 操作时间
            action (str): 操作名称
            doctor (st): 操作医生姓名
        """
        timeline = list(self.model.timeline or [])
        # timeline = json.loads(self.model.timeline) or []
        timeline.append(AuditHistoryItem(
            auditId=self.model.id,
            auditType=auditType,
            action=action,
            doctor=doctor,
            time=actionTime or arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'),
            refuseId=refuseId or 0).asDict())
        self.model.timeline = timeline

    def setFistPageProblemCount(self, count):
        """设置首页问题数

        Args:
            count ([type]): [description]
        """
        self.model.first_problem_count = count

    def setFirstPageRequiredCount(self, count):
        """设置首页必填项问题数

        Args:
            count ([type]): [description]
        """
        self.model.required_problem_count = count

    def setFirstPageOptionalCount(self, count):
        """设置首页非必填项问题数

        Args:
            count ([type]): [description]
        """
        self.model.optional_problem_count = count

    def setScore(self, auditType, score, isFinal=False):
        """设置评分, 四个环节有4个不同的评分"""
        field = self.getOperatorFields(auditType)
        print(f'set score {field.scoreField} = {score}')
        self.setModel(
            **{field.scoreField: score}
        )
        if isFinal:
            self.setModel(
                **{'archiveScore': score}
            )

    def getScore(self, auditType):
        """获取病历评分"""
        field = self.getOperatorFields(auditType)
        return getattr(self.model, field.scoreField)

    def setFirstpageScore(self, auditType, score):
        """设置首页评分, 四个环节有4个不同的评分"""
        field = self.getOperatorFields(auditType)
        self.setModel(
            **{field.firstpageScoreField: score}
        )

    def getArchiveScore(self):
        if self.model:
            return self.model.archiveScore or 0
        return 0

    def setArchiveScore(self, score):
        self.model.archiveScore = score

    def getArchiveFPScore(self):
        if self.model:
            return self.model.archiveFirstpageScore or 100
        return 0

    def setArchiveFPScore(self, score):
        self.model.archiveFirstpageScore = score

    def getFirstPageScore(self, auditType):
        """获取首页评分

        Args:
            auditType ([type]): [description]
        """
        field = self.getOperatorFields(auditType)
        return getattr(self.model, field.firstpageScoreField) or 100

    def setRefuseMessage(self, auditType, comment):
        """设置退回重新质控备注"""
        field = self.getOperatorFields(auditType)
        self.setModel(
            **{field.refuseMessageField: comment}
        )

    def getFinalRefuseMessage(self, auditType):
        """获取退回重新质控的备注

        Args:
            auditType ([type]): [description]
        """
        field = self.getOperatorFields(auditType)
        return getattr(self.model, field.refuseMessageField)

    def setArchivedType(self, type_):
        self.model.archivedType = type_

    def isFinished(self, auditType, config):
        """质控环节是否已经完成，需要终审操作且状态等于已复审完成，或者不需要终审操作且状态等于已初审完成
        """
        status = self.getStatus(auditType)
        if status == self.STATUS_RECHECK_APPROVED and config == '1':
            return True
        if status == self.STATUS_APPROVED and config == '2':
            return True
        return False

    def isOperated(self):
        """是否发生过质控操作，在发生操作时修改对应的标记字段
        """
        if self.model.operateFlag:
            return True
        return False

    def setUrgeFlag(self):
        """催办标记
        """
        self.model.urgeFlag = 1

    def getUrgeFlag(self):
        return self.model.urgeFlag or 0

    def resetUrgeFlag(self):
        """
        重置质控完成标记
        :return:
        """
        self.model.urgeFlag = 0
