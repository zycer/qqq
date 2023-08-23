#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 13:12:14

继承grpc生成的servicer类, 实现相关接口

'''
import json
import random
import uuid
from datetime import datetime

from iyoudoctor.hosp.qc.v3.sample.service_pb2_grpc_wrapper import QCSampleServicer as _QCSampleServicer
from iyoudoctor.hosp.qc.v3.sample.service_message_pb2 import CommonResponse, GetSampleCaseResponse, \
    SubmitSampleCaseResponse, GetSampleListResponse, GetSampleDetailResponse, GetExpertListResponse, CommonIdResponse, \
    GetExportResponse, BranchAssignDoctorListResponse, GetSampleOperationResponse, SampleFilterListResponse, \
    SampleTaskListResponse

from qcaudit.common.const import CASE_LIST_PROBLEM_COUNT, EXPORT_FILE_AUDIT_TYPE, SAMPLE_BY_TAG, SAMPLE_BY_TAG_ALL, \
    SAMPLE_BY_GROUP
from qcaudit.config import Config
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.case.req import GetCaseListRequest
from qcaudit.domain.problem.problem import Problem
from qcaudit.domain.case.case import CaseType
from qcaudit.domain.req import SortField
from qcaudit.domain.problem.req import GetProblemListRequest
from qcaudit.domain.sample.req import GetSampleRecordRequest, GetSampleDetailRequest

from qcaudit.service.protomarshaler import unmarshalCaseInfo, unmarshalProblem

from qcaudit.infra.util import ModelProtoUtil
from google.protobuf.json_format import ParseDict, Parse, MessageToDict

from qcaudit.utils.bidataprocess import BIFormConfig, BIDataProcess
from qcaudit.utils.towebconfig import SAMPLE_HISTORY_EXPORT_DATA, SAMPLE_HISTORY_EXPORT_YAML, \
    SAMPLE_HISTORY_GROUP_EXPORT_YAML


class SampleServicer(_QCSampleServicer):

    def __init__(self, context):
        self.context = context
        self.export_path = "/tmp/"

    def GetSampleCase(self, request, context):
        """获取抽取病历列表
        """
        response = GetSampleCaseResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            raise Exception("Missing auditType")
            return response
        params = ["branch", "ward", "department", "attend", "status", "rating",
                  "caseId", "patientId", "reviewer", "problemFlag", "patientName",
                  "autoReviewFlag", "firstPageFlag", "start", "size", "auditType",
                  "startTime", "endTime", "caseType", "group", "minDays", "maxDays", "minScore", "maxScore", "minCost", "maxCost"]
        req = {c: getattr(request, c) for c in params}
        # 重点病历标签过滤
        req["sampleByTags"] = request.tags
        req["tags"] = [tag for tag in request.tag.split(',') if tag]

        # if request.status:
        req["status"] = []
        if request.caseType:
            if request.caseType == 'running':
                req['includeCaseTypes'] = [CaseType.ACTIVE]
            elif request.caseType == 'archived':
                req['includeCaseTypes'] = [CaseType.ARCHIVE]
            elif request.caseType == 'Final':
                req['includeCaseTypes'] = [CaseType.FINAL]
        if request.sortField:
            # 抽取顺序
            FIELD_MAP = {
                'department': 'outDeptName',
                'ward': 'wardName',
                'attending': 'attendDoctor',
                'branch': 'branch',
                'problems': CASE_LIST_PROBLEM_COUNT,
                'tags': 'tags',
                'receiveTime': 'receiveTime',
                'admitTime': 'admitTime',
                'dischargeTime': 'dischargeTime',
                "group": "medicalGroupName",
            }
            req['sortFields'] = []
            for sf in request.sortField:
                if FIELD_MAP.get(sf.field):
                    if sf.field == 'receiveTime':
                        sort_field = SortField(field=FIELD_MAP.get(sf.field, sf.field), way=sf.way,
                                               table='audit_record', extParams=sf.extParams)
                    elif sf.field == "problems":
                        sort_field = SortField(field=FIELD_MAP.get(sf.field)[request.auditType], way=sf.way,
                                               extParams=sf.extParams)
                    else:
                        sort_field = SortField(field=FIELD_MAP.get(sf.field, sf.field), way=sf.way,
                                               extParams=sf.extParams)
                    req['sortFields'].append(sort_field)

        # 抽取归档标记，如果允许抽取归档，过滤掉终末病历列表中已归档的病历
        req["sampleArchiveFlag"] = app.app.config.get(Config.QC_SAMPLE_ARCHIVE.format(auditType=request.auditType)) == '1'
        # 抽取列表仅需要住院病历
        req["visitType"] = "2"

        req = GetCaseListRequest(**req)
        existCaseIds = list(request.existCaseIds) if request.existCaseIds else []
        caseList, total = app.getSampleCase(req, sampleBy=request.sampleBy, sampleNum=request.sampleCount, existedCaseIds=existCaseIds)
        count = 0
        for x in caseList:
            protoItem = response.items.add()
            unmarshalCaseInfo(x, protoItem, request.auditType, is_sample=1)
            count += 1

        caseIds = [caseInfo.caseId for caseInfo in caseList]
        conditions = ["全部"]
        sampleBy = request.sampleBy
        # 抽取重点病历范围
        if sampleBy == SAMPLE_BY_TAG:
            all_tags = self.context.getCaseApplication(request.auditType).getCaseTag('') or []
            if len(all_tags) > len(request.tags):
                conditions = request.tags
            else:
                sampleBy = SAMPLE_BY_TAG_ALL
        # 抽取诊疗组范围
        if sampleBy == SAMPLE_BY_GROUP and request.group and request.group != "all":
            conditions = request.group.split(',')
        sample = app.record_sample_operation(request.sampleId, request.caseType, caseIds,
                                             operatorId=request.operatorId, operatorName=request.operatorName,
                                             sampleBy=sampleBy, sampleCount=request.sampleCount,
                                             existedCaseIds=existCaseIds, sampleFilter=conditions)
        response.sampleId = sample

        response.total = len(caseList)
        response.start = request.start
        response.size = len(caseList)
        return response

    def SubmitSampleCase(self, request, context):
        """提交抽取结果
        """
        response = SubmitSampleCaseResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return response
        sampleRecord = app.submitSampleResult(request.caseIds,request.auditType, request.caseType, request.operatorId, request.operatorName, request.sampleId)
        if sampleRecord:
            response.isSuccess = True
            response.id = sampleRecord.id
        return response

    def GetSampleList(self, request, context):
        """获取抽取记录列表
        """
        response = GetSampleListResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return response

        req = GetSampleRecordRequest(**MessageToDict(request))
        sampleList, totalCount = app.getSampleRecordHistory(req)
        count = 0
        for x in sampleList:
            protoItem = response.items.add()
            ModelProtoUtil.modelToProto(x, protoItem, keyList=["id","caseType","auditType","operatorId","operatorName"], keyMap={"isAssigned":"status","createdAt":"extractTime"})
            if x.sampleBy:
                for by in x.sampleBy.split(','):
                    protoItem.sampleBy.append(by)
            count += 1
        response.total = totalCount
        response.start = request.start
        response.size = count
        return response

    def GetSampleDetail(self, request, context):
        """获取抽取记录详情列表
        """
        response = GetSampleDetailResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return
        if not request.sampleId:
            return response

        req = GetSampleDetailRequest(**MessageToDict(request))
        print(req)
        sampleList, totalCount = app.getSampleDetail(req)
        count = 0

        caseTagDict = None
        try:
            caseTagDict = {t.code: t for t in self.context.getCaseApplication(request.auditType).getCaseTag('')}
        except Exception as e:
            print(e)

        for x in sampleList:
            protoItem = response.items.add()
            protoItem.id = x.model.id
            protoItem.caseId = x.model.caseId
            protoItem.sampleId = x.model.recordId
            protoItem.patientId = x.caseModel.inpNo or x.caseModel.patientId
            protoItem.visitTimes = x.caseModel.visitTimes if x.caseModel.visitTimes else 0
            protoItem.name = x.caseModel.name if x.caseModel.name else ""
            protoItem.age = str(x.caseModel.age) if x.caseModel.age else ""
            protoItem.gender = x.caseModel.gender if x.caseModel.gender else ""
            protoItem.branch = x.caseModel.branch if x.caseModel.branch else ""
            protoItem.ward = x.caseModel.wardName if x.caseModel.wardName else ""
            protoItem.group = x.caseModel.medicalGroupName or ""
            protoItem.attendDoctor = x.caseModel.attendDoctor if x.caseModel.attendDoctor else ""
            protoItem.admitTime = x.caseModel.admitTime.strftime('%Y-%m-%d') if x.caseModel.admitTime else ""
            protoItem.dischargeTime = x.caseModel.dischargeTime.strftime('%Y-%m-%d') if x.caseModel.dischargeTime else ""
            protoItem.dischargeDept = x.caseModel.outDeptName if x.caseModel.outDeptName else ""
            protoItem.department = x.caseModel.outDeptName or x.caseModel.department or ""
            ar_status = getattr(x.auditRecord, AuditRecord.getOperatorFields(auditType=request.auditType).statusField)
            protoItem.status = ar_status or 0
            protoItem.inpDays = x.caseModel.inpDays if x.caseModel.inpDays else 0
            protoItem.problemCount = AuditRecord(x.auditRecord).getProblemCount(req.auditType) if x.auditRecord else 0
            ar_reviewer = getattr(x.auditRecord,
                                  AuditRecord.getOperatorFields(auditType=request.auditType).reviewerNameField)
            ar_review_time = getattr(x.auditRecord,
                                     AuditRecord.getOperatorFields(auditType=request.auditType).reviewTimeField)
            protoItem.distributeDoctor = x.model.expertName if x.model.expertName else ""
            protoItem.reviewer = ar_reviewer or ""
            protoItem.reviewTime = ar_review_time.strftime('%Y-%m-%d %H:%M:%S') if ar_review_time else ""
            if x.caseModel.tags:
                for tag in x.caseModel.tags:
                    protoItemTag = protoItem.caseTags.add()
                    t = caseTagDict.get(tag) if caseTagDict else None
                    protoItemTag.name = t.name if t else ""
                    protoItemTag.code = t.code if t else tag
                    protoItemTag.icon = t.icon if t else ""

            caseScore = AuditRecord(x.auditRecord).getScore(req.auditType) if x.auditRecord else 100.0
            if not caseScore:
                caseScore = 100.0
            caseRating = "甲" if caseScore >= 90 else "乙"
            protoItem.caseRating = "丙" if caseScore < 80 else caseRating
            protoItem.caseScore = '{:g}'.format(caseScore)
            count += 1
        response.total = totalCount
        response.start = request.start
        response.size = count
        return response

    def GetSampleDetailExport(self, request, context):
        """
        抽取历史导出
        :param request:
        :param context:
        :return:
        """
        response = GetExportResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return
        req = GetSampleDetailRequest(**MessageToDict(request))
        req.is_export = 1
        sampleList, totalCount = app.getSampleDetail(req)

        caseTagDict = {t.code: t for t in self.context.getCaseApplication(request.auditType).getCaseTag('')}

        patient_id_name = app.app.config.get(Config.QC_PATIENT_ID_NAME) or "病案号"
        base_file_name = EXPORT_FILE_AUDIT_TYPE.get(request.auditType) + "抽取历史" + "-{}.xlsx"
        file_name = base_file_name.format(datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(10, 99)))
        file_id = uuid.uuid4().hex
        path_file_name = self.export_path + file_id + ".xlsx"

        # df = app.writeSampleExcel(sampleList, request, caseTagDict, patient_id_name)
        # df.to_excel(path_file_name, index=False)
        data = app.format_sample_history_export_data(sampleList, request, caseTagDict, patient_id_name)

        group_yaml = SAMPLE_HISTORY_GROUP_EXPORT_YAML if int(app.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) else ""
        reason_column = 14 if int(app.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0) else 13
        cfg = BIFormConfig.fromYaml(SAMPLE_HISTORY_EXPORT_YAML.format(patient_name=patient_id_name, group=group_yaml))
        processor = BIDataProcess(cfg, data)
        processor.toExcel(path=path_file_name, sortBy=[], column_width=[reason_column, 120])

        response.id = file_id
        response.fileName = file_name
        return response

    def AddExpert(self, request, context):
        """添加专家
        """
        response = CommonIdResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.expert:
            return response
        app.addExpert(request.expert.id, request.expert.name, request.caseType)
        response.isSuccess = True
        return response

    def DeleteExpert(self, request, context):
        """删除专家
        """
        response = CommonIdResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.expertId:
            return response
        app.removeExpert(request.expertId, request.caseType)
        response.isSuccess = True
        return response

    def GetExpertList(self, request, context):
        """获取特定类型的专家列表
        """
        response = GetExpertListResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app:
            return response

        expertList = app.getExpertList(request.caseType)
        count = 0
        for x in expertList:
            protoItem = response.experts.add()
            protoItem.id = x.userId
            protoItem.name = x.userName if x.userName else ""
            # protoItem.username = x.username if x.username else ""
            count += 1

        return response

    def AssignTask(self, request, context):
        """指定分配任务
        """
        response = CommonResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.expert.id:
            return response
        if (not request.many and not request.taskId) or (request.many and not request.taskIds):
            return response
        recordId = app.assginExpertToItem(request.taskId, request.taskIds, request.expert.id, request.expert.name, request.many)
        app.checkSampleAssigned(recordId, request.auditType)
        response.isSuccess = True
        return response

    def AssignSample(self, request, context):
        """分配抽取记录
        """
        response = CommonResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.sampleId:
            return response
        app.assignExpert(request.sampleId, request.caseType, request.assignType, request.auditType, request.avoidSameDept)
        response.isSuccess = True
        return response

    def DeleteTask(self, request, context):
        """废除抽取任务
        """
        response = CommonResponse()
        app = self.context.getSampleApplication(request.auditType)
        if not app or not request.taskId:
            return response
        app.removeTask(request.taskId)
        response.isSuccess = True
        return response

    def BranchAssignDoctorList(self, request, context):
        """
        按病区分配医生列表
        :return:
        """
        response = BranchAssignDoctorListResponse()
        app = self.context.getSampleApplication("hospital")
        if not request.doctorId:
            return response
        assign_flag = int(app.app.config.get(Config.QC_ASSIGN_DIMENSION))
        data = app.query_wardDoctor_from_ward_doctor(request.doctorId, assign_flag)
        if data:
            tmp_ICU_list = []
            for item in data:
                if "ICU" in item.ward:
                    tmp_ICU_list.append(item)
                    continue
                protoItem = response.items.add()
                protoItem.ward = item.ward
                protoItem.doctorName = item.doctorName or ""
                protoItem.doctorId = item.doctorId or ""
            for item in tmp_ICU_list:
                protoItem = response.items.add()
                protoItem.ward = item.ward
                protoItem.doctorName = item.doctorName or ""
                protoItem.doctorId = item.doctorId or ""
        else:
            data = app.query_wardDoctor_from_ward(assign_flag)
            tmp_ICU_list = []
            for item in data:
                if "ICU" in item.name:
                    tmp_ICU_list.append(item.name)
                    continue
                protoItem = response.items.add()
                protoItem.ward = item.name
            for name in tmp_ICU_list:
                protoItem = response.items.add()
                protoItem.ward = name
        return response

    def BranchAssignTask(self, request, context):
        """
        按病区/科室 分配任务
        :return:
        """
        response = CommonResponse()
        app = self.context.getSampleApplication(request.auditType)
        assign_flag = int(app.app.config.get(Config.QC_ASSIGN_DIMENSION) or 1)
        req = GetSampleDetailRequest(**MessageToDict(request))
        req.is_export = 1
        sampleList, totalCount = app.getSampleDetail(req)
        to_be_assign_data = {}
        # 先查询待分配数据
        for item in sampleList:
            ar_status = getattr(item.auditRecord, AuditRecord.getOperatorFields(auditType=request.auditType).statusField)
            if ar_status != 1 or item.model.isMannalAssigned == 1:
                continue
            case_field = (item.caseModel.outDeptName or item.caseModel.department) if assign_flag == 1 else item.caseModel.wardName
            if case_field not in to_be_assign_data:
                to_be_assign_data[case_field] = []
            to_be_assign_data[case_field].append(item.model.id)
        if request.wardDoctor:
            # 如果病区分配医生有变动则更新
            app.update_wardDoctor(request.doctorId, request.wardDoctor, assign_flag)
        if not to_be_assign_data:
            # 无数据可分配
            response.isSuccess = True
            return response
        # 再查询病区分配数据
        ward_doctor_dict = app.get_ward_doctor_dict(request.doctorId, assign_flag)
        for ward, sample_item_ids in to_be_assign_data.items():
            expert_id = ward_doctor_dict.get(ward, {}).get("doctorId", "")
            expert_name = ward_doctor_dict.get(ward, {}).get("doctorName", "")
            isMannalAssigned = 2
            if not expert_id or not expert_name:
                # 支持将已经病区分配过的病历, 病区分配医生清空, 恢复到未分配前(支持平均分配)
                print("BranchAssignTask, ward: %s, sample_item_ids: %s, assign no expert" % (ward, sample_item_ids))
                isMannalAssigned = 0
            app.ward_assign(sample_item_ids, expert_id, expert_name, isMannalAssigned)
        response.isSuccess = True
        return response

    def UpdateSampleCase(self, request, context):
        """更新病历库结果
        """
        response = SubmitSampleCaseResponse()
        app = self.context.getSampleApplication(request.auditType)
        sampleId = app.update_sample_case(request.sampleId, request.caseType, request.caseIds, request.operatorId, request.operatorName)
        if sampleId:
            response.id = sampleId
            response.isSuccess = True
        return response

    def GetSampleOperation(self, request, context):
        """获取病历抽取规则留痕
        """
        response = GetSampleOperationResponse()
        app = self.context.getSampleApplication("hospital")
        sample, operations = app.getSampleOperations(request.id)
        if sample:
            response.sampleId = sample.id
            response.sampleCount = sample.sampledCount
        for operation in operations[request.start: request.start+request.size]:
            protoItem = response.operations.add()
            protoItem.name = operation.name
            protoItem.content = operation.content
            protoItem.filter.sampleBy = operation.sample_by
            if operation.conditions:
                data = {'全部': "全部"}
                if operation.sample_by == SAMPLE_BY_TAG:
                    data = {t.code: t.icon for t in self.context.getCaseApplication('hospital').getCaseTag('')}
                for item in operation.conditions.split(','):
                    protoItem.filter.conditions.append(data.get(item, item))
            protoItem.sampleCount = operation.sampled_count
            protoItem.operator = operation.operator
        response.total = len(operations)
        response.size = request.size
        response.start = request.start
        return response

    def SampleFilterList(self, request, context):
        """
        抽取管理-抽取条件列表
        :return:
        """
        response = SampleFilterListResponse()
        app = self.context.getSampleApplication("hospital")
        filter_data, response.total = app.getSampleFilterList(request)
        all_tags = self.context.getCaseApplication(request.auditType).getCaseTag('') or []
        tag_dict = {tag.code: str(tag.icon) for tag in all_tags}
        for item in filter_data:
            protoItem = response.data.add()
            protoItem.id = item.id
            protoItem.name = item.name or ""
            protoItem.createTime = item.create_time.strftime("%Y-%m-%d") if item.create_time else ""
            protoItem.describe = item.describe or ""
            sample_filter = json.loads(item.filter)
            sample_range = item.range or ""
            if sample_filter.get("sampleBy") == "tag":
                if sample_range != "全部":
                    tag_icons = []
                    for tag in json.loads(sample_range):
                        tag_icons.append(str(tag_dict.get(tag)))
                    sample_range = json.dumps(tag_icons)
            protoItem.range = sample_range
            ParseDict(sample_filter, protoItem.filter)
        return response

    def SampleFilterSave(self, request, context):
        """
        抽取管理-抽取条件保存
        :return:
        """
        response = CommonResponse()
        app = self.context.getSampleApplication("hospital")
        all_tags = []
        if request.filter.sampleBy == SAMPLE_BY_TAG:
            all_tags = self.context.getCaseApplication(request.auditType).getCaseTag('') or []
        response.isSuccess, response.message = app.saveSampleFilter(request, all_tags=all_tags)
        return response

    def SampleTaskList(self, request, context):
        """
        抽取管理-抽取定时任务列表
        :return:
        """
        response = SampleTaskListResponse()
        app = self.context.getSampleApplication("hospital")
        data, response.total = app.getSampleTaskList(request)
        for item in data:
            protoItem = response.data.add()
            protoItem.id = item.id
            protoItem.name = item.name or ""
            protoItem.createTime = item.create_time.strftime("%Y-%m-%d") if item.create_time else ""
            protoItem.firstSampleTime = item.first_sample_time.strftime("%Y-%m-%d") if item.first_sample_time else ""
            protoItem.type = item.type or ""
            protoItem.days = str(item.days or "")
            protoItem.status = item.status or 0
            protoItem.notCurrentDeptFlag = item.notCurrentDeptFlag or 0
            ParseDict(json.loads(item.sample_filter), protoItem.sampleFilter)
            ParseDict(json.loads(item.query_filter), protoItem.queryFilter)
            assign_doctor = json.loads(item.assign_doctor or json.dumps([]))
            if assign_doctor:
                for doctor in assign_doctor:
                    protoDoctor = protoItem.assignDoctor.add()
                    ParseDict(doctor, protoDoctor, ignore_unknown_fields=True)
        return response

    def SampleTaskSave(self, request, context):
        """
        抽取管理-抽取定时任务保存
        :return:
        """
        response = CommonResponse()
        app = self.context.getSampleApplication("hospital")
        response.id, response.isSuccess, response.message = app.saveSampleTask(request)
        return response
