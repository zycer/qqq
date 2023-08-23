#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 19:33:31

'''
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterator, Optional

import arrow

from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL, AUDIT_TYPE_ACTIVE
from qcaudit.domain.audit.active_record import ActiveRecord
from qcaudit.domain.case.case import Case
from qcaudit.domain.dict.doctor import Doctor
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.domain.case.req import GetCaseListRequest, GetListRequest
from sqlalchemy import and_, or_, distinct, func, desc


class CaseRepository(RepositoryBase):

    def __init__(self, app, auditType=''):
        super().__init__(app, auditType)
        self.caseModel = app.mysqlConnection['case']
        self.case_model = self.caseModel
        self.auditRecordModel = app.mysqlConnection['audit_record']
        self.sampleRecordItemModel = app.mysqlConnection['sample_record_item']
        self.sampleRecordModel = app.mysqlConnection['sample_record']
        self.firstPageModel = app.mysqlConnection['firstpage']
        self.refuseHistoryModel = app.mysqlConnection['refuse_history']
        self.fp_info_model = app.mysqlConnection['fp_info']
        self.audit_model = self.auditRecordModel

    def getQuery(self, session, outJoinSample=False, sampleFlag=False, isJoinSampleRecord=False, isJoinFirstPage=False, innerJoinEmr=False, problemFlag=False):
        """
        获取query对象
        :param session: mysql链接对象
        :param outJoinSample: 是否outer join
        :param sampleFlag: 是否被抽检过
        :param isJoinSampleRecord: 是否关联sample_record表, 通过抽取时间过滤时需关联该表
        :param isJoinFirstPage: 是否关联firstpage表, 详情时查询主治医生、住院医生时需关联该表
        :param innerJoinEmr: 是否关联emrInfo表, 运行病历抽取列表时需过滤无文书病历
        :return:
        """
        query = session.query(self.caseModel, self.auditRecordModel, self.sampleRecordItemModel).distinct()
        if isJoinFirstPage:
            query = session.query(self.caseModel, self.auditRecordModel, self.sampleRecordItemModel, self.firstPageModel).join(
                self.firstPageModel, self.caseModel.caseId == self.firstPageModel.caseId, isouter=True)
        query = query.join(
            self.auditRecordModel, self.caseModel.audit_id == self.auditRecordModel.id, isouter=True
        ).join(
            self.sampleRecordItemModel, and_(
                self.caseModel.caseId == self.sampleRecordItemModel.caseId,
                self.sampleRecordItemModel.auditType == self.auditType),
            isouter=outJoinSample
        )
        if isJoinSampleRecord:
            query = query.join(self.sampleRecordModel, self.sampleRecordItemModel.recordId == self.sampleRecordModel.id,
                               isouter=outJoinSample)
        if sampleFlag:
            query = query.filter(self.sampleRecordItemModel.id.is_(None)).filter(self.caseModel.originCaseId.is_(None))
        if innerJoinEmr:
            emrInfo_model = self.app.mysqlConnection['emrInfo']
            query = query.join(emrInfo_model, self.caseModel.caseId == emrInfo_model.caseId)
        if problemFlag:
            caseProblem = self.app.mysqlConnection['caseProblem']
            qcItem = self.app.mysqlConnection['qcItem']
            query = query.join(caseProblem, and_(caseProblem.audit_id == self.caseModel.audit_id, caseProblem.auditType == self.auditType, caseProblem.is_deleted == 0)).join(qcItem, qcItem.id == caseProblem.qcItemId, isouter=True)

        return query

    def getListQuery(self, session, req: GetCaseListRequest):
        """根据请求参数生成除过滤和limit之外的query, 子类可以在此基础上修改query

        Args:
            session ([type]): [description]
            req (GetCaseListRequest): [description]
        """
        outJoinSample = True
        isJoinSampleRecord = False
        innerJoinEmr = False
        isJoinFirstPage = False
        problemFlag = False
        if req.openSampleFlag and (req.auditStep == 'audit' or req.auditStep == 'recheck'):
            outJoinSample = False
        sampleFlag = True if req.auditStep == '' else False
        if req.timeType == 3:
            isJoinSampleRecord = True
        if req.auditStep == "" and req.caseType == "running":
            # 运行病历抽取增加内关联emrInfo过滤无文书病历
            innerJoinEmr = True
        if req.minCost not in ("", "-1") or req.maxCost:
            isJoinFirstPage = True
        if req.category and req.category > 0:
            problemFlag = True
        return self.getQuery(session, outJoinSample, sampleFlag, isJoinSampleRecord=isJoinSampleRecord, innerJoinEmr=innerJoinEmr, isJoinFirstPage=isJoinFirstPage, problemFlag=problemFlag)

    def getTags(self, session) -> Dict[int, str]:
        """获取所有的标签
        Args:
            session ([type]): [description]

        Returns:
            Dict[int, str]: [description]
        """
        tags = {}
        for row in session.query(self.app.mysqlConnection['tags']):
            tags[row.code] = row.name
        return tags

    def getActiveListQuery(self, session, caseId=None):
        """
        事中质控列表query
        :return:
        """
        problem_model = self.app.mysqlConnection['caseProblem']
        active_record_model = self.app.mysqlConnection['active_record']
        # 当前存在的人工问题数[包含已整改/未整改]
        now_problem_subquery = session.query(problem_model.caseId, func.count(1).label("now_problem_num"), (100 - func.sum(problem_model.score)).label("active_score")).join(
            self.caseModel, problem_model.caseId == self.caseModel.caseId).filter(
            self.caseModel.dischargeTime.is_(None),
            problem_model.auditType == AUDIT_TYPE_ACTIVE, problem_model.is_deleted == 0, problem_model.from_ai == 0).group_by(
            problem_model.caseId).subquery()
        # 所有人工问题数[包含已删除/未删除]
        all_problem_subquery = session.query(problem_model.caseId, func.count(1).label("problem_all_num")).join(
            self.caseModel, problem_model.caseId == self.caseModel.caseId).filter(
            self.caseModel.dischargeTime.is_(None),
            problem_model.auditType == AUDIT_TYPE_ACTIVE, problem_model.from_ai == 0).group_by(
            problem_model.caseId).subquery()
        active_record_subquery = session.query(active_record_model.caseId, func.count(1).label("qc_num")).join(
            self.caseModel, active_record_model.caseId == self.caseModel.caseId).filter(
            self.caseModel.dischargeTime.is_(None)).group_by(active_record_model.caseId).subquery()
        # 所有问题
        all_p_score_subquery = session.query(problem_model.caseId, func.sum(problem_model.problem_count).label("sum_problem_count"),
                                             (100 - func.sum(problem_model.problem_count * problem_model.score)).label("sum_score")).join(
            self.caseModel, problem_model.caseId == self.caseModel.caseId).filter(
            self.caseModel.dischargeTime.is_(None), problem_model.is_deleted == 0, problem_model.auditType == AUDIT_TYPE_ACTIVE).group_by(
            problem_model.caseId).subquery()
        # 当前存在的人工问题数[仅包含未整改的]
        no_fix_problem_subquery = session.query(problem_model.caseId, func.count(1).label("no_fix_problem_num")).join(
            self.caseModel, problem_model.caseId == self.caseModel.caseId).filter(
            self.caseModel.dischargeTime.is_(None),
            problem_model.auditType == AUDIT_TYPE_ACTIVE, problem_model.is_deleted == 0, problem_model.from_ai == 0, problem_model.is_fix == 0).group_by(
            problem_model.caseId).subquery()

        query = session.query(self.caseModel, active_record_model, now_problem_subquery.c.now_problem_num,
                              now_problem_subquery.c.active_score, all_problem_subquery.c.problem_all_num,
                              active_record_subquery.c.qc_num, all_p_score_subquery.c.sum_problem_count,
                              all_p_score_subquery.c.sum_score, no_fix_problem_subquery.c.no_fix_problem_num).join(
            active_record_model, self.caseModel.active_record_id == active_record_model.id, isouter=True).join(
            now_problem_subquery, self.caseModel.caseId == now_problem_subquery.c.caseId, isouter=True).join(
            all_problem_subquery, self.caseModel.caseId == all_problem_subquery.c.caseId, isouter=True).join(
            active_record_subquery, self.caseModel.caseId == active_record_subquery.c.caseId, isouter=True).join(
            all_p_score_subquery, self.caseModel.caseId == all_p_score_subquery.c.caseId, isouter=True).join(
            no_fix_problem_subquery, self.caseModel.caseId == no_fix_problem_subquery.c.caseId, isouter=True)
        if caseId:
            # 详情
            query = query.filter(self.caseModel.caseId == caseId)

        return query

    def getList(self, session, req: GetCaseListRequest) -> Iterator[Case]:
        """获取病历列表

        Args:
            req (GetCaseListRequest): [description]
        """
        req.validate()
        query = self.getListQuery(session, req) if req.auditType != AUDIT_TYPE_ACTIVE else self.getActiveListQuery(session)
        query = req.apply(query, self.app.mysqlConnection)
        # logging.info("case repo getList query: %s", query)
        # tags = self.getTags(session)
        result = []
        for row in query.all():
            # c.convertTagToName(tags)
            case_model = Case(row[0], row[1], row[2]) if req.auditType != AUDIT_TYPE_ACTIVE else Case(row[0], active_record=row[1], activeProblemNum=row[2], activeScore=row[3], activeProblemAllNum=row[4], activeQcNum=row[5], activeAllProblemNum=row[6], activeAllScore=row[7], activeProblemNoFixNum=row[8])
            result.append(case_model)
        return result

    def count(self, session, req: GetCaseListRequest) -> int:
        req.validate()
        query = self.getListQuery(session, req) if req.auditType != AUDIT_TYPE_ACTIVE else self.getActiveListQuery(session)
        query = req.applyFilter(query, self.app.mysqlConnection)
        return query.count()

    def getByCaseId(self, session, caseId: str) -> Optional[Case]:
        """根据caseId获取病历, 快照也会有一个caseId, 与原始caseId不同"""
        query = self.getQuery(session, outJoinSample=True, isJoinFirstPage=True) if self.auditType != AUDIT_TYPE_ACTIVE else self.getActiveListQuery(session, caseId)
        query = query.filter(self.caseModel.caseId == caseId)
        if query.first():
            if self.auditType != AUDIT_TYPE_ACTIVE:
                caseRow, auditRow, sampleRow, fpRow = query.first()
                c = Case(caseRow, auditRow, sampleRow, fpRow)
            else:
                caseRow, active_record_model, activeProblemNum, activeScore, activeProblemAllNum, activeQcNum, activeAllProblemNum, activeAllScore, activeProblemNoFixNum = query.first()
                c = Case(caseRow, active_record=active_record_model, activeProblemNum=activeProblemNum, activeScore=activeScore,
                         activeProblemAllNum=activeProblemAllNum, activeQcNum=activeQcNum, activeAllProblemNum=activeAllProblemNum,
                         activeAllScore=activeAllScore, activeProblemNoFixNum=activeProblemNoFixNum)

            return c

    def getSnapshot(self, session, caseId: str) -> Optional[Case]:
        """获取运行病历对应的snapshot

        Args:
            caseId (str): [description]

        Returns:
            Case: [description]
        """
        snapshotCaseId = f'{caseId}_{self.auditType}'
        return self.getByCaseId(session, snapshotCaseId)

    def takeSnapshot(self, session, caseId: str) -> Case:
        """创建一个快照

        Args:
            session ([type]): [description]
            caseId (str): [description]

        Returns:
            Case: [description]
        """
        raise NotImplementedError()

    def searchDoctor(self, session, kword):
        doctorModel = self.app.mysqlConnection['doctor']
        doctors = []
        query = session.query(distinct(self.caseModel.attendCode), doctorModel).join(doctorModel,self.caseModel.attendCode == doctorModel.id)
        query = query.filter(or_(doctorModel.name.contains(kword), doctorModel.initials.contains(kword.upper())),doctorModel.useflag==1)
        for row in query.all():
            doctors.append(Doctor(row[1]))
        return doctors

    def getFirstPageInfo(self,session,caseId):
        model = self.app.mysqlConnection['firstpage']
        info = session.query(model).filter(model.caseId == caseId).first()
        if info:
            return info
        return None

    def updateRefuseCount(self, session, caseId):
        """
        撤销驳回 更新病历驳回次数
        :param session:
        :param caseId:
        :return:
        """
        case_info = session.query(self.caseModel).filter(self.caseModel.caseId == caseId).first()
        if case_info and case_info.refuseCount > 0:
            new_refuse_count = case_info.refuseCount - 1
            session.query(self.caseModel).filter(self.caseModel.caseId == caseId).update({"refuseCount": new_refuse_count}, synchronize_session=False)

    def updateRefuseFixDeadline(self, session, caseId, fix_deadline):
        """
        更新case表驳回整改截止时间
        :return:
        """
        session.query(self.caseModel).filter(self.caseModel.caseId == caseId).update({"fix_deadline": fix_deadline}, synchronize_session=False)

    def getCaseDiagnosisByCaseId(self, session, caseIds, isMz=False):
        """
        从首页诊断表查主诊断
        :return:
        """
        fp_diagnosis = self.app.mysqlConnection["fpdiagnosis"] if not isMz else self.app.mysqlConnection["mz_diagnosis"]
        query = session.query(fp_diagnosis).filter(fp_diagnosis.caseId.in_(caseIds))
        queryset = query.all()
        res = {}
        if not isMz:
            sort_queryset = sorted(queryset, key=lambda x: int(x.diagnumber or 999))
            for item in sort_queryset:
                if item.diagnumber is None:
                    item.diagnumber = 999
                if int(item.diagnumber) in (0, 1):
                    res[item.caseId] = item.std_name or item.icdname or ""
                    break
            if not res and queryset:
                item = queryset[0]
                res[item.caseId] = item.std_name or item.icdname or ""
            return res
        caseId_diag_dict = defaultdict(list)
        for item in queryset:
            if not res.get(item.caseId):
                res[item.caseId] = item.name or ""
                caseId_diag_dict[item.caseId].append(item.name or "")
            else:
                if item.name and item.name not in caseId_diag_dict[item.caseId]:
                    res[item.caseId] += "、" + (item.name or "")
        return res

    def getCaseOperationByCaseId(self, session, caseIds):
        """
        手术表查询全部手术
        :return:
        """
        operation = self.app.mysqlConnection["operation"]
        query = session.query(operation).filter(operation.caseId.in_(caseIds)).order_by(operation.caseId, desc(operation.oper_date))
        res = defaultdict(dict)
        for item in query.all():
            if not res[item.caseId].get("name"):
                res[item.caseId]["name"] = item.oper_name
            else:
                res[item.caseId]["name"] += "、" + item.oper_name
            if not res[item.caseId].get("time"):
                res[item.caseId]["time"] = datetime.strptime(item.oper_date, "%Y-%m-%d %H:%M:%S") if item.oper_date else None
        return res

    def update_case_active_id(self, session, caseId, active_id):
        """
        更新case表active_record_id
        :return:
        """
        session.query(self.caseModel).filter(self.caseModel.caseId == caseId).update({"active_record_id": active_id},
                                                                                     synchronize_session=False)

    def update_case_problem_save_flag(self, session, problems):
        """
        更新caseProblem表active_save_flag, is_fix
        存在已保存过的问题，质控医生不满意需将整改标记取消掉
        :return:
        """
        caseProblem = self.app.mysqlConnection["caseProblem"]
        session.query(caseProblem).filter(caseProblem.id.in_(list(problems))).update({"active_save_flag": 1, "is_fix": 0},
                                                                                     synchronize_session=False)

    def save_active_info(self, session, request, doctorName):
        """
        保存记录
        :return:
        """
        obj = ActiveRecord.newObject(self.app)
        obj.setModel(auditType=request.auditType,
                     caseId=request.caseId,
                     operator_id=request.operatorId,
                     operator_name=doctorName,
                     problem_num=len(request.problems),
                     problem_ids=list(request.problems),
                     create_time=arrow.utcnow().to('+08:00').naive,
                     )
        self.add(session, obj)
        session.commit()
        return obj.id

    def getCaseDetail(self, session, caseId):
        query = session.query(self.case_model, self.fp_info_model) \
            .outerjoin(self.fp_info_model, self.case_model.caseId == self.fp_info_model.caseId) \
            .filter(self.case_model.caseId == caseId)
        item = query.first()
        if item:
            return Case(model=item[0], fp_info=item[1])

    def getFPListQuery(self, session):
        query = session.query(self.case_model, self.audit_model, self.fp_info_model) \
            .outerjoin(self.audit_model, self.audit_model.id == self.case_model.audit_id) \
            .outerjoin(self.fp_info_model, self.case_model.caseId == self.fp_info_model.caseId)
        return query

    def getFPCaseList(self, session, req: GetListRequest):
        req.validate()
        query = self.getFPListQuery(session)
        query = req.apply(query, self.app.mysqlConnection)
        result = []
        for item in query.all():
            result.append(Case(item[0], audit_record=item[1], fp_info=item[2]))
        return result

    def getFPCaseListCount(self, session, req):
        query = self.getFPListQuery(session)
        query = req.applyFilter(query, self.app.mysqlConnection)
        count = query.count()
        return count


class DepartmentCaseRepository(CaseRepository):
    def __init__(self, app):
        super().__init__(app, auditType=AUDIT_TYPE_DEPARTMENT)


class HospitalCaseRepository(CaseRepository):
    def __init__(self, app):
        super().__init__(app, auditType=AUDIT_TYPE_HOSPITAL)


class FirstpageCaseRepository(CaseRepository):

    def __init__(self, app):
        super().__init__(app, auditType=AUDIT_TYPE_FIRSTPAGE)
