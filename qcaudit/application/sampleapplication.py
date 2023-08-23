#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 11:48:55

'''
import copy
import json
import random
import re
from queue import PriorityQueue
from datetime import timedelta

import pandas as pd
import sys
from collections import defaultdict
import logging
from typing import Dict, List

import requests.structures
from google.protobuf.json_format import MessageToDict
from qcdbmodel.qcdbmodel.models.qcaudit import SampleFilter, SampleTask
from sqlalchemy import and_

from qcaudit.application.applicationbase import ApplicationBase
from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL, \
    SAMPLE_BY_DICT, SAMPLE_BY_TAG, SAMPLE_BY_TAG_ALL, CASE_LIST_PROBLEM_COUNT
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.case.req import GetCaseListRequest
from qcaudit.domain.dict import CaseTagRepository, DepartmentRepository
from qcaudit.domain.dict.department import Department
from qcaudit.domain.dict.dim_dept_statis import DimDeptStatisRepository
from qcaudit.domain.dict.ward import Ward
from qcaudit.domain.dict.ward_doctor import WardDoctor
from qcaudit.domain.req import ListRequestBase, SortField
from qcaudit.domain.case.case import Case
from qcaudit.domain.case.caserepository import CaseRepository
from qcaudit.domain.sample.expertuser import ExpertUser
from qcaudit.domain.sample.expertuserrepository import ExpertUserRepository
from qcaudit.domain.sample.req import GetSampleRecordRequest, GetSampleDetailRequest
from qcaudit.domain.sample.sampleoperation import SampleOperation
from qcaudit.domain.sample.samplerecord import SampleRecord
from qcaudit.domain.sample.samplerecorditem import SampleRecordItem
from qcaudit.domain.sample.samplerecordrepository import SampleRecordRepository
from qcaudit.domain.sample.samplerecordsvc import SampleRecordService

import arrow

from qcaudit.domain.sample.sampletask import SampleFilterModel, SampleTaskModel
from qcaudit.domain.user.user import User
from qcaudit.utils.towebconfig import SAMPLE_HISTORY_EXPORT_DATA


class SampleStatData(object):

    def __init__(self):
        # 病历等级统计
        self.rateStat = {'甲': 0, '乙': 0, '丙': 0}
        # 标签统计
        self.tagStat: Dict[str, int] = defaultdict(int)
        self.totalCount = 0

    def add(self, case: Case):
        """计算抽样结果中的统计信息

        Args:
            case ([type]): [description]
        """
        self.totalCount += 1
        for tag in case.Tags:
            self.tagStat[tag] += 1
        # if case.caseRating:
        #     self.rateStat[case.caseRating] += 1
        return self


class SampleApplication(ApplicationBase):
    # 根据科室抽取
    SAMPLE_BY_DEPARTMENT = 'dept'
    # 根据病区抽取
    SAMPLE_BY_WARD = 'ward'
    # 根据责任医生抽取
    SAMPLE_BY_ATTENDING = 'attending'
    # 根据院区抽取
    SAMPLE_BY_BRANCH = 'branch'
    # 按总量抽取
    SAMPLE_BY_NUM = 'num'
    # 根据诊疗组抽取
    SAMPLE_BY_GROUP = "group"
    # 根据重点病历标签抽取
    SAMPLE_BY_TAG = "tag"

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.sampleRepo = SampleRecordRepository(app, auditType)
        self.sampleSvc = SampleRecordService(app, auditType)
        self.expertRepo = ExpertUserRepository(app, auditType)
        self.caseRepo = CaseRepository(app, auditType)
        self.caseTag = CaseTagRepository(app, auditType)
        self.dimDeptRepo = DimDeptStatisRepository(app, auditType)
        self.DeptRepo = DepartmentRepository(app, auditType)

    def getSampleCase(self, req: GetCaseListRequest, sampleBy=None, sampleNum=0, limit=1000,
                      existedCaseIds: List[str] = []):
        """根据筛选和排序条件抽取病历
        Args:
            req (ListRequestBase): 列表筛选和排序条件
            sampleBy ([type], optional): 根据那个字段抽取. 
                None: 按总量抽取
                TODO: 其他类型待定义: 科室/院区/病区/责任医生
            sampleNum (int, optional): sampleBy字段对应的每种类型抽取多少份病历. Defaults to 0.
            limit (int, optional): 总量最多抽取多少份
            existedCaseIds (list): 已经存在的caseId. 将会和此次抽取的病历合并
        Return:
            返回抽取到的病历的列表
            返回统计信息.  TODO: 也可以考虑前端统计
        """
        existedCaseIdSet = set(existedCaseIds)
        if sampleBy == self.SAMPLE_BY_NUM and sampleNum == 0:
            sampleNum = limit
        total = len(existedCaseIdSet)
        req.size = sys.maxsize
        statData = SampleStatData()
        with self.app.mysqlConnection.session() as session:
            sampledCase = defaultdict(list)
            tags = {t.code: t for t in self.expunge(session, self.caseTag.getList(session))}
            getCaseList = self.caseRepo.getList(session, req)
            logging.info("getCaseList len is : %s" % len(getCaseList))
            for c in getCaseList:
                # print(c)
                sampleField = None
                c.convertTagToModel(tags)
                if sampleBy == self.SAMPLE_BY_BRANCH:
                    sampleField = c.branch
                elif sampleBy == self.SAMPLE_BY_ATTENDING:
                    sampleField = c.attendCode
                elif sampleBy == self.SAMPLE_BY_DEPARTMENT:
                    sampleField = c.departmentId if not c.outDeptName else c.outDeptId
                elif sampleBy == self.SAMPLE_BY_WARD:
                    sampleField = c.wardId
                elif sampleBy == self.SAMPLE_BY_GROUP:
                    sampleField = c.medicalGroupName or c.medicalGroupCode
                else:
                    sampleField = ''

                # 按照重点病历标签抽取，要求每个重点病历标签尽可能抽取到要求的数量
                if sampleBy == self.SAMPLE_BY_TAG:
                    for reqtag in req.sampleByTags:
                        if reqtag in c.tags and len(sampledCase[reqtag]) < sampleNum:
                            sampleField = reqtag
                            break
                    else:
                        continue

                if sampleField is None:
                    continue
                # print("sampleField is : %s" % sampleField)
                if len(sampledCase[sampleField]) >= sampleNum:
                    continue
                # 已经被别的项目抽取到, 忽略
                if c.sampleRecordItem is not None:
                    continue
                if c.caseId not in existedCaseIdSet:
                    total += 1
                else:
                    existedCaseIdSet.remove(c.caseId)
                c.expunge(session)
                # print("sampleField value is : %s" % len(sampledCase[sampleField]))
                sampledCase[sampleField].append(c)
                statData.add(c)
                # print("total is : %s, limit is  : %s" % (total, limit) )
                if total >= limit:
                    break
            result = []
            for _, value in sampledCase.items():
                result.extend(value)
            logging.info("result len is : %s" % len(result))
            # 把已经存在的caseId加入
            for caseId in existedCaseIdSet:
                case = self.caseRepo.getByCaseId(session, caseId)
                if case is not None:
                    case.expunge(session)
                    case.convertTagToModel(tags)
                    result.append(case)
                    statData.add(case)
                else:
                    raise ValueError(f'unknow caseId {caseId}')
            # if result:
            #     self.extraProcessCaseList(result)
        return result, statData

    def submitSampleResult(self, caseIds: List[str], auditType: str, caseType: str, operatorId: str,
                           operatorName: str, sampleId: int = 0) -> SampleRecord:
        """提交抽取结果

        Args:
            caseIds (List[str]): 本次抽取的全部病历id
            auditType (str): 抽取类型
            caseType (str): 病历类型
            operatorId (str): 抽取操作人员id
            operatorName (str): 抽取操作人员姓名
            sampleId: 抽取记录id

        Return:
            抽取历史记录
        """
        now = arrow.utcnow().to('+08:00').naive
        with self.app.mysqlConnection.session() as session:
            # 先发送生成快照的消息
            if caseType == 'running':
                if not self.sendSnapshotMessage(caseIds, self.auditType):
                    raise ValueError('发送创建快照的消息失败')
            # 创建sample_record
            sample = self.sampleRepo.getById(session, sampleId)
            if sample and sample.submit_flag:
                return None
            if not sample:
                sample = SampleRecord.newObject(self.app, operatorId=operatorId, operatorName=operatorName, isAssigned=1,
                                                auditType=auditType, caseType=caseType, createdAt=now, sampledCount=0)
                self.sampleRepo.add(session, sample)
                session.commit()
            recordId = sample.id

            # 插入sample_record_item
            count = 0
            for caseId in caseIds:
                originCaseId = None
                if caseType == 'running':
                    originCaseId = caseId
                    caseId = "{}_{}".format(caseId, self.auditType)
                if not self.sampleRepo.getItemByCaseId(session, auditType, caseId):
                    item = SampleRecordItem.newObject(self.app, caseId=caseId, auditType=self.auditType,
                                                      recordId=recordId, originCaseId=originCaseId)
                    self.sampleRepo.addItem(session, item)
                    count += 1
            sample.setSampledCount(count)
            sample.submit()
            session.commit()

            sample = self.sampleRepo.getById(session, sampleId)
            sample.expunge(session)
            return sample

    def sendSnapshotMessage(self, caseIds: List[str], auditType):
        """发送生成快照的消息

        Args:
            caseIds (List[str]): [description]
            auditType ([type]): [description]
        """
        try:
            for caseId in caseIds:
                self.app.mq.publish(
                    {
                        'type': 'qc.snapshot',
                        'body': {
                            'crawlFirst': True,
                            'caseId': caseId,
                            'patientId': None,
                            'auditType': auditType
                        }
                    }
                )
        except Exception as e:
            logging.exception(e)
            return False
        else:
            return True

    def getSampleRecordHistory(self, req: GetSampleRecordRequest):
        """获取抽取历史
        """
        with self.app.mysqlConnection.session() as session:
            result = []
            count = self.sampleRepo.getCount(session, req)
            for item in self.sampleRepo.getList(session, req):
                item.expunge(session)
                result.append(item)
            return result, count

    def getSampleDetail(self, req: GetSampleDetailRequest):
        """获取抽取病历详情
        """
        with self.app.mysqlConnection.session() as session:
            result = []
            count = self.sampleRepo.getItemCount(session, req)
            itemList = self.sampleRepo.getItemListByQuery(session, req)
            for SampleRecordItem in itemList:
                SampleRecordItem.expunge(session)
                result.append(SampleRecordItem)
            return result, count

    def assignExpert(self, sampleRecordId, caseType, assignType, auditType="", noSameDept=False, users=[]):
        """给抽取结果分配专家

        Args:
            sampleRecordId (int): [description]
            caseType :
            assignType ([type]): 平均分配或自动分配
            auditType ([type]): 平均分配时需读取该属性增加判断
            noSameDept ([bool]): 分配时病历和专家不能是同一个科室
            users ([list]): 指定的用户数组, list[ExpertUser]
        """
        with self.app.mysqlConnection.session() as session:
            if assignType == SampleRecord.ASSIGN_TYPE_AVG:
                # 获取统计科室 科室名称归一
                dept_map = {item.deptname: item.statis_name for item in self.dimDeptRepo.getList(session)}
                if not users:
                    # 获取所有的专家
                    users = list(self.expertRepo.getList(session, caseType))
                userCount = len(users)
                if userCount == 0:
                    raise ValueError('没有可分配的专家')

                # 专家优先级队列，已分配病历数少的专家优先被分配
                experts = PriorityQueue()
                user_map = {}
                for u in users:
                    if not u.department:
                        u.setDepartment(User.getUserDepartment(self.app.mongo, u.userId))
                    experts.put((0, u.userId))
                    user_map[u.userId] = u

                items = list(self.sampleRepo.getItemList(session, sampleRecordId, auditType))
                items = [x for x in items if x.isMannalAssigned not in (1, 2)]  # 1-指定分配, 2-病区分配
                random.shuffle(items)  # 病历顺序先打乱
                for i in range(0, len(items)):
                    # 决定哪个专家审核
                    item = items[i]
                    triedUser = []
                    while not experts.empty():
                        count, userid = experts.get()
                        expert = user_map.get(userid)
                        logging.info("assignExpert, expert.userName: %s", expert.userName)
                        # 判断是否允许病历和专家是同一个科室
                        logging.info("assignExpert, noSameDept: %s, expert.department: %s", noSameDept, expert.department)
                        if noSameDept and expert.department:
                            caseDepartment = item.caseModel.outDeptName or item.caseModel.department
                            if expert.department == caseDepartment or expert.department == dept_map.get(caseDepartment):
                                triedUser.append((count, userid))
                                continue
                        logging.info("assign")
                        item.assignExpert(userid, expert.userName)
                        experts.put((count+1, userid))
                        break
                    for count, userid in triedUser:
                        experts.put((count, userid))

                    if i % 100 == 0:
                        # 中途提交, 防止数量太多
                        session.commit()
            else:
                self.sampleSvc.assignExpertAuto(sampleRecordId)

            sampleModel = self.sampleRepo.getRecordById(session, sampleRecordId)
            # 修改抽取记录分配状态
            if sampleModel:
                sampleModel.model.isAssigned = 2
            session.commit()
            logging.info("assignExpert, end.")

    def assginExpertToItem(self, sampleRecordItemId, sampleRecordItemIds, expertId, expertName, many=0, isMannalAssigned=1):
        """为某一份或多份病历指定审核专家
        """
        with self.app.mysqlConnection.session() as session:
            if many:
                items = self.sampleRepo.getItemById(session, sampleRecordItemIds, many)
                # 人工批量分配
                for item in items:
                    recordId = item.assignExpert(expertId, expertName, isMannalAssigned=isMannalAssigned)
                return recordId
            else:
                # 人工单独分配
                item = self.sampleRepo.getItemById(session, sampleRecordItemId, many)
                recordId = item.assignExpert(expertId, expertName, isMannalAssigned=isMannalAssigned)
                return recordId

    def ward_assign(self, sample_item_ids, expert_id, expert_name, isMannalAssigned):
        """
        病区/科室 批量分配
        :return:
        """
        ids = ",".join([str(item) for item in sample_item_ids])
        with self.app.mysqlConnection.session() as session:
            update_sql = '''update sample_record_item set expertId = "{expertId}", expertName = "{expertName}", isMannalAssigned = "{isMannalAssigned}" where id in ({ids})'''.format(
                expertId=expert_id, expertName=expert_name, isMannalAssigned=isMannalAssigned, ids=ids)
            session.execute(update_sql)
            # print("ward_assign, update_sql:", update_sql)
            isAssigned = 2 if expert_name and expert_id else 1
            update_sample_record_isAssigned_sql = '''update sample_record set isAssigned = {isAssigned} where sample_record.id in (select recordId from sample_record_item where sample_record_item.id in ({ids}))'''.format(
                isAssigned=isAssigned, ids=ids)
            session.execute(update_sample_record_isAssigned_sql)
            # print("ward_assign, update_sample_record_isAssigned_sql:", update_sample_record_isAssigned_sql)

    def addExpert(self, expertId, expertName, caseType):
        """添加一个质控人员到当前审核环节

        Args:
            expertId ([type]): [description]
        """
        user = ExpertUser.newObject(self.app)
        user.setModel(
            userId=expertId, userName=expertName,
            auditType=self.auditType,
            caseType=caseType
        )
        with self.app.mysqlConnection.session() as session:
            self.expertRepo.add(session, user)

    def removeExpert(self, expertId, caseType):
        """将一个质控人员从当前审核环节排除

        Args:
            expertId ([type]): [description]
        """
        with self.app.mysqlConnection.session() as session:
            self.expertRepo.delete(session, expertId, caseType)

    def getExpertList(self, caseType) -> List[ExpertUser]:
        """获取当前环节所有可用的专家
        """
        with self.app.mysqlConnection.session() as session:
            result = []

            for item in self.expertRepo.getList(session, caseType):
                item.expunge(session)
                result.append(item)

            return result

    def removeSampleRecord(self, recordId: int):
        """删除抽取历史

        Args:
            recordId (int): [description]
        """
        with self.app.mysqlConnection.session() as session:
            self.sampleRepo.delete(session, recordId)

    def removeTask(self, taskId):
        """废除任务

        Args:
            expertId ([type]): [description]
        """
        with self.app.mysqlConnection.session() as session:
            self.sampleRepo.deleteItem(session, taskId)

    def extraProcessCaseList(self, caseList):
        # 额外添加分数等级，数据库中不存储等级
        for item in caseList:
            print(item.caseRating)
            print(item.caseScore)
            if float(item.caseScore) >= 90:
                item.caseRating = "甲"
            elif float(item.caseScore) >= 80:
                item.caseRating = "乙"
            else:
                item.caseRating = "丙"

    def writeSampleExcel(self, sampleList, request, caseTagDict, patient_id_name="病历号"):
        """
        抽取历史列表写入excel
        :return:
        """
        title = ["重点病历", "问题数", patient_id_name, "姓名", "科室", "病区", "入院日期", "出院日期", "住院天数", "责任医生", "分配医生",
                 "质控医生", "质控日期"]
        problem_dict = {}
        if request.isExportDetail == 1:
            title += ["问题描述", "病案扣分", "首页扣分"]
            case_id_list = [item.caseModel.caseId for item in sampleList]
            self.get_problem_dict(case_id_list, problem_dict, request)

        row_data = []
        for x in sampleList:
            tag_list = []
            if x.caseModel.tags:
                for tag in x.caseModel.tags:
                    t = caseTagDict.get(tag, None) or None
                    name = t.name if t else ""
                    if name:
                        tag_list.append(name)
            tags = ','.join(tag_list) or ""
            problemCount = AuditRecord(x.auditRecord).getProblemCount(request.auditType) if x.auditRecord else 0
            patientId = x.caseModel.patientId
            name = x.caseModel.name or ""
            dischargeDept = x.caseModel.outDeptName or ""
            department = dischargeDept or x.caseModel.department or ""
            ward = x.caseModel.wardName or ""
            admitTime = x.caseModel.admitTime.strftime('%Y-%m-%d') if x.caseModel.admitTime else ""
            dischargeTime = x.caseModel.dischargeTime.strftime('%Y-%m-%d') if x.caseModel.dischargeTime else ""
            inpDays = x.caseModel.inpDays or 0
            attendDoctor = x.caseModel.attendDoctor or ""
            distributeDoctor = x.model.expertName or ""
            reviewer = getattr(x.auditRecord,
                               AuditRecord.getOperatorFields(auditType=request.auditType).reviewerNameField) or ""
            ar_review_time = getattr(x.auditRecord,
                                     AuditRecord.getOperatorFields(auditType=request.auditType).reviewTimeField)
            reviewTime = ar_review_time.strftime('%Y-%m-%d %H:%M:%S') if ar_review_time else ""

            tmp = [tags, problemCount, patientId, name, department, ward, admitTime, dischargeTime, inpDays,
                   attendDoctor, distributeDoctor, reviewer, reviewTime]
            if request.isExportDetail == 1:
                problem_list = problem_dict.get(x.caseModel.caseId, [])
                if not problem_list:
                    tmp += ["", "", ""]
                    row_data.append(tmp)
                for item in problem_list:
                    tmp1 = copy.deepcopy(tmp)
                    tmp1 += item
                    row_data.append(tmp1)
            else:
                row_data.append(tmp)

        df = pd.DataFrame(row_data, columns=title)
        return df

    def format_sample_history_export_data(self, sampleList, request, caseTagDict, patient_id_name="病历号"):
        """
        格式化抽取历史导出数据
        :return:
        """
        problem_dict = {}
        if request.isExportDetail == 1:
            case_id_list = [item.caseModel.caseId for item in sampleList]
            self.get_problem_dict(case_id_list, problem_dict, request)
        row_data = []
        if not sampleList:
            tmp = dict(SAMPLE_HISTORY_EXPORT_DATA, **{patient_id_name: ""})
            row_data.append(tmp)
        for x in sampleList:
            tag_list = []
            if x.caseModel.tags:
                for tag in x.caseModel.tags:
                    t = caseTagDict.get(tag, None) or None
                    name = t.name if t else ""
                    if name:
                        tag_list.append(name)
            tags = ','.join(tag_list) or ""
            problemCount = AuditRecord(x.auditRecord).getProblemCount(request.auditType) if x.auditRecord else 0
            patientId = x.caseModel.patientId
            name = x.caseModel.name or ""
            dischargeDept = x.caseModel.outDeptName or ""
            department = dischargeDept or x.caseModel.department or ""
            ward = x.caseModel.wardName or ""
            group = x.caseModel.medicalGroupName or ""
            admitTime = x.caseModel.admitTime.strftime('%Y-%m-%d') if x.caseModel.admitTime else ""
            dischargeTime = x.caseModel.dischargeTime.strftime('%Y-%m-%d') if x.caseModel.dischargeTime else ""
            inpDays = x.caseModel.inpDays or 0
            attendDoctor = x.caseModel.attendDoctor or ""
            distributeDoctor = x.model.expertName if x.model else ""
            reviewer = getattr(x.auditRecord,
                               AuditRecord.getOperatorFields(auditType=request.auditType).reviewerNameField) if x.auditRecord else ""
            ar_review_time = getattr(x.auditRecord,
                                     AuditRecord.getOperatorFields(auditType=request.auditType).reviewTimeField) if x.auditRecord else ""
            reviewTime = ar_review_time.strftime('%Y-%m-%d %H:%M:%S') if ar_review_time else ""

            tmp = {"重点病历": tags, "问题数": problemCount, patient_id_name: patientId, "姓名": name, "科室": department,
                   "病区": ward, "诊疗组": group, "入院日期": admitTime, "出院日期": dischargeTime, "住院天数": inpDays, "责任医生": attendDoctor,
                   "分配医生": distributeDoctor, "质控医生": reviewer, "质控日期": reviewTime}
            if request.isExportDetail == 1:
                problem_list = problem_dict.get(x.caseModel.caseId, [])
                if not problem_list:
                    tmp["问题描述"] = ""
                    tmp["病案扣分"] = ""
                    tmp["首页扣分"] = ""
                    row_data.append(tmp)
                for item in problem_list:
                    tmp1 = copy.deepcopy(tmp)
                    tmp1["问题描述"] = item[0]
                    tmp1["病案扣分"] = item[1]
                    tmp1["首页扣分"] = item[2]
                    row_data.append(tmp1)
            else:
                row_data.append(tmp)
        return row_data

    def get_problem_dict(self, case_id_list, problem_dict, request):
        """
        根据caseId查询问题
        :return:
        """
        if not case_id_list:
            return
        case_ids = ','.join(['"%s"' % item for item in case_id_list])
        with self.app.mysqlConnection.session() as session:
            query_problem_score_sql = '''select cp.caseId, cp.reason, cp.score, cp.problem_count, df.score, cp.comment, 
            ei.documentName, ei.first_save_time, cp.docId from caseProblem cp 
            inner join `case` c on c.audit_id = cp.audit_id left join dim_firstpagescore df on cp.qcItemId = df.qcitemid 
            left join emrInfo ei on cp.caseId = ei.caseId and cp.docId = ei.docId
            where cp.is_deleted = 0 and cp.score != 0 and cp.caseId in (%s) and cp.auditType = "%s"''' % (case_ids, request.auditType)
            query = session.execute(query_problem_score_sql)
            queryset = query.fetchall()
            for item in queryset:
                if not problem_dict.get(item[0], None):
                    problem_dict[item[0]] = []
                score = item[2] or 0
                problem_count = item[3] or 1
                fp_score = item[4] or 0
                reason = item[1] or ""
                comment = item[5] or ""
                doc_name = item[6] or ""
                doc_save_time = item[7] or None
                doc_info = ""
                if str(item[8]) != "0":
                    if doc_name:
                        doc_info += "【" + doc_name
                    if doc_info:
                        if doc_save_time:
                            doc_info += doc_save_time.strftime("%Y-%m-%d") + "】"
                        else:
                            doc_info += "】"
                else:
                    doc_info = "【缺失文书】"
                reason_comment = doc_info + reason + "。" + comment
                problem_dict[item[0]].append([reason_comment, score * problem_count or "",
                                              fp_score * problem_count or ""])

    def checkSampleAssigned(self, sampleRecordId, auditType):
        with self.app.mysqlConnection.session() as session:
            sample_obj = self.sampleSvc.repo.getRecordById(session, sampleRecordId)
            items = self.sampleSvc.repo.getItemList(session, sampleRecordId, auditType)
            for item in items:
                if not item.expertId:
                    return
            sample_obj.model.isAssigned = 2

    def query_wardDoctor_from_ward(self, assign_flag=2):
        """
        从ward基础表查询ward信息
        :return:
        """
        if str(assign_flag) == "1":
            wardModel = Department.getModel(self.app)
        else:
            wardModel = Ward.getModel(self.app)
        with self.app.mysqlConnection.session() as session:
            query = session.query(wardModel).order_by(wardModel.sort_no)
        return query.all()

    def query_wardDoctor_from_ward_doctor(self, doctor_id, assign_flag=0):
        """
        从ward_doctor表查询已保存过的病区分配医生
        :return:
        """
        if assign_flag == 1:
            wardModel = Department.getModel(self.app)
        else:
            wardModel = Ward.getModel(self.app)
        wardDoctorModel = WardDoctor.getModel(self.app)
        with self.app.mysqlConnection.session() as session:
            query = session.query(wardDoctorModel).join(wardModel, wardDoctorModel.ward == wardModel.name).filter(
                wardDoctorModel.user_id == doctor_id).order_by(wardModel.sort_no)
        return query.all()

    def update_wardDoctor(self, doctor_id, ward_doctor, assign_flag=2):
        """
        更新ward_doctor数据
        :return:
        """
        wardDoctorModel = WardDoctor.getModel(self.app)
        if assign_flag == 1:
            wardModel = Department.getModel(self.app)
        else:
            wardModel = Ward.getModel(self.app)
        with self.app.mysqlConnection.session() as session:
            query_doctor_id_is_exist = session.query(wardDoctorModel).filter(wardDoctorModel.user_id == doctor_id).first()
            if query_doctor_id_is_exist:
                for item in ward_doctor:
                    ward_doctor_obj = session.query(wardDoctorModel).filter(
                        wardDoctorModel.user_id == doctor_id, wardDoctorModel.ward == item["ward"]).first()
                    if ward_doctor_obj:
                        ward_doctor_obj.doctorName = item["doctorName"]
                        ward_doctor_obj.doctorId = item["doctorId"]
            else:
                ward_data = session.query(wardModel).all()
                insert_sql = '''insert into ward_doctor (ward, user_id) values '''
                for item in ward_data:
                    insert_sql += '("%s", "%s"),' % (item["name"], doctor_id)
                insert_sql = insert_sql[:-1]
                session.execute(insert_sql)
                session.commit()
                for item in ward_doctor:
                    ward_doctor_obj = session.query(wardDoctorModel).filter(
                        and_(wardDoctorModel.user_id == doctor_id, wardDoctorModel.ward == item["ward"])).first()
                    if ward_doctor_obj:
                        ward_doctor_obj.doctorName = item["doctorName"]
                        ward_doctor_obj.doctorId = item["doctorId"]

    def get_ward_doctor_dict(self, doctor_id, assign_flag):
        """
        获取病区分配医生字典
        :return:
        """
        data = self.query_wardDoctor_from_ward_doctor(doctor_id, assign_flag)
        return {item.ward: {"doctorId": item.doctorId or "", "doctorName": item.doctorName or ""} for item in data}

    @classmethod
    def verify_ward_doctor(cls, data, ward_doctor_dict):
        """
        验证待分配数据是否均有分配医生信息
        :return:
        """
        for ward, sample_item_ids in data.items():
            expert_id = ward_doctor_dict.get(ward, {}).get("doctorId", "")
            expert_name = ward_doctor_dict.get(ward, {}).get("doctorName", "")
            if not expert_id or not expert_name:
                return False
        return True

    def record_sample_operation(self, sampleId, caseType, caseIds, operatorId=None, operatorName=None, sampleBy=None, sampleCount=0, existedCaseIds=[], sampleFilter=None):
        """记录抽取操作日志
        """
        now = arrow.utcnow().to('+08:00').naive
        with self.app.mysqlConnection.session() as session:
            sample = self.sampleRepo.getById(session, sampleId)
            if sample and sample.submit_flag:
                return None
            if not sample:
                sample = SampleRecord.newObject(self.app, operatorId=operatorId, operatorName=operatorName, isAssigned=1,
                                                auditType=self.auditType, caseType=caseType, createdAt=now, sampledCount=0)
                self.sampleRepo.add(session, sample)
                session.commit()

            sample.setSampledCount(len(caseIds))
            sample_dict = {"dept": "科室", "ward": "病区", "attending": "责任医生", "branch": "院区",
                           "num": "总量", "group": "诊疗组", "tag": "重点病历", "tags": "重点病历"}
            sample.addSampleBy(sample_dict.get(sampleBy))

            action = "抽取"
            content = f"按{sample_dict.get(sampleBy)}抽取，每个{sample_dict.get(sampleBy)}至少抽取{sampleCount}份"
            if sampleCount >= 1000000:
                content = f"按{sample_dict.get(sampleBy)}抽取，抽取全部"
            count = len(caseIds) - (len(existedCaseIds) or 0)
            # 新增加操作日志
            operation = SampleOperation.newObject(self.app, sample_id=sample.id, name=action, content=content,
                                                  sample_by=sampleBy, conditions=','.join(sampleFilter),
                                                  sampled_count=count, sampled_case=','.join(caseIds), submit_flag=0,
                                                  operator=operatorName, operate_time=now)
            self.sampleRepo.addOperation(session, operation)
            session.commit()
            sample.setLastOperationId(operation.id)
            return sample.id

    def update_sample_case(self, sampleId, caseType, caseIds, operatorId=None, operatorName=None):
        """记录抽取历史记录，添加病历和删除病历 两种操作
        如果与之前的操作是同一种类型，不新增操作日志
        """
        now = arrow.utcnow().to('+08:00').naive
        with self.app.mysqlConnection.session() as session:
            sample = self.sampleRepo.getById(session, sampleId)
            if sample and sample.submit_flag:
                return None
            if not sample:
                sample = SampleRecord.newObject(self.app, operatorId=operatorId, operatorName=operatorName, isAssigned=1,
                                                auditType=self.auditType, caseType=caseType, createdAt=now, sampledCount=0)
                self.sampleRepo.add(session, sample)
                session.commit()

            # 根据抽取病历号数量判断是添加还是删除
            action = "删除" if len(caseIds) < sample.sampledCount else "添加"
            count = abs(len(caseIds) - sample.sampledCount)
            content = f'{action}病历{count}份'

            # 在sampleRecord中缓存已抽取病历数和抽取规则
            sample.setSampledCount(len(caseIds))
            sample.addSampleBy("自定义")

            # 相同的操作日志合并
            last_operation = self.sampleRepo.getSampleOperationById(session, sample.lastOperation)
            if last_operation and last_operation.name == action:
                last_operation.setSampledCase(caseIds)
                count += int(re.search(r'\d+', f'{last_operation.content}默认0份').group())
                last_operation.model.content = f'{action}病历{count}份'
                return sample.id
            # 新增加操作日志
            operation = SampleOperation.newObject(self.app, sample_id=sample.id, name=action, content=content,
                                                  sample_by="custom", conditions="", sampled_count=0,
                                                  sampled_case=','.join(caseIds), submit_flag=0,
                                                  operator=operatorName, operate_time=now)
            self.sampleRepo.addOperation(session, operation)
            session.commit()
            sample.setLastOperationId(operation.id)
            return sample.id

    def getSampleOperations(self, sampleId):
        with self.app.mysqlConnection.session() as session:
            sample = self.sampleRepo.getRecordById(session, sampleId)
            sample.expunge(session)
            result = [item for item in self.expunge(session, self.sampleRepo.getSampleOperations(session, sampleId))]
        return sample, result

    def getSampleFilterList(self, request):
        """
        获取抽取条件列表
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query = session.query(SampleFilter).filter(SampleFilter.is_delete == 0)
            if request.name:
                query = query.filter(SampleFilter.name.like("%{}%".format(request.name)))
            if request.auditType:
                query = query.filter(SampleFilter.auditType == request.auditType)
            if request.startTime:
                query = query.filter(SampleFilter.create_time >= request.startTime)
            if request.endTime:
                query = query.filter(SampleFilter.create_time <= request.endTime)
            if request.caseType:
                query = query.filter(SampleFilter.caseType == request.caseType)
            res = []
            total = query.count()
            start = request.start or 0
            size = request.size or 15
            query = query.slice(start, start + size)
            for item in query.all():
                session.expunge(item)
                res.append(item)
            return res, total

    def saveSampleFilter(self, request, all_tags=[]):
        """
        抽取条件保存
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            if request.id:
                query = session.query(SampleFilter).filter(SampleFilter.id == request.id)
                if request.deleteFlag == 1:
                    query.update({"is_delete": 1}, synchronize_session=False)
                    return True, ""
                if request.name:
                    query.update({"name": request.name}, synchronize_session=False)
                if request.filter:
                    # filter_data = MessageToDict(request.filter)
                    filter_data = request.filter
                    sample_by = SAMPLE_BY_DICT.get(request.filter.get("sampleBy")) or ""
                    sample_num = request.filter.get("sampleCount") or 0
                    describe = f"按{sample_by}抽取"
                    sample_range = "全部"
                    if sample_num and sample_num != 1000000:
                        describe += f"，每个{sample_by}至少抽取{sample_num}份。"
                    if sample_by == "重点病历":
                        sample_range = "全部" if len(all_tags) == len(request.filter.tags) else json.dumps(list(request.filter.tags))
                    elif sample_by == "诊疗组":
                        sample_range = "全部" if request.filter.get("group", "") == "all" else request.filter.get("group", "")
                    query.update({"filter": json.dumps(filter_data), "range": sample_range, "describe": describe}, synchronize_session=False)
                return True, ""
            query = session.query(SampleFilter).filter(SampleFilter.name == request.name, SampleFilter.auditType == request.auditType, SampleFilter.caseType == request.caseType, SampleFilter.is_delete == 0)
            if query.first():
                logging.info("sample filter name: %s is exist.", request.name)
                return False, "名称已存在"
            if not request.name:
                return False, "名称不能为空"
            # filter_data = MessageToDict(request.filter)
            filter_data = request.filter
            sample_by = SAMPLE_BY_DICT.get(request.filter.get("sampleBy")) or ""
            sample_num = request.filter.get("sampleCount") or 0
            describe = f"按{sample_by}抽取"
            sample_range = "全部"
            if sample_num and sample_num != 1000000:
                describe += f"，每个{sample_by}至少抽取{sample_num}份。"
            if sample_by == "重点病历":
                sample_range = "全部" if len(all_tags) == len(request.filter.get("tags", [])) else json.dumps(list(request.filter.get("tags", [])))
            elif sample_by == "诊疗组":
                sample_range = "全部" if request.filter.get("group") == "all" else request.filter.get("group", "")
            obj_dict = {"name": request.name, "auditType": request.auditType, "filter": json.dumps(filter_data),
                        "describe": describe, "range": sample_range, "is_delete": 0, "create_time": arrow.utcnow().to('+08:00').naive,
                        "caseType": request.caseType}
            obj = SampleFilterModel.newObject(self.app, **obj_dict)
            self.sampleRepo.add(session, obj)
            return True, ""

    def getSampleTaskList(self, request):
        """
        抽取定时任务列表
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query = session.query(SampleTask).filter(SampleTask.is_delete == 0, SampleTask.status.in_([1, 2]))
            if request.name:
                query = query.filter(SampleTask.name.like("%{}%".format(request.name)))
            if request.auditType:
                query = query.filter(SampleTask.auditType == request.auditType)
            if request.startTime:
                query = query.filter(SampleTask.create_time >= request.startTime)
            if request.endTime:
                query = query.filter(SampleTask.create_time <= request.endTime)
            if request.caseType:
                query = query.filter(SampleTask.caseType == request.caseType)
            total = query.count()
            start = request.start or 0
            size = request.size or 15
            query = query.slice(start, start + size)
            res = []
            for item in query.all():
                session.expunge(item)
                res.append(item)
            return res, total

    def saveSampleTask(self, request):
        """
        抽取定时任务保存
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            if request.id:
                query = session.query(SampleTask).filter(SampleTask.id == request.id)
                if request.deleteFlag == 1:
                    query.update({"is_delete": 1}, synchronize_session=False)
                    return 0, True, ""
                if request.name:
                    query.update({"name": request.name}, synchronize_session=False)
                if request.status:
                    query.update({"status": request.status}, synchronize_session=False)
                if request.sampleFilter and request.sampleFilter.sampleBy:
                    # filter_data = MessageToDict(request.sampleFilter)
                    filter_data = request.sampleFilter
                    query.update({"sample_filter": json.dumps(filter_data)}, synchronize_session=False)
                if request.days:
                    query.update({"days": request.days}, synchronize_session=False)
                if request.firstSampleTime:
                    query.update({"first_sample_time": request.firstSampleTime}, synchronize_session=False)
                if request.queryFilter:
                    # filter_data = MessageToDict(request.queryFilter)
                    filter_data = request.queryFilter
                    if filter_data:
                        query.update({"query_filter": json.dumps(filter_data)}, synchronize_session=False)
                if request.assignDoctor:
                    # filter_data = [MessageToDict(item) for item in request.assignDoctor]
                    filter_data = request.assignDoctor
                    if filter_data:
                        query.update({"assign_doctor": json.dumps(filter_data, ensure_ascii=False)}, synchronize_session=False)
                if request.taskType:
                    query.update({"type": request.taskType}, synchronize_session=False)
                if request.notCurrentDeptFlag != query.first().notCurrentDeptFlag:
                    query.update({"notCurrentDeptFlag": request.notCurrentDeptFlag}, synchronize_session=False)
                if request.firstSampleTime:
                    query.update({"first_sample_time": request.firstSampleTime}, synchronize_session=False)
                    query.update({"next_run_time": request.firstSampleTime}, synchronize_session=False)
                return 0, True, ""
            query = session.query(SampleTask).filter(SampleTask.name == request.name, SampleTask.auditType == request.auditType, SampleTask.caseType == request.caseType, SampleTask.is_delete == 0)
            if query.first():
                logging.info("sample task name: %s is exist.", request.name)
                return 0, False, "名称已存在"
            if not request.name:
                return 0, False, "名称不能为空"
            obj_dict = {"name": request.name, "auditType": request.auditType,
                        "type": request.taskType, "notCurrentDeptFlag": request.notCurrentDeptFlag,
                        "is_delete": 0, "create_time": arrow.utcnow().to('+08:00').naive, "days": request.days or 0,
                        "caseType": request.caseType, "status": 1}
            if request.firstSampleTime:
                obj_dict["first_sample_time"] = request.firstSampleTime
                obj_dict["next_run_time"] = request.firstSampleTime
            else:
                next_run_time = self.get_next_run_time()
                obj_dict["next_run_time"] = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
            if request.queryFilter:
                # obj_dict["query_filter"] = json.dumps(MessageToDict(request.queryFilter), ensure_ascii=False)
                obj_dict["query_filter"] = json.dumps(request.queryFilter, ensure_ascii=False)
            if request.sampleFilter:
                # obj_dict["sample_filter"] = json.dumps(MessageToDict(request.sampleFilter), ensure_ascii=False)
                obj_dict["sample_filter"] = json.dumps(request.sampleFilter, ensure_ascii=False)
            if request.assignDoctor:
                assign_doctors = request.assignDoctor
                # assign_doctors = []
                # for item in request.assignDoctor:
                #     assign_doctors.append(MessageToDict(item))
                obj_dict["assign_doctor"] = json.dumps(assign_doctors, ensure_ascii=False)
            obj = SampleTaskModel.newObject(self.app, **obj_dict)
            self.sampleRepo.add(session, obj)
            session.commit()
            return obj.id, True, ""

    @classmethod
    def get_next_run_time(cls):
        import datetime
        now = arrow.utcnow().to("+08:00").naive
        year = now.year
        month = now.month + 1
        if month == 13:
            month = 1
            year += 1
        return datetime.date(year=year, month=month, day=1)

    def queryRunTask(self):
        """
        查询需执行的抽取任务
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            now = arrow.utcnow().to("+08:00").naive
            query = session.query(SampleTask).filter(SampleTask.status == 1, SampleTask.is_delete == 0, SampleTask.next_run_time <= now)
            res = []
            for item in query.all():
                session.expunge(item)
                res.append(item)
            return res

    def run_task(self, task: SampleTask):
        """
        执行抽取任务
        1. 生成GetCaseListRequest请求对象req, sampleBy: task.sample_filter.sampleBy, sampleNum: task.sample_filter.sampleNum
        2. 执行self.getSampleCase(req, sampleBy=, sampleNum=)
            得到caseList、caseIds
        3. 执行self.record_sample_operation(sampleId, caseType, caseIds, operatorId=, operatorName=, sampleBy=, sampleCount=, sampleFilter=conditions)
            得到sampleId
        4. 执行self.submitSampleResult(caseIds, auditType, caseType, operatorId, operatorName, sampleId)
        5. 根据 task.type==分配
            task.assign_doctor 生成 list[ExpertUser]
            判断是否执行 self.assignExpert(sampleId, caseType, assignType=avg, auditType, avoidSameDept=task.notCurrentDeptFlag, users=)
        6. 全部执行完成后将task.next_run_time 设置成 task.days 天后
        :return:
        """
        sample_filter = json.loads(task.sample_filter)
        req = self.get_run_task_case_req(task)
        caseList, total = self.getSampleCase(req, sampleBy=sample_filter["sampleBy"], sampleNum=sample_filter["sampleCount"])
        caseIds = [caseInfo.caseId for caseInfo in caseList]
        conditions = ["全部"]
        sampleBy = sample_filter["sampleBy"]
        if sampleBy == SAMPLE_BY_TAG:
            with self.app.mysqlConnection.session() as session:
                all_tags = self.caseTag.getList(session) or []
            if len(all_tags) > len(sample_filter["tags"]):
                conditions = sample_filter["tags"]
            else:
                sampleBy = SAMPLE_BY_TAG_ALL
        sampleId = self.record_sample_operation(-1, task.caseType, caseIds, operatorId="AI", operatorName="AI", sampleBy=sampleBy,
                                                sampleCount=sample_filter["sampleCount"], sampleFilter=conditions)
        self.submitSampleResult(caseIds, task.auditType, task.caseType, "system", "task", sampleId)
        if "分配" in task.type:
            users = []
            if task.assign_doctor:
                for item in json.loads(task.assign_doctor):
                    user_dict = {"userId": item["code"], "userName": item["name"]}
                    user = ExpertUser.newObject(self.app, **user_dict)
                    user.setDepartment(item["department"])
                    users.append(user)
            self.assignExpert(sampleId, task.caseType, assignType="avg", auditType=task.auditType, noSameDept=task.notCurrentDeptFlag, users=users)
        self.updateTaskNextRunTime(task)

    @classmethod
    def get_run_task_case_req(cls, task):
        """
        获取case list的req对象
        :return:
        """
        now = arrow.utcnow().to("+08:00").naive
        last_time = now - timedelta(days=int(task.days))
        query_filter = json.loads(task.query_filter)
        query_filter["auditType"] = task.auditType
        query_filter["caseType"] = task.caseType
        # sample_filter = json.loads(task.sample_filter)
        # tags = sample_filter["tags"]
        # query_filter["sampleByTags"] = tags
        # query_filter["tags"] = [tag for tag in tags.split(',') if tag]
        timeType = 5 if task.caseType == "running" else 1
        query_filter["timeType"] = timeType
        query_filter["startTime"] = last_time.strftime("%Y-%m-%d %H:%M:%S")
        if query_filter.get("sortField"):
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
            query_filter['sortFields'] = []
            for sf in query_filter["sortField"]:
                if FIELD_MAP.get(sf["field"]):
                    if sf["field"] == 'receiveTime':
                        sort_field = SortField(field=FIELD_MAP.get(sf["field"], sf["field"]), way=sf.get("way", ""),
                                               table='audit_record', extParams=sf.get("extParams"))
                    elif sf["field"] == "problems":
                        sort_field = SortField(field=FIELD_MAP.get(sf["field"])[task.auditType], way=sf.get("way", ""),
                                               extParams=sf.get("extParams"))
                    else:
                        sort_field = SortField(field=FIELD_MAP.get(sf["field"], sf["field"]), way=sf.get("way", ""),
                                               extParams=sf.get("extParams"))
                    query_filter['sortFields'].append(sort_field)
            del query_filter["sortField"]
        if query_filter.get("tag"):
            query_filter["tags"] = [tag for tag in query_filter["tag"].split(',') if tag]
            del query_filter["tag"]
        logging.info("get_run_task_case_req, query_filter: %s", query_filter)
        return GetCaseListRequest(**query_filter)

    def updateTaskNextRunTime(self, task):
        """
        将任务的下次执行时间更新
        :return:
        """
        next_time = task.next_run_time + timedelta(days=task.days)
        with self.app.mysqlConnection.session() as session:
            session.query(SampleTask).filter(SampleTask.id == task.id).update({"next_run_time": next_time}, synchronize_session=False)


class DepartmentSampleApplication(SampleApplication):

    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_DEPARTMENT)


class HospitalSampleApplication(SampleApplication):

    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_HOSPITAL)


class FirstpageSampleApplication(SampleApplication):

    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_FIRSTPAGE)


class ExpertSampleApplication(SampleApplication):

    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_EXPERT)
