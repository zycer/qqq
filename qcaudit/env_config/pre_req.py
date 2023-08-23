#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   pre_req.py
@Time    :   2023/05/29 13:27:20
@Author  :   zhangda 
@Desc    :   装饰器等
'''


import os 


def pre_request(request, req_args):
    """
    请求参数处理
    将req_args定义的参数赋给request对象
    """
    def wrap_func(func):
        def wrap(*args, **kwargs):
            request_data = request.args if request.method.upper() == "GET" else request.json
            for arg in req_args:
                _type = ""
                if len(arg.split(":")) > 1:
                    arg, _type = arg.split(":")
                default_value = ""
                if _type == "dict":
                    default_value = {}
                elif _type == "int":
                    default_value = 0
                    value = int(request_data.get(arg)) if str(request_data.get(arg)).isdigit() else 0
                    setattr(request, arg, value)
                elif _type == "list":
                    default_value = []
                if not hasattr(request, arg):
                    setattr(request, arg, request_data.get(arg) or default_value)
            res = func(*args, **kwargs)
            return res
        return wrap
    return wrap_func


def after_download(request, export_path):
    """
    下载文件后删除该文件释放空间
    """
    def wrap_func(func):
        def wrap(*args, **kwargs):
            res = func(*args, **kwargs)
            filename = os.path.join(export_path, request.fileName)
            if os.path.exists(filename):
                os.remove(filename)
            return res
        return wrap
    return wrap_func


SortDict = {
    "secondApply": 11,
    "secondNoApply": 12,
    "secondArchivingRate": 13,
    "thirdApply": 14,
    "thirdNoApply": 15,
    "thirdArchivingRate": 16,
    "seventhApply": 17,
    "seventhNoApply": 18,
    "seventhArchivingRate": 19,
    "department": 0,
    "applyCount": 3,
    "dischargeCount": 2,
    "refusedCount": 4,
    "archivedCount": 5,
    "unreviewCount": 6,
    "archivingRate": 7,
    "refusedRate": 8,
    "finishRate": 9,
    "imperfect": 10,
    "timelyRate": 22,
    "fixRate": 23,
}


GetReviewersReq = ["doctorType", "input"]
GetCaseQcItemsReq = ["caseId", "docId", "input", "orgCode", "page", "count", "auditType", "auditStep"]
GetCaseListReq = ["branch", "ward", "department", "attend", "status:int", "rating", "caseId", "patientId", "refused:int", 
                  "startTime", "endTime", "patientName", "reviewer", "problemFlag:int", "tag", "assignDoctor", "autoReviewFlag:int", 
                  "firstPageFlag:0", "sortKey", "sortWay", "sortField:list", "existCaseIds:list", "sampleBy", "sampleCount:int", "start:int", 
                  "size:int", "auditType", "auditStep", "caseType", "deptType:int", "isExportDetail", "timeType:int", "orgCode", "diagnosis", 
                  "operation", "archiveRating", "refuseCount", "fieldData", "visitType", "fixOvertimeFlag", "detailFields:dict", 
                  "operatorId", "group", "minScore", "maxScore", "minCost", "maxCost", "activeQcNum", "activeManProblemNum", 
                  "activeProblemStatus", "category", "minDays", "maxDays", "overtime", "sampleId:int", "tags:list", "operatorId", "operatorName"]
DownloadFileReq = ["id", "fileName"]
GetCaseDetailReq = ["caseId", "orgCode", "auditType", "auditStep", "readOnly:int"]
GetCaseEmrListReq = ["caseId", "groupBy", "documentName", "addSpec", "orgCode", "auditType", "auditStep", "page:int", "count:int"]
GetCaseProblemReq = ["caseId", "orgCode", "docId", "tabIndex:int", "id:int", "tag", "auditType", "auditStep", "readOnly:int", 
                     "nowStatusFlag:int"]
CheckProblemReq = ["id", "orgCode", "caseId", "docId", "qcItemId", "aiFlag", "createTime"]
AddCaseProblemReq = ["caseId", "docId", "qcItemId", "operatorId", "operatorName", "reason", "comment", "score:int", 
                  "aiToken", "deductFlag:int", "categoryId:int", "doctor", "requirement", "counting:int", 
                  "auditType", "auditStep", "orgCode", "id:int"]
AddQCItemProblemReq = ["caseId", "docId", "qcItemId", "operatorId", "operatorName", "reason", "comment", "score:int", 
                  "aiToken", "deductFlag:int", "categoryId:int", "doctor", "requirement", "counting:int", 
                  "auditType", "auditStep", "orgCode", "score", "refer"]
DeductProblemReq = ["id:int", "deductFlag:int", "operatorId", "operatorName", "auditType", "auditStep"]
GetCaseDoctorsReq = ["caseId", "input", "attendingFlag", "department"]
BatchSetRefuseDoctorReq = ["caseId", "input", "attendingFlag", "department", "auditType", "auditStep", "problems:list",
                           "doctor", "operatorId", "operatorName"]
GetRefuseDoctorReq = ["caseId", "docId", "auditType"]
GetCaseReasonReq = ["caseId", "ignoreAi:int", "ignoreOnce:int", "auditType", "auditStep", "isAddRefuse:int"]
ApproveCaseReq = ["caseId", "comment", "auditType", "auditStep", "operatorId", "operatorName"]
ApproveCaseBatchReq = ["caseId:list", "comment", "auditType", "auditStep", "operatorId", "operatorName"]
RefuseCaseReq = ["caseId", "status:int", "auditType", "auditStep", "operatorId", "operatorName", "problems:list", 
                 "comment", "inDays", "transTo"]
GetCaseCheckHistoryReq = ["caseId", "orgCode", "auditType", "auditStep", "page:int", "count:int"]
GetMedicalAdviceReq = ["caseId", "orgCode", "auditType", "auditStep", "page:int", "count:int", "name", 
                          "startTime", "endTime", "status", "category", "type"]
GetEmrDataReq = ["caseId", "patientId", "visitTimes:int", "docId", "docType:list", "startTime", "endTime"]
GetIpBlockListReq = ["ip", "rule:int", "start:int", "size:int", "id:int"]
ActiveSaveReq = ["caseId", "problems:list", "doctor", "operatorId", "operatorName", "auditType", "auditStep"]
ProblemRecordListReq = ["reason", "docType", "problemType", "problemStatus:int", "auditType", "startTime", 
                        "endTime", "createDoctor", "caseId", "start:int", "size:int"]
ActiveSaveReq = ["caseIds:list", "operatorId", "operatorName", "auditType", "auditStep", "id:int"]
SubmitSampleCaseReq = ["caseType", "auditType", "caseIds:list", "operatorId", "operatorName", "sampleId"]
GetSampleListReq = ["caseType", "auditType", "caseId", "operatorId", "operatorName", "sampleId", "startTime", 
                    "endTime", "start:int", "size:int"]
GetSampleDetailReq = ["branch", "ward", "department", "attending", "sampleId:int", "caseId", "patientId", 
                      "auditType", "tag", "minScore", "maxScore", "sortField:list", "start:int", "size:int", 
                      "isExportDetail:int", "group", "assignDoctor"]
AssignSampleReq = ["sampleId:int", "caseType", "auditType", "assignType", "avoidSameDept:int"]
AssignTaskReq = ["taskId:int", "taskIds:list", "auditType", "expert:dict", "many:int", "caseType"]
BranchAssignTaskReq = ["sampleId:int", "auditType", "wardDoctor:dict", "doctorId"]
UpdateSampleCaseReq = ["caseType", "auditType", "caseIds:list", "operatorId", "operatorName", "sampleId:int"]
SampleFilterListReq = ["auditType", "startTime", "endTime", "name", "caseType", "start:int", "size:int"]
SampleFilterSaveReq = ["id:int", "name", "filter:dict", "deleteFlag:int", "auditType", "caseType"]
SampleTaskListReq = ["start:int", "name", "startTime", "endTime", "auditType", "caseType", "size:int"]
SampleTaskSaveReq = ["id:int", "name", "days", "firstSampleTime", "queryFilter:dict", "sampleFilter:dict", 
                     "deleteFlag:int", "auditType", "assignDoctor:list", "notCurrentDeptFlag:int", "taskType", 
                     "caseType", "status:int"]
GetDoctorEMRProblemListReq = ["caseId", "doctor", "isFix:int", "isIgnore:int", "auditId", "refuseTime", "docIds", 
                              "isApply:int"]
AppealCreateReq = ["caseId", "doctorId", "problemId", "doctorName", "content"]
MessageReceiveReq = ["messageType:int", "doctorId", "caseId", "emrName"]
EmrSaveDebugReq = ["doctor", "caseId", "time", "url", "method", "apiName", "content", "apiStatus", "fileName"]
CreateQCItemReq = ["code", "requirement", "emrName", "rule", "instruction", "linkEmr:list", "enable:int", 
                   "type:int", "departments:list", "disease:list", "operatorId", "operatorName", "tags:list", 
                   "category:int", "remindInfo:dict", "includeQuery", "excludeQuery", "id:int", "department", 
                   "disease", "status:int", "custom:int", "enable:int", "ruleType", "enableType:int", "start:int", 
                   "size:int"]
GetQcGroupItemReq = ["id:int", "itemName", "inside:int", "page:int", "count:int"]
AddQcCategoryReq = ["groupId:int", "parent", "name", "maxScore:int"]
RuleSearchReq = ["type", "text", "start:int", "size:int"]
StatsCaseRatioReq = ["timeType", "time", "targetName", "isFirstPage:int", "sortTags:list"]
GetHospitalArchivingRateReq = ["startTime", "endTime", "branch", "department", "deptType:int", "statusType:int", 
                               "attend", "ward", "start", "size", "problemType"]
GetBranchTimelinessRateDetailReq = ["targetName", "accordFlag:int", "branch", "department", "attend", "startTime", 
                                    "endTime", "ward", "timeFlag", "start:int", "size:int", "doctor", "enableFR", 
                                    "doctorFR", "sortKey", "sortWay", "deptType:int"]
GetDoctorArchivingRateCaseReq = ["applyFlag", "reviewFlag", "branch", "department", "attend", "startTime", 
                                    "endTime", "ward", "timeFlag", "start:int", "size:int", "doctor", "enableFR", 
                                    "doctorFR", "sortKey", "sortWay", "deptType:int", "isPrimaryDiagValid", 
                                    "isMinorDiagValid", "isPrimaryOperValid", "isMinorOperValid", "doctorFRFlag", 
                                    "outDept", "status:int", "problemFlag:int", "input", "page:int", "count:int"]
StartEndTimeReq = ["startTime", "endTime", "indicates:list"]
GetFirstPageIndicateStatsReq = ["startTime", "endTime", "indicateName", "count:int", "indicateParams"]
GetProblemCategoryStatsReq = ["applyFlag", "reviewFlag", "branch", "department", "attend", "startTime", 
                            "endTime", "ward", "timeFlag", "start:int", "size:int", "attending", "enableFR", 
                            "doctorFR", "sortKey", "sortWay", "deptType:int", "isPrimaryDiagValid", 
                            "isMinorDiagValid", "isPrimaryOperValid", "isMinorOperValid", "doctorFRFlag", 
                            "outDept", "status:int", "problemFlag:int", "input", "page:int", "count:int", 
                            "emrName", "category:int", "problem", "auditType", "caseType", "problemType:int", 
                            "operatorId", "fixed:int", "itemtype:int", "itemsId", "itemId:int", "exportType:int"]
ExpertAllNumReq = ["timeType:int", "startTime", "endTime", "caseType", "deptType:int", "branch", "statsType:int", 
                   "department", "doctorName", "level", "sortBy", "sortWay:int", "start:int", "size:int"]
StatsDefectRateListReq = ["type", "branch", "department", "group", "ward", "attend", "startTime", "endTime", 
                          "start:int", "size:int", "startScore", "endScore", "qualifiedFlag:int", "status:int", 
                          "finishedFlag:int", "level"]

ReceiveEventReq = ["patientId", "caseId", "eventType", "operationId", "operationName", "operationTime", "docId",
                   "title", "data"]
ReceiveActionEventReq = ["action", "doctorName", "doctorId", "deptCode", "deptName", "params", "departmentId", 
                         "departmentName", "options"]
GetPatientPortraitReq = ["patientID", "caseID", "idCode", "type"]
GetFPListReq = ["codeStatus", "department", "branch", "doctor", "startTime", "endTime", "timeType:int", 
                "problemFlag:int", "patientId", "attend", "tag", "diagnosis", "operation", "ward", "deptType:int", 
                "start:int", "size:int", "fieldData:list"]
SaveCaseDiagnosisReq = ["caseId", "operatorId", "operator", "diagnosisInfo:dict", "type:int", "sortIds:list", 
                        "operationInfo:dict"]

'''
// 病历id
    string caseId = 1;
    // 操作人id
    string operatorId = 2;
    // 操作人
    string operator = 3;
    // 诊断信息
    Diagnosis diagnosisInfo = 4;
    // 诊断类型, 默认0-诊断信息, 1-病理诊断, 2-损伤/中毒诊断
    int32 type = 5;
    // 排序后id数组, [123, 125, 124]
    repeated int32 sortIds = 6;
'''

