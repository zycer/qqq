#!/usr/bin/env python3
import logging

from qcaudit.application.auditapplication import AuditApplication as _AuditApplication
from qcaudit.common.const import CASE_STATUS_ARCHIVED, CASE_STATUS_APPLIED, AUDIT_STEP_RECHECK, AUDIT_STEP_AUDIT
# from qcaudit.common.exception import GrpcInvalidArgumentException
from qcaudit.config import Config
from qcaudit.common.result import CommonResult
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.problem.deduct_detail import DeductDetail


class AuditApplication(_AuditApplication):

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
        # 归档配置项对应的质控环节对照
        auditTypeMap = {
            '1': "",
            '2': "department",
            '3': "hospital",
            '4': "firstpage",
            '5': "expert"
        }
        # 归档配置项
        configAuditType = self.app.config.get(Config.QC_ARCHIVE_STEP).split(',')
        finalAuditType = [auditTypeMap.get(item) for item in configAuditType if auditTypeMap.get(item)]
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

    def getDeductDetail(self, caseId, auditId: int = -1):

        # 归档配置项对应的质控环节对照
        auditTypeMap = {
            '1': "",
            '2': "department",
            '3': "hospital",
            '4': "firstpage",
            '5': "expert"
        }
        # 归档配置项
        configAuditType = self.app.config.get(Config.QC_ARCHIVE_STEP).split(',')
        finalAuditType = [auditTypeMap.get(item) for item in configAuditType if auditTypeMap.get(item)]

        with self.app.mysqlConnection.session() as session:
            audit = self._auditRecordRepository.get(session, auditId)
            if not audit:
                return CommonResult(False, '没有找到对应的审核记录')

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
                                                  createTime=reviewTime.strftime('%Y-%m-%d %H:%M:%S'),
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
        """计算病历归档得分
        """
        # 取病案质控和首页质控的问题
        # 每个环节里的问题按照质控点合并分数
        # 取质控规则组里质控点的最高分设置，判断合并之后的扣分和质控点最高扣分谁大谁小
        # 将两个环节的质控点扣分合起来，如果质控点重复取扣分多的
        # 如果有专家质控抽取了归档病历，按照归档病历的结果算
        auditTypeMap = {
            '1': "",
            '2': "department",
            '3': "hospital",
            '4': "firstpage",
            '5': "expert"
        }
        configAuditType = self.app.config.get(Config.QC_ARCHIVE_STEP).split(',')
        finalAuditType = [auditTypeMap.get(item) for item in configAuditType if auditTypeMap.get(item)]

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

    def calculateArchiveFPScore(self, session, caseId: str, audit: AuditRecord):
        """计算归档首页得分
        """
        # 配置项
        auditTypeMap = {
            '1': "",
            '2': "department",
            '3': "hospital",
            '4': "firstpage",
            '5': "expert"
        }
        configAuditType = self.app.config.get(Config.QC_ARCHIVE_STEP).split(',')
        finalAuditType = [auditTypeMap.get(item) for item in configAuditType if auditTypeMap.get(item)]

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
                audit.approve(self.auditType, operatorId, operatorName, archiveFlag)

            # 审核通过清理问题
            if self.app.config.get(Config.QC_APPROVE_CLEAR_PROBLEM_FIRST.format(auditType=self.auditType)):
                self._problemRepository.clearProblem(session, audit.id, isApproved=True)

            # 计算分数/更新首页问题数目, TODO: 支持配置在哪个环节不计算分数
            self.calculateCaseScore(session, caseId, audit.id, False)
            # self._auditRecordRepository.calculateFirstpageProblemCount(session, audit.id)

            # 归档
            action = '审核通过' if auditStep == AUDIT_STEP_RECHECK else '质控完成'
            if archiveFlag:
                action = '归档'
                c.setStatus(CASE_STATUS_ARCHIVED)
                # 计算归档得分
                self.calculateArchiveScore(session, caseId, audit)
                # 计算归档首页得分
                self.calculateArchiveFPScore(session, caseId, audit)

            # 写日志
            self._checkHistoryRepository.log(session, caseId, operatorId, operatorName, action, "", "", "病历", auditStep)

        return CommonResult(True)

    def cancelApprove(self, caseId: str, operatorId: str, username: str, comment: str = '', auditStep: str = ''):
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

            operatorId, username, operatorCode = self.ensureUserName(operatorId, username)

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
                audit.cancelApprove(self.auditType, operatorId, username)
            else:
                audit.cancelAudit(self.auditType, operatorId, username)

            # 恢复因为审核通过被删除的问题
            if self.app.config.get(Config.QC_APPROVE_CLEAR_PROBLEM_FIRST.format(auditType=self.auditType)):
                self._problemRepository.restoreProblemRemovedByApprove(session, audit.id)

            # 重新计算分数
            self.calculateCaseScore(session, caseId, audit.id)
            # TODO:重新计算首页问题数

            self._checkHistoryRepository.log(session, c.caseId, operatorId, username, '撤销完成', '', '', '病历', auditStep)

        return CommonResult(True, '撤销成功')
