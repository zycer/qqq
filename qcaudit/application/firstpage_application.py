#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   firstpage_application.py
@Time    :   2023/06/27 10:13:48
@Author  :   zhangda 
@Desc    :   None
'''


import json
import logging
import random
import uuid
from datetime import datetime

import arrow
import requests
from sqlalchemy import or_, func

from qcaudit.config import Config
from qcaudit.domain.case.casetagrepository import CaseTagRepository
from qcaudit.domain.diagnosis.diagnosis import DiagnosisInfo, DiagnosisDict
from qcaudit.domain.operation.operationrepository import OperationRepository
from qcaudit.domain.case.caserepository import CaseRepository
from typing import List, Any
from qcaudit.domain.operation.req import OperationRequest
from qcaudit.domain.case.req import GetListRequest
from qcaudit.domain.req import Page, SortField
from qcaudit.service.protomarshaler import setRequestStatus
from qcaudit.utils.towebconfig import CASE_LIST_YAML


class FirstPageApplication:

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.operation_repository = OperationRepository(self.app)
        self.case_repository = CaseRepository(self.app)
        self.caseTagRepository = CaseTagRepository(self.app)
        self.case_model = self.app.mysqlConnection["case"]
        self.diagnosis_info_model = self.app.mysqlConnection["diagnosis_info"]
        self.fp_diagnosis_model = self.app.mysqlConnection["fpdiagnosis"]
        self.origin_dict_model = self.app.mysqlConnection["diagnosis_origin_dict"]
        self.diagnosis_dict_model = self.app.mysqlConnection["mi_diagnosis_dict"]
        self.narcosis_model = self.app.mysqlConnection["narcosis"]
        self.diagnosis_origin_dict = self.app.mysqlConnection["diagnosis_origin_dict"]

    def getCaseList(self, req: GetListRequest):
        with self.app.mysqlConnection.session() as session:
            tags = {t.code: t for t in self.expunge(session, self.caseTagRepository.getList(session))}

            count = self.case_repository.getFPCaseListCount(session, req)
            items = self.case_repository.getFPCaseList(session, req)
            for item in items:
                item.convertTagToModel(tags)
                item.expunge(session)
            return items, count

    def getCaseListReq(self, request, is_export=0):
        """
        获取病历列表查询请求结构体
        :return:
        """
        params = ['codeStatus', 'department', 'branch', 'doctor', 'startTime', 'endTime', 'timeType', 'problemFlag',
                  'patientId', 'attend', 'tag', 'diagnosis', 'operation', 'ward', 'deptType', 'fieldData', 'start', 'size']
        reqDict = {c: getattr(request, c) for c in params}
        # reqDict['page'] = Page(start=request.start, size=request.size)
        setRequestStatus(reqDict)
        reqDict["not_apply"] = self.app.config.get(Config.QC_NOT_APPLY_AUDIT.format(auditType="firstpage"))
        reqDict['is_export'] = is_export
        reqDict['sortFields'] = [SortField(field="dischargeTime", table="case")]
        req = GetListRequest(**reqDict)
        return req

    @classmethod
    def get_file_id(cls, file_name):
        """
        获取文件id
        :return:
        """
        return uuid.uuid3(uuid.NAMESPACE_DNS, file_name + str(random.randint(100, 1000))).hex

    def format_case_list(self, data, request):
        """
        格式化导出数据
        :return:
        """
        to_excel_data = []
        for item in data:
            problemCount = 0
            score = 100
            inpDays = (item.inpDays or 0) if item.dischargeTime else (datetime.now() - item.admitTime).days
            tags = ""
            if item.TagsModel:
                tags = ",".join([tag.name for tag in item.TagsModel])
            if item.audit_record:
                problemCount = item.audit_record.fpProblemCount or 0
                score = item.audit_record.firstpageScore or 100
            coder = ""
            codeTime = ""
            if item.fp_info:
                coder = item.fp_info.coder or ""
                codeTime = item.fp_info.code_time.strftime('%Y-%m-%d') if item.fp_info.code_time else ''
            dischargeTime = item.dischargeTime.strftime('%Y-%m-%d') if item.dischargeTime else ''
            tmp = {"重点病历": tags, "问题": problemCount, "分数": score, "病历号": item.patientId, "姓名": item.name or "",
                   "科室": item.outDeptName or item.department or '', "病区": item.branch or '', "入院日期": item.admitTime.strftime('%Y-%m-%d') if item.admitTime else '',
                   "出院日期": dischargeTime, "住院天数": inpDays, "责任医生": item.attendDoctor or '',
                   "编码员": coder, "编码日期": codeTime, "编码状态": "已编码" if item.codeStatus else "未编码", "dischargeTime": int(dischargeTime.replace("-", "") or 0)}
            to_excel_data.append(tmp)
        if not request.fieldData:
            return to_excel_data, CASE_LIST_YAML

        return to_excel_data, self.get_yaml_by_fieldData(request.fieldData)

    @classmethod
    def get_yaml_by_fieldData(cls, data):
        """
        获取导出配置
        :param data:
        :return:
        """
        data_yaml = '''\nname: test\nfields:\n'''
        for field in data[1:]:
            data_yaml += "    - name: " + field + "\n"
        data_yaml += '''    - name: dischargeTime\n      hide: true\ngroupFields:\n    - name: ''' + data[0]
        return data_yaml

    def get_case_diagnosis(self, request):
        """
        查询病历诊断信息
        :param request:
        :return:
        """
        data = []
        with self.app.mysqlConnection.session() as session:
            self.logger.info("get_case_diagnosis, request.syncFlag: %s", request.syncFlag)
            if request.syncFlag == 1:
                # 执行同步操作
                self.sync_case_diagnosis(session, request.caseId)
            query = session.query(self.diagnosis_info_model).filter(
                self.diagnosis_info_model.caseId == request.caseId, self.diagnosis_info_model.is_deleted == 0).order_by(
                self.diagnosis_info_model.orderNum)
            # self.logger.info("get_case_diagnosis, query: %s", query)
            for item in query.all():
                session.expunge(item)
                data.append(item)
        if not data:
            if request.syncFlag != 1:
                query_is_first = session.query(func.count(self.diagnosis_info_model.id).label("c")).filter(
                    self.diagnosis_info_model.caseId == request.caseId).first()
                if not query_is_first.c:
                    # 判断该病历还未抓取诊断 从fpdiagnosis中抓诊断数据
                    request.syncFlag = 1
                    self.logger.info("get_case_diagnosis, set request.syncFlag = 1, request.syncFlag: %s", request.syncFlag)
                    return self.get_case_diagnosis(request)
        return data

    def sync_case_diagnosis(self, session, caseId):
        """
        同步病历诊断信息
        :return:
        """
        now_time = arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S')
        session.query(self.diagnosis_info_model).filter(
            self.diagnosis_info_model.caseId == caseId, self.diagnosis_info_model.is_deleted == 0).update(
            {'is_deleted': 1}, synchronize_session=False)

        fp_dig_data = session.query(self.fp_diagnosis_model).filter(self.fp_diagnosis_model.caseId == caseId).all()
        origin_dig_dict = self.get_origin_dig_dict(session, fp_dig_data)
        is_primary = 1
        orderNum = 1
        for fp_dig in fp_dig_data:
            obj = DiagnosisInfo.newObject(self.app)
            obj.setModel(
                caseId=caseId,
                isPrimary=is_primary,
                code=origin_dig_dict.get(fp_dig.icdname, {}).get("code", ""),
                name=origin_dig_dict.get(fp_dig.icdname, {}).get("name", ""),
                originName=fp_dig.icdname,
                coder="system sync",
                create_time=now_time,
                update_time=now_time,
                orderNum=orderNum
            )
            is_primary = 0
            orderNum += 1
            session.add(obj.model)
        self.sync_pathology_poison(session, caseId, now_time)
        session.commit()

    def get_origin_dig_dict(self, session, fp_dig_data):
        """
        诊断-原始诊断映射表查询数据
        :param session:
        :param fp_dig_data:
        :return:
        """
        origin_dig_names = [item.icdname for item in fp_dig_data]
        origin_dig_data = session.query(self.diagnosis_origin_dict).filter(
            self.diagnosis_origin_dict.originName.in_(origin_dig_names)).all()
        origin_dig_dict = {}
        for item in origin_dig_data:
            origin_dig_dict[item.originName] = {"code": item.code, "name": item.name}
        return origin_dig_dict

    def sync_pathology_poison(self, session, caseId, now_time):
        """
        同步病历诊断、损伤中毒诊断
        :return:
        """
        first_page_model = self.app.mysqlConnection["firstpage"]
        first_page_info = session.query(first_page_model).filter(first_page_model.caseId == caseId).first()
        if first_page_info:
            if first_page_info.pathology_diag and first_page_info.pathology_code:
                # 存在原始病历诊断,
                obj = DiagnosisInfo.newObject(self.app)
                obj.setModel(
                    caseId=caseId,
                    originName=first_page_info.pathology_diag,
                    coder="system sync",
                    create_time=now_time,
                    update_time=now_time,
                    type=1,
                )
                # 映射关系表查后, 存入DiagnosisInfo
                diagnosis_origin_info = session.query(self.diagnosis_origin_dict).filter(
                    self.diagnosis_origin_dict.originName == first_page_info.pathology_diag).first()
                if diagnosis_origin_info:
                    obj.setModel(
                        code=diagnosis_origin_info.code,
                        name=diagnosis_origin_info.name,
                    )
                session.add(obj)
            if first_page_info.poison_diag and first_page_info.poison_code:
                obj = DiagnosisInfo.newObject(self.app)
                obj.setModel(
                    caseId=caseId,
                    originName=first_page_info.poison_diag,
                    coder="system sync",
                    create_time=now_time,
                    update_time=now_time,
                    type=2,
                )
                diagnosis_origin_info = session.query(self.diagnosis_origin_dict).filter(
                    self.diagnosis_origin_dict.originName == first_page_info.poison_diag).first()
                if diagnosis_origin_info:
                    obj.setModel(
                        code=diagnosis_origin_info.code,
                        name=diagnosis_origin_info.name,
                    )
                session.add(obj)

    def get_diagnosis(self, request, base_dict={}, name_code_dict={}):
        """
        查询诊断字典数据
        :return:
        """
        data = []
        with self.app.mysqlConnection.session() as session:
            if request.isOrigin == 1:
                # 在质控信息内查该病历可用原始诊断信息
                queryset = session.query(self.fp_diagnosis_model).filter(
                    self.fp_diagnosis_model.caseId == request.caseId).all()
                # 查询展示诊断信息表内已使用过的 原始诊断信息
                query_used_origin_info = session.query(self.diagnosis_info_model.originName).filter(
                    self.diagnosis_info_model.caseId == request.caseId, self.diagnosis_info_model.is_deleted == 0).all()
                used_origin_list = [item.originName for item in query_used_origin_info]
                for item in queryset:
                    if item.icdname not in used_origin_list:
                        session.expunge(item)
                        data.append(item)
                return data
            if request.originName:
                # 存在原始诊断 则去诊断-原始诊断表 查已保存的诊断信息
                query_origin_data = session.query(self.origin_dict_model).filter(
                    self.origin_dict_model.originName == request.originName).first()
                if query_origin_data and query_origin_data.name and query_origin_data.name != request.originName:
                    session.expunge(query_origin_data)
                    data.append(query_origin_data)
                data.extend(self.get_most_similar(request.originName, base_dict, name_code_dict))
                return data
            if request.input:
                # 存在模糊查询字符, 则可能是编码、中文名、首字母
                query_str = "%" + request.input + "%"
                queryset = session.query(self.diagnosis_dict_model).filter(
                    or_(self.diagnosis_dict_model.code.like(query_str), self.diagnosis_dict_model.name.like(query_str),
                        self.diagnosis_dict_model.initials.like(query_str))).limit(20).all()
                self.append_data(data, queryset, session)
            else:
                queryset = session.query(self.diagnosis_dict_model).limit(20).all()
                self.append_data(data, queryset, session)
        return data

    def get_narcosis(self, query_str):
        """
        诊断列表
        :param query_str:
        :return:
        """
        data = []
        with self.app.mysqlConnection.session() as session:
            query = session.query(self.narcosis_model)
            if query_str:
                query_str = "%" + query_str + "%"
                query = query.filter(
                    or_(self.narcosis_model.code.like(query_str), self.narcosis_model.name.like(query_str),
                        self.narcosis_model.initials.like(query_str)))
            for item in query.limit(10).all():
                session.expunge(item)
                data.append(item)
        return data

    def get_most_similar(self, originName, base_dict, name_code_dict):
        """
        查询命中字最高的诊断
        :param originName: 要匹配的诊断名
        :param base_dict: 基础索引字典
        :param name_code_dict: 诊断名: 编码
        :return:
        """
        all_diagnosis_list = []
        for word in originName:
            all_diagnosis_list.extend(base_dict.get(word, []))
        diagnosis_count_dict = {}
        for item in all_diagnosis_list:
            if not diagnosis_count_dict.get(item, 0):
                diagnosis_count_dict[item] = 0
            diagnosis_count_dict[item] += 1
        sort_diagnosis_list = sorted(diagnosis_count_dict, key=lambda key: diagnosis_count_dict[key], reverse=True)
        obj1 = None
        if name_code_dict.get(originName, ""):
            obj1 = DiagnosisDict.newObject(self.app)
            obj1.setModel(code=name_code_dict[originName], name=originName)
        res = []
        if obj1:
            res.append(obj1)
        for name in sort_diagnosis_list[:21]:
            if name_code_dict.get(name, "") and name != originName:
                obj = DiagnosisDict.newObject(self.app)
                obj.setModel(code=name_code_dict[name], name=name)
                res.append(obj)
        return res

    @classmethod
    def append_data(cls, data, queryset, session):
        """
        增量诊断
        :return:
        """
        for item in queryset:
            session.expunge(item)
            data.append(item)

    def save_case_diagnosis(self, request):
        """
        保存病历诊断信息
        :return:
        """
        now_time = arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S')
        with self.app.mysqlConnection.session() as session:
            diagnosisInfo = request.diagnosisInfo
            is_create = 0 if diagnosisInfo.id else 1
            if diagnosisInfo.isPrimary:
                # 新诊断为主诊断时, 检查旧诊断是否存在主诊断, 存在则更新为非主诊断
                query_old_primary = session.query(self.diagnosis_info_model).filter(
                    self.diagnosis_info_model.caseId == request.caseId, self.diagnosis_info_model.isPrimary == 1).all()
                for item in query_old_primary:
                    old_obj = DiagnosisInfo(item)
                    old_obj.setModel(isPrimary=0, orderNum=0)
                session.commit()
            max_orderNum = 0
            if not is_create:
                queryset = session.query(self.diagnosis_info_model).filter(
                    self.diagnosis_info_model.id == diagnosisInfo.id).first()
                obj = DiagnosisInfo(queryset)
                max_orderNum = queryset.orderNum or 0
            else:
                if request.type == 0:
                    # 只有诊断信息需要排序字段
                    query_max_orderNum = session.query(func.max(self.diagnosis_info_model.orderNum).label("c")).filter(
                        self.diagnosis_info_model.caseId == request.caseId).first()
                    if query_max_orderNum:
                        max_orderNum = (query_max_orderNum.c or 0) + 1
                obj = DiagnosisInfo.newObject(self.app)
            params = {"code": "code", "diagnosis": "name", "originDiagnosis": "originName",
            "situation": "situation", "returnTo": "returnTo"}
            updateDict = {params[c]: getattr(diagnosisInfo, c) for c in params if getattr(diagnosisInfo, c) and getattr(diagnosisInfo, c) != "-"}
            isPrimary = 1 if diagnosisInfo.isPrimary and diagnosisInfo.isPrimary != "-" else 0
            obj.setModel(
                **updateDict,
                caseId=request.caseId,
                isPrimary=isPrimary,
                coder=request.operatorId,
                coder_id=request.operator,
                type=request.type,
                update_time=now_time,
                orderNum=max_orderNum
            )
            if is_create:
                obj.setModel(create_time=now_time)
                session.add(obj.model)
            session.commit()
            if request.sortIds:
                self.update_diagnosis_orderNum(session, request.sortIds)
            self.update_diagnosis_origin(session, diagnosisInfo.code, diagnosisInfo.diagnosis, obj.originName)
        return True

    def update_diagnosis_orderNum(self, session, sortIds):
        """
        诊断排序更新
        :param session:
        :param sortIds:
        :return:
        """
        for index in range(len(sortIds)):
            session.query(self.diagnosis_info_model).filter(
                self.diagnosis_info_model.id == sortIds[index]).update({'orderNum': index + 1}, synchronize_session=False)

    def update_diagnosis_origin(self, session, code, name, originName):
        """
        诊断-原始诊断映射关系保存
        :return:
        """
        queryset = session.query(self.diagnosis_origin_dict).filter(
            self.diagnosis_origin_dict.originName == originName).first()
        if queryset:
            obj = DiagnosisDict(queryset)
        else:
            obj = DiagnosisDict.newObject(self.app)
        obj.setModel(
            code=code,
            name=name,
            originName=originName,
            create_time=arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'),
        )
        session.add(obj.model)

    def delete_case_diagnosis(self, did):
        """
        删除诊断信息
        :return:
        """
        now_time = arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S')
        with self.app.mysqlConnection.session() as session:
            dig_info = session.query(self.diagnosis_info_model).filter(self.diagnosis_info_model.id == did).first()
            update_info = DiagnosisInfo(dig_info)
            if not dig_info:
                self.logger.info("delete_case_diagnosis, id: %s is not exist", did)
                return False
            if dig_info.isPrimary == 1:
                # 主诊断被删除需要在剩余诊断中指定主诊断
                update_info.setModel(isPrimary=0)
                new_primary_dig_info = session.query(self.diagnosis_info_model).filter(
                    self.diagnosis_info_model.caseId == dig_info.caseId, self.diagnosis_info_model.is_deleted == 0,
                    self.diagnosis_info_model.id != did).order_by(self.diagnosis_info_model.orderNum).first()
                if new_primary_dig_info:
                    # 可能存在最后一条主诊断被删除情况
                    new_primary_dig_info = DiagnosisInfo(new_primary_dig_info)
                    new_primary_dig_info.setModel(isPrimary=1)
            update_info.setModel(is_deleted=1, update_time=now_time)
            self.logger.info("delete_case_diagnosis, caseId: %s, id: %s, is deleted", dig_info.caseId, did)
        return True

    def expunge(self, session, dataList: List[Any]) -> List[Any]:
        dataList = dataList or []
        result = []
        for item in dataList:
            if item:
                item.expunge(session)
            result.append(item)
        return result

    def initOperationList(self, caseId):
        with self.app.mysqlConnection.session() as session:
            self.operation_repository.initOperationList(session, caseId)

    def getOperationList(self, caseId):
        with self.app.mysqlConnection.session() as session:
            return self.expunge(session, self.operation_repository.getOperationList(session, caseId))

    def deleteOpertion(self, id):
        with self.app.mysqlConnection.session() as session:
            model = self.app.mysqlConnection['operation_info']
            obj = session.query(model).filter(model.id == id).first()
            obj.is_deleted = 1
            return obj.id

    def updateOperation(self, caseId, operation, sortIds=[]):
        params = {'id': 'id', 'type': 'type', 'code': 'code', 'operation': 'name',
                  'originOperation': 'originName', 'operationTime': 'operation_time', 'operator': 'operator',
                  'helperOne': 'helperOne', 'helperTwo': 'helperTwo', 'narcosis': 'narcosis',
                  'narcosisDoctor': 'narcosisDoctor',
                  'cut': 'cut', 'healLevel': 'healLevel', 'level': 'level'}
        updateDict = dict()
        for c in params:
            if column := getattr(operation, c):
                if column == '-':
                    updateDict[params[c]] = ''
                else:
                    updateDict[params[c]] = column
        with self.app.mysqlConnection.session() as session:
            operation_info = self.operation_repository.updateOperation(session, caseId, operation.id, updateDict)
            self.operation_repository.updateOperationOriginDict(session, operation_info)
            if sortIds:
                self.operation_repository.updateOperationOrderNum(session, sortIds)

    def getOperation(self, request, base_dict, name_code_dict, name_type_dict):
        caseId = request.caseId
        input = request.input or ""
        originName = request.originName or ""
        isOrigin = request.isOrigin or 0
        reqDict = {'input': input, 'originName': originName, "base_dict": base_dict, "name_code_dict": name_code_dict,
                   "name_type_dict": name_type_dict}
        req = OperationRequest(**reqDict)
        with self.app.mysqlConnection.session() as session:
            if isOrigin == 1:
                # 在质控信息内查该病历可用原始诊断信息
                return self.expunge(session, self.operation_repository.getOriginOperationList(session, caseId))
            return self.expunge(session, self.operation_repository.getOperationFromDict(session, req))

    def submitCheck(self, caseId, operatorId, operator):
        if not self.app.qcetlRpcUrl:
            return False
        try:
            # todo 构建请求体
            data = {}
            headers = {
                'Content-Type': 'application/json'
            }
            logging.info(json.dumps(data, ensure_ascii=False))
            resp = requests.post(self.app.qcetlRpcUrl, headers=headers, json=data)
            if resp.status_code != 200:
                raise ValueError('call %s failed, code=%s, resp: %s' % (self.app.qcetlRpcUrl, resp.status_code, resp.text))
            response = resp.json()
            # todo 解析Ai得出的问题结果
        except Exception as e:
            logging.exception(e)
            return False

    def submit(self, caseId, operatorId, operator):
        model = self.app.mysqlConnection['fp_info']
        case_model = self.app.mysqlConnection['case']
        try:
            with self.app.mysqlConnection.session() as session:
                item = session.query(model).filter(model.caseId == caseId).first()
                case = session.query(case_model).filter(case_model.caseId == caseId).first()
                if item:
                    item.code_time = arrow.utcnow().to("+08:00").naive.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    item = model(
                        caseId=caseId,
                        coder=operator,
                        coder_id=operatorId,
                        create_time=arrow.utcnow().to("+08:00").naive.strftime('%Y-%m-%d %H:%M:%S'),
                        code_time=arrow.utcnow().to("+08:00").naive.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    session.add(item)
                case.codeStatus = 1
            return True
        except BaseException as e:
            self.logger.error('submit error :%s' % e)
            return False

    def getCaseDetail(self, caseId):
        with self.app.mysqlConnection.session() as session:
            item = self.case_repository.getFPCaseDetail(session, caseId)
            if item:
                item.expunge(session)
                return item

    def query_is_first(self, caseId):
        """
        判断是否为未同步过的首次查询
        :param caseId:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            return self.operation_repository.query_count_by_caseId(session, caseId)
