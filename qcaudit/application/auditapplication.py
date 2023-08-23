#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 17:58:18

'''
import json
import logging
import operator
from abc import ABC
from typing import Iterable, List, Optional, Tuple

import redis

from qcaudit.app import Application
from qcaudit.application.applicationbase import ApplicationBase
from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL, \
    CASE_STATUS_ARCHIVED, CASE_STATUS_APPLIED, CASE_STATUS_REFUSED, AUDIT_STEP_RECHECK, AUDIT_STEP_AUDIT, \
    SAMPLE_ARCHIVE_REDIS_LIST_KEY, AUDIT_TYPE_ACTIVE
# from qcaudit.common.exception import GrpcInvalidArgumentException
from qcaudit.common.result import CommonResult
from qcaudit.config import Config, ConfigItem
from qcaudit.domain.audit.auditrecord import AuditRecord, AuditHistoryItem
from qcaudit.domain.audit.auditrecordsvc import AuditRecordService
from qcaudit.domain.audit.checkhistoryrepository import CheckHistoryRepository
from qcaudit.domain.audit.refusedetail import RefuseDetail
from qcaudit.domain.audit.refusedetailrepository import RefuseDetailRepository
from qcaudit.domain.audit.refusehistory import RefuseHistory
from qcaudit.domain.audit.refusehistoryrepository import RefuseHistoryRepository
from qcaudit.domain.audit.req import GetCheckHistoryListRequest
from qcaudit.domain.case.case import CaseDoctor
from qcaudit.domain.case.caserepository import CaseRepository
from qcaudit.domain.case.emr import EmrDocument
from qcaudit.domain.case.emrrepository import EmrRepository
from qcaudit.domain.case.emrversion import EmrVersion
from qcaudit.domain.case.orderrepository import OrderRepository
from qcaudit.domain.audit.auditrecordrepository import AuditRecordRepository
from qcaudit.domain.case.req import GetEmrListRequest, GetCaseListRequest
from qcaudit.domain.dict import QcItemRepository, DocumentsRepository
from qcaudit.domain.dict.doctor import Doctor
from qcaudit.domain.dict.doctorrepository import DoctorRepository
from qcaudit.domain.dict.qcitem import QcItem
from qcaudit.domain.problem.deduct_detail import DeductDetail
from qcaudit.domain.problem.problemrepository import ProblemRepository
from qcaudit.domain.problem.problem import Problem
from qcaudit.domain.problem.req import GetProblemListRequest
from qcaudit.domain.qcgroup.qcgroup import QcCateItems
from qcaudit.domain.qcgroup.qcgrouprepository import QcGroupRepository
from qcaudit.domain.sample import SampleRecordRepository
from qcaudit.domain.message.message_repository import MessageRepo
from qcaudit.domain.user.user import User
# from iyoudoctor.hosp.qc.v3.emradapter.service_message_pb2 import RefuseRequest, ApproveRequest, RevokeRequest

import arrow
import requests


class AuditApplication(ApplicationBase):

    def __init__(self, app: Application, auditType: str):
        super().__init__(app, auditType)
        self._problemRepository = None
        self._auditRecordRepository = None
        self._auditSvc = None
        self._caseRepository = None
        self._emrRepository = None
        self._refuseHistoryRepository = RefuseHistoryRepository(app, auditType)
        self._refuseDetailRepository = RefuseDetailRepository(self.app, self.auditType)
        self._doctorRepository = DoctorRepository(app, auditType)
        self._qcGroupRepository = QcGroupRepository(app, auditType)
        self._qcItemRepository = QcItemRepository(app, auditType)
        self._sampleRecordRepository = SampleRecordRepository(app, auditType)
        self._documentsRepository = DocumentsRepository(app, auditType)
        self._messageRepository = MessageRepo(app, auditType)

        self.initAuditRecordRepository()
        self.initProblemRepository()
        self.initAuditSvc()
        self.initCaseRepository()
        self.initEmrRepository()

    def initEmrRepository(self):
        if not self._emrRepository:
            self._emrRepository = EmrRepository(self.app, self.auditType)

    def initCaseRepository(self):
        if not self._caseRepository:
            self._caseRepository = CaseRepository(self.app, self.auditType)

    def initAuditRecordRepository(self):
        if not self._auditRecordRepository:
            self._auditRecordRepository = AuditRecordRepository(self.app, self.auditType)

    def initProblemRepository(self):
        if not self._problemRepository:
            self._problemRepository = ProblemRepository(self.app, self.auditType)

    def initAuditSvc(self):
        self._auditSvc = AuditRecordService(self.app, self.auditType)

    def sendApproveRequestToEmr(self, caseId: str, operatorId: str, comment: str = '') -> CommonResult:
        """通知EMR审核通过, 初审和终审一样处理

        Args:
            caseId (str): [description]
            operatorId (str): [description]
            operatorName (str): [description]
            comment (str, optional): [description]. Defaults to ''.
            isFinal (bool, optional): 是否终审
        Returns:
            CommonResult: [description]
        """
        if self.app.emrAdapterUrl:
            # result = self.app.emrAdapterClient.ApproveCase(ApproveRequest(caseId=caseId, operator=operatorId))
            data = {"caseId": caseId, "operator": operatorId}
            headers = {'Content-Type': 'application/json'}
            res = requests.post(f"{self.app.emrAdapterUrl}/emr/adapter/approve", headers=headers, json=data).json()
            return CommonResult(res.get("isSuccess") or True, res.get("message") or "")
        return CommonResult(True)

    def sendCancelApproveRequestToEmr(self, caseId: str, operatorId: str, comment: str = '') -> CommonResult:
        """通知EMR撤销审核通过, 只有在撤销归档环节才应该调用

        Args:
            caseId (str): [description]
            operatorId (str): [操作医生工号]
            comment (str, optional): [description]. Defaults to ''.
        Returns:
            CommonResult: [description]
        """
        # if self.app.emrAdapterClient:
        #     result = self.app.emrAdapterClient.RevokeApproved(
        #         RevokeRequest(caseId=caseId, operator=operatorId, comment=comment))
        #     return CommonResult(result.isSuccess, result.message)
        if self.app.emrAdapterUrl:
            data = {"caseId": caseId, "operator": operatorId, "comment": comment}
            headers = {'Content-Type': 'application/json'}
            res = requests.post(f"{self.app.emrAdapterUrl}/emr/adapter/revoke/approve", headers=headers, json=data).json()
            return CommonResult(res.get("isSuccess") or True, res.get("message") or "")
        return CommonResult(True)

    def sendRefuseRequestToEmr(self, caseId: str, operatorId: str, comment: str = '', problems=[],
                               attending='') -> CommonResult:
        """通知EMR审核不通过, 并将问题传递给EMR, 初审和终审一样处理

        Args:
            caseId (str): [description]
            operatorId (str): [操作人医生工号]
            operatorName (str): [description]
            comment (str, optional): [description]. Defaults to ''.
            problems (List): [驳回问题清单, id, caseId, docId, documentName, recordTime, reason, comment, refuseDoctor]
            isFinal (bool, optional): [description]. Defaults to False.
            attending (str): [病历的责任医生，默认的驳回医生工号]

        Returns:
            CommonResult: [description]
        """
        # if (isFinal and self.app.config.get(Config.QC_REFUSE_NOTIFY_EMR_FINAL.format(auditType=self.auditType)) == '2'
        #     ) or (
        #         not isFinal and self.app.config.get(Config.QC_REFUSE_NOTIFY_EMR_FIRST.format(auditType=self.auditType)) == '2'):
        #     return CommonResult(True)

        # if self.app.emrAdapterClient:
        #     result = self.app.emrAdapterClient.RefuseCase(
        #         RefuseRequest(caseId=caseId, operator=operatorId, attending=attending, comment=comment))
        #     return CommonResult(result.isSuccess, result.message)
        # return CommonResult(True)
        if self.app.emrAdapterUrl:
            data = {"caseId": caseId, "operator": operatorId, "comment": comment, "attending": attending}
            headers = {'Content-Type': 'application/json'}
            res = requests.post(f"{self.app.emrAdapterUrl}/emr/adapter/refuse", headers=headers, json=data).json()
            return CommonResult(res.get("isSuccess") or True, res.get("message") or "")
        return CommonResult(True)

    def sendCancelRefuseRequestToEmr(self, caseId: str, operatorId: str, comment: str = '') -> CommonResult:
        """通知EMR撤销审核通过, 只有在撤销归档环节才应该调用

        Args:
            caseId (str): [description]
            operatorId (str): [操作医生工号]
            comment (str, optional): [description]. Defaults to ''.
        Returns:
            CommonResult: [description]
        """
        # if self.app.emrAdapterClient:
        #     result = self.app.emrAdapterClient.RevokeRefused(
        #         RevokeRequest(caseId=caseId, operator=operatorId, comment=comment))
        #     return CommonResult(result.isSuccess, result.message)
        # return CommonResult(True)
        if self.app.emrAdapterUrl:
            data = {"caseId": caseId, "operator": operatorId, "comment": comment}
            headers = {'Content-Type': 'application/json'}
            res = requests.post(f"{self.app.emrAdapterUrl}/emr/adapter/revoke/refuse", headers=headers, json=data).json()
            return CommonResult(res.get("isSuccess") or True, res.get("message") or "")
        return CommonResult(True)

    def ensureUserName(self, operatorId: str, operatorName: str = ''):
        """用户姓名为空时补齐用户姓名

        Args:
            operatorId (str): [description]
            operatorName (str): [description]
        """
        User.DATABASE = self.app.iamDatabase
        u = User.getById(self.app.mongo, operatorId)
        name = u.name if u.name else operatorName
        return operatorId, name, operatorName

    def isCaseArchived(self, audit) -> bool:
        """判断病历是否是归档状态
        """
        # 初审已完成状态
        AUDIT_STATUS_3 = 3
        AUDIT_STATUS_6 = 6
        # 质控环节对应的状态字段对照
        auditStatusMap = {
            'department': 'deptStatus',
            'hospital': 'status',
            'firstpage': 'fpStatus',
            'expert': 'expertStatus'
        }

        finalAuditType = self.app.config.getArchiveSteps()
        for t in finalAuditType:
            # 判断归档时初审还是终审环节，1是有终审，2是只有初审
            setting = self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=t))
            # 质控节点对应的状态值
            stepStatus = getattr(audit, auditStatusMap.get(t))
            # 有终审且状态是终审完成 或者 无终审且状态未初审完成 =》 节点已完成
            if (setting == '1' and stepStatus != AUDIT_STATUS_6) or (setting == '2' and stepStatus != AUDIT_STATUS_3):
                return False
        return True

    def getArchiveConfig(self, auditStep: str, audit) -> bool:
        """根据配置项判断当前是否是归档环节
        获取质控归档节点的配置项和对应节点质控环节的设置
        """
        # 初审已完成状态
        AUDIT_STATUS_3 = 3
        AUDIT_STATUS_6 = 6
        # 质控环节对应的状态字段对照
        auditStatusMap = {
            'department': 'deptStatus',
            'hospital': 'status',
            'firstpage': 'fpStatus',
            'expert': 'expertStatus'
        }
        # 归档配置项对应的质控环节
        finalAuditType = self.app.config.getArchiveSteps()
        # 归档环节
        if self.auditType not in finalAuditType:
            return False

        # 检查归档配置项中所有节点，除当前节点运行是归档的最后一步外，其它环节需要是已完成状态
        for t in finalAuditType:
            # 判断归档时初审还是终审环节，1是有终审，2是只有初审
            setting = self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=t))
            # 允许当前节点是归档的最后一个步骤，不需要判断状态。有终审的情况下 auditStep = recheck
            if t == self.auditType:
                if setting == '1' and auditStep != AUDIT_STEP_RECHECK:
                    return False
                continue
            # 质控节点对应的状态值
            stepStatus = getattr(audit, auditStatusMap.get(t))
            # 有终审且状态是终审完成 或者 无终审且状态未初审完成 =》 节点已完成
            if (setting == '1' and stepStatus != AUDIT_STATUS_6) or (setting == '2' and stepStatus != AUDIT_STATUS_3):
                return False
        return True

    def approve(self, caseId: str, operatorId: str, operatorName: str, comment: str = '', auditStep='') -> CommonResult:
        """审核通过
        """
        with self.app.mysqlConnection.session() as session:
            c = self._caseRepository.getByCaseId(session, caseId)
            if not c:
                raise # GrpcInvalidArgumentException(message=f'case {caseId} not found')

            audit = self._auditRecordRepository.get(session, c.audit_id)
            if not audit:
                return CommonResult(False, '没有找到对应的审核记录')

            # 判断状态是否可以操作
            current_status = audit.getStatus(self.auditType)
            if auditStep == AUDIT_STEP_AUDIT and current_status != AuditRecord.STATUS_APPLIED and current_status != AuditRecord.STATUS_RECHECK_REFUSED:
                return CommonResult(False, '病历状态错误, 请刷新页面')
            if auditStep == AUDIT_STEP_RECHECK and current_status != AuditRecord.STATUS_APPROVED:
                return CommonResult(False, '病历状态错误, 请刷新页面')

            # 查询当前操作是否是归档操作
            archiveFlag = self.getArchiveConfig(auditStep, audit)
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)

            # 通知emr审核通过
            if archiveFlag:
                r = self.sendApproveRequestToEmr(caseId, operatorCode, comment)
                if not r.isSuccess:
                    return CommonResult(False, f'调用电子病历归档接口失败. {r.message}')

            # 更新质控环节的状态，添加质控流程
            if auditStep == AUDIT_STEP_RECHECK:
                audit.recheckApprove(self.auditType, operatorId, operatorName)
            else:
                completeAuditType = self.app.config.get(Config.QC_COMPLETE_AUDIT_TYPE)
                audit.approve(self.auditType, operatorId, operatorName, archiveFlag, completeAuditType=completeAuditType)

            # 审核通过清理问题
            if self.app.config.get(Config.QC_APPROVE_CLEAR_PROBLEM_FIRST.format(auditType=self.auditType)):
                self._problemRepository.clearProblem(session, audit.id, isApproved=True)

            # 计算分数/更新首页问题数目, TODO: 支持配置在哪个环节不计算分数
            self.calculateCaseScore(session, caseId, audit.id, False)
            # 重新计算首页得分
            self.calculateFirstpageScore(session, caseId, audit.id)
            # self._auditRecordRepository.calculateFirstpageProblemCount(session, audit.id)

            # 归档
            action = '审核通过' if auditStep == AUDIT_STEP_RECHECK else '质控完成'
            if archiveFlag:
                action = '归档'
                c.setStatus(CASE_STATUS_ARCHIVED)
                # 标记人工审核归档，1=AI，2=非质控完成归档，3=人工质控审核完成
                if auditStep == AUDIT_STEP_AUDIT or auditStep == AUDIT_STEP_RECHECK:
                    audit.setArchivedType(3)
                # 计算归档得分
                self.calculateArchiveScore(session, caseId, audit)
                # 计算归档首页得分
                self.calculateArchiveFPScore(session, caseId, audit)

            # 如果配置项设置了当前环节分数覆盖院级病案得分，重新计算archiveScore
            ow_type = self.app.config.get(Config.QC_ARCHIVESCORE_OVERWRITE_STEP)
            if ow_type and self.auditType == ow_type:
                final_status = audit.getStatus(ow_type)
                final_config = self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=ow_type))
                if (final_status == 6 and final_config == '1') or (final_status == 3 and final_config == '2'):
                    self.calculateArchiveScore(session, caseId, audit)
                    self.calculateArchiveFPScore(session, caseId, audit)

            # 写日志
            self._checkHistoryRepository.log(session, caseId, operatorId, operatorName, action, "", "", "病历", auditStep)
            # 专家抽检质控完成给医生端发消息
            if self.app.config.get(Config.QC_FINISH_NOTIFY_DOCTOR.format(auditType=self.auditType)) == 1:
                self._messageRepository.send_approve_message(session, c, operatorName, self.auditType)

        return CommonResult(True)

    def refuse(self, request, toClinic=False, isAdd=False):
        """
        审核不通过
        :param request:
        :param toClinic: 是否退回给临床医生
        :param isAdd: 是否是追加退回操作
        :return:
        """
        caseId = request.caseId
        operatorId = request.operatorId
        operatorName = request.operatorName
        problemIds = request.problems
        comment = ""
        if not isAdd:
            comment = request.comment
        auditStep = request.auditStep
        fixDays = request.inDays or 3
        fix_deadline = arrow.utcnow().to('+08:00').shift(days=fixDays + 1).date().strftime('%Y-%m-%d %H:%M:%S')
        currentTime = arrow.utcnow().to('+08:00').naive
        with self.app.mysqlConnection.session() as session:
            c = self._caseRepository.getByCaseId(session, caseId)
            if not c:
                raise ValueError(f'case {caseId} not found')
            self._caseRepository.updateRefuseFixDeadline(session, caseId, fix_deadline)
            audit = self._auditRecordRepository.get(session, c.audit_id)
            if not audit:
                return CommonResult(False, '没有找到对应的审核记录')
            if not isAdd:
                if c.status == CASE_STATUS_REFUSED:
                    return CommonResult(False, '此病历已经在其它环节退回给临床医生')
                # 检查状态是否允许退回
                allowedStatus = self.app.config.refuseAllowedStatus(self.auditType)
                if not allowedStatus:
                    if toClinic:
                        pass
                    else:
                        if audit.getStatus(self.auditType) != AuditRecord.STATUS_APPROVED:
                            return CommonResult(False, '病历状态错误, 请刷新页面')
                elif allowedStatus and audit.getStatus(self.auditType) not in allowedStatus:
                    return CommonResult(False, '病历状态错误, 请刷新页面')
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            emrInfoList = list(self._emrRepository.getEmrListByCaseId(session, c.caseId))

            def getEmrInfo(docId):
                if not docId or docId == '0':
                    return None
                for item in emrInfoList:
                    if item.docId == docId:
                        return item
                return None

            problems = list(self._problemRepository.getByIds(session, problemIds))
            reportProblems = []
            refuseDoctors = []
            lostScore = 0
            problemCount = 0
            for p in problems:
                doc = getEmrInfo(p.docId)
                instruction = p.qcItemModel.instruction
                if p.qcItemModel.flexTipFlag:
                    instruction = p.reason if p.reason else instruction
                refuseCode = p.doctorCode
                if doc and doc.refuseCode:
                    refuseCode = doc.refuseCode
                if not refuseCode:
                    refuseCode = c.attendCode
                if refuseCode not in refuseDoctors:
                    refuseDoctors.append(refuseCode)
                if not isAdd:
                    # 问题标记退回
                    p.refuse(currentTime)
                else:
                    p.addRefuse(currentTime, refuseCode)
                # 整改书
                reportProblems.append({
                    'problemId': p.id,
                    'docId': p.docId,
                    'qcItemId': str(p.qcItemId),
                    "reason": instruction,
                    "comment": p.comment,
                    "aiFlag": p.fromAi(),
                    "score": str(p.score),
                    "reviewer": p.operator_name,
                    "reviewTime": p.created_at.strftime("%Y-%m-%d") if p.created_at else "",
                    "refuseCode": refuseCode,
                    "detail": p.detail,
                    "problemCount": p.problem_count,
                    "documentName": doc.documentName if doc else "缺失文书",
                    "recordTime": doc.recordTime.strftime("%Y-%m-%d") if doc and doc.recordTime else "",
                    "veto": p.qcItemModel.veto,
                    "fixedFlag": p.is_fix,
                    "appeal": p.appeal,
                    "appealTime": p.appeal_time.strftime("%Y-%m-%d") if p.appeal_time else "",
                    "ignoreFlag": p.is_ignore,
                })
                lostScore += p.score
                problemCount += 1
            if isAdd:
                # 将已存在的refuse_history的整改期限更新
                rh_list = self._refuseHistoryRepository.getALlByCaseId(session, c.caseId, request.auditType)
                for rh in rh_list:
                    rh.setModel(fix_deadline=fix_deadline)
            refuseHistory = RefuseHistory.newObject(self.app)
            refuseHistory.setModel(
                caseId=caseId,
                auditType=self.auditType,
                audit_id=audit.id,
                patient_id=c.patientId,
                visit_times=c.visitTimes,
                refuse_time=currentTime.strftime('%Y-%m-%d %H:%M:%S'),
                qc_doctor=operatorName,
                comment=comment,
                problems=json.dumps(reportProblems, ensure_ascii=False),
                lost_score=lostScore,
                problemCount=problemCount,
                fix_deadline=fix_deadline,
            )
            if isAdd:
                refuseHistory.setModel(type=1)  # 区分是否为追加退回
            if not isAdd:
                # 通知emr审核不通过
                r = self.sendRefuseRequestToEmr(caseId, operatorCode, comment=comment, problems=problems,
                                                attending=c.attendCode)
                if not r.isSuccess:
                    return CommonResult(False, f'调用电子病历退回接口失败. {r.message}')
            self._refuseHistoryRepository.add(session, refuseHistory)
            session.commit()
            if not isAdd:
                audit.refuse(self.auditType, operatorId, operatorName, currentTime.strftime('%Y-%m-%d %H:%M:%S'),
                             refuseHistory.id)
                for d in refuseDoctors:
                    item = RefuseDetail.newObject(self.app)
                    item.setModel(
                        caseId=c.caseId,
                        audit_id=c.audit_id,
                        history_id=refuseHistory.id,
                        created_at=currentTime.strftime('%Y-%m-%d %H:%M:%S'),
                        is_deleted=0,
                        reviewer=operatorName,
                        doctor=d,
                        apply_flag=0,
                        auditType=self.auditType,
                    )
                    self._refuseDetailRepository.add(session, item)
                if c.status == AuditRecord.STATUS_PENDING:
                    pass
                else:
                    c.refuse(operatorId, operatorName, currentTime)
                self._messageRepository.send_refuse_msg(c, fixDays, operatorName, lostScore, refuseDoctors,
                                                        self.auditType, AuditHistoryItem.ACTION_REFUSE)
                self._checkHistoryRepository.log(session, caseId, operatorId, operatorName,
                                                 AuditHistoryItem.ACTION_REFUSE, f'退回{problemCount}个问题', comment,
                                                 '病历', auditStep=auditStep)
            else:
                audit.appendTimeline(self.auditType, action=AuditHistoryItem.ACTION_ADD_REFUSE, doctor=operatorName,
                                     actionTime=currentTime.strftime('%Y-%m-%d %H:%M:%S'), refuseId=refuseHistory.id)
                self._messageRepository.send_refuse_msg(c, fixDays, operatorName, lostScore, refuseDoctors,
                                                        self.auditType, AuditHistoryItem.ACTION_ADD_REFUSE)
                self._checkHistoryRepository.log(session, caseId, operatorId, operatorName,
                                                 AuditHistoryItem.ACTION_ADD_REFUSE, f'退回{problemCount}个问题', comment,
                                                 '病历', auditStep=auditStep)
            for p in problems:
                self._problemRepository.recordProblemAction(session, caseId, p.qcItemId, "退回返修", operatorId, operatorName, self.auditType)

        return CommonResult(True)

    def cancelApprove(self, caseId: str, operatorId: str, operatorName: str, comment: str = '', auditStep: str = ''):
        """撤销归档，撤销完成质控
        """
        with self.app.mysqlConnection.session() as session:
            # 查询病历基本信息和当前质控节点信息
            c = self._caseRepository.getByCaseId(session, caseId)
            if not c:
                raise ValueError(f'case {caseId} not found')
            audit = self._auditRecordRepository.get(session, c.audit_id)

            if auditStep == 'recheck':
                if audit.getStatus(self.auditType) != AuditRecord.STATUS_RECHECK_APPROVED:
                    return CommonResult(False, '病历状态错误, 请刷新页面')
            else:
                if audit.getStatus(self.auditType) != AuditRecord.STATUS_APPROVED:
                    return CommonResult(False, '病历状态错误, 请刷新页面')

            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)

            # 判断当前是否是撤销归档操作，调用emr接口通知取消审核通过, 若失败则放弃后续操作
            archiveFlag = self.getArchiveConfig(auditStep, audit)
            if archiveFlag:
                r = self.sendCancelApproveRequestToEmr(caseId=caseId, operatorId=operatorCode, comment=comment)
                if not r.isSuccess:
                    return CommonResult(False, f'调用电子病历撤销归档接口失败，{r.message}')
                # 撤销归档，修改病历状态为待质控
                c.setStatus(CASE_STATUS_APPLIED)

            # 更新质控节点状态
            if auditStep == AUDIT_STEP_RECHECK:
                audit.cancelApprove(self.auditType, operatorId, operatorName)
            else:
                audit.cancelAudit(self.auditType, operatorId, operatorName)

            # 恢复因为审核通过被删除的问题
            if self.app.config.get(Config.QC_APPROVE_CLEAR_PROBLEM_FIRST.format(auditType=self.auditType)):
                self._problemRepository.restoreProblemRemovedByApprove(session, audit.id)

            # 重新计算分数
            self.calculateCaseScore(session, caseId, audit.id)
            # 重新计算首页得分
            self.calculateFirstpageScore(session, caseId, audit.id)
            # 重新计算院级病案得分
            ow_type = self.app.config.get(Config.QC_ARCHIVESCORE_OVERWRITE_STEP)
            if archiveFlag or (ow_type and self.auditType == ow_type):
                self.calculateArchiveScore(session, caseId, audit)
                self.calculateArchiveFPScore(session, caseId, audit)
            # TODO:重新计算首页问题数

            self._checkHistoryRepository.log(session, c.caseId, operatorId, operatorName, '撤销完成', '', '', '病历', auditStep)

            return CommonResult(True, '撤销成功')

    def cancelRefuse(self, caseId: str, operatorId: str, operatorName: str, comment: str = '', toRecheck=False,
                     auditStep='', transFrom=''):
        """撤销驳回

        Args:
            caseId (str): [description]
            operatorId (str): [description]
            operatorName (str): [description]
            comment (str): [description]
            toRecheck (bool): [ True 表示撤销退回重新质控， False 默认撤销退回临床]
            auditStep (str): [audit or recheck (初审 or 复审)]
            transFrom(str): [clinic or audit ]
        Raises:
            ValueError: [description]
        """
        with self.app.mysqlConnection.session() as session:
            c = self._caseRepository.getByCaseId(session, caseId)
            if not c:
                raise ValueError(f'case {caseId} not found')
            audit = self._auditRecordRepository.get(session, c.audit_id)
            if toRecheck:
                if audit.getStatus(self.auditType) != AuditRecord.STATUS_RECHECK_REFUSED:
                    return CommonResult(False, '病历状态错误, 请刷新页面')
            else:
                if audit.getStatus(self.auditType) != AuditRecord.STATUS_REFUSED:
                    return CommonResult(False, '病历状态错误, 请刷新页面')
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            # 调用emr接口通知取消审核不通过
            if transFrom == 'clinic':
                r = self.sendCancelRefuseRequestToEmr(caseId=caseId, operatorId=operatorCode, comment=comment)
                if not r.isSuccess:
                    return CommonResult(False, f'调用电子病历撤销驳回接口失败，{r.message}')

            audit.cancelRefuse(self.auditType, operatorId, operatorName, isFinal=auditStep == 'recheck')
            # 撤销质控问题的驳回标记
            self._problemRepository.cancelRefused(session, audit.id)
            # 修改病历状态
            if self.isCaseArchived(audit):
                c.setStatus(CASE_STATUS_ARCHIVED)
            else:
                c.setStatus(CASE_STATUS_APPLIED)
            # 驳回次数-1
            c.decreaseRefuseCount()
            # 清空驳回记录
            self._refuseHistoryRepository.revokeRefuse(session, caseId, audit.id)

            self._checkHistoryRepository.log(session, caseId, operatorId, operatorName, '撤销退回', '', '', '病历',
                                             auditStep=auditStep)

            return CommonResult(True, '撤销成功')

    def recheckRefuse(self, caseId: str, operatorId: str, operatorName: str, comment: str = ''):
        """终审不通过

        Args:
            caseId (str): [description]
            operatorId (str): [description]
            operatorName (str): [description]
            comment (str): [description]
        Raises:
            ValueError: [description]
        """
        with self.app.mysqlConnection.session() as session:
            c = self._caseRepository.getByCaseId(session, caseId)
            if not c:
                raise ValueError(f'case {caseId} not found')
            audit = self._auditRecordRepository.get(session, c.audit_id)
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            # TODO: 调用emr接口通知终审不通过, 若失败则放弃后续操作, 可以放在子类实现, 是否要实现此功能取决于实际医院场景
            audit.recheckRefuse(self.auditType, operatorId, operatorName, comment)
            self._checkHistoryRepository.log(session, caseId, operatorId, operatorName, '退回重新质控', '', '', '病历',
                                             auditStep='recheck')
            return CommonResult(True, '退回成功')

    def archiveCaseList(self, req: GetCaseListRequest, operatorId, exclude=[]):
        """直接归档
        """
        statusField = {
            'department': 'deptStatus',
            'hospital': 'status',
            'firstpage': 'fpStatus',
            'expert': 'expertStatus',
        }.get(req.auditType)

        with self.app.mysqlConnection.session() as session:
            result = self._caseRepository.getList(session, req)

            auditIds = []  # 记录 audit_record.id 修改对应病历的 audit_record.status 为已归档
            redis_data = []  # 放入 redis 队列，异步处理归档
            for item in result:
                # 过滤掉病历库中的病历号
                if item.model.caseId in exclude:
                    continue
                auditIds.append(item.auditRecord.id)
                redis_data.append({
                    "auditType": req.auditType,
                    "caseId": item.model.caseId,
                    "operatorId": operatorId
                })

            with redis.Redis(connection_pool=self.app.redis_pool) as r:
                for data in redis_data:
                    r.rpush(SAMPLE_ARCHIVE_REDIS_LIST_KEY, json.dumps(data, ensure_ascii=False))

            # 修改 audit_record.status 为已归档，抽取病历列表查询就可以过滤掉
            if auditIds:
                session.execute("update audit_record set %s = 3 where id in (%s)" % (statusField, ','.join([str(item) for item in auditIds])))

        return CommonResult(True)

    def archiveSampleCase(self, auditType, caseId, operatorId):
        # 操作人
        operatorId, operatorName, operatorCode = self.ensureUserName(operatorId)
        # 根据配置项是否有终审，设置当前操作是对应质控环节的最后一个环节，有终审=审核通过，无终审=质控完成
        auditStep = AUDIT_STEP_AUDIT
        if self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=auditType)) == '1':
            auditStep = AUDIT_STEP_RECHECK
        action = '审核通过' if auditStep == AUDIT_STEP_RECHECK else '质控完成'

        with self.app.mysqlConnection.session() as session:
            case = self._caseRepository.getByCaseId(session, caseId)
            audit = case.auditRecord
            if not audit:
                return
            audit = AuditRecord(audit)

            # 是否是归档操作
            archiveFlag = self.getArchiveConfig(auditStep, audit)

            # 修改auditRecord的状态和流程
            if auditStep == AUDIT_STEP_RECHECK:
                audit.recheckApprove(self.auditType, operatorId, operatorName)
            else:
                audit.approve(self.auditType, operatorId, operatorName, archiveFlag)

            # 归档
            if archiveFlag:
                action = '归档'
                case.setStatus(CASE_STATUS_ARCHIVED)
                # 标记人工审核归档，1=AI，2=非质控完成归档，3=人工质控审核完成
                audit.setArchivedType(2)
                # 计算归档得分
                self.calculateArchiveScore(session, caseId, audit)
                # 计算归档首页得分
                self.calculateArchiveFPScore(session, caseId, audit)

            # 写日志
            self._checkHistoryRepository.log(session, caseId, operatorId, operatorName, action, "", "", "病历", auditStep)
            session.commit()

        return CommonResult(True)

    def getProblem(self, caseId: str, auditId: int = -1, withDeleted=False) -> List[Problem]:
        """获取问题列表

        Args:
            caseId (str): [description]
            auditId (int, optional): 不传时获取历史上全部的问题列表, 传的时候返回指定audit_id对应的问题列表. Defaults to -1.
        """
        with self.app.mysqlConnection.session() as session:
            if auditId > 0:
                return list(
                    self.expunge(session,
                                 self._problemRepository.getListByAuditId(session, auditId, withDeleted=withDeleted)
                                 )
                )
            else:
                return list(
                    self.expunge(session,
                                 self._problemRepository.getListByCaseId(session, caseId, withDeleted=withDeleted))
                )

    def deleteProblem(self, problemId: int, operatorId: str, operatorName: str, auditStep=''):
        """删除问题

        Args:
            problemId (int): [description]
        """
        with self.app.mysqlConnection.session() as session:
            p = self._problemRepository.get(session, problemId)
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            p.setModel(
                is_deleted=1,
                fix_doctor_code=operatorId,
                fix_doctor=operatorName,
                fix_time=arrow.utcnow().to('+08:00').naive,
            )
            session.commit()
            # 重新计算分数
            self.calculateCaseScore(session, p.caseId, p.audit_id)
            # 重新计算首页得分
            self.calculateFirstpageScore(session, p.caseId, p.audit_id)
            # TODO: 计算首页问题数
            # 记录日志
            documentName = p.emrInfoModel.documentName if p.emrInfoModel else "缺失文书"
            self._checkHistoryRepository.log(
                session, p.caseId, operatorId, operatorName, '删除', f'{p.reason}。{p.comment}',
                p.comment, documentName, auditStep=auditStep
            )
            self._problemRepository.recordProblemAction(session, p.caseId, p.qcItemId, "确认解决", operatorId, operatorName, self.auditType)
            return CommonResult(True)

    def updateProblem(self, problemId: int, reason: str, comment: str, deductFlag: int, score, doctorCode: str,
                      count: int, operatorId: str, operatorName: str, auditStep=''):
        """修改问题, 修改问题会涉及到文书驳回医生/评分等的变化

        Args:
            problem (Problem): [description]
        """
        with self.app.mysqlConnection.session() as session:
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            p = self._problemRepository.get(session, problemId)
            # 修改驳回医生
            if p.EmrInfo:
                p.EmrInfo.setRefuseDoctor(doctorCode)
            # 修改问题信息
            p.setModel(
                reason=reason,
                comment=comment,
                deduct_flag=deductFlag if deductFlag else 0,
                score=score or 0,
                doctorCode=doctorCode,
                problem_count=count,
            )
            # 是否修改状态
            if p.qcItemModel.enableType != 1:
                p.setModel(status=1)
            session.commit()
            # 重新计算分数
            self.calculateCaseScore(session, p.caseId, p.audit_id)
            # 重新计算首页得分
            self.calculateFirstpageScore(session, p.caseId, p.audit_id)
            # TODO: 计算首页问题数
            # 记录日志
            documentName = p.emrInfoModel.documentName if p.emrInfoModel else "缺失文书"
            self._checkHistoryRepository.log(
                session, p.caseId, operatorId, operatorName, '编辑', reason,
                p.comment, documentName, auditStep=auditStep
            )
            return CommonResult(True)

    def deductProblem(self, problemId: int, deductFlag, operatorId, operatorName):
        """设置扣分不扣分, 会涉及分数重新计算

        Args:
            id (int): [description]
            deductFlag ([type]): [description]
            operatorId ([type]): [description]
            operatorName ([type]): [description]
        """
        with self.app.mysqlConnection.session() as session:
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            p = self._problemRepository.get(session, problemId)
            # 修改问题信息
            p.setModel(
                deduct_flag=deductFlag if deductFlag else 0,
            )
            session.commit()
            self._checkHistoryRepository.log(session, p.caseId, operatorId, operatorName, '编辑',
                                             content='不扣分>扣分' if deductFlag else '扣分>不扣分', comment='',
                                             docType=p.emrInfoModel.documentName, auditStep='')
            # 重新计算分数
            self.calculateCaseScore(session, p.caseId, p.audit_id)
            # 重新计算首页得分
            self.calculateFirstpageScore(session, p.caseId, p.audit_id)
            return CommonResult(True)

    def calculateCaseScore(self, session, caseId: str, auditId: int = -1, isFinal=False):
        """计算病历得分
        """
        audit = self._auditRecordRepository.get(session, auditId)
        if not audit:
            return CommonResult(False, '没有找到对应的审核记录')
        qcGroup = self._qcGroupRepository.getQcGroup(session)
        if not qcGroup:
            return CommonResult(False, '没有找到规则组配置')
        try:
            problems = self._problemRepository.getListByAuditId(session, auditId)
            qcGroup.addProblems(problems)
            score = qcGroup.getCurrentScore()
            # qcGroup.printCalculator()
            audit.setScore(self.auditType, score, isFinal)
            problemCount = self._problemRepository.countByAuditId(session, audit.id)
            audit.setProblemCount(self.auditType, problemCount)
            return CommonResult(True, message=str(score))
        except Exception as e:
            print(e)

    def calculateFirstpageScore(self, session, caseId: str, auditId: int = -1):
        """计算首页分数
        """
        audit = self._auditRecordRepository.get(session, auditId)
        if not audit:
            return CommonResult(False, '没有找到对应的审核记录')
        # 查询扣分规则
        query_sql = "select distinct qcitemid ,score, maxscore from dim_firstpagescore where is_select = 1;"
        query = session.execute(query_sql)
        ret = query.fetchall()
        fpRule = {}
        for x in ret:
            fpRule[x[0]] = {
                'score': x[1],
                'maxscore': x[2]
            }
        try:
            # 计算分数
            deductSum = 0
            problems = self._problemRepository.getListByAuditId(session, auditId)
            for p in problems:
                rule = fpRule.get(p.qcItemId)
                if not rule:
                    continue
                deductScore = rule.get('score', 0) * p.getProblemCount()
                deductSum += deductScore if deductScore < rule.get('maxscore', 0) else rule.get('maxscore', 0)
            audit.setFirstpageScore(self.auditType, 100 - deductSum)
            logging.info('fp score %d', 100 -deductSum)
            return CommonResult(True, message=str(100 - deductSum))
        except Exception as e:
            print(e)

    def getCaseQCItems(self, caseId: str):
        """获取病历适用的质控项
        TODO: 这个功能应该是质控点管理服务实现, 前端得到病历信息后将病历类型或文书类型传给质控点服务得到list
        Args:
            caseId (str): [description]
        """
        raise NotImplementedError()

    def getCurrentAudit(self, caseId: str) -> Optional[AuditRecord]:
        """获取当前的auditRecord记录

        Args:
            caseId (str): [description]
        """
        with self.app.mysqlConnection.session() as session:
            c = self._caseRepository.getByCaseId(session, caseId)
            if not c:
                return None
            else:
                r = self._auditRecordRepository.get(session, c.audit_id)
                if not r:
                    return None
                else:
                    r.expunge(session)
                    return r

    def getCaseProblems(self, caseId: str, docId: str = '') -> List[Problem]:
        """获取病历中的问题

        Args:
            caseId (str): [description]
            docId (str, optional): [description]. Defaults to None.
        """
        with self.app.mysqlConnection.session() as session:
            c = self._caseRepository.getByCaseId(session, caseId)
            if not c:
                raise ValueError('case not found')
            req = GetProblemListRequest(
                caseId=caseId,
                auditId=c.audit_id,
                docId=docId
            )
            return list(
                self.expunge(
                    session, self._problemRepository.getProblem(session, req)))

    def addCaseProblem(self, caseId: str, docId: str, qcItemId: int, operatorId: str, operatorName: str = '',
                       refuseDoctor: str = '', comment='', requirement='', deductFlag=0, score=0, count=1,
                       newQcItemFlag=False, auditStep='', categoryId=0):
        """添加质控问题
        """
        operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
        with self.app.mysqlConnection.session() as session:
            problem = Problem.newObject(self.app)
            c = self._caseRepository.getByCaseId(session, caseId)
            if qcItemId or not newQcItemFlag:
                if self._problemRepository.problemIsExist(session, caseId, docId, requirement, self.auditType, qcItemId):
                    return CommonResult(False, '当前问题描述已添加过，如果需要继续添加，可在原问题上增加问题数量。')
            if not qcItemId:
                newQcItemFlag = True
            emrInfo = self._emrRepository.get(session, caseId, docId)
            standard_emr = ""
            title = ""
            if emrInfo:
                title = emrInfo.getDocumentName()
                document = self._documentsRepository.get(session, title)
                if document:
                    logging.info(document.model)
                    standard_emr = document.getStandardName()
            if newQcItemFlag:
                qcItem = {
                    "requirement": requirement,
                    "instruction": requirement,
                    "standard_emr": standard_emr,
                    "comment": "",
                    "score": score,
                    "operator_id": operatorId,
                    "operator_name": operatorName,
                    "approve_status": 1,
                    "custom": 1,
                    "flexTipFlag": 1,
                    "autoRefuseFlag": 1,
                    "enable": 1,
                    "type": 1,
                }
                qcItem = QcItem.newObject(self.app, **qcItem)
                self._qcItemRepository.add(session, qcItem)
                session.commit()
                qcItem.setModel(code='LS' + str(qcItem.getId()))
                qcItemId = qcItem.getId()
                if not categoryId:
                    categoryId = self._qcGroupRepository.getFirstCategoryId(session)
                qcCateItem = {
                    "groupId": self._qcGroupRepository.getGroupId(),
                    "categoryId": categoryId,
                    "itemId": qcItemId,
                    "maxScore": 100,
                    "score": score
                }
                qcCateItem = QcCateItems.newObject(self.app, **qcCateItem)
                self._qcGroupRepository.addQcCateItems(session, qcCateItem)
                session.commit()
            problem.setModel(
                audit_id=c.audit_id,
                caseId=caseId,
                qcItemId=qcItemId,
                docId=docId,
                title=title,
                reason=requirement or '',
                deduct_flag=1 if deductFlag else 0,
                score=score,
                comment=comment,
                operator_id=operatorId,
                operator_name=operatorName,
                from_ai=0,
                doctorCode=refuseDoctor,
                problem_count=count or 1,
                created_at=arrow.utcnow().to('+08:00').naive,
                refuseCount=0,
                refuseFlag=0,
                updated_at=arrow.utcnow().to('+08:00').naive,
                auditType=self.auditType
            )
            self._problemRepository.add(session, problem)
            session.commit()
            if emrInfo:
                emrInfo.setRefuseDoctor(refuseDoctor)
            # 计算分数
            self.calculateCaseScore(session, c.caseId, c.audit_id)
            # 重新计算首页得分
            self.calculateFirstpageScore(session, c.caseId, c.audit_id)
            # TODO: 计算首页问题数
            # 记录质控日志
            self._checkHistoryRepository.log(
                session, caseId, operatorId, operatorName, '添加', f'{problem.reason}。{problem.comment}',
                comment, title, auditStep=auditStep
            )
            # 记录问题操作记录
            self._problemRepository.recordProblemAction(session, caseId, qcItemId, "提出问题", operatorId, operatorName, self.auditType)
            return CommonResult(True)

    def getCheckHistory(self, caseId, auditStep='', start=0, size=100):
        """质控日志
        """
        with self.app.mysqlConnection.session() as session:
            req = GetCheckHistoryListRequest(caseId=caseId, auditType=self.auditType, auditStep=auditStep, start=start,
                                             size=size)
            count = self._checkHistoryRepository.count(session, req)
            return self.expunge(session, self._checkHistoryRepository.getList(session, req)), count

    def getReviewers(self, name):
        """审核人列表
        """
        with self.app.mysqlConnection.session() as session:
            return self._auditRecordRepository.getReviewers(session, name)

    def getAssignedDoctors(self, name):
        """审核人列表
        """
        with self.app.mysqlConnection.session() as session:
            return self._sampleRecordRepository.getAssignedDoctors(session, name)

    def getAuditRecords(self, caseId):
        """审核流程
        """
        with self.app.mysqlConnection.session() as session:
            return self.expunge(session, self._auditRecordRepository.getListByCaseId(session, caseId))

    def getAuditRecordById(self, auditId):
        """审核记录
        """
        with self.app.mysqlConnection.session() as session:
            r = self._auditRecordRepository.get(session, auditId)
            if not r:
                return None
            else:
                r.expunge(session)
                return r

    def getRefuseHistory(self, caseId, refuseTime):
        """驳回记录，问题清单
        """
        with self.app.mysqlConnection.session() as session:
            report = self._refuseHistoryRepository.getRefuseHistory(session, caseId, refuseTime)
            if not report:
                return None

    def getEmrVersions(self, caseId, docId):
        """文书版本
        """
        with self.app.mysqlConnection.session() as session:
            # 根据audit_record 记录的每次申请归档时间，计算每次申请记录涵盖的时间段范围
            audit_periods = self._auditRecordRepository.getAuditRecordPeriods(session, caseId)

            # 查询病历所有文书的修改记录，将每次修改根据时间落到申请记录时间范围中
            emr_record = self._emrRepository.getAuditEmrLog(session, caseId)
            result = []
            for rec in emr_record:
                doc_id = rec.docId
                if doc_id != docId:
                    continue
                create_time = arrow.get(rec.createTime)
                # 判断文书修改时间落在哪个申请记录时间范围中
                for audit, start_time, end_time in audit_periods:
                    if start_time < create_time <= end_time:
                        last_version = result[-1] if result else None
                        if last_version and last_version.audit_record.id == audit.id:
                            result.pop()
                        version = EmrVersion(rec, audit)
                        version.expunge(session)
                        result.append(version)
            # 查询当前申请记录
            logging.info(result)
            return result

    def crawlCase(self, caseId, patientId, auditType='hospital'):
        """手动请求更新病历数据
        """
        try:
            routing_key = 'qc.archive' if auditType != 'active' else 'qc.active'
            message = {
                    "type": routing_key,
                    "body": {
                        "caseId": caseId,
                        "patientId": patientId
                    },
                }
            self.app.mq.publish(message, exchange='qcetl', routing_key=routing_key)
            logging.info("crawlCase send msg: %s", message)
            import time
            time.sleep(5)  # todo 当前为发送mq消息异步抓数据，一般病历5秒内可以抓完，可能存在未抓完情况
        except Exception as e:
            logging.exception(e)
            return False
        else:
            return True

    def getArchiveScoreStep(self, audit):
        # 判断是否覆盖分数计算规则，如果指定质控环节已结束，覆盖分数
        ow_type = self.app.config.get(Config.QC_ARCHIVESCORE_OVERWRITE_STEP)
        if ow_type and audit.isFinished(ow_type, self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=ow_type))):
            return [ow_type]
        # 如果不可以覆盖（没有相关配置或者指定环节未完成），返回归档环节配置项
        for item in self.app.config.getArchiveSteps():
            if not audit.isFinished(item, self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=item))):
                return []
        return self.app.config.getArchiveSteps()

    def getDeductDetail(self, caseId, auditId: int = -1):
        """院级病案得分扣分明细
        """
        with self.app.mysqlConnection.session() as session:
            audit = self._auditRecordRepository.get(session, auditId)
            if not audit:
                return CommonResult(False, '没有找到对应的审核记录')

            finalAuditType = self.getArchiveScoreStep(audit)  # 院级病案得分的质控环节

            deductList = []
            for auditType in finalAuditType:
                # 质控人和质控时间
                reviewer = audit.getReviewer(auditType, isFinal=self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=auditType)) == '1')[1]
                reviewTime = audit.getReviewTime(auditType, isFinal=self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=auditType)) == '1')

                # 质控规则组和质控点
                groupId = self.app.config.get(Config.QC_GROUP_ARCHIVE.format(auditType=auditType))
                if not groupId or not int(groupId):
                    logging.exception(f"configItem[{Config.QC_GROUP_ARCHIVE.format(auditType=auditType)}] is empty.")
                qcItems = self._qcGroupRepository.getQcCateItems(session, groupId=int(groupId))
                if not qcItems:
                    return CommonResult(False, '没有找到规则组设置')

                problems = self._problemRepository.getListByAuditId(session, auditId, auditType=auditType)

                deduct = {}
                # 质控问题按照质控点合并分数
                for p in problems:
                    if deduct.get(p.getReason()) is not None:
                        deduct[p.getReason()].score += p.problem_count * p.score
                    else:
                        deductItem = DeductDetail(auditType=auditType, caseId=caseId, docId=p.getDocId(),
                                                  qcItemId=p.getQcItemId(), problemCount=p.problem_count,
                                                  singleScore=p.score, score=p.problem_count * p.score,
                                                  operatorName=reviewer,
                                                  createTime=reviewTime.strftime('%Y-%m-%d %H:%M:%S') if reviewTime else '',
                                                  reason=p.getReason())
                        deduct[p.getReason()] = deductItem
                # 质控规则组质控点配置过滤一遍分数，如果扣分超过最高扣分，设置为扣最高分
                for value in deduct.values():
                    score = 0
                    for item in qcItems:
                        if item.itemId == value.qcItemId:
                            score = min(item.maxScore, value.score)
                            break
                    value.score = score
                deductList.append(deduct)
            # 将质控节点的问题合并，相同质控点保留扣分更多的
            result = {}
            for deductItem in deductList:
                for value in deductItem.values():
                    if value.score > result.get(value.reason, DeductDetail()).score:
                        result[value.reason] = value
            data = [item for item in result.values()]
            logging.info(f'合并之后的扣分结果：{data}')
            return data
        return []

    def calculateArchiveScore(self, session, caseId: str, audit: AuditRecord):
        """计算院级病案得分
        """
        # 取病案质控和首页质控的问题
        # 每个环节里的问题按照质控点合并分数
        # 取质控规则组里质控点的最高分设置，判断合并之后的扣分和质控点最高扣分谁大谁小
        # 将两个环节的质控点扣分合起来，如果质控点重复取扣分多的
        # 如果有专家质控抽取了归档病历，按照归档病历的结果算
        finalAuditType = self.getArchiveScoreStep(audit)
        if not finalAuditType:
            audit.setArchiveScore(None)
            return CommonResult(False, '不满足院级病案得分条件')

        deductList = []
        for auditType in finalAuditType:
            groupId = self.app.config.get(Config.QC_GROUP_ARCHIVE.format(auditType=auditType))
            if not groupId or not int(groupId):
                logging.exception(f"configItem[{Config.QC_GROUP_ARCHIVE.format(auditType=auditType)}] is empty.")

            qcItems = self._qcGroupRepository.getQcCateItems(session, groupId=int(groupId))
            if not qcItems:
                return CommonResult(False, '没有找到规则组设置')

            problems = self._problemRepository.getListByAuditId(session, audit.id, auditType=auditType)

            deduct = {}
            # 质控问题按照质控点合并分数
            for p in problems:
                if deduct.get(p.qcItemId) is not None:
                    deduct[p.qcItemId] += p.problem_count * p.score
                else:
                    deduct[p.qcItemId] = p.problem_count * p.score
            # 质控规则组质控点配置过滤一遍分数，如果扣分超过最高扣分，设置为扣最高分
            for k, value in deduct.items():
                score = 0
                for item in qcItems:
                    if item.itemId == k:
                        score = min(item.maxScore, value)
                        break
                deduct[k] = score
            deductList.append(deduct)
        # 将质控节点的问题合并，相同质控点保留扣分更多的
        result = {}
        for deductItem in deductList:
            for k, v in deductItem.items():
                result[k] = max(v, result.get(k, 0))
        logging.info(f'合并之后的扣分结果：{result}')
        try:
            deductScore = sum([float(score) for score in result.values()])
            score = 100 - deductScore
            audit.setArchiveScore(score)
            return CommonResult(True, message=str(score))
        except Exception as e:
            print(e)

    def calculateArchiveFPScore(self, session, caseId, audit):
        """计算归档首页得分
        """
        finalAuditType = self.getArchiveScoreStep(audit)
        if not finalAuditType:
            audit.setArchiveFPScore(None)
            return

        # 查询首页质控点扣分规则
        query_sql = "select distinct qcitemid ,score, maxscore from dim_firstpagescore where is_select = 1;"
        query = session.execute(query_sql)
        ret = query.fetchall()
        fpRule = {x[0]: {'score': x[1], 'maxscore': x[2]} for x in ret}

        # 查询归档节点的问题列表，将相同质控点问题合并
        deduct = {}
        for auditType in finalAuditType:
            groupId = self.app.config.get(Config.QC_GROUP_ARCHIVE.format(auditType=auditType))
            if not groupId or not int(groupId):
                logging.exception(f"configItem[{Config.QC_GROUP_ARCHIVE.format(auditType=auditType)}] is empty.")
            # 质控问题按照质控点合并分数，不同质控节点合并取扣分高的，质控点最高可扣 maxscore
            problems = self._problemRepository.getListByAuditId(session, audit.id, auditType=auditType)
            for p in problems:
                rule = fpRule.get(p.qcItemId)
                if rule:
                    deduct[p.qcItemId] = max(deduct.get(p.qcItemId, 0), p.problem_count * rule.get('score', 0))
                    deduct[p.qcItemId] = min(deduct[p.qcItemId], rule.get('maxscore', 0))
                else:
                    deduct[p.qcItemId] = 0
        deductScore = sum([float(score) for score in deduct.values()])
        audit.setArchiveFPScore(100-deductScore)

    def updateConfig(self, request):
        model = self.app.mysqlConnection['configItem']
        config_dict = request.config
        with self.app.mysqlConnection.session() as session:
            items = session.query(model).filter(model.name.in_(config_dict.keys())).all()
            for item in items:
                item.value = config_dict.get(item.name)

    def getGroupList(self, input_str, response):
        """
        查询诊疗组
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_sql = '''select distinct group_name from medical_group_info'''
            if input_str:
                query_sql += ''' where group_name like "%{}%"'''.format(input_str)
            query = session.execute(query_sql)
            for item in query.fetchall():
                if item[0]:
                    response["items"].append(item[0])


class DepartmentAuditApplication(AuditApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_DEPARTMENT)


class HospitalAuditApplication(AuditApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_HOSPITAL)


class ExpertAuditApplication(AuditApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_EXPERT)


class FirstpageAuditApplication(AuditApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_FIRSTPAGE)

class ActiveAuditApplication(AuditApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_ACTIVE)
