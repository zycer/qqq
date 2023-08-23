#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 23:07:43

'''
import logging
from collections import defaultdict
from typing import Iterable, List

import arrow
from qcdbmodel.qcdbmodel.models import CaseProblem, CaseProblemRecord as CPR

from qcaudit.common.const import AUDIT_TYPE_ACTIVE, QCITEM_CATEGORY_DICT
from qcaudit.config import Config
from qcaudit.domain.audit.case_problem_record import CaseProblemRecord
from qcaudit.domain.case.case import Case
from qcaudit.domain.problem.problem import Problem, ProblemRecord
from qcaudit.domain.problem.req import GetProblemListRequest
from qcaudit.domain.problem.statsreq import GetProblemStatsRequest
from qcaudit.domain.repobase import RepositoryBase
from sqlalchemy import and_, func, desc, or_


class ProblemRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.problemModel = Problem.getModel(app)
        self.qcItemModel = self.app.mysqlConnection['qcItem']
        self.emrInfoModel = self.app.mysqlConnection['emrInfo']
        self.auditRecordModel = self.app.mysqlConnection['audit_record']
        self.caseModel = self.app.mysqlConnection['case']
        self.cache = {
            "CategoryStatsCounting": {}  # 质控问题统计缓存每个质控点在各环节的病历总数
        }

    def getQuery(self, session):
        query = session.query(self.problemModel, self.qcItemModel, self.emrInfoModel).join(
            self.qcItemModel, self.problemModel.qcItemId == self.qcItemModel.id,
            isouter=True
        ).join(
            self.emrInfoModel, and_(
                self.problemModel.caseId == self.emrInfoModel.caseId,
                self.problemModel.docId == self.emrInfoModel.docId),
            isouter=True
        )
        return query

    def getProblem(self, session, req: GetProblemListRequest) -> List[Problem]:
        query = self.getQuery(session)
        query = req.apply(query, self.app.mysqlConnection)
        problems = []
        # print(query)
        for row in query.all():
            problems.append(Problem(row[0], row[1], row[2]))
        return problems

    def getRefuseProblemCount(self, session, caseId, docId):
        """
        查询文书下被驳回过问题数
        :return:
        """
        total = session.query(self.problemModel).filter(
            self.problemModel.caseId == caseId, self.problemModel.docId == docId, self.problemModel.is_deleted == 0,
            self.problemModel.refuseFlag == 1).count()
        return total

    def getDocRefuseProblemCount(self, session, caseId, auditType):
        """
        查询文书驳回问题数
        :return:
        """
        query = session.query(self.problemModel.docId, func.sum(self.problemModel.refuseFlag).label('ss')).filter(
            self.problemModel.caseId == caseId, self.problemModel.auditType == auditType,
            self.problemModel.is_deleted == 0).group_by(self.problemModel.docId)
        doc_dict = {}
        for item in query.all():
            count = 2 if item.ss > 0 else 1
            doc_dict[item.docId] = count
        return doc_dict

    def getDoctorProblem(self, session, caseId):
        """
        医生端质控评分表查询当前问题
        :return:
        """
        query_status = session.query(self.caseModel).filter(self.caseModel.caseId == caseId).first()
        case_status = query_status.status
        query = session.query(self.problemModel, self.qcItemModel, self.auditRecordModel, self.caseModel).distinct().join(
            self.qcItemModel, self.problemModel.qcItemId == self.qcItemModel.id).join(
            self.caseModel, and_(self.problemModel.caseId == self.caseModel.caseId,
                                 self.problemModel.audit_id == self.caseModel.audit_id)).join(
            self.auditRecordModel, and_(self.problemModel.caseId == self.auditRecordModel.caseId,
                                        self.problemModel.audit_id == self.auditRecordModel.id))
        if case_status == 5:
            query = query.filter(self.problemModel.caseId == caseId, self.problemModel.is_deleted == 0,
                                 self.problemModel.is_fix == 0, self.problemModel.is_ignore == 0,
                                 or_(self.problemModel.refuseFlag == 1, self.problemModel.auditType == "active"))
        elif case_status in (1, 3):
            query = query.filter(1 != 1)
        else:
            query = query.filter(self.problemModel.caseId == caseId, self.problemModel.is_deleted == 0,
                                 self.problemModel.is_fix == 0, self.problemModel.is_ignore == 0,
                                 self.problemModel.refuseFlag == 1)
        problems = []
        for row in query.all():
            problems.append(Problem(row[0], qcItemModel=row[1]))
        return problems

    def problemIsExist(self, session, caseId, docId, requirement, auditType, qcItemId=0):
        """
        判断要创建的问题是否存在
        :return:
        """
        handler = session.query(self.problemModel).filter_by(caseId=caseId, docId=docId, is_deleted=0, auditType=auditType)
        if qcItemId:
            handler = handler.filter_by(qcItemId=qcItemId)
        else:
            handler = handler.filter_by(reason=requirement)
        return handler.first()

    def count(self, session, req: GetProblemListRequest):
        req.validate()
        query = self.getQuery(session)
        query = req.applyFilter(query, self.app.mysqlConnection)
        print(query)
        return query.count()

    def clearProblem(self, session, auditId, isApproved=False):
        """清理所有问题

        Args:
            session ([type]): [description]
            auditId ([type]): [description]
            isApproved (bool, optional): 标记是否是审核通过时清理掉的. Defaults to False.
        """
        session.query(self.problemModel).filter_by(
            audit_id=auditId,
            audit_type=self.auditType,
            is_deleted=0
        ).update({
            'is_deleted': 1,
            'approve_flag': 1 if isApproved else 0
        })

    def restoreProblemRemovedByApprove(self, session, auditId):
        """还原因为审核通过被清理的问题

        Args:
            session ([type]): [description]
            auditId ([type]): [description]
        """
        session.query(self.problemModel).filter_by(
            audit_id=auditId,
            auditType=self.auditType,
            is_deleted=1,
            approve_flag=1
        ).update({
            'is_deleted': 0,
            'approve_flag': 0
        })

    def getListByCaseId(self, session, caseId, withDeleted=False, allAuditType=False) -> List[Problem]:
        """根据caseId获取病历中的问题列表

        Args:
            session ([type]): [description]
            caseId ([type]): [description]

        Returns:
            List[Problem]: [description]
        """
        req = GetProblemListRequest(
            caseId=caseId,
            withDeleted=withDeleted
        )
        if not allAuditType:
            req.auditType = self.auditType
        return self.getProblem(session, req)

    def getListByAuditId(self, session, auditId: int, withDeleted=False, allAuditType=False, auditType='') -> List[
        Problem]:
        """根据auditId获取病历中的当前问题列表

        Args:
            session ([type]): [description]
            auditId ([type]): [description]

        Returns:
            List[Problem]: [description]
        """
        req = GetProblemListRequest(
            auditId=auditId,
            withDeleted=withDeleted
        )
        if not auditType:
            auditType = self.auditType
        if not allAuditType:
            req.auditType = auditType
        return self.getProblem(session, req)

    def count(self, session, req: GetProblemListRequest):
        """计算结果数量
        """
        query = self.getQuery(session)
        query = req.apply(query, self.app.mysqlConnection)
        return query.count()

    def countByAuditId(self, session, auditId: int, withDeleted=False, allAuditType=False) -> int:
        """获取auditId对应的问题数量
        """
        req = GetProblemListRequest(
            auditId=auditId,
            withDeleted=withDeleted
        )
        if not allAuditType:
            req.auditType = self.auditType
        return self.count(session, req)

    def getListByEmr(self, session, caseId: str, docId: str, auditId: int = 0, qcItemId=None, withDeleted=False,
                     allAuditType=False) -> List[Problem]:
        """获取文书版本对应的问题

        Args:
            session ([type]): [description]
            caseId ([type]): [description]
            docId ([type]): [description]
            auditId (int): 只获取对应版本的问题. Defaults to -1.
        """
        req = GetProblemListRequest(
            caseId=caseId,
            docId=docId,
            auditId=auditId,
            qcItemId=qcItemId,
            withDeleted=withDeleted
        )
        if not allAuditType:
            req.auditType = self.auditType
        return self.getProblem(session, req)

    def add(self, session, problem: Problem):
        """创建问题

        Args:
            session ([type]): [description]
            problem (Problem): [description]
        """
        session.add(problem.model)

    def delete(self, session, id):
        """删除问题

        Args:
            session ([type]): [description]
            id ([type]): [description]
        """
        session.query(self.problemModel).filter_by(
            id=id
        ).delete()

    def get(self, session, id):
        """获取问题详情

        Args:
            session ([type]): [description]
            id ([type]): [description]
        """
        query = self.getQuery(session)

        row = query.filter(self.problemModel.id == id).first()
        if row:
            return Problem(row[0], row[1], row[2])

    def getByIds(self, session, ids: List[int]) -> List[Problem]:
        """获取问题详情

        Args:
            session ([type]): [description]
            id ([type]): [description]
        """
        query = self.getQuery(session)
        problems = []
        for row in query.filter(self.problemModel.id.in_(ids)):
            problems.append(Problem(row[0], row[1], row[2]))
        return problems

    def cancelRefused(self, session, auditId):
        """将质控问题的驳回标记还原

        Args:
            session ([type]): [description]
            auditId ([type]): [description]
        """
        for p in self.getListByAuditId(session, auditId):
            p.cancelRefuse()

    def getFixedProblemQuery(self, req: GetProblemStatsRequest):
        """质控问题统计
        """
        if req.fixed == 1:
            return self._queryLatestProblems(req)
        if req.fixed == 2:
            return self._queryFixedProblems(req)
        return self._queryAllProblems(req)

    def _queryLatestProblems(self, req: GetProblemStatsRequest):
        return f"""select caseProblem.caseId, caseProblem.qcItemId, 1 as pstatus from caseProblem 
          left join `case` on `case`.audit_id = caseProblem.audit_id 
          left join qcItem on caseProblem.qcItemId = qcItem.id {self._sampleJoin(req)}
        {self._whereFilter(req)}
        group by caseProblem.caseId, caseProblem.qcItemId"""

    def _queryFixedProblems(self, req: GetProblemStatsRequest):
        return f"""select caseId, qcItemId, 0 as pstatus
        from (
          select caseProblem.caseId, caseProblem.qcItemId, if(caseProblem.audit_id = `case`.audit_id and caseProblem.is_deleted = 0, 1, 0) as flag
          from caseProblem
            left join `case` on `case`.caseId = caseProblem.caseId 
            left join qcItem on caseProblem.qcItemId = qcItem.id {self._sampleJoin(req)}
          {self._whereFilter(req)}) subquery
        group by caseId, qcItemId having max(flag) = 0"""

    def _queryAllProblems(self, req: GetProblemStatsRequest):
        return f"""select caseId, qcItemId, max(flag) as pstatus
        from (
          select caseProblem.caseId, caseProblem.qcItemId, if(caseProblem.audit_id = `case`.audit_id and caseProblem.is_deleted = 0, 1, 0) as flag
          from caseProblem
            left join `case` on `case`.caseId = caseProblem.caseId 
            left join qcItem on caseProblem.qcItemId = qcItem.id {self._sampleJoin(req)}
          {self._whereFilter(req)}) subquery
        group by caseId, qcItemId"""

    def _whereFilter(self, req):
        where = "where `case`.id > 0"
        # 现存问题
        if req.fixed == 1:
            where += " and caseProblem.is_deleted = 0"
        # 质控环节是否是抽查环节
        if self.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=req.auditType)) == '1':
            where += f" and sample_record_item.id > 0"
        # 根据配置过滤病历类型
        patientType = self.app.config.get(Config.QC_DOCTOR_WAIT_APPLY_PATIENT_TYPE, None)
        if patientType:
            where += f" and `case`.patientType = {patientType}"
        # 事中问题统计只查询未申请状态的病历
        if req.auditType == AUDIT_TYPE_ACTIVE:
            where += f" and `case`.status = 5"
        elif self.app.config.get(Config.QC_NOT_APPLY_AUDIT.format(auditType=req.auditType)) != '1':
            # 如果配置项中未申请病历在当前节点中不需要质控（1是需要质控），过滤质控问题对应的病历状态不包含未申请病历，默认不包含未申请
            where += f" and `case`.status <> 5"

        return f"{where} and {req.getFilterSql()}"

    def _sampleJoin(self, req):
        if self.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=req.auditType)) == '1':
            return f"left join sample_record_item on sample_record_item.caseId = `case`.caseId and sample_record_item.auditType = '{req.auditType}'"
        return ""

    def getCaseProblemQuery(self, session, req: GetProblemStatsRequest):
        caseModel = self.app.mysqlConnection['case']
        qcItemModel = self.app.mysqlConnection['qcItem']
        sampleRecordItemModel = self.app.mysqlConnection['sample_record_item']

        # select caseId, qcItemId
        query = session.query(self.problemModel.caseId, self.problemModel.qcItemId). \
            outerjoin(caseModel, self.problemModel.audit_id == caseModel.audit_id). \
            outerjoin(qcItemModel, self.problemModel.qcItemId == qcItemModel.id)

        # 如果是抽检环节，增加过滤条件只查询抽检到的病历
        if self.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=req.auditType)) == '1':
            query = query.outerjoin(sampleRecordItemModel, and_(
                caseModel.caseId == sampleRecordItemModel.caseId, sampleRecordItemModel.auditType == req.auditType))
            query = query.filter(sampleRecordItemModel.id > 0)

        # 根据配置过滤病历类型
        patientType = self.app.config.get(Config.QC_DOCTOR_WAIT_APPLY_PATIENT_TYPE, None)
        if patientType:
            query = query.filter(caseModel.patientType == patientType)
        # 事中问题统计只查询未申请状态的病历
        if req.auditType == AUDIT_TYPE_ACTIVE:
            query = query.filter(caseModel.status == 5)
        elif self.app.config.get(Config.QC_NOT_APPLY_AUDIT.format(auditType=req.auditType)) != '1':
            # 如果配置项中未申请病历在当前节点中不需要质控（1是需要质控），过滤质控问题对应的病历状态不包含未申请病历，默认不包含未申请
            query = query.filter(caseModel.status != 5)
        # 过滤请求
        query = req.applyFilter(query, self.app.mysqlConnection)
        # group by caseId, qcItemId
        query = query.group_by(self.problemModel.caseId, self.problemModel.qcItemId)
        return query.subquery()

    def getCaseProblemQuery_caseId(self, session, req: GetProblemStatsRequest):
        """质控问题统计简化版查询
        select caseId from caseProblem
        """
        caseModel = self.app.mysqlConnection['case']
        qcItemModel = self.app.mysqlConnection['qcItem']
        sampleRecordItemModel = self.app.mysqlConnection['sample_record_item']

        # select caseId, qcItemId
        query = session.query(self.problemModel.caseId). \
            outerjoin(caseModel, self.problemModel.audit_id == caseModel.audit_id). \
            outerjoin(qcItemModel, self.problemModel.qcItemId == qcItemModel.id)

        # 如果是抽检环节，增加过滤条件只查询抽检到的病历
        if self.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=req.auditType)) == '1':
            query = query.outerjoin(sampleRecordItemModel, and_(
                caseModel.caseId == sampleRecordItemModel.caseId, sampleRecordItemModel.auditType == req.auditType))
            query = query.filter(sampleRecordItemModel.id > 0)

        # 根据配置过滤病历类型
        patientType = self.app.config.get(Config.QC_DOCTOR_WAIT_APPLY_PATIENT_TYPE, None)
        if patientType:
            query = query.filter(caseModel.patientType == patientType)
        # 如果配置项中未申请病历在当前节点中不需要质控（1是需要质控），过滤质控问题对应的病历状态不包含未申请病历，默认不包含未申请
        if self.app.config.get(Config.QC_NOT_APPLY_AUDIT.format(auditType=req.auditType)) != '1':
            query = query.filter(caseModel.status < 5)
        if req.auditType == AUDIT_TYPE_ACTIVE:
            query = query.filter(caseModel.status == 5)
        # 过滤请求
        query = req.applyFilter(query, self.app.mysqlConnection)
        return query.subquery()

    def getCategoryStats(self, session, req: GetProblemStatsRequest):
        """统计目前的问题和存在该问题的病历份数
        """
        subquery = self.getFixedProblemQuery(req)

        result, count = [], 0

        sql = f"select qcItemId, count(*) case_count from ({subquery}) sq group by qcItemId order by case_count desc"
        query = session.execute(sql)
        for qcItemId, counting in query.fetchall():
            result.append({
                "qcItemId": qcItemId,
                "counting": counting,
            })
            count += 1
            # 将统计的病历总数缓存起来，查询明细不再计算总数
            if counting > 1000:
                key = f"{req.auditType}-{req.branch}-{req.ward}-{req.department}-{req.attending}-{req.startTime}-{req.endTime}-{req.caseType}-{req.deptType}-{qcItemId}"
                self.cache['CategoryStatsCounting'][key] = counting

        return result, count

    def getCategoryStatsCase(self, session, req: GetProblemStatsRequest):
        """查询存在某个质控问题的病历列表
        """
        subquery = self.getFixedProblemQuery(req)

        count = 0
        if req.withTotal:
            cache_key = f"{req.auditType}-{req.branch}-{req.ward}-{req.department}-{req.attending}-{req.startTime}-{req.endTime}-{req.caseType}-{req.deptType}-{req.qcItemsId[0] if req.qcItemsId else 0}"
            cache_counting = self.cache.get('CategoryStatsCounting', {}).get(cache_key)
            if cache_counting and cache_counting > 0:
                logging.info(f"read from cache, counting = {cache_counting}")
                count = cache_counting
            else:
                query = session.execute(f"select count(*) from ({subquery}) as tmp")
                count = query.fetchone()[0]

        sql = f"select caseId, pstatus from ({subquery}) sq group by caseId, pstatus "
        if 0 < req.size < 500:
            sql += f"limit {req.start},{req.size}"
        queryset = session.execute(sql)

        result = []
        for caseId, pstatus in queryset.fetchall():
            result.append({
                "caseId": caseId,
                "pstatus": {1: "现存", 0: "已解决"}.get(pstatus)
            })

        return result, count

    def getCategoryStatsProblem(self, session, req, caseIds):
        """
        根据qcItemId caseIds 查问题 创建人、时间，整改人、时间，AI标记
        :return:
        """
        qcItemId = req.qcItemsId[0] if req.qcItemsId else 0
        query = session.query(self.problemModel).filter(self.problemModel.qcItemId == qcItemId, self.problemModel.caseId.in_(caseIds))
        problem_data = defaultdict(dict)
        no_delete_caseIds = []
        for item in query.all():
            if item.is_deleted == 0:
                no_delete_caseIds.append(item.caseId)
            create_time = item.created_at.strftime("%Y-%m-%d") if item.created_at else ""
            fix_time = item.fix_time.strftime("%Y-%m-%d") if item.fix_time else ""
            create_doctor = item.operator_name or ""
            if create_doctor.upper() == "大数AI":
                create_doctor = "AI"
            problem_data[item.caseId] = {"from_ai": item.from_ai or 0, "create_doctor": create_doctor,
                                         "create_time": create_time, "fix_doctor": item.fix_doctor, "fix_time": fix_time}
        # 质控点未删除的病历, 将解决人、解决时间去掉
        for caseId in no_delete_caseIds:
            problem_data[caseId]["fix_doctor"] = ""
            problem_data[caseId]["fix_time"] = ""
        return problem_data

    def getCategoryStatsCaseDetail(self, session, caseList):
        result = []
        caseModel = self.app.mysqlConnection['case']
        handler = session.query(caseModel.id, caseModel.caseId, caseModel.patientId, caseModel.visitTimes,
                                caseModel.name, caseModel.age, caseModel.ageUnit, caseModel.gender, caseModel.branch,
                                caseModel.department, caseModel.outDeptName, caseModel.attendDoctor,
                                caseModel.admitTime, caseModel.dischargeTime, caseModel.status, caseModel.wardName,
                                caseModel.tags, caseModel.inpNo).filter(caseModel.caseId.in_(caseList))
        handler = handler.order_by(caseModel.id)
        for caseRow in handler.all():
            result.append(Case(caseRow))
        return result

    def getCaseQuery(self, session, req, caseIds):
        """
        筛选条件在 from `case` where 下写
        :return:
        """
        caseModel = self.app.mysqlConnection['case']
        query = session.query(caseModel).filter(caseModel.caseId.in_(caseIds))

        if req.branch:
            query = query.filter(
                caseModel.branch == req.branch
            )
        if req.ward:
            query = query.filter(
                caseModel.wardName == req.ward
            )
        # TODO 根据 auditType 决定是 department 还是 outDeptName
        if req.department:
            query = query.filter(
                caseModel.department == req.department
            )
        if req.attending:
            query = query.filter(
                caseModel.attendDoctor == req.attending
            )

        if req.caseType == "running" or req.auditType == AUDIT_TYPE_ACTIVE:
            query = req.applyDateRangeFilter(
                query,
                field='admitTime',
                start=req.startTime,
                end=req.getDischargeEndTime(),
                model=caseModel
            )
        else:
            query = req.applyDateRangeFilter(
                query,
                field='dischargeTime',
                start=req.startTime,
                end=req.getDischargeEndTime(),
                model=caseModel
            )

        # query = query.group_by(caseModel.caseId)
        return query

    def getRecordList(self, session, request):
        """
        查询问题日志列表
        :return:
        """
        query = session.query(self.problemModel.reason, self.problemModel.qcItemId, self.qcItemModel.standard_emr,
                              self.qcItemModel.category, self.problemModel.is_deleted, self.problemModel.auditType,
                              self.problemModel.audit_id.label("cp_audit_id"),
                              self.caseModel.audit_id.label("c_audit_id")).distinct().join(
            self.qcItemModel, self.problemModel.qcItemId == self.qcItemModel.id).join(
            self.caseModel, self.problemModel.caseId == self.caseModel.caseId).filter(
            self.problemModel.caseId == request.caseId)
        if request.reason:
            query = query.filter(self.problemModel.reason.like("%{}%".format(request.reason)))
        if request.docType:
            query = query.filter(self.qcItemModel.standard_emr.like("%{}%".format(request.docType)))
        if request.problemType and QCITEM_CATEGORY_DICT.get(request.problemType):
            query = query.filter(self.qcItemModel.category == QCITEM_CATEGORY_DICT[request.problemType])
        if request.startTime:
            query = query.filter(self.problemModel.created_at >= request.startTime)
        if request.endTime:
            query = query.filter(self.problemModel.created_at <= request.endTime)
        if request.createDoctor:
            query = query.filter(self.problemModel.operator_name.like("%{}%".format(request.createDoctor)))

        res = []
        for item in query.all():
            t = ProblemRecord(*item)
            res.append(t)
        return res

    def recordProblemAction(self, session, caseId, qcItemId, action, doctor_code, doctor_name, auditType):
        """
        记录问题操作
        :return:
        """
        obj = CaseProblemRecord.newObject(self.app)
        obj.setModel(
            auditType=auditType,
            caseId=caseId,
            qcItemId=qcItemId,
            doctor_code=doctor_code,
            action=action,
            doctor_name=doctor_name,
            create_time=arrow.utcnow().to('+08:00').naive,
        )
        self.add(session, obj)

    @classmethod
    def getQcItemIdByProblemIds(cls, session, problem_ids):
        """
        根据问题id获取质控点id
        :return:
        """
        query = session.query(CaseProblem.qcItemId).distinct().filter(CaseProblem.id.in_(problem_ids))
        return [item[0] for item in query.all()]

    @classmethod
    def getProblemRecordDetail(cls, session, request):
        """
        查询问题日志详情
        :return:
        """
        query = session.query(CPR).filter(CPR.caseId == request.caseId, CPR.qcItemId == request.qcItemId)
        if request.auditType:
            query = query.filter(CPR.auditType == request.auditType)
        query = query.order_by(CPR.create_time)
        res = []
        for item in query.all():
            session.expunge(item)
            res.append(item)
        return res
