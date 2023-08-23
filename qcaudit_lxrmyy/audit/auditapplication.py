#!/usr/bin/env python3
import logging

from qcaudit.application.auditapplication import AuditApplication as _AuditApplication
from qcaudit.common.const import CASE_STATUS_ARCHIVED, AUDIT_TYPE_HOSPITAL, AUDIT_TYPE_FIRSTPAGE, CASE_STATUS_APPLIED, \
    AUDIT_TYPE_EXPERT
# from qcaudit.common.exception import GrpcInvalidArgumentException
from qcaudit.config import Config
from qcaudit.common.result import CommonResult
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.case.req import GetCaseListRequest
from qcaudit.service.protomarshaler import parseRating, parseStatus


class AuditApplication(_AuditApplication):

    def getCustomArchiveConfig(self, auditStep: str, auditRecord: AuditRecord) -> bool:
        """根据配置项判断当前是否是归档环节
        """
        if self.auditType not in [AUDIT_TYPE_HOSPITAL, AUDIT_TYPE_FIRSTPAGE]:
            return False

        if self.app.config.get(
                Config.QC_FINAL_STATUS.format(auditType=self.auditType)) == '1' and auditStep != 'recheck':
            return False
        elif self.app.config.get(
                Config.QC_FINAL_STATUS.format(auditType=self.auditType)) == '2' and auditStep != 'audit':
            return False

        if not auditRecord:
            return False

        # 当前是病案之后，查看首页质控的状态是否已经达到完成归档的状态
        # 如果当前是首页质控，查看病案质控的状态是否已经完成归档
        # 备注 QC_FINAL_STATUS == 1 表示需要终审环节，此时归档状态是终审对应的完成状态
        hospitalStatus = auditRecord.getStatus(AUDIT_TYPE_HOSPITAL)
        firstpageStatus = auditRecord.getStatus(AUDIT_TYPE_FIRSTPAGE)
        if self.auditType == AUDIT_TYPE_HOSPITAL:
            if (self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=AUDIT_TYPE_FIRSTPAGE)) == '1'
                and firstpageStatus == AuditRecord.STATUS_RECHECK_APPROVED) or \
                    (self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=AUDIT_TYPE_FIRSTPAGE)) == '2'
                     and firstpageStatus == AuditRecord.STATUS_APPROVED):
                return True
        elif self.auditType == AUDIT_TYPE_FIRSTPAGE:
            if (self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=AUDIT_TYPE_HOSPITAL)) == '1'
                and hospitalStatus == AuditRecord.STATUS_RECHECK_APPROVED) or \
                    (self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=AUDIT_TYPE_HOSPITAL)) == '2'
                     and hospitalStatus == AuditRecord.STATUS_APPROVED):
                return True
        return False

    def getDeductDetail(self, caseId, auditId: int = -1):

        def getGroupDeductDetail(dbsession, auditRecord, auditType, groupId):
            qcGroup = self._qcGroupRepository.getQcGroup(session, groupId)
            if not qcGroup:
                return None
            reviewer = auditRecord.getReviewer(auditType, isFinal=self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=auditType)) == '1')[1]
            reviewTime = auditRecord.getReviewTime(auditType, isFinal=self.app.config.get(Config.QC_FINAL_STATUS.format(auditType=auditType)) == '1')
            problems = self._problemRepository.getListByAuditId(dbsession, auditRecord.id, auditType=auditType)
            qcGroup.addProblems(problems)
            details = qcGroup.getDeductDetail()
            for d in details:
                if d.get('ext') is not None:
                    d['ext']['operatorName'] = reviewer
                    d['ext']['createTime'] = reviewTime.strftime('%Y-%m-%d %H:%M:%S') if reviewTime else ""
            return details

        with self.app.mysqlConnection.session() as session:
            audit = self._auditRecordRepository.get(session, auditId)
            if not audit:
                return CommonResult(False, '没有找到对应的审核记录')
            detail = None
            if (audit.getStatus('expert') == 6 and self.app.config.get(Config.QC_FINAL_STATUS.format(auditType='expert')) == '1') \
                    or (audit.getStatus('expert') == 3 and self.app.config.get(Config.QC_FINAL_STATUS.format(auditType='expert')) == '2'):
                print('专家质控已完成，归档分数已专家结果为准')
                detail = getGroupDeductDetail(session, audit, 'expert', 4)
            else:
                # 归档涉及两个规则组
                hospDeductDetails = getGroupDeductDetail(session, audit, 'hospital', 2)
                fpDeductDetails = getGroupDeductDetail(session, audit, 'firstpage', 3)
                detail = hospDeductDetails + fpDeductDetails
            try:
                # 问题汇总去重，TODO 去重有逻辑问题
                data = []
                problemsDict = {}
                for item in detail:
                    problem = problemsDict.get(item.get('name'), None)
                    if not problem:
                        problemsDict[item.get('name')] = item
                    elif item.get('score') > problem.get('score'):
                        problemsDict[item.get('name')] = item
                for k, v in problemsDict.items():
                    data.append(v)
                return data
            except Exception as e:
                print(e)

    def calculateArchiveScore(self, session, caseId: str, auditId: int = -1):
        """计算病历归档得分
        """
        # 取病案质控和首页质控的问题
        # 每个环节里的问题按照质控点合并分数
        # 取质控规则组里质控点的最高分设置，判断合并之后的扣分和质控点最高扣分谁大谁小
        # 将两个环节的质控点扣分合起来，如果质控点重复取扣分多的
        # 如果有专家质控抽取了归档病历，按照归档病历的结果算
        audit = self._auditRecordRepository.get(session, auditId)
        if not audit:
            return CommonResult(False, '没有找到对应的审核记录')
        #
        hospitalQcItems = self._qcGroupRepository.getQcCateItems(session, groupId=2)
        if not hospitalQcItems:
            return CommonResult(False, '没有找到规则组配置')
        hospitalProblems = self._problemRepository.getListByAuditId(session, auditId, auditType='hospital')
        # 病案质控问题按照质控点合并分数
        hpDeduct = {}
        for p in hospitalProblems:
            if hpDeduct.get(p.qcItemId) is not None:
                hpDeduct[p.qcItemId] += p.problem_count * p.score
            else:
                hpDeduct[p.qcItemId] = p.problem_count * p.score
        # 病案质控规则组质控点配置过滤一遍分数
        for k, v in hpDeduct.items():
            itemFind = False
            for item in hospitalQcItems:
                if item.itemId == k:
                    itemFind = True
                    if item.maxScore < v:
                        hpDeduct[k] = item.maxScore
                    break
            if not itemFind:
                hpDeduct[k] = 0
        # 首页质控
        fpQcItems = self._qcGroupRepository.getQcCateItems(session, groupId=3)
        if not fpQcItems:
            return CommonResult(False, '没有首页质控规则组')
        fpProblems = self._problemRepository.getListByAuditId(session, auditId, auditType='firstpage')
        # 首页质控问题按照质控点合并分数
        fpDeduct = {}
        # TODO 可以把首页质控和病案质控相同的代码封装一下
        for p in fpProblems:
            if fpDeduct.get(p.qcItemId) is not None:
                fpDeduct[p.qcItemId] += p.problem_count * p.score
            else:
                fpDeduct[p.qcItemId] = p.problem_count * p.score
        for k, v in fpDeduct.items():
            itemFind = False
            for item in fpQcItems:
                if item.itemId == k:
                    itemFind = True
                    if item.maxScore < v:
                        fpDeduct[k] = item.maxScore
                    break
            if not itemFind:
                fpDeduct[k] = 0
        # 病案质控和首页质控合并，相同质控点保留扣分多的
        deduct = {k: v for k, v in hpDeduct.items()}
        for k, v in fpDeduct.items():
            if deduct.get(k) is not None:
                if v > deduct.get(k):
                    deduct[k] = v
            else:
                deduct[k] = v
        try:
            deductScore = 0
            for k, v in deduct.items():
                print(f'质控点id = {k}, 扣分 {v}')
                deductScore += float(v)
            score = 100 - deductScore
            audit.setArchiveScore(score)
            return CommonResult(True, message=str(score))
        except Exception as e:
            print(e)

    def calculateArchiveFPScore(self, session, caseId, auditId: int = -1):
        """计算归档首页得分
        """
        def getDeductDetail(qcRule, problems):
            detail = {}
            for p in problems:
                singleScore = 0
                if qcRule.get(p.qcItemId) is not None:
                    singleScore = qcRule.get(p.qcItemId).get('score', 0)
                if detail.get(p.qcItemId) is not None:
                    detail[p.qcItemId] += p.problem_count * singleScore
                else:
                    detail[p.qcItemId] = p.problem_count * singleScore
            for key, score in detail.items():
                if qcRule.get(key) is not None:
                    if qcRule.get(key).get('maxscore', 0) < score:
                        detail[key] = qcRule.get(key).get('maxscore')
                else:
                    detail[key] = 0
            return detail

        query_sql = "select distinct qcitemid ,score, maxscore from dim_firstpagescore where is_select = 1;"
        query = session.execute(query_sql)
        ret = query.fetchall()
        fpRule = {}
        for x in ret:
            fpRule[x[0]] = {
                'score': x[1],
                'maxscore': x[2]
            }
        audit = self._auditRecordRepository.get(session, auditId)
        if not audit:
            return CommonResult(False, '没有找到对应的审核记录')
        deductList = {}
        if (audit.getStatus('expert') == 6 and self.app.config.get(Config.QC_FINAL_STATUS.format(auditType='expert')) == '1') \
                or (audit.getStatus('expert') == 3 and self.app.config.get(Config.QC_FINAL_STATUS.format(auditType='expert')) == '2'):
            expertProblems = self._problemRepository.getListByAuditId(session, auditId, auditType='expert')
            deductList = getDeductDetail(fpRule, expertProblems)
        else:
            hospitalProblems = self._problemRepository.getListByAuditId(session, auditId, auditType='hospital')
            fpProblems = self._problemRepository.getListByAuditId(session, auditId, auditType='firstpage')
            hospDetail = getDeductDetail(fpRule, hospitalProblems)
            fpDetail = getDeductDetail(fpRule, fpProblems)
            deductList = hospDetail
            for k, v in fpDetail.items():
                if deductList.get(k) is None or deductList.get(k) < v:
                    deductList[k] = v
        deductScore = 0
        for qcItem, score in deductList.items():
            deductScore += score
        audit.setArchiveFPScore(100-deductScore)

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
            if auditStep == 'audit' and audit.getStatus(self.auditType) != AuditRecord.STATUS_APPLIED \
                    and audit.getStatus(self.auditType) != AuditRecord.STATUS_RECHECK_REFUSED:
                return CommonResult(False, '病历状态错误, 请刷新页面')
            if auditStep == 'recheck' and audit.getStatus(self.auditType) != AuditRecord.STATUS_APPROVED:
                return CommonResult(False, '病历状态错误, 请刷新页面')
            # 查询当前操作是否是归档操作
            archiveFlag = self.getCustomArchiveConfig(auditStep, audit)
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)

            # 通知emr审核通过
            # if self.app.config.get(Config.QC_APPROVE_NOTIFY_EMR_FIRST.format(auditType=self.auditType)) == '1':
            if archiveFlag:
                r = self.sendApproveRequestToEmr(caseId, operatorCode, comment)
                if not r.isSuccess:
                    return CommonResult(False, f'调用电子病历归档接口失败. {r.message}')
            if auditStep == 'recheck':
                audit.recheckApprove(self.auditType, operatorId, operatorName)
            else:
                audit.approve(self.auditType, operatorId, operatorName, archiveFlag)
            # 审核通过清理问题
            if self.app.config.get(Config.QC_APPROVE_CLEAR_PROBLEM_FIRST.format(auditType=self.auditType)):
                self._problemRepository.clearProblem(session, audit.id, isApproved=True)
            # 计算分数/更新首页问题数目, TODO: 支持配置在哪个环节不计算分数
            self.calculateCaseScore(session, caseId, audit.id, False)
            # self._auditRecordRepository.calculateFirstpageProblemCount(session, audit.id)

            # 归档
            action = '审核通过' if auditStep == 'recheck' else '质控完成'
            if archiveFlag:
                action = '归档'
                c.setStatus(CASE_STATUS_ARCHIVED)
                # 计算归档得分
                self.calculateArchiveScore(session, caseId, audit.id)
                # 计算归档首页得分
                self.calculateArchiveFPScore(session, caseId, audit.id)
            if (audit.getStatus('expert') == 6 and self.app.config.get(Config.QC_FINAL_STATUS.format(auditType='expert')) == '1') \
                    or (audit.getStatus('expert') == 3 and self.app.config.get(Config.QC_FINAL_STATUS.format(auditType='expert')) == '2'):
                print('专家质控已完成，归档分数已专家结果为准')
                audit.setArchiveScore(audit.getScore('expert'))
                score = audit.getScore('expert')
                self.calculateArchiveFPScore(session, caseId, audit.id)
                return CommonResult(True, message=f'专家质控结果：{score}')

            # 写日志
            self._checkHistoryRepository.log(session, caseId, operatorId, operatorName, action, "", "", "病历",
                                             auditStep=auditStep)
            return CommonResult(True)

    def cancelApprove(self, caseId: str, operatorId: str, operatorName: str, comment: str = '', auditStep: str = ''):

        with self.app.mysqlConnection.session() as session:
            c = self._caseRepository.getByCaseId(session, caseId)
            if not c:
                raise ValueError(f'case {caseId} not found')
            audit = self._auditRecordRepository.get(session, c.audit_id)
            archiveFlag = self.getCustomArchiveConfig(auditStep, audit)
            if auditStep == 'recheck':
                if audit.getStatus(self.auditType) != AuditRecord.STATUS_RECHECK_APPROVED:
                    return CommonResult(False, '病历状态错误, 请刷新页面')
            else:
                if audit.getStatus(self.auditType) != AuditRecord.STATUS_APPROVED:
                    return CommonResult(False, '病历状态错误, 请刷新页面')
            operatorId, operatorName, operatorCode = self.ensureUserName(operatorId, operatorName)
            # TODO: 调用emr接口通知取消审核通过, 若失败则放弃后续操作, 可以放在子类实现
            if archiveFlag:
                self.sendCancelApproveRequestToEmr(caseId=caseId, operatorId=operatorCode, comment=comment)
            if auditStep == 'recheck':
                audit.cancelApprove(self.auditType, operatorId, operatorName)
            else:
                audit.cancelAudit(self.auditType, operatorId, operatorName)
            # 恢复因为审核通过被删除的问题
            self._problemRepository.restoreProblemRemovedByApprove(session, audit.id)
            # 重新计算分数
            self.calculateCaseScore(session, caseId, audit.id)
            # TODO:重新计算首页问题数

            # 撤销归档
            if archiveFlag:
                c.setStatus(CASE_STATUS_APPLIED)
            # 专家质控撤销完成，重新计算归档得分
            if self.auditType == AUDIT_TYPE_EXPERT and c.status == CASE_STATUS_ARCHIVED:
                self.calculateArchiveScore(session, caseId, audit.id)
                self.calculateArchiveFPScore(session, caseId, audit.id)

            self._checkHistoryRepository.log(session, c.caseId, operatorId, operatorName, '撤销完成', '', '', '病历',
                                             auditStep=auditStep)
            return CommonResult(True, '撤销成功')
