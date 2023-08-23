#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 19:58:44

'''
import logging
from dataclasses import dataclass, field
import json
from typing import List, Mapping
# from qcaudit.common.exception import GrpcInvalidArgumentException
from qcaudit.common.const import CASE_STATUS_ARCHIVED, AUDIT_TYPE_ACTIVE
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.case.case import CaseType
from qcaudit.domain.dict import DepartmentRepository
from qcaudit.domain.req import ListRequestBase, SortField
import arrow
from arrow.api import factory
from sqlalchemy import case, and_, or_
from sqlalchemy import func, text


@dataclass
class TagSortField(SortField):
    # 字段中出现的字符的优先级
    # way=DESC时最前面的优先级越高, 不指定的优先级最低
    # way=ASC时最前面的优先级最低, 不指定的优先级最高
    terms: List[str] = field(default_factory=list)

    def apply(self, query, model):
        # 增加一个伪列仅用来排序
        maxWeight = len(self.terms)
        # way=DESC时最前面的优先级越高, 不指定的优先级最低
        if self.way == 'desc':
            whens = {}
            weight = maxWeight
            for t in self.terms:
                whens[t] = weight
                weight -= 1
            query = query.order_by(case(
                value=getattr(model, self.field),
                whens=whens,
                else_=0
            ))
        else:
            # way=ASC时最前面的优先级最低, 不指定的优先级最高
            whens = {}
            weight = 0
            for t in self.terms:
                whens[t] = weight
                weight += 1
            query = query.order_by(case(
                value=getattr(model, self.field),
                whens=whens,
                else_=maxWeight
            ))
        return query


@dataclass
class GetCaseListRequest(ListRequestBase):
    """获取病历列表的请求参数
    """
    # 患者Id
    patientId: str = ''
    # 患者姓名
    patientName: str = ''
    # caseId
    caseId: str = ''
    # 院区
    branch: str = ''
    # 科室
    department: str = ''
    # 病历状态
    status: List[int] = field(default_factory=list)
    # 甲乙丙
    rating: str = ''
    # 分数区间
    minScore: int = 0
    maxScore: int = 100
    # 病区
    ward: str = ''
    # attending doctor
    attend: str = ''
    # 是否有首页
    firstPageFlag: str = ''
    # 出院开始时间
    startTime: str = ''
    # 出院结束时间
    endTime: str = ''
    # 是否整改
    refused: int = 0
    # 是否有问题
    problemFlag: int = 0
    # 重点标记, 重点标记是or的关系, 命中任何一个标签即召回
    tags: List[str] = field(default_factory=list)
    # 重点病历标记抽取
    sampleByTags: List[str] = field(default_factory=list)
    # 过滤抽样信息
    sampleRecordId: int = 0
    # 过滤抽样任务的分配医生
    sampleExpert: str = ''
    # 包含哪些病历类型, 1、运行病历, 2、运行病历的快照, 3、终末病历，4、归档病历
    includeCaseTypes: List[CaseType] = field(default_factory=list)
    # ai质控状态
    autoReviewFlag: int = 0
    # 审核人
    reviewer: str = ''
    # 分配医生
    assignDoctor: str = ''
    # 病案等级
    archiveRating: str = ''

    # 排除已抽中的审核类型
    excludeSampledCase: str = ''
    # 只保留已经抽中的病历
    onlySampledCase: str = ''
    # 审核类型, 与其他参数配合使用, active-事中质控
    auditType: str = ''
    # 环节
    auditStep: str = ''
    # 是否终审
    isFinal: bool = False
    # 环节
    caseType: str = ''
    # 是否需要经过前道流程控制
    precondition: str = ""
    # 是否需要过滤已出院未申请病历
    not_apply: int = 2
    # 内外科类型 0-全部, 1-内科, 2-外科
    deptType: int = 0
    # 查询时间类型, 1-出院时间, 2-质控时间, 3-抽取时间, 4-签收时间, 5-入院时间
    timeType: int = 1
    # 疾病诊断查询条件
    diagnosis: str = ''
    # 手术操作查询条件
    operation: str = ''
    # 退回返修次数
    refuseCount: str = ''
    # 是否开启抽取环节
    openSampleFlag: bool = False
    # 是否允许抽取归档
    sampleArchiveFlag: bool = False

    # 请求字段与数据库字段的映射, 默认一致
    FIELD_MAP = {
        'department': 'outDeptName',
        'rating': 'caseRating',
        'ward': 'wardName',
        'attend': 'attendDoctor'
    }
    # 精确匹配字段
    EQUAL_FILTER_FIELDS = [
        'branch', 'firstPageFlag',
        'rating',
    ]
    # 病历类型 1=门诊，2=住院，3=急诊 `case`.patientType
    visitType: str = ''
    # 是否超整改时限标记, 0-全部, 1-是, 2-否
    fixOvertimeFlag: int = 0
    # 权限字段
    pField: str = ""
    # 权限字段筛选列表
    pList: List[str] = field(default_factory=list)
    # 上线开始时间，过滤质控列表和病历列表和医生端待申请病历列表
    onlineStartTime: str = ''
    # 诊疗组
    group: str = ""
    # 总费用
    minCost: int = 0
    # 总费用
    maxCost: int = 0
    # 质控问题类别
    category: int = 0
    # 事中质控次数, 0,1,2,3,4,5,>5
    activeQcNum: str = ''
    # 事中人工问题数, 0, 1, 2, 3, 4, 5, > 5
    activeManProblemNum: str = ""
    # 事中人工问题状态, 无问题, 未整改, 部分整改, 全部整改
    activeProblemStatus: str = ""
    # 住院天数最小值(不包含)
    minDays: int = 0
    # 住院天数最大值(包含)
    maxDays: int = 0
    # 超整改时限天数 <1, 1, 2, 3, 4, 5, > 5
    overtime: str = ''

    def getDischargeEndTime(self):
        """出院截止时间是日期的, 补充时间部分
        """
        if self.endTime:
            if len(self.endTime) <= 10:
                return f'{self.endTime} 23:59:59'
            else:
                return self.endTime
        return None

    def getDischargeStartTime(self):
        """获取出院时间开始时间
        """
        return self.startTime or None

    def applyPageSize(self, query, connection):
        """应用翻页参数"""

        # 最后附加上id排序，保证顺序固定
        query = query.order_by(text(f'case.id'))
        return query.slice(self.start, self.start + self.size)

    def applyFilter(self, query, connection):
        # 先处理精确匹配的字段
        # TODO: 病历等级和病历得分的过滤可能得根据auditType分别查不同的字段, 而且查询的是audit_record表
        model = connection['case']
        auditModel = connection['audit_record']
        sampleRecordModel = connection['sample_record']
        sampleRecordItemModel = connection['sample_record_item']
        firstpageModel = connection['firstpage']
        # 如果不是抽取环节 根据用户权限筛选，+ 抽取分配的任务
        if not self.caseType and self.auditType != AUDIT_TYPE_ACTIVE:
            field_dict = {'dept': 'outDeptName', 'ward': 'wardName'}
            if self.pField and self.pField in field_dict:
                field = field_dict.get(self.pField, None)
                if field:
                    query = query.filter(or_(getattr(model, field).in_(self.pList), sampleRecordItemModel.id > 0))
        if self.precondition and CaseType.FINAL not in self.includeCaseTypes:
            # 存在前提条件流程且非抽取列表
            precondition = self.precondition.split(",")
            for pre in precondition:
                audit_record_field = AuditRecord.getOperatorFields(pre, self.isFinal)
                query = query.filter(getattr(auditModel, audit_record_field.statusField).in_([3, 6]))
        if self.caseType != "running" and self.not_apply and int(self.not_apply) == 2:
            # 运行病历抽取列表不需要过滤 已出院未申请的病历
            query = query.filter(getattr(model, "status") != 5)
        # 终末病历抽取列表不需要显示已经批量归档的病历
        if self.sampleArchiveFlag and self.auditStep == "":
            field = AuditRecord.getOperatorFields(self.auditType, self.isFinal)
            query = query.filter(getattr(auditModel, field.statusField) == 1)
        # 过滤病历类型，住院病历 or 门急诊
        if self.visitType:
            query = query.filter(model.patientType == self.visitType)

        # 过滤病历类型
        if self.includeCaseTypes:
            # query = query.filter(getattr(model, 'caseType').in_(tuple(self.includeCaseTypes)))
            exps = []
            # 终末病历
            if CaseType.FINAL in self.includeCaseTypes:
                exps.append(model.dischargeTime.isnot(None))
            # 归档病历
            if CaseType.ARCHIVE in self.includeCaseTypes:
                exps.append(and_(model.dischargeTime.isnot(None), model.status == CASE_STATUS_ARCHIVED))
            # 运行病历的快照
            if CaseType.SNAPSHOT in self.includeCaseTypes:
                exps.append(model.originCaseId.isnot(None))
            # 运行病历
            if CaseType.ACTIVE in self.includeCaseTypes:
                exps.append(and_(model.dischargeTime.is_(None), model.originCaseId.is_(None)))
                if self.auditStep == "":
                    # 运行病例的抽取列表, 不展示被抽取过的病例
                    query = query.filter(
                        model.caseId.notin_(text('(select distinct originCaseId from sample_record_item where auditType = "%s" and originCaseId is not null)' % self.auditType)))
            query = query.filter(or_(*exps))

        if not self.openSampleFlag:
            # 未开启抽取环节的节点, 需要仅查询originCaseId is None的数据,
            # 开启抽取环节的节点已做内连接关联sample_record_item表查询抽取记录
            query = query.filter(model.originCaseId.is_(None))
        if self.auditType == AUDIT_TYPE_ACTIVE:
            # 事中时限制病历范围
            query = query.filter(model.dischargeTime.is_(None))
        if self.patientId:
            # 病历号查询可以精确查询患者id或者模糊查询患者姓名
            if self.includeCaseTypes and CaseType.ARCHIVE in self.includeCaseTypes:
                query = query.filter(and_(model.dischargeTime.isnot(None), model.status == CASE_STATUS_ARCHIVED))
            query = query.filter(or_(model.patientId == self.patientId, model.inpNo == self.patientId, model.name.like('%' + self.patientId + '%')))

            return query

        # 根据出院时间过滤，质控列表和审核列表只显示上线之后出院的病历，抽取页面不限制
        if not self.caseType and self.onlineStartTime:
            query = query.filter(or_(model.dischargeTime > self.onlineStartTime, sampleRecordItemModel.id > 0))

        now = arrow.utcnow().to('+08:00').naive
        if self.fixOvertimeFlag == 1:
            query = query.filter(model.fix_deadline < now)
        elif self.fixOvertimeFlag == 2:
            query = query.filter(model.fix_deadline >= now)

        # 科室 出院科室或者入院科室
        if self.department:
            value = self.department.split(",")
            query = query.filter(
                or_(and_(model.department.in_(value), model.outDeptName == None), model.outDeptName.in_(value)))
        # 诊疗组
        if self.group:
            if self.group != "all":
                query = query.filter(model.medicalGroupName.in_(self.group.split(",")))
            else:
                query = query.filter(model.medicalGroupName.isnot(None))
        # 病区
        if self.ward:
            query = query.filter(model.wardName.in_(self.ward.split(",")))
        # 责任医生
        if self.attend:
            query = query.filter(model.attendDoctor.in_(self.attend.split(",")))
        # 住院天数
        if self.minDays not in ("", "-1", None):
            query = query.filter(model.inpDays > float(self.minDays))
        if self.maxDays:
            query = query.filter(model.inpDays <= float(self.maxDays))

        for filter_field in self.EQUAL_FILTER_FIELDS:
            value = getattr(self, filter_field)
            if not value:
                continue
            dbField = self.FIELD_MAP.get(filter_field, filter_field)
            query = self.applyEqualFilter(
                query,
                field=dbField,
                value=value,
                model=model
            )
        # 过滤状态
        if self.status and self.auditType != AUDIT_TYPE_ACTIVE:
            if not self.auditType:
                raise #GrpcInvalidArgumentException(message='状态查询必须有auditType')
            field = AuditRecord.getOperatorFields(self.auditType, self.isFinal)
            query = query.filter(
                getattr(auditModel, field.statusField).in_(self.status)
            )

        # 审核人
        if self.reviewer:
            if not self.auditType:
                raise #GrpcInvalidArgumentException(message='审核人查询必须有auditType')
            if self.auditType != AUDIT_TYPE_ACTIVE:
                field = AuditRecord.getOperatorFields(self.auditType, self.isFinal)
                query = query.filter(
                    getattr(auditModel, field.reviewerNameField) == self.reviewer
                )
            else:
                filter_sql = 'active_record.operator_name = "%s"' % self.reviewer
                query = query.filter(text(filter_sql))

        # 继续处理特殊字段
        if self.timeType in (0, 1):
            # 出院时间
            if self.caseType == "running":
                query = self.applyDateRangeFilter(
                    query,
                    field='admitTime',
                    start=self.getDischargeStartTime(),
                    end=self.getDischargeEndTime(),
                    model=model
                )
            else:
                query = self.applyDateRangeFilter(
                    query,
                    field='dischargeTime',
                    start=self.getDischargeStartTime(),
                    end=self.getDischargeEndTime(),
                    model=model
                )
        elif self.timeType == 2:
            # 质控时间
            aField = AuditRecord.getOperatorFields(self.auditType, isFinal=False)
            query = self.applyDateRangeFilter(
                query,
                field=aField.reviewTimeField,
                start=self.getDischargeStartTime(),
                end=self.getDischargeEndTime(),
                model=auditModel
            )
        elif self.timeType == 3:
            # 抽取时间
            query = self.applyDateRangeFilter(
                query,
                field="createdAt",
                start=self.getDischargeStartTime(),
                end=self.getDischargeEndTime(),
                model=sampleRecordModel
            )
        elif self.timeType == 4:
            query = self.applyDateRangeFilter(
                query,
                field="receiveTime",
                start=self.getDischargeStartTime(),
                end=self.getDischargeEndTime(),
                model=auditModel
            )
        elif self.timeType == 5:
            query = self.applyDateRangeFilter(
                query,
                field='admitTime',
                start=self.getDischargeStartTime(),
                end=self.getDischargeEndTime(),
                model=model
            )
        # caseId
        if self.caseId:
            caseId = self.caseId.strip()
            if len(caseId) > 7:
                query = self.applyEqualFilter(query, 'caseId', caseId, model)
            else:
                query = self.applyLikeFilter(query, 'caseId', caseId, model)
        # 姓名
        if self.patientName:
            query = self.applyLikeFilter(query, 'name', self.patientName, model)

        # 内外科
        if self.deptType:
            dept_list = DepartmentRepository.DEPT_TYPE_DEPARTMENT[self.deptType]
            query = query.filter(or_(getattr(model, "outDeptName").in_(dept_list),
                                     getattr(model, "department").in_(dept_list)))

        # 是否整改
        if self.refused == 1:
            query = self.applyEqualFilter(query, 'refuseCount', 0, model)
        elif self.refused == 2:
            query = query.filter(getattr(model, 'refuseCount') > 0)

        # 是否有问题
        if self.problemFlag:
            if not self.auditType:
                raise #GrpcInvalidArgumentException(message='问题数量查询必须有auditType')
            if self.auditType == AUDIT_TYPE_ACTIVE:
                if self.problemFlag == 1:  # 有问题
                    filter_sql = "sum_problem_count > 0"
                    query = query.filter(text(filter_sql))
                elif self.problemFlag == 2:
                    filter_sql = "(sum_problem_count = 0 or sum_problem_count is null)"
                    query = query.filter(text(filter_sql))
            else:
                field = AuditRecord.getOperatorFields(self.auditType, self.isFinal)
                if self.problemFlag == 1:  # 有问题
                    query = query.filter(getattr(auditModel, field.problemCountField) > 0)
                elif self.problemFlag == 2:
                    query = query.filter(or_(getattr(auditModel, field.problemCountField) == 0,
                                             getattr(auditModel, field.problemCountField).is_(None)))

        # 过滤抽样医生
        sampleRecordItemModel = connection['sample_record_item']
        if self.sampleExpert:
            query = self.applyEqualFilter(query, 'expertName', self.sampleExpert, sampleRecordItemModel)
        if self.sampleRecordId:
            query = self.applyEqualFilter(
                query, 'recordId', self.sampleRecordId,
                sampleRecordItemModel
            )

        # 疾病诊断条件
        if self.diagnosis:
            icdcodes = "'" + "','".join(self.diagnosis.split(',')) + "'"
            case_diag_sql = "select name from diagnosis_dict where code in ({})".format(icdcodes)
            if self.auditType != AUDIT_TYPE_ACTIVE:
                diag_sql = "select caseId from fpdiagnosis where icdcode in ({})".format(icdcodes)
            else:
                diag_sql = "select caseId from mz_diagnosis where code in ({})".format(icdcodes)
            query = query.filter(or_(model.caseId.in_(text(diag_sql)), model.diagnosis.in_(text(case_diag_sql))))
        # 手术条件
        if self.operation:
            opercodes = "'" + "','".join(self.operation.split(',')) + "'"
            oper_sql = "select caseId from operation where oper_code in ({})".format(opercodes)
            query = query.filter(model.caseId.in_(text(oper_sql)))

        # 质控问题类别过滤
        if self.category:
            qcItem = connection['qcItem']
            query = query.filter(qcItem.category == self.category)

        # 返修次数
        if self.refuseCount:
            refuse_count_filters = self.refuseCount.split(',')
            exps = []
            if '>5' in refuse_count_filters:
                exps.append(model.refuseCount > 5)
                refuse_count_filters.remove('>5')
            if len(refuse_count_filters) > 0:
                exps.append(model.refuseCount.in_(refuse_count_filters))
            query = query.filter(or_(*exps))

        # 超整改时限天数
        if self.overtime:
            query = query.filter(model.fix_deadline < now)
            if self.overtime == '<1':
                start = arrow.utcnow().to('+08:00').shift(days=-1).naive
                query = query.filter(model.fix_deadline > start)
            elif self.overtime == '>5':
                end = arrow.utcnow().to('+08:00').shift(days=-5).naive
                query = query.filter(model.fix_deadline < end)
            else:
                days = int(self.overtime)
                start = arrow.utcnow().to('+08:00').shift(days=-1*(days + 1)).naive
                end = arrow.utcnow().to('+08:00').shift(days=-1*days).naive
                query = query.filter(model.fix_deadline < end).filter(model.fix_deadline > start)

        # 事中质控独有条件
        if self.auditType == AUDIT_TYPE_ACTIVE:
            query = query.filter(model.dischargeTime.is_(None))
            field_dict = {'dept': 'department', 'ward': 'wardName'}
            if self.pField and self.pField in field_dict:
                field = field_dict.get(self.pField, None)
                if field:
                    query = query.filter(getattr(model, field).in_(self.pList))
            # 事中质控次数
            if self.activeQcNum:
                active_qc_num_filters = self.activeQcNum.split(",")
                flag_5 = False
                flag_0 = False
                if '>5' in active_qc_num_filters:
                    flag_5 = True
                    active_qc_num_filters.remove('>5')
                if '0' in active_qc_num_filters:
                    flag_0 = True
                    active_qc_num_filters.remove('0')
                filter_sql = "("
                if len(active_qc_num_filters) > 0:
                    qc_nums = ",".join(active_qc_num_filters)
                    filter_sql += "qc_num in (%s)" % qc_nums
                if flag_5:
                    if filter_sql != "(":
                        filter_sql += " or"
                    filter_sql += " qc_num > 5"
                if flag_0:
                    if filter_sql != "(":
                        filter_sql += " or"
                    filter_sql += " qc_num is null"
                filter_sql += ")"
                if filter_sql != "()":
                    query = query.filter(text(filter_sql))
            # 事中人工问题数
            if self.activeManProblemNum:
                problem_num_filters = self.activeManProblemNum.split(",")
                p_flag_5 = False
                p_flag_0 = False
                if '>5' in problem_num_filters:
                    p_flag_5 = True
                    problem_num_filters.remove('>5')
                if '0' in problem_num_filters:
                    p_flag_0 = True
                    problem_num_filters.remove('0')
                filter_sql = "("
                if len(problem_num_filters) > 0:
                    p_nums = ",".join(problem_num_filters)
                    filter_sql += "now_problem_num in (%s)" % p_nums
                if p_flag_5:
                    if filter_sql != "(":
                        filter_sql += " or"
                    filter_sql += " now_problem_num > 5"
                if p_flag_0:
                    if filter_sql != "(":
                        filter_sql += " or"
                    filter_sql += " now_problem_num is null"
                filter_sql += ")"
                if filter_sql != "()":
                    query = query.filter(text(filter_sql))
            # 事中人工问题状态, 无问题, 未整改, 部分整改, 全部整改
            if self.activeProblemStatus:
                if self.activeProblemStatus == "无问题":
                    query = query.filter(text("(now_problem_num = 0 or now_problem_num is null)"))
                elif self.activeProblemStatus == "未整改":
                    query = query.filter(text("no_fix_problem_num > 0 and no_fix_problem_num = now_problem_num"))
                elif self.activeProblemStatus == "部分整改":
                    query = query.filter(text("no_fix_problem_num > 0 and no_fix_problem_num < now_problem_num"))
                elif self.activeProblemStatus == "全部整改":
                    query = query.filter(text("(no_fix_problem_num = 0 or no_fix_problem_num is null) and now_problem_num > 0"))

        # 过滤重点病历标签
        if self.tags:
            exps = []
            for tag in self.tags:
                exps.append(
                    func.json_contains(model.tags, json.dumps(tag)) == 1)
            query = query.filter(or_(*exps))
        if self.sampleByTags:
            exps = []
            for tag in self.sampleByTags:
                exps.append(
                    func.json_contains(model.tags, json.dumps(tag)) == 1)
            query = query.filter(or_(*exps))

        # 过滤病案等级
        if self.archiveRating:
            if self.archiveRating.startswith('甲'):
                query = query.filter(auditModel.archiveScore >= 90)
            if self.archiveRating.startswith('乙'):
                query = query.filter(auditModel.archiveScore >= 80, auditModel.archiveScore < 90)
            if self.archiveRating.startswith('丙'):
                query = query.filter(auditModel.archiveScore > 0, auditModel.archiveScore < 80)

        # 根据分数区间过滤
        if self.minScore not in ("", "-1", None):
            field = AuditRecord.getOperatorFields(self.auditType, self.isFinal)
            query = query.filter(getattr(auditModel, field.scoreField) > float(self.minScore))
        if self.maxScore:
            field = AuditRecord.getOperatorFields(self.auditType, self.isFinal)
            query = query.filter(getattr(auditModel, field.scoreField) <= float(self.maxScore))

        # 排除在此auditType下抽中的病历
        if self.excludeSampledCase:
            query = query.filter(sampleRecordItemModel.auditType != self.auditType)
        # 只包含此auditType下抽中的病历
        if self.onlySampledCase:
            query = query.filter(sampleRecordItemModel.auditType == self.auditType)

        # 根据首页总费用区间过滤
        if self.minCost not in ("", "-1", None):
            query = query.filter(firstpageModel.totalcost > float(self.minCost))
        if self.maxCost:
            query = query.filter(firstpageModel.totalcost <= float(self.maxCost))
        return query


class ExportCaseListRequest(GetCaseListRequest):
    # 导出的列名 -> 原始数据库字段名
    fieldMap: Mapping[str, str] = field(default_factory=dict)


@dataclass
class GetEmrListRequest(ListRequestBase):
    # emrInfo的流水号
    id: int = 0
    # caseId
    caseId: str = ''
    # 文书名称, 模糊搜索
    documentName: str = ''
    # 文书id
    docId: str = ''
    # 是否同时返回内容
    withContent: bool = False

    def applyFilter(self, query, connection):
        emrInfoModel = connection['emrInfo']
        query = query.filter(emrInfoModel.caseId == self.caseId, emrInfoModel.is_deleted == 0)
        if self.documentName:
            query = self.applyLikeFilter(query, 'documentName', self.documentName, emrInfoModel)
        if self.docId:
            query = self.applyEqualFilter(query, 'docId', self.docId, emrInfoModel)
        if self.id:
            query = self.applyEqualFilter(query, 'id', self.id, emrInfoModel)
        return query

    def validate(self):
        if not self.caseId and not self.id:
            raise #GrpcInvalidArgumentException(
            #     code=grpc.StatusCode.INVALID_ARGUMENT,
            #     message='id or caseId is required'
            # )
        return super().validate()


@dataclass
class GetOrderListRequest(ListRequestBase):
    caseId: str = ''
    # request.category, 长期临时
    orderType: List[str] = field(default_factory=list)
    # 医嘱状态
    status: List[str] = field(default_factory=list)
    # 开始时间
    startTime: str = ''
    # 结束时间
    endTime: str = ''
    # 医嘱名称
    name: str = ''
    # request.type, 医嘱类型
    orderFlag: List[str] = field(default_factory=list)

    def applyFilter(self, query, connection):
        model = connection['medicalAdvice']

        query = query.filter(model.caseId == self.caseId)

        if self.orderType:
            query = query.filter(model.order_type.in_(self.orderType))
        if self.status:
            query = query.filter(model.status.in_(self.status))
        if self.startTime:
            startTime = arrow.get(self.startTime).naive
            query = query.filter(model.date_start >= startTime)
        if self.endTime:
            endTime = arrow.get(self.endTime).naive
            query = query.filter(model.date_start <= f'{endTime.date()} 23:59:59')
        if self.name:
            query = query.filter(model.name.contains(self.name))
        if self.orderFlag:
            query = query.filter(model.order_flag.in_(self.orderFlag))
        return query


@dataclass
class GetAssayListRequest(ListRequestBase):
    caseId: str = ''
    withContent: bool = False
    size: int = 10000

    def applyFilter(self, query, connection):
        model = connection['labInfo']
        query = query.filter(model.caseId == self.caseId)
        return query


@dataclass
class GetExamListRequest(ListRequestBase):
    caseId: str = ''
    withContent: bool = False
    withTotal: bool = False
    size: int = 10000

    def applyFilter(self, query, connection):
        model = connection['examInfo']
        query = query.filter(model.caseId == self.caseId)
        return query


@dataclass
class GetListRequest(ListRequestBase):
    # 编码状态 0-全部 1-已编码 2-未编码
    codeStatus: str = ''
    # 科室
    department: str = ''
    # 院区
    branch: str = ''
    # 编码员
    doctor: str = ''
    # 起始时间
    startTime: str = ''
    # 截止时间
    endTime: str = ''
    # 时间查询类型 1-出院日期 2-编码日期
    timeType: int = 0
    # 问题过滤 0-全部 1-有问题 2-无问题
    problemFlag: int = 0
    # 患者Id / 姓名
    patientId: str = ''
    # 责任医生
    attend: str = ''
    # 重点病历标签
    tag: str = ''
    # 诊断
    diagnosis: str = ''
    # 手术
    operation: str = ''
    # 病区
    ward: str = ''
    # 科室类型
    deptType: int = 0
    # 标题列数据
    fieldData: List[str] = field(default_factory=list)
    # 是否需要过滤已出院未申请病历
    not_apply: int = 0
    # 病案首页状态
    status: List[int] = field(default_factory=list)
    # 兼容
    auditType: str = ''

    def applyFilter(self, query, connection):
        case_model = connection['case']
        fp_info_model = connection['fp_info']
        audit_model = connection['audit_record']
        if self.not_apply and int(self.not_apply) == 2:
            query = query.filter(case_model.status != 5)
        # patientId 或 姓名
        if self.patientId:
            query = query.filter(or_(case_model.patientId.like('%%%s%%' % self.patientId),
                                     case_model.name.like('%%%s%%' % self.patientId)))
            return query
        # 过滤状态
        if self.status:
            query = query.filter(audit_model.fpStatus.in_(self.status))
        # 编码状态
        if self.codeStatus and int(self.codeStatus):
            status_dict = {1: 1, 2: 0}
            query = query.filter(case_model.codeStatus == status_dict[int(self.codeStatus)])
        # 科室
        if value := self.department:
            query = query.filter(
                or_(and_(case_model.department == value, case_model.outDeptName == None), case_model.outDeptName == value))
        # 院区
        if self.branch:
            query = query.filter(case_model.branch == self.branch)
        # 编码医生
        if self.doctor:
            query = query.filter(fp_info_model.coder == self.doctor)
        # 时间查询类型
        if self.timeType == 1:
            if self.startTime and self.endTime:
                query = self.applyDateRangeFilter(
                    query=query,
                    field='dischargeTime',
                    start=arrow.get(self.startTime).naive,
                    end=arrow.get(self.endTime).naive,
                    model=case_model
                )
        if self.timeType == 2:
            if self.startTime and self.endTime:
                query = self.applyDateRangeFilter(
                    query=query,
                    field='code_time',
                    start=arrow.get(self.startTime).naive,
                    end=arrow.get(self.endTime).naive,
                    model=fp_info_model
                )
        # 是否有问题
        if self.problemFlag:
            if self.problemFlag == 1:
                query = query.filter(audit_model.fpProblemCount > 0)
            if self.problemFlag == 2:
                query = query.filter(or_(audit_model.fpProblemCount == 0, audit_model.fpProblemCount.is_(None)))
        # 责任医生
        if self.attend:
            query = query.filter(case_model.attendDoctor == self.attend)
        # 疾病诊断条件
        if self.diagnosis:
            icdcodes = "'" + "','".join(self.diagnosis.split(',')) + "'"
            diag_sql = "select caseId from fpdiagnosis where icdcode in ({})".format(icdcodes)
            query = query.filter(case_model.caseId.in_(text(diag_sql)))
        # 手术条件
        if self.operation:
            opercodes = "'" + "','".join(self.operation.split(',')) + "'"
            oper_sql = "select caseId from operation where oper_code in ({})".format(opercodes)
            query = query.filter(case_model.caseId.in_(text(oper_sql)))

        # 病区
        if self.ward:
            query = query.filter(case_model.wardName == self.ward)
        # 科室类型
        if self.deptType:
            # dept_list = DepartmentRepository.DEPARTMENT_DICT[self.deptType]
            query_dept_sql = '''select name from department where deptType = "%s"''' % self.deptType
            query = query.filter(or_(getattr(case_model, "outDeptName").in_(text(query_dept_sql)),
                                     getattr(case_model, "department").in_(text(query_dept_sql))))
        # 过滤重点病历标签
        if self.tag:
            query = query.filter(func.json_contains(case_model.tags, json.dumps(self.tag)) == 1)
        return query
