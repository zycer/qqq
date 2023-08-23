#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   qc_handler.py
@Time    :   2023/05/29 13:29:50
@Author  :   zhangda 
@Desc    :   None
'''


from datetime import datetime
import json, arrow, openpyxl
from flask import jsonify, make_response, g, request
from qcaudit.env_config import *
from qcaudit.common.const import *
from qcaudit.env_config.pre_req import *
from qcaudit.domain.case.req import GetCaseListRequest, GetEmrListRequest, GetOrderListRequest, GetAssayListRequest, GetExamListRequest
from qcaudit.domain.qcgroup.qcitem_req import GetItemsListRequest
import logging, random, uuid
from .qc_util import QCUtil
from qcaudit.service.protomarshaler import *
from qcaudit.config import Config
from qcaudit.utils.bidataprocess import BIFormConfig, BIDataProcess
from qcaudit.domain.case.case import CaseType
from qcaudit.domain.problem.req import GetProblemListRequest
from qcaudit.domain.doctor.appeal_repository import AppealRepository
from qcaudit.domain.case.emr import EmrDocument
from qcaudit.domain.lab.req import GetLabListRequest
from qcaudit.domain.ipaddr.ip_rule import IpRule
from . import *


logger = logging.getLogger(__name__)


class GetBranch(MyResource):

    def get(self):
        """院区列表
        """
        # response = GetBranchResponse()
        with context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
            data = []
            for b in context.getBranchRepository("hospital").getList(session):
                data.append(b.name)
                
            return make_response(jsonify({"branches": data}), 200)


class GetWard(MyResource):

    def get(self):
        """获取楼层（病区）列表
        """
        with context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
            name = request.args.get("name") or ""
            branch = request.args.get("branch") or ""
            data = []
            for w in context.getWardRepository("hospital").getList(session, name=name, branch=branch):
                data.append({"branch": w.branch or "", "name": w.name or ""})
            res = {"wards": data, "total": len(data)}
        return make_response(jsonify(res), 200)


class GetDepartment(MyResource):

    def get(self):
        """获取科室列表
        """
        with context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
            depts = []
            if int(request.args.get("mzFlag", 0)) == 1:
                deptList = context.getDepartmentRepository("hospital").getMzList(session, request)
                depts.extend(deptList)
            else:
                for d in context.getDepartmentRepository("hospital").getList(session, name=request.args.get("name", ""), branch=request.args.get("branch", "")):
                    if not d.name:
                        continue
                    depts.append(d.name)
            res = {"departments": depts, "total": len(depts)}
        return make_response(jsonify(res), 200)
    
    
class AddDepartment(MyResource):
    
    def post(self):
        """添加科室
        """
        with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
            self.context.getDepartmentRepository("hospital").add(session, request.json.get("departments", []))
        return make_response(jsonify(g.result), 200)
    
    
class GetCaseTag(MyResource):

    def get(self):
        """病历标签字典
        """
        tags = self.context.getCaseApplication("hospital").getCaseTag(request.args.get("input", ""))
        data = []
        for t in tags:
            data.append({"id": t.id, "name": t.name or "", "code": t.code or "", "status": t.status or 0, 
                         "orderNo": t.orderNo or 0, "icon": t.icon.decode() or ""})
        return make_response(jsonify({"data": data}), 200)


class GetAuditStatus(MyResource):
    def get(self):    
        """病历状态字典
        """
        statusList = []
        if request.args.get("auditStep") == 'audit':
            statusList = AUDIT_STATUS
        elif request.args.get("auditStep") == "recheck":
            statusList = RECHECK_STATUS

        for status in statusList:
            if not status.get('hideflag'):
                g.result["data"].append({"id": status.get('returnid'), "name": status.get('name')})
        return make_response(jsonify(g.result), 200)
    

class GetDoctors(MyResource):

    def get(self):
        """获取病历中涉及到的医生
        """
        # todo 实现
        return make_response(jsonify(g.result), 200)
    

class GetReviewers(MyResource):

    @pre_request(request, GetReviewersReq)
    def get(self):
        """审核人列表
        """
        doctors = []
        if request.doctorType == 'assign':
            for reviewer in self.context.getAuditApplication(request.auditType).getAssignedDoctors(request.input):
                if reviewer:
                    doctors.append(reviewer)
        elif request.doctorType == 'review':
            for reviewer in self.context.getAuditApplication(request.auditType).getReviewers(request.input):
                if reviewer:
                    doctors.append(reviewer)
        res = {"doctors": doctors, "total": len(doctors)}
        return make_response(jsonify(res), 200)


class GetStandardEmr(MyResource):

    @pre_request(request, GetReviewersReq)
    def get(self):
        """标准文书列表
        """
        with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
            items = []
            for name in self.context.getDocumentsRepository("hospital").getDistinctStandardName(session):
                if request.input:
                    if request.input in name:
                        items.append(name)
                elif name:
                    items.append(name)
            res = {"items": items, "total": len(items)}
        return make_response(jsonify(res), 200)
    

class GetCaseQcItems(MyResource):

    @pre_request(request, GetCaseQcItemsReq)
    def get(self, caseId=""):
        """病历可用的质控项列表
        """
        request.caseId = caseId
        item_type_dict = {1: '通用', 2: '专科', 3: '专病'}
        if not request.page:
            request.page = 1
        if not request.count:
            request.count = 50
        app = self.context.getCaseApplication(request.auditType)
        with app.app.mysqlConnection.session() as session:
            case = app._caseRepository.getByCaseId(session, request.caseId)
            department = case.outDeptName or case.department or ''
            diagnosis = app.getDiagnosisInfo(session, request.caseId)
            diagnosis_list = [d.name for d in diagnosis]
            emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, docId=request.docId))
            emrInfo = None
            emrStandardName = "0"
            for emr in emrList:
                emrInfo = emr
            if emrInfo:
                document = self.context.getDocumentsRepository(request.auditType).get(session, emrInfo.getDocumentName())
                if not document:
                    return 
                emrStandardName = document.standard_name
            qcGroup = self.context.getQcGroupRepository(request.auditType).getQcGroup(session)
            if not qcGroup:
                logger.info('没有找到规则组配置')
                return
            index = 0
            items = []
            for item in self.context.getQcItemRepository("hospital").getList(session, GetItemsListRequest(emrName=emrStandardName, instruction=request.input, caseId=request.caseId, dept=department, diagnosis=diagnosis_list)):
                if item and qcGroup.getItem(item.id):
                    if (request.page - 1) * request.count <= index < request.page * request.count:
                        obj = {"id": item.id or 0, "code": item.code or "", "emrName": item.standard_emr or "", 
                                "requirement": item.requirement or "", "instruction": item.instruction or "", 
                                "typeName": item_type_dict.get(item.type, ""), "score": "", "scoreValue": ""}
                        
                        ruleItem = qcGroup.getItem(item.id)
                        if ruleItem.score:
                            obj["score"] = '{:g}'.format(float(ruleItem.score))
                            obj["scoreValue"] = float(ruleItem.score)
                        items.append(obj)
                    index += 1
            res = {"items": items, "total": index}
        return make_response(jsonify(res), 200)
    

class GetCaseList(MyResource):
    
    @pre_request(request, GetCaseListReq)
    def post(self):
        """获取病历列表
        """
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return
        field, pList = app.getDeptPermission(request.operatorId)
        logger.info(f'user id: {request.operatorId}, permType: {field}, departments: {pList}')

        req = QCUtil.get_case_list_req(app, request, field=field, p_list=pList)
        caseList, total = app.getCaseList(req)
        operation_data = {}
        diagnosis_data = {}
        if request.auditType == AUDIT_TYPE_ACTIVE:
            caseIds = [item.caseId for item in caseList]
            operation_data = app.getCaseOperationData(caseIds)
            diagnosis_data = app.getCaseDiagnosis(caseIds, isMz=True)
        items = []
        for x in caseList:
            protoItem = {"caseTags": [], "timeline": {}}
            unmarshalCaseInfo(x, protoItem, request.auditType, isFinal=request.auditStep == "recheck", diagnosis_data=diagnosis_data, operation_data=operation_data)
            if app.app.config.get(Config.QC_AUDIT_ONLY_RECEIVED.format(auditType=request.auditType)) == '1':
                # 当前节点配置项只允许质控已签收的病历时，没有签收时间的病历视为未签收
                protoItem["notReceive"] = int(protoItem["receiveTime"] == "")
            items.append(protoItem)
        res = {"items": items, "total": total, "start": request.start, "size": request.size}
        return make_response(jsonify(res), 200)
    
    
class CaseExport(MyResource):
    
    @pre_request(request, GetCaseListReq)
    def post(self):
        """
        病例导出excel
        """
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return
        # 查询用户数据权限
        field, pList = app.getDeptPermission(request.operatorId)
        logging.info(f'user id: {request.operatorId}, permType: {field}, departments: {pList}')
        have_sample = 2
        if request.auditType != AUDIT_TYPE_ACTIVE:
            have_sample = int(app.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=request.auditType), 2))
        group_flag = int(app.app.config.get(Config.QC_CASE_GROUP_FLAG) or 0)

        req = QCUtil.get_case_list_req(app, request, is_export=1, field=field, p_list=pList)
        caseList, total = app.getCaseList(req)
        operation_data, diagnosis_data = {}, {}
        if request.auditType == AUDIT_TYPE_ACTIVE:
            caseIds = [item.caseId for item in caseList]
            operation_data = app.getCaseOperationData(caseIds)
            diagnosis_data = app.getCaseDiagnosis(caseIds, isMz=True)
        patient_id_name = app.app.config.get(Config.QC_PATIENT_ID_NAME)
        base_file_name = EXPORT_FILE_AUDIT_TYPE.get(request.auditType) + EXPORT_FILE_AUDIT_STEP.get(request.auditStep) + "-{}.xlsx"
        file_name = base_file_name.format(datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(10, 99)))
        file_id = uuid.uuid4().hex
        path_file_name = export_path + file_id + ".xlsx"
        # sort_field = 'dischargeTime' if request.auditType != AUDIT_TYPE_ACTIVE else 'admitTime'
        # sortBy = [(sort_field, -1)]
        # if request.sortField:
        #     sortBy = [(item.field, SORT_DESC_DICT.get(item.way.upper(), -1)) for item in request.sortField]

        # 事中质控根据配置项决定导出是否包含重点病历列
        tag_hide = app.app.config.get(Config.QC_ACTIVE_TAGS) == '2' and request.auditType == AUDIT_TYPE_ACTIVE
        data, data_yaml, reason_column = app.format_qc_list_export_data(caseList, request, have_sample, patient_id_name, group_flag=group_flag, operation_data=operation_data, diagnosis_data=diagnosis_data, tag_hide=tag_hide)
        cfg = BIFormConfig.fromYaml(data_yaml)
        processor = BIDataProcess(cfg, data)
        column_width = []
        if request.detailFields.get("problem") and reason_column:
            column_width = [reason_column, 120]
        processor.toExcel(path=path_file_name, column_width=column_width)
        res = {"id": file_id, "fileName": file_name}
        return make_response(jsonify(res), 200)


class DownloadFile(MyResource):
    
    @after_download(request, export_path)
    @pre_request(request, DownloadFileReq)
    def get(self):
        if not request.id:
            return get_error_resp("DownloadFile require id")
        filename = request.id + ".xlsx"
        fullname = os.path.join(export_path, filename)
        if request.fileName:
            newFullname = os.path.join(export_path, request.fileName)
            os.rename(fullname, newFullname)
            fullname = newFullname
        return get_resp_file(fullname)
        

class GetInpatientList(MyResource):

    def post(self):
        """在院病历列表
        """
        return make_response(jsonify(g.result), 200)

        
class GetCaseTimeline(MyResource):

    @pre_request(request, ["caseId"])
    def get(self):
        """病历审核流程
        """
        caseInfo = self.context.getCaseApplication("hospital").getCaseDetail(caseId=request.caseId)
        if not caseInfo:
            logger.error("GetCaseTimeline, caseId: %s, not exist.", request.caseId)
            return get_error_resp("caseId: %s, not exist." % request.caseId)
        audit = self.context.getAuditApplication("hospital").getAuditRecordById(caseInfo.audit_id)
        data = []
        for t in audit.getTimeline():
            protoItem = {}
            unmarshalAuditTimeline(t, protoItem)
            data.append(protoItem)
        res = {"data": data}
        return make_response(jsonify(res), 200)
    
    
class GetRefusedProblem(MyResource):

    @pre_request(request, ["auditId", "time"])
    def get(self):
        """驳回的问题清单
        """
        auditType = "hospital"
        response = {}
        with self.context.getAuditApplication(auditType).app.mysqlConnection.session() as session:
            if not request.time:
                return get_error_resp("time can not be empty.")
            audit = self.context.getAuditRepository(auditType).get(session, request.auditId)
            if not audit:
                return get_error_resp("auditId: %s is not exist." % request.auditId)
            report = self.context.getRefuseHistoryRepository(auditType).getRefuseHistory(session, audit.caseId, request.time)
            if not report:
                return get_error_resp("caseId: %s, time: %s have no refuse history." % (audit.caseId, request.time))
            reportProblems = report.problems
            response["time"] = report.refuse_time.strftime("%Y-%m-%d %H:%M") if report.refuse_time else ""
            if isinstance(reportProblems, str):
                reportProblems = json.loads(reportProblems)
            response["total"] = len(reportProblems)
            # 医生列表
            doctorCodes = [p.get("refuseCode", "") for p in reportProblems]
            doctors = self.context.getDoctorRepository(auditType).getByCodes(session, doctorCodes)
            emrList = self.context.getEmrRepository(auditType).getEmrList(session, GetEmrListRequest(caseId=audit.caseId, size=10000))
            # 重新申请
            applyDict = {}
            refuseDetails = self.context.getRefuseHistoryRepository(auditType).getRefuseDetail(session, audit.caseId, report.id)
            for d in refuseDetails:
                applyDict[d.doctor] = {
                    "apply_flag": d.apply_flag or 0,
                    "apply_time": d.apply_time.strftime("%Y-%m-%d %H:%M") if d.apply_time else "",
                }
            doctorList = []
            data = []
            for d in doctors:
                if d.id in doctorList:
                    continue
                protoItem = {"doctor": {}, "problems": [], "count": 0}
                protoItem["doctor"]["name"] = d.name
                protoItem["doctor"]["department"] = d.department
                protoItem["doctor"]["code"] = d.id
                protoItem["applyStatus"] = applyDict.get(d.id).get("apply_flag", 0) if applyDict and applyDict.get(d.id) else 0
                protoItem["applyTime"] = applyDict.get(d.id).get("apply_time", "") if applyDict and applyDict.get(d.id) else ""
                for p in reportProblems:
                    if p.get('refuseCode') == d.id:
                        title = '缺失文书'
                        for emr in emrList:
                            if emr.docId == p.get('docId'):
                                title = emr.documentName
                        problem = {"docName": title, "instruction": p.get('reason'), "comment": p.get('comment')}
                        protoItem["problems"].append(problem)
                        protoItem["count"] += 1
                data.append(protoItem)
            response["data"] = data
        return response
    

class GetCaseDetail(MyResource):

    @pre_request(request, GetCaseDetailReq)
    def get(self):
        """获取病历详情
        """
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        caseInfo = app.getCaseDetail(request.caseId)
        if not caseInfo:
            logging.info("GetCaseDetail, caseId: %s is not exist.", request.caseId)
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        isMz = True if request.auditType == AUDIT_TYPE_ACTIVE else False
        diagnosis = app.getCaseDiagnosis([request.caseId], isMz=isMz)
        res = {"basicInfo": {}}
        unmarshalCaseInfo(caseInfo, res["basicInfo"], request.auditType, isFinal=request.auditStep == 'recheck', diagnosis_data=diagnosis)
        # 快照需要查询 originCase.dischargeTime 判断是否已经出院
        if caseInfo.getCaseType == CaseType.SNAPSHOT:
            originCaseInfo = app.getCaseDetail(caseInfo.originCaseId)
            if not originCaseInfo:
                return get_error_resp("caseId: %s is not exist." % request.caseId)
            res["basicInfo"]["dischargeTime"] = originCaseInfo.dischargeTime.strftime('%Y-%m-%d') if originCaseInfo.dischargeTime else ""
        res["basicInfo"]["readOnly"] = request.readOnly
        return make_response(jsonify(res), 200)
    
    
class GetCaseEmrList(MyResource):

    @pre_request(request, GetCaseEmrListReq)
    def get(self):
        """文书列表
        """
        app = self.context.getCaseApplication("hospital")
        emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, size=10000, documentName=request.documentName),
                                 withNoDocOption=request.addSpec)
        emrDict = {emr.docId: emr for emr in emrList}
        emrCount = len(emrList) - 1 if request.addSpec else len(emrList)

        # 文书编目录
        catalog = app.getEmrCatalog(emrList)
        emr_catalog = {}
        catalogItems = []
        groupItem = None
        catalogs = []
        for c in catalog:
            groupItem = {"list": [], "count": 0}  # response.catalog.add()
            groupItem["cid"] = c.get('id') or 10000
            groupItem["cname"] = c.get('name') or '其它'
            groupItem["count"] = len(c.get('items', []))
            for item in c.get('items', []):
                emr = emrDict.get(item)
                if not emr:
                    continue
                protoItem = {}  # groupItem.list.add()
                protoItem["documentName"] = emr.documentName or ''
                protoItem["docId"] = emr.docId or ''
                protoItem["createTime"] = emr.recordTime.strftime('%Y-%m-%d %H:%M:%S') if emr.recordTime else ""
                protoItem["isSave"] = emr.isSave or False
                protoItem["refuseDoctor"] = emr.getRefuseDoctor() or ''
                groupItem["list"].append(protoItem)
                catalogItems.append(item)
                emr_catalog[emr.docId] = c
            catalogs.append(groupItem)
        if len(catalogItems) < emrCount:
            if not groupItem or groupItem["name"] != '其它':
                groupItem = {"list": [], "count": 0}  # response.catalog.add()
                groupItem["cid"] = 10000
                groupItem["cname"] = '其它'
            for emr in emrList:
                if emr.docId in catalogItems:
                    continue
                protoItem = {}  # groupItem.list.add()
                protoItem["docId"] = emr.docId or ''
                protoItem["documentName"] = emr.documentName or ''
                protoItem["createTime"] = emr.recordTime.strftime('%Y-%m-%d %H:%M:%S') if emr.recordTime else ""
                protoItem["isSave"] = emr.isSave or False
                protoItem["refuseDoctor"] = emr.refuseCode or ''
                groupItem["list"].append(protoItem)
                groupItem["count"] += 1
            catalogs.append(groupItem)
        # 文书列表
        if int(app.app.config.get(Config.QC_EMR_SORT) or 1) == 2:
            emrList.sort(key=lambda data: data.recordTime if data.recordTime else data.createTime or datetime.now())
        else:
            emrList.sort(key=lambda data: emr_catalog.get(data.docId, {}).get('id', 10000))

        # contentDocIdDict = app.countEmrContent(request.caseId)
        emr_histories = app.getAuditEmrInfo(caseId=request.caseId)
        total = 0
        items = []
        for emr in emrList:
            protoItem = {}  # response.items.add()
            unmarshalCaseEmr(emr, {}, protoItem)
            # 文书目录
            if emr.docId == '0':
                protoItem["catalogId"] = 0
            else:
                protoItem["catalogId"] = emr_catalog.get(emr.docId).get('id')
                protoItem["catalog"] = emr_catalog.get(emr.docId).get('name')
            # 文书的修改对应的申请记录，如果加上当前申请，多于1个版本说明有过修改
            emr_audit = emr_histories.get(emr.docId, set())
            # emr_audit.add(caseInfo.audit_id)
            protoItem["isChange"] = 1 if len(emr_audit) > 1 else 0
            total += 1
            items.append(protoItem)
        res = {"items": items, "catalog": catalogs, "total": total}
        return make_response(jsonify(res), 200)


class GetEmrVersion(MyResource):
    
    @pre_request(request, ["caseId", "docId", "auditType"])
    def get(self):
        """emr版本
        """
        app = self.context.getAuditApplication("hospital")
        # 查询文书的修改记录
        versions = app.getEmrVersions(caseId=request.caseId, docId=request.docId)
        data = []
        for version in versions:
            protoItem = {}  # response.data.add()
            protoItem["auditId"] = str(version.audit_record.id)
            protoItem["version"] = str(version.dataId)
            protoItem["applyTime"] = version.audit_record.applyTime.strftime("%Y-%m-%d %H:%M") if version.audit_record.applyTime else ""
            protoItem["updateTime"] = version.createTime.strftime("%Y-%m-%d %H:%M") if version.createTime else ""
            req = {'auditId': str(version.audit_record.id), 'caseId': request.caseId, 'docId': request.docId, 'auditType': request.auditType}
            problems, total = self.context.getCaseApplication('hospital').getCaseProblems(GetProblemListRequest(**req))
            protoItem["problemCount"] = total
            data.append(protoItem)
        return make_response(jsonify({"data": data}), 200)
    
    
class GetEmrDiff(MyResource):

    @pre_request(request, ["caseId", "docId", "auditType", "auditId", "version"])
    def get(self):
        """历史版本文书和当前版本对比
        """
        response = {"problems": []}
        response["caseId"] = request.caseId
        response["docId"] = request.docId
        app = self.context.getCaseApplication("hospital")
        caseInfo = app.getCaseDetail(request.caseId)
        if not caseInfo:
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        audit = self.context.getAuditApplication("hospital").getAuditRecordById(auditId=request.auditId)
        if not audit:
            return get_error_resp("auditId: %s is not exist." % request.auditId)
        version_now = app.getEmrVersionByAudit(request.caseId, request.docId, caseInfo.audit_id)
        version_old = app.getEmrVersionByAudit(request.caseId, request.docId, request.auditId)
        response["diff"] = self.context.getEmrRepository("hospital").diff(old=version_old, new=version_now)
        response["newVersion"] = version_now.getMd5()
        response["oldVersion"] = version_old.getMd5()
        response["title"] = f"【{version_now.getDocumentName()}】{audit.applyTime.strftime('%Y-%m-%d')}申请版本同当前最新版本对比结果"
        # response.title = f"【{version_now.getDocumentName()}】历史申请版本同当前最新版本对比结果"
        for title, version in {'最新版本问题': version_now, "{applyTime}版本问题".format(applyTime=audit.applyTime.strftime('%Y-%m-%d')): version_old}.items():
        # for title, version in {'最新版本问题': version_now, "历史版本问题": version_old}.items():
            item = {"data": []} # response.problems.add()
            req = {'caseId': request.caseId, 'docId': request.docId, 'auditType': request.auditType}
            if title == '最新版本问题':
                req['auditId'] = caseInfo.audit_id
            else:
                req['auditId'] = request.auditId
            version_problems, total = self.context.getCaseApplication('hospital').getCaseProblems(GetProblemListRequest(**req))
            unmarshalDiffProblem(item, version_problems, total, title)
            response["problems"].append(item)
        return make_response(jsonify(response), 200)
    
    
class GetCaseEmr(MyResource):

    @pre_request(request, ["caseId", "emrId"])
    def get(self):
        """文书内容
        """
        response = {"data": {}}
        app = self.context.getCaseApplication("hospital")
        emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, docId=request.emrId, withContent=True))
        for emr in emrList:
            unmarshalCaseEmr(emr, {emr.getEmrContentId(): emr.getEmrHtml()}, response["data"])
        return response
    
    
class GetCaseProblem(MyResource):

    @pre_request(request, GetCaseProblemReq)
    def get(self):
        """获取质控问题列表
        """
        def getProblemTags(problem):
            if not problem:
                return []
            t = problem.getTags()
            if problem.qcItemModel:
                t.extend(QcItem(problem.qcItemModel).getTags())
            return t

        response = {"summary": {}, "sumtags": [], "items": [], "groups": []}  # GetCaseProblemResponse()
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s error." % request.auditType)
        # reqDict = MessageToDict(request)
        isFinal = request.auditStep == "recheck"
        caseInfo = app.getCaseDetail(caseId=request.caseId)
        if not caseInfo:
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        reqDict = {c: getattr(request, c) for c in ['id', 'caseId', 'docId', 'auditType', 'nowStatusFlag']}
        reqDict["auditId"] = caseInfo.audit_id
        reqDict["caseStatus"] = caseInfo.status
        reqDict["refuseCount"] = caseInfo.refuseCount or 0
        problems, total = app.getCaseProblems(GetProblemListRequest(**reqDict))
        # 统计
        response["summary"]["total"] = 0
        response["summary"]["addByDr"] = 0
        response["summary"]["confirmed"] = 0
        deductSum = 0  # 问题扣分总和
        problem_id_list = []
        problems_sum_tags = ProblemSumTags()
        for p in problems:
            problem_id_list.append(p.id)
            response["summary"]["total"] += p.getProblemCount()
            if not p.fromAi():
                response["summary"]["addByDr"] += p.getProblemCount()
            else:
                response["summary"]["confirmed"] += p.getProblemCount()
            deductSum += float(p.getScore() if p.getDeductFlag() else 0)
            if p.qcItemModel:
                qcitem = QcItem(p.qcItemModel)
                if qcitem.isSingleDisease():
                    response["summary"]["singleCount"] += p.getProblemCount()
                if qcitem.isVeto():
                    response["summary"]["vetoCount"] += p.getProblemCount()
            # 问题列表标签统计
            problems_sum_tags.add_sum_tags(tags=getProblemTags(p), count=p.getProblemCount())
        # 问题标签统计
        unmarshalProblemSumTags(response["sumtags"], problems_sum_tags)
        # 总扣分
        response["deductSum"] = '{:g}'.format(float(deductSum))
        # 文书列表和对应的标准文书名称
        emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, size=10000), withNoDocOption=False)
        documents = app.getDocumentsByName([emr.documentName.strip() for emr in emrList])
        dorder = {document.name: document.type_order for document in documents}
        dtypes = {document.type_order: document.type_name for document in documents}
        appeal = AppealRepository(self.context.app, request.auditType)
        have_appeal_dict = appeal.get_appeal_dict(problem_id_list, caseId=request.caseId)
        fix_doctor_flag_dict = app.getFixDoctorFlag(request.caseId, request.auditType)
        firstpage_score_dict = {}
        if request.nowStatusFlag:
            firstpage_score_dict = app.getFirstPageScoreDict()
        # 返回值
        if not request.tabIndex:
            for p in problems:
                protoItem = {"tags": []}  # response.items.add()
                unmarshalProblem(p, protoItem, request.auditType, have_appeal_dict=have_appeal_dict)
                response["items"].append(protoItem)
        elif request.tabIndex == 1:
            case_audit_status = 3
            if not request.nowStatusFlag and request.auditType != AUDIT_TYPE_ACTIVE:
                if caseInfo.auditRecord:
                    audit = AuditRecord(caseInfo.auditRecord)
                    auditScore = audit.getScore(request.auditType)
                    problemCount = audit.getProblemCount(request.auditType)
                    if not auditScore and not problemCount:
                        auditScore = 100.0
                    response["caseScore"] = '{:g}'.format(auditScore)
                    response["caseRating"] = parseRating(auditScore)
                    response["lostScore"] = '{:g}'.format(float(100 - auditScore))
                    if audit.getFirstPageScore(request.auditType):
                        response["firstpageScore"] = '{:g}'.format(audit.getFirstPageScore(request.auditType))
                    case_audit_status = parseStatus(isFinal, audit.getStatus(request.auditType, isFinal))
            else:
                # 病历现状/事中质控 不使用统计后的分数, 需根据问题统计

                response["lostScore"] = '{:g}'.format(float(deductSum))
                response["caseScore"] = '{:g}'.format(100 - float(deductSum))
                response["caseRating"] = parseRating(response["caseScore"])

            # 排序和文书列表保持一致
            if int(app.app.config.get(Config.QC_EMR_SORT) or 1) == 2:
                emrList.sort(key=lambda data: data.recordTime if data.recordTime else data.createTime or datetime.now())
            else:
                documents = app.getDocumentsByName([emr.documentName.strip() for emr in emrList])
                order = {document.name: document.type_order for document in documents}
                emrList.sort(key=lambda data: order.get(data.documentName.strip(), 10000))
            fp_lost_score = 0
            for emr in emrList:
                docId = emr.docId
                fixDoctorFlag = fix_doctor_flag_dict.get(docId, 2)
                groupAdded = False  # 每个文书创建一个groups
                group = None
                for p in problems:
                    # 问题状态
                    p_status = p.checkProblemStatus()
                    # 问题标签
                    tags = getProblemTags(p)
                    if request.tag and request.tag not in tags:
                        continue
                    # 问题分组
                    if p.docId and p.docId == docId:
                        if not groupAdded:
                            group = {"summary": {"auditProblemNum": 0, "tipProblemNum": 0, "total": 0}, "problems": []}  # response.groups.add()
                            group["summary"]["total"] = 0
                            group["summary"]["lostScore"] = '0'
                            group["docId"] = p.docId
                            group["docName"] = p.emrInfoModel.documentName if p.emrInfoModel and p.emrInfoModel.documentName else p.title
                            group["createTime"] = p.emrInfoModel.recordTime.strftime('%Y-%m-%d %H:%M') if p.emrInfoModel and p.emrInfoModel.recordTime else ""
                            group["doctorCode"] = p.emrInfoModel.refuseCode if p.emrInfoModel and p.emrInfoModel.refuseCode else ""
                            group["doctor"] = p.doctor or ""
                            group["fixDoctorFlag"] = fixDoctorFlag
                            groupAdded = True
                            if "病案首页" in emr.documentName:
                                group["isFirstPage"] = 1

                        group["summary"]["total"] += p.getProblemCount()
                        group["summary"]["auditProblemNum"] += p_status
                        group["summary"]["tipProblemNum"] += (1 - p_status)
                        group["summary"]["lostScore"] = '{:g}'.format(float(group["summary"]["lostScore"]) + float(p.getScore() if p.getDeductFlag() else 0))
                        item = {"tags": []}  # group.problems.add()
                        unmarshalProblem(p, item, request.auditType, have_appeal_dict=have_appeal_dict)
                        item["catalogId"] = dorder.get(emr.documentName.strip(), 0)  # 文书目录id
                        item["catalog"] = dtypes.get(item["catalogId"], '')
                        if request.auditType == AUDIT_TYPE_ACTIVE:
                            # 事中质控的人工问题均可随时修改, AI问题不可修改
                            item["editStatus"] = 2 if request.readOnly or p.fromAi() else 1
                        else:
                            item["editStatus"] = 2 if request.readOnly or p.refuseFlag == 1 or case_audit_status == 3 else 1
                        item["fixDoctorFlag"] = fixDoctorFlag
                        # 单独计算病案首页文书问题扣分情况
                        fp_score_max = firstpage_score_dict.get(p.qcItemId, {}).get("max_score", 0)
                        fp_score = firstpage_score_dict.get(p.qcItemId, {}).get("score", 0) * (p.problem_count or 0)
                        fp_lost_score += min(fp_score, fp_score_max)
                        group["problems"].append(item)
                if group:
                    response["groups"].append(group)
            if request.nowStatusFlag:
                response["firstpageScore"] = '{:g}'.format(100 - fp_lost_score)
            group = None
            for p in problems:
                # 问题标签
                tags = getProblemTags(p)
                p_status = p.checkProblemStatus()
                if request.tag and request.tag not in tags:
                    continue
                if p.docId and p.docId == "0":
                    fixDoctorFlag = fix_doctor_flag_dict.get(p.docId, 2)
                    if not group:
                        group = {"summary": {"auditProblemNum": 0, "tipProblemNum": 0, "total": 0}, "problems": []}  # response.groups.add()
                        group["docName"] = "文书缺失"
                        group["docId"] = "0"
                        group["summary"]["lostScore"] = '0'
                        group["fixDoctorFlag"] = fixDoctorFlag
                    group["summary"]["total"] += p.getProblemCount()
                    group["summary"]["auditProblemNum"] += p_status
                    group["summary"]["tipProblemNum"] += (1 - p_status)
                    group["summary"]["lostScore"] = '{:g}'.format(float(group["summary"]["lostScore"]) + float(p.getScore() if p.getDeductFlag() else 0))
                    item = {"tags": []}  # group.problems.add()
                    unmarshalProblem(p, item, request.auditType, have_appeal_dict=have_appeal_dict)
                    if request.auditType == AUDIT_TYPE_ACTIVE:
                        # 事中质控的人工问题均可随时修改, AI问题不可修改
                        item["editStatus"] = 2 if request.readOnly or p.fromAi() else 1
                    else:
                        item["editStatus"] = 2 if request.readOnly or p.refuseFlag == 1 or case_audit_status == 3 else 1
                    item["fixDoctorFlag"] = fixDoctorFlag
                    group["problems"].append(item)
            if group:
                response["groups"].append(group)
        elif request.tabIndex == 2:
            case_audit_status = 3
            if not request.nowStatusFlag:
                if caseInfo.auditRecord:
                    audit = AuditRecord(caseInfo.auditRecord)
                    auditScore = audit.getScore(request.auditType)
                    problemCount = audit.getProblemCount(request.auditType)
                    if not auditScore and not problemCount:
                        auditScore = 100.0
                    response["caseScore"] = '{:g}'.format(auditScore)
                    response["caseRating"] = parseRating(auditScore)
                    response["lostScore"] = '{:g}'.format(float(100 - auditScore))
                    if audit.getFirstPageScore(request.auditType):
                        response["firstpageScore"] = '{:g}'.format(audit.getFirstPageScore(request.auditType))
                    case_audit_status = parseStatus(isFinal, audit.getStatus(request.auditType, isFinal))
            else:
                # 病历现状不使用统计后的分数, 需根据问题统计
                response["lostScore"] = '{:g}'.format(float(deductSum))
                response["caseScore"] = '{:g}'.format(100 - float(deductSum))
                response["caseRating"] = parseRating(response["caseScore"])
            for p in problems:
                if not p.doctorCode:
                    p.doctorCode = caseInfo.attendCode
                    p.doctor = caseInfo.attendDoctor
            emrList.append(EmrDocument(self.context.getEmrRepository(request.auditType).emrInfoModel(docId='0', documentName='缺失文书')))
            doctors = app.getCaseDoctors({'caseId': request.caseId, "caseInfo": caseInfo, "emrList": emrList,
                                          "problems": problems})
            orderedDoctor = []
            if doctors:
                doctors = {doctor.id: doctor for doctor in doctors}
                for (code, d) in doctors.items():
                    count = 0
                    for p in problems:
                        if p.doctorCode and p.doctorCode == code:
                            count += p.getProblemCount()
                    if count > 0:
                        orderedDoctor.append([code, count])
            orderedDoctor.sort(key=lambda data: data[1], reverse=True)
            # 按照文书排序
            preOrderedProblems = []
            for emr in emrList:
                for p in problems:
                    if p.docId and p.docId == emr.docId:
                        preOrderedProblems.append(p)
            fp_lost_score = 0
            # 按照医生问题数排序
            for d in orderedDoctor:
                groupAdded = False
                group = None
                for p in preOrderedProblems:
                    # 问题标签
                    tags = getProblemTags(p)
                    if request.tag and request.tag not in tags:
                        continue
                    doctorCode = p.doctorCode if p.doctorCode else caseInfo.attendCode
                    doctorName = doctors.get(p.doctorCode).name if doctors.get(p.doctorCode) else caseInfo.attendDoctor
                    fixDoctorFlag = fix_doctor_flag_dict.get(p.docId, 2)
                    if doctorCode == d[0]:
                        if not groupAdded:
                            group =  {"summary": {"auditProblemNum": 0, "tipProblemNum": 0, "total": 0}, "problems": []}  # response.groups.add()
                            group["summary"]["total"] = 0
                            group["summary"]["lostScore"] = '0'
                            group["doctorCode"] = doctorCode
                            group["doctor"] = doctorName
                            group["department"] = doctors.get(doctorCode).department if doctors.get(doctorCode) else ""
                            group["fixDoctorFlag"] = fixDoctorFlag
                            groupAdded = True
                            title = p.title or ''
                            if not title and p.emrInfoModel:
                                title = p.emrInfoModel.documentName
                            if "病案首页" in title:
                                group["isFirstPage"] = 1
                        group["summary"]["total"] += p.getProblemCount()
                        group["summary"]["lostScore"] = '{:g}'.format(float(group["summary"]["lostScore"]) + float(p.getScore() if p.getDeductFlag() else 0))
                        item = {"tags": []}  # group.problems.add()
                        unmarshalProblem(p, item, request.auditType, have_appeal_dict=have_appeal_dict)
                        if p.emrInfoModel:
                            item["catalogId"] = dorder.get(p.emrInfoModel.documentName.strip(), 0)  # 文书目录id
                            item["catalog"] = dtypes.get(item["catalogId"], '')
                        item["editStatus"] = 2 if request.readOnly or p.refuseFlag == 1 or case_audit_status == 3 else 1
                        item["fixDoctorFlag"] = fixDoctorFlag
                        fp_score_max = firstpage_score_dict.get(p.qcItemId, {}).get("max_score", 0)
                        fp_score = firstpage_score_dict.get(p.qcItemId, {}).get("score", 0) * (p.problem_count or 0)
                        fp_lost_score += min(fp_score, fp_score_max)
                        group["problems"].append(item)
                if group:
                    response["groups"].append(group)
            if request.nowStatusFlag:
                response["firstpageScore"] = '{:g}'.format(100 - fp_lost_score)
        response["total"] = total
        return make_response(jsonify(response), 200)

    
class CheckProblem(MyResource):

    @pre_request(request, CheckProblemReq)
    def get(self):
        """质控问题详情
        """
        response = {"data": {"tags": []}}
        problem = self.context.getCaseApplication("hospital").getProblemDetail(request.id)
        if not problem:
            return get_error_resp("problem id: %s is not exist." % request.id)
        unmarshalProblem(problem, response["data"])
        return make_response(jsonify(response), 200)


class CheckEmr(MyResource):

    @pre_request(request, ["caseId", "docId", "auditType", "auditStep"])
    def get(self):
        """检查文书是否存在质控问题
        """
        response = {}
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        req = {c: getattr(request, c) for c in ["caseId", "docId", "auditType"]}
        problems, total = app.getCaseProblems(GetProblemListRequest(**req))
        response["problemsExist"] = str(total > 0)
        return make_response(jsonify(response), 200)


class AddCaseProblem(MyResource):

    @pre_request(request, AddCaseProblemReq)
    def post(self):
        """添加质控问题
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        result = app.addCaseProblem(request.caseId, request.docId, request.qcItemId, request.operatorId,
                                    request.operatorName,
                                    request.doctor, request.comment, request.requirement, request.deductFlag,
                                    request.score, request.counting, auditStep=request.auditStep)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)
    
    
class AddQCItemProblem(MyResource):
    
    @pre_request(request, AddQCItemProblemReq)
    def post(self):
        """添加质控点和问题
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        result = app.addCaseProblem(request.caseId, request.docId, qcItemId=0, operatorId=request.operatorId, operatorName=request.operatorName,
                                    refuseDoctor=request.doctor, comment=request.comment, requirement=request.requirement,
                                    deductFlag=request.deductFlag, score=request.score, count=request.counting,
                                    newQcItemFlag=True, auditStep=request.auditStep, categoryId=request.categoryId)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)
    
    
class UpdateCaseProblem(MyResource):
    
    @pre_request(request, AddCaseProblemReq)
    def post(self):
        """编辑质控问题
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        result = app.updateProblem(request.id, request.requirement, request.comment, request.deductFlag, request.score,
                                   request.doctor, request.counting, request.operatorId, request.operatorName, auditStep=request.auditStep)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)

    
class DeductProblem(MyResource):
    
    @pre_request(request, DeductProblemReq)
    def put(self, id=0):
        """设置扣分不扣分
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        request.id = id
        result = app.deductProblem(request.id, request.deductFlag, request.operatorId, request.operatorName)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)


class DeleteCaseProblem(MyResource):

    @pre_request(request, ActiveSaveReq)
    def post(self, id=0):
        """删除质控问题
        """
        request.id = id
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        result = app.deleteProblem(request.id, request.operatorId, request.operatorName, auditStep=request.auditStep)
        return g.result

class GetCaseDoctors(MyResource):

    @pre_request(request, GetCaseDoctorsReq)
    def get(self):
        """获取病历的医生列表
        """
        response = {"doctors": []}
        app = self.context.getCaseApplication("hospital")
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        doctors = app.getCaseDoctors(
            {'caseId': request.caseId, "input": request.input, 'attendingFlag': request.attendingFlag,
             'department': request.department})
        total = len(doctors)
        if doctors:
            for d in doctors[:50]:
                protoItem = {}  # response.doctors.add()
                protoItem["code"] = d.id
                protoItem["name"] = d.name or ""
                protoItem["department"] = d.department or ""
                protoItem["role"] = d.role or ""
                response["doctors"].append(protoItem)
        response["total"] = total
        return make_response(jsonify(response), 200)
    
    
class SetRefuseDoctor(MyResource):
    
    @pre_request(request, AddCaseProblemReq)
    def post(self):
        """设置驳回医生
        """
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        result = app.setRefuseDoctor(request.caseId, request.docId, request.doctor, request.operatorId, request.operatorName)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)
    
    
class BatchSetRefuseDoctor(MyResource):

    @pre_request(request, BatchSetRefuseDoctorReq)
    def post(self):
        """批量设置驳回医生
        """
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        if not request.problems:
            return get_error_resp("problems can not be tmpty.")
        result = app.batchSetRefuseDoctor(request.problems, request.doctor, request.operatorId, request.operatorName)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)


class GetRefuseDoctor(MyResource):
    
    @pre_request(request, GetRefuseDoctorReq)
    def get(self):
        """获取驳回医生
        """
        response = {}
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        refuseCode, fixDoctorFlag = app.getRefuseDoctor(request.caseId, request.docId)
        response["doctor"] = refuseCode or ""
        response["fixDoctorFlag"] = fixDoctorFlag
        return response

        
class GetCaseReason(MyResource):

    @pre_request(request, GetCaseReasonReq)
    def get(self):
        """当前病历存在的问题说明
        """
        response = {"problems": [], "total": 0}
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        problems = app.GetCaseReason(request.caseId, ignoreAi=request.ignoreAi, isAddRefuse=request.isAddRefuse)
        emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, size=10000), withNoDocOption=True)
        for emr in emrList:
            protoItem = None
            for p in problems:
                if p.docId == emr.docId:
                    if not protoItem:
                        protoItem = {"children": [], "count": 0}  # response.problems.add()
                        protoItem["id"] = len(response["problems"])
                        protoItem["docId"] = p.docId
                        protoItem["documentName"] = p.emrInfoModel.documentName if p.emrInfoModel else "缺失文书"
                    reasonItem = {}  # protoItem.children.add()
                    reasonItem["id"] = p.id
                    reasonItem["reason"] = f'{p.reason}。{p.comment}'
                    reasonItem["counting"] = p.getProblemCount()
                    protoItem["count"] += p.getProblemCount()
                    response["total"] += p.getProblemCount()
                    protoItem["children"].append(reasonItem)
            if protoItem:
                response["problems"].append(protoItem)
        return response
    
    
class ApproveCase(MyResource):

    @pre_request(request, ApproveCaseReq)
    def post(self):
        """归档
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        result = app.approve(request.caseId, request.operatorId, request.operatorName, request.comment, auditStep=request.auditStep)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)
    
    
class ApproveCaseBatch(MyResource):

    @pre_request(request, ApproveCaseBatchReq)
    def post(self):
        """批量归档
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        for caseId in request.caseId:
            result = app.approve(caseId, request.operatorId, request.operatorName, request.comment, auditStep=request.auditStep)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)


class RefuseCase(MyResource):

    @pre_request(request, RefuseCaseReq)
    def post(self):
        """驳回
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        result = None
        if request.transTo == 'audit':
            # 终审不通过，退回给质控医生
            result = app.recheckRefuse(request.caseId, request.operatorId, request.operatorName, request.comment)
        elif request.transTo == 'clinic':
            # 退回给临床医生
            result = app.refuse(request, toClinic=True)
        g.result["isSuccess"] = result.isSuccess
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)
    
    
class AddRefuseCase(MyResource):

    @pre_request(request, RefuseCaseReq)
    def post(self):
        """
        追加退回
        :return:
        """
        app = self.context.getAuditApplication(request.auditType)
        result = app.refuse(request, toClinic=True, isAdd=True)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)
    

class LockCase(MyResource):
    
    def post(self):
        """
        病历封存
        """
        # todo 未实现
        return make_response(jsonify(g.result), 200)
    
    
class UnlockCase(MyResource):
    
    def post(self):
        """
        病历撤销封存
        """
        # todo 未实现
        return make_response(jsonify(g.result), 200)
    
    
class RevokeApproved(MyResource):

    @pre_request(request, RefuseCaseReq)
    def post(self):
        """撤销归档
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        # 撤销
        result = app.cancelApprove(request.caseId, request.operatorId, request.operatorName, request.comment, auditStep=request.auditStep)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)
    
    
class RevokeRefused(MyResource):

    @pre_request(request, RefuseCaseReq)
    def post(self):
        """撤销驳回
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        result = None
        if request.transFrom == 'clinic':
            # 从临床撤回
            # TODO 查询驳回记录，emr接口需要的参数
            result = app.cancelRefuse(request.caseId, request.operatorId, request.operatorName, request.comment, auditStep=request.auditStep, transFrom=request.transFrom)
        elif request.transFrom == 'audit':
            # 从质控医生撤回
            result = app.cancelRefuse(request.caseId, request.operatorId, request.operatorName, request.comment, toRecheck=True, auditStep=request.auditStep)
            return make_response(jsonify(g.result), 200)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        return make_response(jsonify(g.result), 200)
    
    
class GetCaseCheckHistory(MyResource):
    
    @pre_request(request, GetCaseCheckHistoryReq)
    def get(self, caseId=""):
        """质控日志
        """
        response = {"items": []}
        request.caseId = caseId
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        checkHistory, total = app.getCheckHistory(request.caseId, auditStep=request.auditStep,
                                                  start=(request.page - 1) * request.count, size=request.count)
        count = 0
        for h in checkHistory:
            protoItem = {}  # response.items.add()
            unmarshalCheckHistory(h, protoItem)
            count += 1
            response["items"].append(protoItem)
        response["total"] = total
        response["page"] = request.page
        response["count"] = count
        return make_response(jsonify(response), 200)
    
    
class GetAdviceType(MyResource):
    
    @pre_request(request, GetCaseCheckHistoryReq)
    def get(self):
        """医嘱类别"""
        response = {"items": []}
        with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
            for o in self.context.getOrderTypeRepository("hospital").getList(session):
                protoItem = {}  # response.items.add()
                protoItem["code"] = o.type or ""
                protoItem["name"] = o.name or ""
        return response
        
        
class GetMedicalAdvice(MyResource):
    
    @pre_request(request, GetMedicalAdviceReq)
    def get(self):
        """医嘱列表
        """
        response = {}
        app = self.context.getCaseApplication("hospital")
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        with app.app.mysqlConnection.session() as session:
            listReq = {
                "caseId": request.caseId,
                "startTime": request.startTime,
                "endTime": request.endTime,
                "name": request.name,
                "start": (request.page - 1) * request.count,
                "size": request.count
            }
            if request.category:
                listReq["orderType"] = request.category.split(',')
            if request.status:
                listReq["status"] = str(request.status).split(',')
            if request.type:
                listReq["orderFlag"] = request.type.split(',')
            req = GetOrderListRequest(**listReq)
            orderList = self.context.getOrderRepository("hospital").search(session, req)
            total = self.context.getOrderRepository("hospital").count(session, req)
            drugTagDict = self.context.getOrderRepository("hospital").getDrugTags(session)
            for o in orderList:
                protoItem = {}  # response.items.add()
                unmarshalMedicalAdvice(o, protoItem)
                protoItem["tag"] = drugTagDict.get(protoItem["orderName"], '')
            response["total"] = total
            return make_response(jsonify(response), 200)
        

class GetEmrData(MyResource):

    @pre_request(request, GetEmrDataReq)
    def post(self):
        """获取病历数据用于质控 - ai质控专用
        """
        response = {"basicInfo": {}, "emr": [], "doctor_advice": []}
        # 病历基本信息
        app = self.context.getCaseApplication('hospital')
        caseInfo = app.getCaseDetail(request.caseId)
        if not caseInfo:
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        # 赋值基本信息
        response["basicInfo"]["id"]= caseInfo.id or 0
        response["basicInfo"]["caseId"]= caseInfo.caseId or ""
        response["basicInfo"]["patientId"]= caseInfo.patientId or ""
        response["basicInfo"]["visitTimes"]= caseInfo.visitTimes or 0
        response["basicInfo"]["name"]= caseInfo.name or ""
        response["basicInfo"]["gender"]= parseGender(caseInfo.gender)
        response["basicInfo"]["age"]= f'{caseInfo.age or ""}{caseInfo.ageUnit or ""}'
        response["basicInfo"]["hospital"]= caseInfo.hospital or ""
        response["basicInfo"]["branch"]= caseInfo.branch or ""
        response["basicInfo"]["department"]= caseInfo.department or ""
        response["basicInfo"]["attendDoctor"]= caseInfo.attendDoctor or ""
        response["basicInfo"]["admitTime"]= caseInfo.admitTime.strftime('%Y-%m-%d %H:%M:%S') if caseInfo.admitTime else ""
        response["basicInfo"]["dischargeTime"]= caseInfo.dischargeTime.strftime('%Y-%m-%d %H:%M:%S') if caseInfo.dischargeTime else ""
        if caseInfo.dischargeTime:
            response["basicInfo"]["inpDays"]= caseInfo.inpDays or 0
        response["basicInfo"]["isDead"]= True if caseInfo.isDead else False
        response["basicInfo"]["diagnosis"]= caseInfo.diagnosis or ""
        response["basicInfo"]["ward"]= caseInfo.wardName or ""
        response["basicInfo"]["bedno"]= caseInfo.bedId or ""
        response["basicInfo"]["dischargeDept"]= caseInfo.outDeptName or ""
        # TODO 将标准文书对照加入到getCaseEmr中，一次查询获取到类型对应的文书列表
        for emr in app.getAIEmrData(request.caseId, request.docType):
            protoItem = {}  # response.emr.add()
            unmarshalCaseEmr(emr, {emr.getEmrContentId(): emr.getEmrHtml()}, protoItem, {emr.getEmrContentId(): emr.getEmrContents()})
            if protoItem["createTime"]== "":
                protoItem["createTime"]= '0001-01-01 00:00:00'
            if protoItem["updateTime"]== "":
                protoItem["updateTime"]= '0001-01-01 00:00:00'
            if protoItem["recordTime"]== "":
                protoItem["recordTime"]= '0001-01-01 00:00:00'
            response["emr"].append(protoItem)
        # 医嘱
        if not request.docType or '医嘱' in request.docType:
            for order in app.getMedicalAdvice(GetOrderListRequest(caseId=request.caseId, size=10000)):
                protoItem = {}  # response.doctor_advice.add()
                protoItem["order_no"]= order.order_no or ''
                protoItem["order_type"]= order.order_type or ''
                protoItem["set_no"]= order.set_no or ''
                protoItem["date_start"]= order.date_start.strftime('%Y-%m-%d %H:%M:%S') if order.date_start else ''
                protoItem["date_stop"]= order.date_stop.strftime('%Y-%m-%d %H:%M:%S') if order.date_stop else ''
                protoItem["code"]= order.code or ''
                protoItem["name"]= order.name or ''
                protoItem["dosage"]= order.dosage or ''
                protoItem["unit"]= order.unit or ''
                protoItem["instruct_name"]= order.instruct_name or ''
                protoItem["frequency_code"]= order.frequency_code or ''
                protoItem["frequency_name"]= order.frequency_name or ''
                protoItem["order_flag"]= order.order_flag or ''
                response["doctor_advice"].append(protoItem)
        return make_response(jsonify(response), 200)
        
        
class GetConfigItems(MyResource):
    
    def get(self):
        """配置项
        """
        response = {"items": []}
        app = self.context.getAuditApplication("hospital")
        configItems = app.app.config.itemList
        for item in configItems:
            protoItem = {}  # response.items.add()
            protoItem["name"] = item.name
            protoItem["value"] = str(item.value) if item.value else ""
            protoItem["system"] = item.platform if item.platform else ""
            protoItem["scope"] = item.scope if item.scope else ""
            response["items"].append(protoItem)

        return make_response(jsonify(response), 200)
    
    def post(self):
        """设置配置项
        """
        app = self.context.getAuditApplication("hospital")
        app.app.config.set(request.name, request.value, platform=request.system, scope=request.scope)
        return make_response(jsonify(g.result), 200)
    

class CrawlCase(MyResource):

    @pre_request(request, RefuseCaseReq)
    def post(self):
        """手动请求更新病历数据
        """
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        caseInfo = app.getCaseDetail(request.caseId)
        if not caseInfo:
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        if caseInfo.getCaseType() == CaseType.SNAPSHOT:
            originCaseInfo = app.getCaseDetail(caseInfo.originCaseId)
            if not originCaseInfo:
                return get_error_resp("originCaseId: %s is not exist." % caseInfo.originCaseId)
            if originCaseInfo.dischargeTime:
                g.result["message"] = "当前患者已出院，不可更新病历！"
                g.result["isSuccess"] = "False"
                return make_response(jsonify(g.result), 200)
            sampleApp = self.context.getSampleApplication(request.auditType)
            if not sampleApp:
                return get_error_resp("auditType: %s is error." % request.auditType)
            g.result["isSuccess"] = str(sampleApp.sendSnapshotMessage([request.caseId], request.auditType))
        else:
            auditApp = self.context.getAuditApplication(request.auditType)
            if not auditApp:
                return get_error_resp("auditType: %s is error." % request.auditType)
            g.result["isSuccess"] = str(auditApp.crawlCase(caseInfo.caseId, caseInfo.patientId, auditType=request.auditType))
        return make_response(jsonify(g.result), 200)

        
class GetCaseDeductDetail(MyResource):

    @pre_request(request, ["caseId"])
    def get(self):
        """
        院级病案得分扣分明细接口的默认实现
        """
        response = {"data": []}
        app = self.context.getCaseApplication('hospital')
        caseInfo = app.getCaseDetail(request.caseId)
        if not caseInfo:
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        emrList = app.getCaseEmr(GetEmrListRequest(caseId=request.caseId, size=10000))
        emrDict = {emr.docId: emr.documentName for emr in emrList}
        emrDict['0'] = "缺失文书"

        app = self.context.getAuditApplication('hospital')
        deductList = app.getDeductDetail(caseInfo.caseId, caseInfo.audit_id)
        for item in deductList:
            data = {}  # response.data.add()
            data["instruction"]= item.reason
            data["totalScore"]= item.score
            data["documentName"]= emrDict.get(item.docId, "") or ''
            data["docId"]= item.docId or ''
            data["createTime"]= item.createTime or ''
            data["operatorName"]= item.operatorName or ''
            data["problemCount"]= item.problemCount or 0
            data["singleScore"]= item.singleScore or 0
            data["qcItemId"]= item.qcItemId or 0
            response["data"].append(data)
        response["total"] = len(deductList)
        return make_response(jsonify(response), 200)


class ArchiveScoreExport(MyResource):

    @pre_request(request, GetCaseListReq)
    def post(self):
        """院级病历得分病历列表导出
        """
        response = {}
        app = self.context.getCaseApplication('hospital')
        params = ["branch", "ward", "department", "attend", "rating",
                  "caseId", "patientId", "reviewer", "problemFlag", "patientName",
                  "autoReviewFlag", "firstPageFlag", "start", "size",
                  "auditType", "auditStep", "startTime", "endTime", "caseType", "deptType", "timeType",
                  "diagnosis", "operation", "archiveRating", "refuseCount"]
        req = {c: getattr(request, c) for c in params}
        req["is_export"] = 1
        if request.caseType:
            if request.caseType == 'running':
                req['includeCaseTypes'] = [CaseType.ACTIVE]
            elif request.caseType == 'archived':
                req['includeCaseTypes'] = [CaseType.ARCHIVE]
            elif request.caseType == 'Final':
                req['includeCaseTypes'] = [CaseType.FINAL]
        req['isFinal'] = request.auditStep == "recheck"
        if request.assignDoctor:
            req['sampleExpert'] = request.assignDoctor
        if app.app.config.get(Config.QC_PRECONDITION.format(auditType=request.auditType)):
            req["precondition"] = app.app.config.get(Config.QC_PRECONDITION.format(auditType=request.auditType))
        req["not_apply"] = app.app.config.get(Config.QC_NOT_APPLY_AUDIT.format(auditType=request.auditType))
        if request.tag:
            req['tags'] = [request.tag]
        req['timeType'] = int(request.timeType) if request.timeType else 0
        req = GetCaseListRequest(**req)

        caseList, total = app.getCaseList(req)

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        patient_id_name = app.app.config.get(Config.QC_PATIENT_ID_NAME)
        app.writeArchiveScoreExcel(sheet, caseList, patient_id_name)

        file_id = uuid.uuid4().hex
        workbook.save(export_path + file_id + ".xlsx")

        response["id"] = file_id
        now = arrow.utcnow().to('+08:00').naive.strftime("%Y%m%d")
        response["fileName"] = f'院级病案得分统计-{now}.xlsx'
        return make_response(jsonify(response), 200)


class GetDiseaseList(MyResource):

    @pre_request(request, ["input"])
    def get(self):
        """专病诊断列表
        """
        response = {"items": []}
        with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
            for d in self.context.getDiseaseRepository("hospital").getList(session, sug=request.input):
                response["items"].append(d.name)
        return make_response(jsonify(response), 200)


class GetDiagnosisList(MyResource):

    @pre_request(request, ["input"])
    def get(self):
        """诊断列表
        """
        response = {"items": []}
        with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
            for d in self.context.getDiagnosisRepository("hospital").getList(session, sug=request.input):
                if d.code and d.name:
                    protoItem = {}  # response.items.add()
                    protoItem["code"] = d.code
                    protoItem["name"] = d.name
                    response["items"].append(protoItem)
        return make_response(jsonify(response), 200)


class GetOperationList(MyResource):

    @pre_request(request, ["input"])
    def get(self):
        """手术列表
        """
        response = {"items": []}
        with self.context.getAuditApplication("hospital").app.mysqlConnection.session() as session:
            for d in self.context.getOperationRepository("hospital").getList(session, sug=request.input):
                if d.code and d.name:
                    protoItem = {}  # response.items.add()
                    protoItem["code"] = d.code
                    protoItem["name"] = d.name
                    response["items"].append(protoItem)
        return make_response(jsonify(response), 200)


class GetOrg(MyResource):

    def get(self):
        """
        机构列表
        """
        # todo 未实现
        return make_response(jsonify(g.result), 200)
    
    
class GetCalendar(MyResource):
    
    @pre_request(request, ["startTime", "endTime"])
    def post(self):
        """获取日历维护数据
        """
        response = {"data": []}

        start = arrow.get(request.startTime).to('+08:00').strftime('%Y-%m-%d %H:%M:%S')
        end = arrow.get(request.endTime).to('+08:00').strftime('%Y-%m-%d %H:%M:%S')
        with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
            for d in self.context.getCalendarRepository("hospital").getList(session, start, end):
                protoItem = {}  # response.data.add()
                protoItem["date"] = arrow.get(d.date).strftime('%Y-%m-%dT%H:%M:%SZ')
                protoItem["isWorkday"] = str(d.isWorkday == 1)
                response["data"].append(protoItem)
        return make_response(jsonify(response), 200)
    
    
class SetCalendar(MyResource):

    @pre_request(request, ["data:list"])
    def post(self):
        """设置日历维护数据
        """
        data = [{'date': arrow.get(info["date"]).to('+08:00').strftime('%Y-%m-%d'), 'isWorkday': 1 if info["isWorkday"] == "True" else 0} for info in request.data]

        try:
            with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
                self.context.getCalendarRepository("hospital").upsert(session, data)
        except Exception as e:
            logging.error(e)
        return make_response(jsonify(g.result), 200)


class GetQCReport(MyResource):

    @pre_request(request, ["auditType", "caseId"])
    def post(self):
        """质控评分表
        """
        response = {}
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        caseInfo = app.getCaseDetail(request.caseId)
        if not caseInfo:
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        response["patientId"] = caseInfo.inpNo or caseInfo.patientId
        response["name"] = caseInfo.name
        report = app.getScoreReport(request.caseId)
        response["content"] = report
        return make_response(jsonify(response), 200)


class GetCaseLab(MyResource):

    @pre_request(request, ["caseId", "start:int", "size:int"])
    def get(self):
        """化验报告
        """
        response = {"data": []}
        app = self.context.getCaseApplication('hospital')
        caseInfo = app.getCaseDetail(request.caseId)
        if not caseInfo:
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        response["caseId"] = caseInfo.caseId
        reports, total = app.getCaseLabList(GetLabListRequest(caseId=request.caseId, start=request.start, size=request.size or 100))
        for r in reports:
            protoItem = {"items": []}  # response.data.add()
            unmarshalLabReport(r, protoItem)
            response["data"].append(protoItem)
        response["total"] = total
        return make_response(jsonify(response), 200)

        
class GetCaseExam(MyResource):

    @pre_request(request, ["caseId", "start:int", "size:int"])
    def get(self):
        """检查报告
        """
        response = {"data": []}
        app = self.context.getCaseApplication('hospital')
        caseInfo = app.getCaseDetail(request.caseId)
        if not caseInfo:
            return get_error_resp("caseId: %s is not exist." % request.caseId)
        response["caseId"] = caseInfo.caseId
        reports, total = app.getCaseExamList(GetExamListRequest(caseId=request.caseId, withTotal=True, start=request.start, size=request.size or 100))
        for exam in reports:
            protoItem = {}  # response.data.add()
            unmarshalExamination(exam, protoItem)
            response["data"].append(protoItem)
        response["total"] = total
        return make_response(jsonify(response), 200)


class GetIpBlockList(MyResource):

    @pre_request(request, GetIpBlockListReq)
    def get(self):
        """获取医生端ip黑白名单列表
        """
        response = {"data": []}

        with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
            handler = session.query(IpRule)
            if request.ip:
                handler = handler.filter_by(ip=request.ip)
            if request.rule:
                handler = handler.filter_by(rule=request.rule)
            # 列表总数
            response["total"] = handler.count()
            # 黑白名单列表
            for r in handler.slice(request.start, request.start+request.size).all():
                protoItem = {}  # response.data.add()
                protoItem["id"] = r.id
                protoItem["ip"] = r.ip or ''
                protoItem["rule"] = r.rule or 0
                response["data"].append(protoItem)
        return make_response(jsonify(response), 200)
    
    @pre_request(request, GetIpBlockListReq)
    def post(self):
        """创建或修改医生端ip黑白名单
        """
        if not request.ip:
            return get_error_resp("ip can not be empty.")
        with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
            rule = session.query(IpRule).filter_by(ip=request.ip).first()
            if rule:
                rule.rule = request.rule
            else:
                session.add(IpRule(ip=request.ip, rule=request.rule or 0))
                session.commit()
        return make_response(jsonify(g.result), 200)


class DeleteIpBlock(MyResource):

    @pre_request(request, GetIpBlockListReq)
    def delete(self, id=0):
        """删除黑白名单中ip记录
        """
        request.id = id
        if not request.id:
            return get_error_resp("ip can not be empty.")
        with self.context.getCaseApplication("hospital").app.mysqlConnection.session() as session:
            session.query(IpRule).filter(IpRule.id == request.id).delete()
            session.commit()
        return make_response(jsonify(g.result), 200)
        
class GetConfigList(MyResource):

    @pre_request(request, ["input", "scope"])
    def post(self):
        """
        配置项管理-获取配置列表
        """
        response = {"items": []}
        app = self.context.getAuditApplication('hospital')
        items = app.app.config.getConfigList(request)
        for item in items:
            protoItem = {"choice": []}  # response.items.add()
            protoItem["scope"]= item.scope or ''
            protoItem["name"]= item.name_ch or ''
            protoItem["value"]= item.value or ''
            protoItem["description"]= item.message or ''
            protoItem["type"]= item.type or ''
            protoItem["key"]= item.name or ''
            protoItem["default"]= item.default_value or ''
            if item.choice:
                for i in item.choice.split('|'):
                    protoItem["choice"].append(json.loads(i))
            response["items"].append(protoItem)
        return make_response(jsonify(response), 200)


class UpdateConfigList(MyResource):

    @pre_request(request, ["config:dict"])
    def post(self):
        """
        配置项管理-更新配置列表
        """
        app = self.context.getAuditApplication('hospital')
        app.updateConfig(request)
        app.app.config.reload()
        return make_response(jsonify(g.result), 200)


class CaseGroupList(MyResource):

    @pre_request(request, ["input"])
    def get(self):
        """
        诊疗组筛选框列表
        :return:
        """
        response = {"items": []}
        app = self.context.getAuditApplication('hospital')
        app.getGroupList(request.input, response)
        return make_response(jsonify(response), 200)


class ArchiveSampleList(MyResource):

    @pre_request(request, GetCaseListReq)
    def post(self):
        """抽取病历列表查询结果直接归档
        """
        app = self.context.getAuditApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        if app.app.config.get(Config.QC_SAMPLE_STATUS.format(auditType=request.auditType)) != '1':
            return get_error_resp("auditType: %s 未开启抽取." % request.auditType)
        field, pList = app.getDeptPermission(request.operatorId)
        req = QCUtil.get_case_list_req(app, request, field=field, p_list=pList)
        existCaseIds = list(request.existCaseIds) if request.existCaseIds else []
        req.start = 0
        req.size = 1000000
        result = app.archiveCaseList(req, request.operatorId, exclude=existCaseIds)
        g.result["isSuccess"] = str(result.isSuccess)
        g.result["message"] = result.message
        # 异步处理归档
        QCUtil.check_archive_task(self.context)
        return make_response(jsonify(g.result), 200)
    
    
class ExternalSystemLinks(MyResource):
    
    @pre_request(request, ApproveCaseReq)
    def get(self):
        """获取其它系统的外链
        """
        response = {"links": []}
        app = self.context.getCaseApplication("hospital")
        doctorId = request.operatorName
        caseInfo = app.getCaseDetail(request.caseId)
        for link in app.getExternalLinks():
            protoItem = {}  # response.links.add()
            protoItem["title"] = link.title
            protoItem["url"] = link.url
            protoItem["icon"] = link.icon or ""
            if caseInfo:
                protoItem["url"] = link.url.format(caseId=caseInfo.caseId, patientId=caseInfo.patientId, inpNo=caseInfo.inpNo, doctorId=doctorId)
            response["links"].append(protoItem)
        return make_response(jsonify(response), 200)


class ActiveSave(MyResource):

    @pre_request(request, ActiveSaveReq)
    def post(self):
        """
        事中质控-保存质控结果
        :return:
        """
        app = self.context.getCaseApplication(request.auditType)
        if not app:
            return get_error_resp("auditType: %s is error." % request.auditType)
        operatorId, name, operatorName = self.context.getAuditApplication(request.auditType).ensureUserName(request.operatorId, request.operatorName)
        app.active_save(request, name)
        return make_response(jsonify(g.result), 200)
    
    
class ProblemRecordList(MyResource):

    @pre_request(request, ProblemRecordListReq)
    def get(self):
        """
        问题日志列表
        :return:
        """
        response = {"data": []}
        app = self.context.getCaseApplication("hospital")
        data, response["total"] = app.getProblemRecordList(request)
        for item in data:
            protoItem = {}  # response.data.add()
            unmarshalProblemRecordList(protoItem, item)
            response["data"].append(protoItem)
        return make_response(jsonify(response), 200)


class ProblemRecordDetail(MyResource):

    @pre_request(request, ["caseId", "auditType", "qcItemId"])
    def get(self):
        """
        问题日志详情
        :return:
        """
        response = {"data": []}
        app = self.context.getCaseApplication("hospital")
        data = app.getProblemRecordDetail(request)
        for item in data:
            protoItem = {}  # response.data.add()
            unmarshalProblemRecordDetail(protoItem, item)
            response["data"].append(protoItem)
        return make_response(jsonify(response), 200)


class UrgeRefusedCase(MyResource):

    @pre_request(request, ["caseIds:list"])
    def post(self):
        """针对已退回状态的病历，在配置项可选的环节 对科室质控催办
        """
        app = self.context.getCaseApplication("hospital")
        app.urgeRefusedCase(request.caseIds)
        return make_response(jsonify(g.result), 200)

    