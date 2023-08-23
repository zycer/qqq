#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: doctor_repository.py
@time: 2021/7/22 8:06 下午
@desc:
"""
import json
import logging
import time
import traceback
import arrow
from collections import defaultdict
from datetime import datetime

import requests
from qcdbmodel.qcdbmodel.models import CaseProblem, Case

from qcaudit.common.const import QCITEM_TAGS
from qcaudit.domain.debuglog.debuglog import DebugLog
from qcaudit.domain.ipaddr.ip_rule import IpRule
from qcaudit.domain.problem import ProblemRepository
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.domain.message.message_repository import MessageRepo


class DoctorRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.logger = logging.getLogger("qcaudit.doctor")
        self.PROBLEM_TAGS = {"force": "强制", "veto": "否决", "isAi": "AI", "my": "我的", "notAi": "人工"}
        self._messageRepository = MessageRepo(app, auditType)
        self._problemRepository = ProblemRepository(self.app, auditType)
        self.color_dict = self.get_color_dict()

    def get_color_dict(self):
        """
        获取cdss色值字典
        :return:
        """
        try:
            with self.app.mysqlConnection.session() as session:
                query_sql = '''select word, color from cdss_color_info'''
                query = session.execute(query_sql)
                data = query.fetchall()
                return {item[0]: item[1] for item in data}
        except Exception as e:
            self.logger.error(e)
            return {}

    def update_doctor_not_remind(self, doctor, notRemind):
        """
        更新当前医生今日不再提醒
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            now = datetime.now().strftime('%Y%m%d%H%M%S')
            insert_sql = '''insert into doctor_setting (doctor, tip_setting, date) values ("{}", {}, "{}")'''.format(
                doctor, notRemind, int(now))
            # self.logger.info("update_doctor_not_remind, insert_sql: %s", insert_sql)
            session.execute(insert_sql)

    @classmethod
    def get_doctor_name(cls, session, doctor):
        """
        查询医生姓名
        :return:
        """
        query_doctor_name_sql = '''select name from doctor where id = "%s"''' % doctor
        query = session.execute(query_doctor_name_sql)
        queryset = query.fetchone()
        doctor_name = queryset[0] if queryset else ""

        return doctor_name

    def query_doctor_is_remind(self, doctor):
        """
        查询当前医生今日是否需要提醒
        :param doctor:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            today = datetime.now().strftime('%Y%m%d')
            start_time = today + "000000"
            end_time = today + "235959"
            query_sql = '''select 1 from doctor_setting where date between "{}" and "{}" 
            and doctor = "{}" and tip_setting = 1'''.format(int(start_time), int(end_time), doctor)
            # self.logger.info("query_doctor_is_remind, query_sql: %s", query_sql)
            query = session.execute(query_sql)
            is_remind = 2 if query.fetchone() else 1
            doctor_name = self.get_doctor_name(session, doctor)

        return is_remind, doctor_name

    def query_doctor_refuse_num(self, doctor):
        """
        查询当前医生待整改病历数量
        :param doctor:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            wait_alter_case_data, waitAlterCaseCount = self.query_wait_alter_data(session, doctor)
            wa_caseId_list = [item[0] for item in wait_alter_case_data]
            wa_caseId_str = ",".join(['"%s"' % item for item in wa_caseId_list])
            wa_problem_count_dict, wa_force_problem_count_dict, wa_score_dict = self.query_problem_count(
                session, wa_caseId_str)
            firstNum = sum(1 if wa_score_dict.get(caseId, 0) <= 10 else 0 for caseId in wa_caseId_list)
            secondNum = sum(1 if 10 < wa_score_dict.get(caseId, 0) <= 20 else 0 for caseId in wa_caseId_list)
            thirdNum = sum(1 if wa_score_dict.get(caseId, 0) > 20 else 0 for caseId in wa_caseId_list)
            doctorName = self.get_doctor_name(session, doctor)

        return waitAlterCaseCount, firstNum, secondNum, thirdNum, doctorName

    def query_caseId_is_sample(self, caseIds, is_extract=False):
        """
        根据caseId查询是否有过抽检记录
        :return:
        """
        # self.logger.info("query_caseId_is_sample, caseIds: %s", caseIds)
        originCaseIdList = []
        for case_id in caseIds:
            if "_" in case_id and len(case_id.split("_")[-1]) > 0:
                originCaseIdList.append(''.join(case_id.split("_")[:-1]))
            else:
                originCaseIdList.append(case_id)
        # self.logger.info("query_caseId_is_sample, originCaseIdList: %s", originCaseIdList)
        if not originCaseIdList:
            return {} if not is_extract else {}, {}
        originCaseIdListStr = ','.join(['"%s"' % item for item in originCaseIdList])
        is_sample_caseId_dict = {}
        with self.app.mysqlConnection.session() as session:
            query_is_sample_sql = '''select c.caseId, c.originCaseId, ar.timeline
            from `case` c 
            inner join sample_record_item sri on c.caseId = sri.caseId 
            inner join audit_record ar on c.caseId = ar.caseId 
            where c.caseId in (%s)''' % originCaseIdListStr
            # self.logger.info("query_caseId_is_sample, query_is_sample_sql: %s", query_is_sample_sql)
            query = session.execute(query_is_sample_sql)
            is_sample_data = query.fetchall()
            # self.logger.info("query_caseId_is_sample, len query.fetchall: %s", len(is_sample_data))
            case_qc_time_dict = {}
            for item in is_sample_data:
                if not is_sample_caseId_dict.get(item[0], ""):
                    is_sample_caseId_dict[item[0]] = 1
                if is_extract:
                    data = json.loads(item[2])
                    for i in range(len(data) - 1, -1, -1):
                        if "质控" in data[i].get("action", "") and "撤销" not in data[i].get("action", ""):
                            case_qc_time_dict[item[0]] = data[i].get("time", "")
                            break
        if is_extract:
            return is_sample_caseId_dict, case_qc_time_dict
        return is_sample_caseId_dict

    def query_wait_alter_case_list(self, session, doctor, response):
        """
        查询待整改病历列表
        :return:
        """
        wait_alter_case_data, waitAlterCaseCount = self.query_wait_alter_data(session, doctor)

        wa_caseId_list = [item[0] for item in wait_alter_case_data]
        is_sample_caseId_dict = self.query_caseId_is_sample(wa_caseId_list)
        wa_caseId_str = ",".join(['"%s"' % item[0] for item in wait_alter_case_data])
        wa_problem_count_dict, wa_force_problem_count_dict, wa_score_dict = self.query_problem_count(
            session, wa_caseId_str)
        have_appeal_dict = self.query_have_appeal(case_id_list=wa_caseId_list, doctorId=doctor)
        overtime_case_list = []
        for item in wait_alter_case_data:
            if item[10] and datetime.now() > item[10]:
                overtime_case_list.append(item)
        if overtime_case_list:
            for item in overtime_case_list:
                wait_alter_case_data.remove(item)
        self.unmarshal_case_info(overtime_case_list, response, wa_score_dict, wa_problem_count_dict,
                                 wa_force_problem_count_dict, is_sample_caseId_dict, case_type=1,
                                 have_appeal_dict=have_appeal_dict)
        self.unmarshal_case_info(wait_alter_case_data, response, wa_score_dict, wa_problem_count_dict,
                                 wa_force_problem_count_dict, is_sample_caseId_dict, case_type=1,
                                 have_appeal_dict=have_appeal_dict)

        return waitAlterCaseCount

    @classmethod
    def query_wait_alter_data(cls, session, doctor):
        """
        查询当前医生待整改数据
        :return:
        """
        query_wait_alter_case_sql = '''select distinct c.caseId, c.patientId, c.name, c.attendDoctor, c.dischargeTime, 
        c.reviewTime, c.reviewer, c.status, c.originCaseId, rh.auditType, rh.fix_deadline, c.inpNo
        from refuse_detail rd inner join `case` c on rd.caseId = c.caseId
        inner join refuse_history rh on c.caseId = rh.caseId and c.audit_id = rh.audit_id and rd.history_id = rh.id
        where (rd.doctor = "{doctor}" or c.attendCode = "{doctor}") and c.status != 5 
        and rd.is_deleted = 0 and rd.apply_flag = 0 
        order by c.reviewTime '''.format(doctor=doctor)
        query = session.execute(query_wait_alter_case_sql)
        wait_alter_case_data = query.fetchall()
        waitAlterCaseCount = len(wait_alter_case_data)

        return wait_alter_case_data, waitAlterCaseCount

    def query_wait_apply_case_list(self, session, doctor, response, patientType=None, onlineStartTime=None):
        """
        查询待申请病历列表
        :return:
        """
        query_wait_apply_case_sql = '''select c.caseId, c.patientId, c.name, c.attendDoctor, c.dischargeTime, 
        c.reviewTime, c.reviewer, c.status, c.originCaseId, c.department, c.inpDays, c.inpNo from `case` c 
        where c.attendCode = "{doctor}" and c.status = 5 and c.dischargeTime is not NULL '''.format(doctor=doctor)
        if patientType:
            query_wait_apply_case_sql += 'and c.patientType = "%s" ' % patientType
        # 第一次正式上线的时间，在此之前出院的病历不显示在待申请病历列表中
        if onlineStartTime:
            query_wait_apply_case_sql += 'and c.dischargeTime > "%s" ' % arrow.get(onlineStartTime).naive.strftime("%Y-%m-%d")
        query_wait_apply_case_sql += "order by c.dischargeTime"
        query = session.execute(query_wait_apply_case_sql)
        wait_apply_case_data = query.fetchall()
        waitApplyCaseCount = len(wait_apply_case_data)

        caseId_list = [item[0] for item in wait_apply_case_data]
        is_sample_caseId_dict = self.query_caseId_is_sample(caseId_list)
        caseId_str = ",".join(['"%s"' % item[0] for item in wait_apply_case_data])
        have_appeal_dict = self.query_have_appeal(case_id_list=caseId_list, doctorId=doctor)
        problem_count_dict, force_problem_count_dict, score_dict = self.query_problem_count(
            session, caseId_str, is_apply=1)

        self.unmarshal_case_info(wait_apply_case_data, response, score_dict, problem_count_dict,
                                 force_problem_count_dict, is_sample_caseId_dict, case_type=2,
                                 have_appeal_dict=have_appeal_dict)

        return waitApplyCaseCount

    def query_extract_case_list(self, session, doctor, response):
        """
        查询待抽检病历列表
        :return:
        """
        query_extract_case_sql = '''select c.caseId, c.patientId, c.name, c.attendDoctor, c.dischargeTime, 
        c.reviewTime, c.reviewer, sri.auditType, sr.caseType, c.status, c.originCaseId, c.inpNo, sri.is_read
        from `case` c inner join sample_record_item sri on c.caseId = sri.caseId 
        inner join sample_record sr on sri.recordId = sr.id 
        where c.attendCode = "{doctor}" order by c.reviewTime desc '''.format(doctor=doctor)
        query = session.execute(query_extract_case_sql)
        extract_case_data = query.fetchall()
        extractCaseCount = len(extract_case_data)
        extractNotReadCaseCount = sum(1 for item in extract_case_data if item[11] == 0)

        extract_caseId_list = [item[0] for item in extract_case_data]
        is_sample_caseId_dict, case_qc_time_dict = self.query_caseId_is_sample(extract_caseId_list, is_extract=True)
        extract_problem_count_dict, extract_force_problem_count_dict, \
        extract_score_dict = self.query_extract_problem_count(extract_case_data)

        self.unmarshal_case_info(extract_case_data, response, extract_score_dict, extract_problem_count_dict,
                                 extract_force_problem_count_dict, is_sample_caseId_dict, case_type=3,
                                 case_qc_time_dict=case_qc_time_dict)

        return extractCaseCount, extractNotReadCaseCount

    def query_extract_problem_count(self, extract_case_data):
        """
        根据caseId查询 抽检 问题数/强制问题数/分数
        :return:
        """
        extract_score_dict = {}
        extract_problem_count_dict = {}
        extract_force_problem_count_dict = {}
        for item in extract_case_data:
            caseId = item[0]
            sample_data = self.query_sample_data(caseId)
            for sample_info in sample_data:
                operator_id = sample_info[1]
                auditType = sample_info[3]
                problem_data, problemCount = self.query_problem_data_by_audit_type(caseId, auditType)
                extract_problem_count_dict[caseId] = problemCount
                score = 0
                tmp_key = ""
                for problem_info in problem_data:
                    tmp_key = caseId + (problem_info[10] or "")
                    if not extract_score_dict.get(tmp_key, None):
                        extract_score_dict[tmp_key] = 0
                    score += problem_info[4]
                extract_score_dict[tmp_key] = score
                for item1 in problem_data:
                    if item1[18] == 1:
                        extract_force_problem_count_dict[caseId] = problemCount
                    break
        return extract_problem_count_dict, extract_force_problem_count_dict, extract_score_dict

    @classmethod
    def query_problem_count(cls, session, caseId_list, is_apply=0):
        """
        根据caseId查询问题数/强制问题数/分数
        :return:
        """
        problem_count_dict = {}
        force_problem_count_dict = {}
        score_dict = {}
        if caseId_list:
            if is_apply == 1:  # 查询待申请的 可能存在事中未驳回问题
                query_wait_apply_problem_count_sql = '''select cp.caseId, cp.qcItemId, cp.problem_count, cp.score, 
                qi.veto, cp.id, cp.is_fix, cp.is_ignore from caseProblem cp inner join `case` c on cp.caseId = c.caseId 
                and cp.audit_id = c.audit_id inner join qcItem qi on cp.qcItemId = qi.id where cp.caseId in ({}) 
                and cp.is_deleted = 0 and cp.is_ignore = 0 and cp.is_fix = 0 
                and (cp.refuseFlag = 1 or cp.auditType = "active")'''.format(caseId_list)
            else:
                query_wait_apply_problem_count_sql = '''select cp.caseId, cp.qcItemId, cp.problem_count, cp.score, 
                qi.veto, cp.id, cp.is_fix, cp.is_ignore from caseProblem cp inner join `case` c on cp.caseId = c.caseId 
                and cp.audit_id = c.audit_id inner join qcItem qi on cp.qcItemId = qi.id where cp.caseId in ({}) 
                and cp.is_deleted = 0 and cp.is_ignore = 0 and cp.is_fix = 0 and cp.refuseFlag = 1'''.format(
                    caseId_list)
            query = session.execute(query_wait_apply_problem_count_sql)
            wait_apply_problem_count_data = query.fetchall()
            for item in wait_apply_problem_count_data:
                if not problem_count_dict.get(item[0], None):
                    problem_count_dict[item[0]] = 0
                if not score_dict.get(item[0], None):
                    score_dict[item[0]] = 0
                if not force_problem_count_dict.get(item[0], None):
                    force_problem_count_dict[item[0]] = 0

                if item[6] == 0 and item[7] == 0:
                    problem_count_dict[item[0]] += item[2]  # {病历号: 问题总数}
                    score_dict[item[0]] += item[3]  # {病历号: 总扣分}
                    if item[4] == 1:
                        force_problem_count_dict[item[0]] += item[2]  # {病历号: 强制问题数}

        return problem_count_dict, force_problem_count_dict, score_dict

    @classmethod
    def unmarshal_case_info(cls, data, response, score_dict, problem_count_dict, force_problem_count_dict,
                            is_sample_caseId_dict=None, case_type=1, case_qc_time_dict=None, have_appeal_dict=None):
        """
        病历信息写入response
        :return:
        """
        if not is_sample_caseId_dict:
            is_sample_caseId_dict = {}
        if not case_qc_time_dict:
            case_qc_time_dict = {}
        if not have_appeal_dict:
            have_appeal_dict = {}
        for item in data:
            if case_type == 1:  # 待整改病历
                protoItem = {}  # response.waitAlterCase.add()
                protoItem["status"]= item[7] or 0
                protoItem["originCaseId"]= item[8] or item[0]
                protoItem["auditType"]= item[9] or ""
                protoItem["score"]= 100 - score_dict.get(item[0], 0)
                protoItem["reviewTime"]= item[5].strftime("%Y-%m-%d %H:%M:%S") if item[5] else ""
                if item[10]:
                    protoItem["isOvertime"]= 1 if datetime.now() > item[10] else 0
            elif case_type == 2:  # 待申请病历
                protoItem = {}  # response.waitApplyCase.add()
                protoItem["status"]= item[7] or 0
                protoItem["originCaseId"]= item[8] or item[0]
                protoItem["score"]= 100 - score_dict.get(item[0], 0)
                protoItem["reviewTime"]= item[5].strftime("%Y-%m-%d %H:%M:%S") if item[5] else ""
            else:  # 抽检病历
                protoItem = {}  # response.extractCase.add()
                protoItem["auditType"]= item[7] or ""
                protoItem["status"]= item[9] or 0
                protoItem["originCaseId"]= item[10] or item[0]
                protoItem["isRead"]= item[12] or 0
                tmp_key = item[0] + (item[7] or "")
                tmp_score = score_dict.get(tmp_key, score_dict.get(item[0], 0))
                protoItem["score"]= 100 - tmp_score
                protoItem["reviewTime"]= case_qc_time_dict.get(item[0], "")
                protoItem["caseType"]= item[8] or ""
            protoItem["caseId"]= item[0] or ""
            protoItem["patientId"]= item[11] or item[1] or ""
            protoItem["name"]= item[2] or ""
            protoItem["attending"]= item[3] or ""
            protoItem["dischargeTime"]= item[4].strftime("%Y-%m-%d") if item[4] else ""

            protoItem["reviewer"]= item[6] or ""

            level = "甲" if protoItem["score"]>= 90 else "乙"
            protoItem["level"]= "丙" if protoItem["score"]< 80 else level

            protoItem["isSample"]= is_sample_caseId_dict.get(item[0], 0)
            protoItem["problemCount"]= problem_count_dict.get(item[0], 0)
            protoItem["forceProblemCount"]= force_problem_count_dict.get(item[0], 0)
            have_appeal_list = have_appeal_dict.get(str(item[0]), [0, 0])
            protoItem["haveAppeal"]= have_appeal_list[0]
            protoItem["haveNotReadAppeal"]= have_appeal_list[1]
            if case_type == 1:
                response["waitAlterCase"].append(protoItem)
            elif case_type == 2:
                response["waitApplyCase"].append(protoItem)
            else:
                response["extractCase"].append(protoItem)

    @classmethod
    def query_three_day_start_time(cls, session):
        """
        查询三日/两日归档率计算起始时间
        :return:
        """
        threeDayStartTime = ""
        twoDayStartTime = ""
        query_three_day_start_sql = '''select date from calendar where date < "{today}" and isWorkday = 1 
        order by date desc limit 3'''.format(today=datetime.now().strftime("%Y-%m-%d"))
        query = session.execute(query_three_day_start_sql)
        three_day_data = query.fetchall()
        if three_day_data and len(three_day_data) == 3:
            threeDayStartTime = three_day_data[2][0].strftime("%Y-%m-%d") + " 00:00:00"
            twoDayStartTime = three_day_data[1][0].strftime("%Y-%m-%d") + " 00:00:00"

        return threeDayStartTime, twoDayStartTime

    def query_emr_problem_count(self, request):
        """
        查询病历问题数
        :return:
        """
        problem_data, problemCount = self.query_emr_problem_data(request, is_query_count=1)
        with self.app.mysqlConnection.session() as session:
            doctorName = self.get_doctor_name(session, request.doctor)
        return problemCount, doctorName

    def query_emr_problem_data(self, request, is_query_count=0):
        """
        查询病历问题数据
        :return:
        """
        caseId = request.caseId or ""
        isFix = 0
        isIgnore = 0
        if not is_query_count:
            isFix = request.isFix or 0
            isIgnore = request.isIgnore or 0
        case_status = self.query_case_status(caseId)
        with self.app.mysqlConnection.session() as session:
            query_problem_sql = '''select distinct cp.id, cp.caseId, cp.reason, cp.comment, cp.score, cp.problem_count, 
            cp.is_fix, cp.is_ignore, cp.appeal, cp.appeal_time, cp.auditType, cp.detail, c.patientId, c.name, 
            c.attendDoctor, c.dischargeTime, c.reviewTime, c.reviewer, qi.veto, cp.doctorCode, cp.from_ai, 
            ar.id, ar.timeline, cp.docId, cp.deduct_flag, c.attendCode, c.status, c.gender, c.age, cp.status, qi.tags, c.inpNo, cp.docId, cp.active_save_flag
            from `case` c
            inner join caseProblem cp on cp.caseId = c.caseId and cp.audit_id = c.audit_id 
            inner join qcItem qi on cp.qcItemId = qi.id 
            inner join audit_record ar on cp.caseId = ar.caseId and cp.audit_id = ar.id '''
            if case_status == 5:
                # 待申请病历时需要查事中未驳回问题
                query_problem_sql += '''where c.caseId = "%s" and cp.is_deleted = 0 
                and (cp.refuseFlag = 1 or cp.auditType = "active")''' % caseId
            elif case_status in (1, 3):
                # 待审核病历存在问题也要不展示
                query_problem_sql += "where 1 != 1"
            else:
                query_problem_sql += '''where c.caseId = "%s" and cp.is_deleted = 0 and cp.refuseFlag = 1''' % caseId
            if isFix != 1:
                query_problem_sql += " and cp.is_fix = 0"
            if isIgnore != 1:
                query_problem_sql += " and cp.is_ignore = 0"
            if request.docIds:
                is_first_page = self.get_docIds_is_first_page(session, request.docIds)
                if not is_first_page:
                    docId_str = ','.join(['"%s"' % docId for docId in request.docIds.split(",")])
                    query_problem_sql += " and cp.docId in (%s)" % docId_str

            query = session.execute(query_problem_sql)
            self.logger.info("query_emr_problem_data, query_problem_sql: %s", query_problem_sql)
            problem_data = query.fetchall()
            # problemCount = sum([item[5] for item in problem_data if item[6] == 0 and item[7] == 0 and item[33] == 1])  # 问题总数 忽略已整改已忽略
            problemCount = 0
            for item in problem_data:
                # 忽略已整改已忽略
                if item[6] == 0 and item[7] == 0:
                    if item[20] == 0:
                        # 人工问题忽略未保存的
                        if item[33] == 1:
                            problemCount += item[5]
                    else:
                        problemCount += item[5]

        return problem_data, problemCount

    def query_docName_recordTime(self, docId_list):
        """
        根据docID查询docName, recordTime
        :return:
        """
        title_dict = {}
        doctor_code_dict = {}
        docId_str = ','.join(['"%s"' % docId for docId in docId_list])
        with self.app.mysqlConnection.session() as session:
            query_docName_recordTime_sql = '''select docId, documentName, recordTime, refuseCode
            from emrInfo where docId in (%s)''' % docId_str
            query = session.execute(query_docName_recordTime_sql)
            emr_info = query.fetchall()
            for item in emr_info:
                recordTime = item[2].strftime("%Y-%m-%d") if item[2] else ""
                title_dict[item[0]] = item[1] + " " + recordTime
                doctor_code_dict[item[0]] = item[3]
        return title_dict, doctor_code_dict

    @classmethod
    def get_docIds_is_first_page(cls, session, docIds):
        """
        判断要打印的文书id是否是首页
        :return:
        """
        doc_ids = ','.join(['"%s"' % item for item in docIds.split(',')])
        query_sql = '''select documentName from emrInfo where docId in (%s)''' % doc_ids
        query = session.execute(query_sql)
        data = query.fetchall()
        for item in data:
            if "病案首页" in item[0]:
                return True
        return False

    def query_case_status(self, caseId):
        """
        查询判断当前病历是否为事中
        :param caseId:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_case_status_sql = '''select status from `case` where caseId = "%s"''' % caseId
            query = session.execute(query_case_status_sql)
            data = query.fetchone()
            status = data[0] if data else 0

        return status

    def query_emr_problem_list(self, request, response):
        """
        查询病历问题列表
        :return:
        """
        doctor = request.doctor
        problem_data, problemCount = self.query_emr_problem_data(request)
        problem_id_list = [item[0] for item in problem_data]
        have_appeal_dict = self.query_have_appeal(problem_id_list=problem_id_list, doctorId=doctor)

        title_problem_dict, audit_record_dict, vetoProblemCount, forceProblemCount, \
            myProblemCount, score = self.get_title_problem_dict(problem_data, doctor, response,
                                                                have_appeal_dict=have_appeal_dict)

        response["caseInfo"]["caseId"]= request.caseId
        response["caseInfo"]["score"]= 100 - score
        level = "甲" if response["caseInfo"]["score"]>= 90 else "乙"
        response["caseInfo"]["level"]= "丙" if response["caseInfo"]["score"]< 80 else level
        if not response["caseInfo"].get("patientId"):
            case_info = self.query_case_info(request.caseId)
            if case_info:
                response["caseInfo"]["patientId"]= case_info[9] or case_info[0] or ""
                response["caseInfo"]["name"]= case_info[1] or ""
                response["caseInfo"]["attending"]= case_info[2] or ""
                response["caseInfo"]["dischargeTime"]= case_info[3].strftime("%Y-%m-%d %H:%M:%S") if case_info[3] else ""
                response["caseInfo"]["reviewTime"]= case_info[4].strftime("%Y-%m-%d %H:%M:%S") if case_info[4] else ""
                response["caseInfo"]["reviewer"]= case_info[5] or ""
                response["caseInfo"]["status"]= case_info[6] or 0
                response["caseInfo"]["gender"]= case_info[7] or ""
                response["caseInfo"]["age"]= case_info[8] or 0

        fix_deadline = self.query_case_fix_deadline(request.caseId)
        if fix_deadline and datetime.now() > fix_deadline:
            response["caseInfo"]["isOvertime"]= 1
        response["problemSummary"]["vetoProblemCount"]= vetoProblemCount
        response["problemSummary"]["forceProblemCount"]= forceProblemCount
        response["problemSummary"]["problemCount"]= problemCount
        response["problemSummary"]["myProblemCount"]= myProblemCount
        isBlock = self.unmarshal_problem_info(title_problem_dict, response, isApply=int(request.isApply or 0))
        if isBlock:
            self.update_case_block_time(request.caseId)
        self.unmarshal_audit_info(audit_record_dict, response)

    def update_case_block_time(self, caseId):
        """
        提交页面存在强控问题时，记录case表block_time
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            case_model = self.app.mysqlConnection["case"]
            session.query(case_model).filter(case_model.caseId == caseId, case_model.block_time.is_(None)).update({"block_time": arrow.utcnow().to("+08:00").naive}, synchronize_session=False)

    def query_have_appeal(self, problem_id_list=None, case_id_list=None, doctorId=""):
        """
        根据问题id或病历id查询是否存在申诉信息/未读申诉信息
        :return:
        """
        have_appeal_dict = {}
        if not problem_id_list and not case_id_list:
            return have_appeal_dict
        with self.app.mysqlConnection.session() as session:
            if problem_id_list:
                problem_ids = ",".join([str(item) for item in problem_id_list])
                query_sql = '''select cp.id, count(ai.id) cc, sum(ai.is_read) ss from caseProblem cp 
                left join appeal_info ai on cp.qcItemId = ai.qcItemId and cp.docId = ai.doc_id 
                and ai.must_read_user = "%s" where cp.id in (%s) group by cp.id''' % (doctorId, problem_ids)
            else:
                case_ids = ",".join(['"%s"' % item for item in case_id_list])
                query_sql = '''select a.caseId, count(a.id) cc, sum(a.is_read) ss from appeal_info a inner join caseProblem cp on a.problem_id = cp.id 
                where a.caseId in (%s) and a.must_read_user = "%s" and a.is_deleted = 0 and cp.is_deleted = 0 group by a.caseId''' % (case_ids, doctorId)
            query = session.execute(query_sql)
            self.logger.info("query_have_appeal, query_sql: %s", query_sql)
            data = query.fetchall()
            for item in data:
                c = item[1] or 0
                s = item[2] or 0
                have_appeal = 1 if c > 0 else 0
                have_not_read_appeal = 1 if c - s > 0 else 0
                have_appeal_dict[str(item[0])] = [have_appeal, have_not_read_appeal]
        return have_appeal_dict

    def query_case_info(self, caseId):
        """
        查询病历基本信息
        :param caseId:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_sql = '''select patientId, name, attendDoctor, dischargeTime, reviewTime, reviewer, status, gender, age, inpNo from `case` where caseId = "%s"''' % caseId
            query = session.execute(query_sql)
            queryset = query.fetchone()
        return queryset

    def query_case_fix_deadline(self, caseId):
        """
        查询退回病历整改期限
        :param caseId:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_sql = '''select distinct rh.fix_deadline from refuse_detail rd 
            inner join `case` c on rd.caseId = c.caseId inner join refuse_history rh on c.caseId = rh.caseId 
            and c.audit_id = rh.audit_id and rd.history_id = rh.id where rd.caseId = "%s" and rd.is_deleted = 0 
            and rd.apply_flag = 0''' % caseId
            query = session.execute(query_sql)
            queryset = query.fetchone()
        if queryset:
            return queryset[0]

    def get_title_problem_dict(self, problem_data, doctor, response, audit_record_dict=None, have_appeal_dict=None):
        """
        格式化文书问题数据
        :return:
        """
        if audit_record_dict is None:
            audit_record_dict = {}
        if have_appeal_dict is None:
            have_appeal_dict = {}
        docId_list = list(set([item[23] for item in problem_data]))
        title_dict = {}
        doctor_code_dict = {}
        if docId_list:
            title_dict, doctor_code_dict = self.query_docName_recordTime(docId_list)
        title_problem_dict = defaultdict(list)  # 文书名: [问题1, 问题2]
        title_problem_count_dict = {}
        score = 0
        vetoProblemCount = 0
        forceProblemCount = 0
        myProblemCount = 0
        for item in problem_data:
            title = title_dict.get(item[23], "文书缺失")
            problem_score = (item[4] or 0) if item[24] == 1 else 0
            have_appeal_list = have_appeal_dict.get(str(item[0]), [0, 0])
            problem_info = {"reason": item[2] or "", "comment": item[3] or "", "score": problem_score,
                            "problemId": item[0], "fixedFlag": item[6], "appealFlag": have_appeal_list[0],
                            "appeal": item[8] or "", "appealTime": item[9] or "", "ignoreFlag": item[7] or 0,
                            "detail": item[11] or "", "problemCount": item[5] or 0, "is_force": 0,
                            "from_ai": item[20] or 0, "my": 0, "haveNotReadAppeal": have_appeal_list[1],
                            "status": item[29] or 0, "tags": item[30] or "", "docId": str(item[32]), 
                            "active_save_flag": item[33] or 0, "case_status": item[26] or 5}

            if not title_problem_count_dict.get(title, None):
                title_problem_count_dict[title] = 0
            title_problem_count_dict[title] += 1
            if item[6] == 0 and item[7] == 0:
                if item[20] == 0:
                    if item[33] == 1:
                        score += problem_score
                        if item[18] == 1:
                            forceProblemCount += item[5] or 0
                        elif item[18] == 2:
                            vetoProblemCount += item[5] or 0
                else:
                    score += problem_score
                    if item[18] == 1:
                        forceProblemCount += item[5] or 0
                    elif item[18] == 2:
                        vetoProblemCount += item[5] or 0
            if item[18] == 1:
                problem_info["is_force"] = 1
            elif item[18] == 2:
                problem_info["is_force"] = 2
            if item[19] == doctor or (not item[19] and doctor_code_dict.get(item[23], "") == doctor) \
                    or item[25] == doctor:
                if item[6] == 0 and item[7] == 0:
                    if item[20] == 0:
                        if item[33] == 1:
                            myProblemCount += item[5] or 0
                    else:
                        myProblemCount += item[5] or 0
                problem_info["my"] = 1
            title_problem_dict[title].append(problem_info)

            if not response["caseInfo"].get("patientId"):
                response["caseInfo"]["patientId"]= item[31] or item[12] or ""
                response["caseInfo"]["name"] = item[13] or ""
                response["caseInfo"]["attending"] = item[14] or ""
                response["caseInfo"]["dischargeTime"] = item[15].strftime("%Y-%m-%d %H:%M:%S") if item[15] else ""
                response["caseInfo"]["reviewTime"] = item[16].strftime("%Y-%m-%d %H:%M:%S") if item[16] else ""
                response["caseInfo"]["reviewer"] = item[17] or ""
                response["caseInfo"]["status"] = item[26] or 0
                response["caseInfo"]["gender"] = item[27] or ""
                response["caseInfo"]["age"] = item[28] or 0
            if not audit_record_dict:
                audit_record_dict["id"] = item[21] or 0
                audit_record_dict["timeline"] = json.loads(item[22]) if item[22] else []

        return title_problem_dict, audit_record_dict, vetoProblemCount, forceProblemCount, myProblemCount, score

    def unmarshal_problem_info(self, title_problem_dict, response, isApply=0):
        """
        写入问题数据
        :return:
        """
        isBlock = False  # 是否记录拦截时间
        for title, problem_list in title_problem_dict.items():
            total = 0
            for item in problem_list:
                if item.get("case_status") == 5 and not item["from_ai"] and not item.get("active_save_flag"):
                    # 事中质控的人工问题且未保存发送给医生, 不展示，驳回的问题需要正常展示
                    continue
                total += item["problemCount"]
            if total == 0:
                continue
            protoItem = {"problem": []}  # response.problemList.add()
            protoItem["problemCount"]= total
            protoItem["title"]= title
            # protoItem.problemCount = sum([item["problemCount"] for item in problem_list])
            for item in problem_list:
                if item.get("case_status") == 5 and not item["from_ai"] and not item.get("active_save_flag"):
                    # 事中质控的人工问题且未保存发送给医生, 不展示
                    continue
                problem = {"tags": []}  # protoItem.problem.add()
                problem["reason"]= item.get("reason", "")
                problem["comment"]= item.get("comment", "")
                problem["score"]= item.get("score", float(0))
                problem["problemId"]= item.get("problemId", 0)
                problem["docId"]= item.get("docId", "0")
                problem["fixedFlag"]= item.get("fixedFlag", 0)
                problem["appealFlag"]= item.get("appealFlag", 0)
                problem["appeal"]= item.get("appeal", "") or ""
                problem["ignoreFlag"]= item.get("ignoreFlag", 0)
                problem["detail"]= item.get("detail", "") or ""
                problem["problemCount"]= item.get("problemCount", 0)
                problem["appealTime"]= item["appealTime"].strftime("%Y-%m-%d %H:%M:%S") if item["appealTime"] else ""
                if item["is_force"] == 1:
                    problem["tags"].append(self.PROBLEM_TAGS["force"])
                    if isApply:
                        isBlock = True
                elif item["is_force"] == 2:
                    problem["tags"].append(self.PROBLEM_TAGS["veto"])
                problem["tags"].append(self.PROBLEM_TAGS["isAi"] if item["from_ai"] else self.PROBLEM_TAGS["notAi"])
                if item["my"]:
                    problem["tags"].append(self.PROBLEM_TAGS["my"])
                if item.get("tags", ""):
                    tags = item["tags"].split(",")
                    for tag in tags:
                        if QCITEM_TAGS.get(tag, ""):
                            problem["tags"].append(QCITEM_TAGS[tag])
                problem["haveNotReadAppeal"]= item.get("haveNotReadAppeal", 0)
                problem["addFlag"]= item.get("status", 0)
                protoItem["problem"].append(problem)
            response["problemList"].append(protoItem)
        return isBlock

    @classmethod
    def unmarshal_audit_info(cls, audit_record_dict, response):
        """
        写入审核流程信息
        :return:
        """
        response["auditInfo"]["auditId"]= audit_record_dict.get("id", 0)
        for index in range(len(audit_record_dict.get("timeline", [])) - 1, -1, -1):
            item = audit_record_dict["timeline"][index]
            if "退" in item.get("action", "") or "回" in item.get("action", "") or "返" in item.get("action", ""):
                if "撤销" in item.get("action", ""):
                    continue
                if response["caseInfo"]["status"]== 5:
                    response["caseInfo"]["isRefuse"]= 1
                response["auditInfo"]["time"]= item.get("time", "")
                response["auditInfo"]["doctor"]= item.get("doctor", "")
                response["auditInfo"]["action"]= item.get("action", "")
                response["auditInfo"]["auditType"]= item.get("auditType", "")
                break

    @classmethod
    def unmarshal_assign_audit_info(cls, audit_record_dict, refuseTime, response):
        """
        指定流程写入审核流程信息
        :return:
        """
        response["auditInfo"]["auditId"]= audit_record_dict.get("id", "")
        for item in audit_record_dict["timeline"]:
            if item.get("time", "") == refuseTime:
                response["auditInfo"]["time"]= item.get("time", "")
                response["auditInfo"]["doctor"]= item.get("doctor", "")
                response["auditInfo"]["action"]= item.get("action", "")
                response["auditInfo"]["auditType"]= item.get("auditType", "")
                break

    def query_emr_assign_audit_record_problem_list(self, request, response):
        """
        指定质控流程查看问题列表
        :return:
        """
        refuseTime = request.refuseTime or ""
        caseId = request.caseId or ""
        doctor = request.doctor or ""
        with self.app.mysqlConnection.session() as session:
            query_record_problem_sql = '''select rh.problems, c.patientId, c.name, c.attendDoctor, c.dischargeTime, 
            c.reviewTime, c.reviewer, ar.id, ar.timeline, c.status, c.gender, c.age, c.inpNo
            from refuse_history rh 
            inner join `case` c on rh.caseId = c.caseId 
            inner join audit_record ar on rh.caseId = ar.caseId
            where rh.refuse_time = "%s" and rh.caseId = "%s"''' % (refuseTime, caseId)
            query = session.execute(query_record_problem_sql)
            record_problem_data = query.fetchone()
            if not record_problem_data:
                return
            problems = json.loads(record_problem_data[0])
            tmp_problem_id_list = [str(item.get("problemId", "")) for item in problems]
            problem_ids = ','.join(tmp_problem_id_list)
            query_ai_veto_sql = '''select distinct cp.id, qi.veto, cp.from_ai, cp.problem_count, cp.reason, cp.comment, 
            cp.score, cp.is_fix, cp.is_ignore, cp.appeal, cp.appeal_time, cp.detail, cp.doctorCode, cp.docId
            from caseProblem cp
            inner join qcItem qi on cp.qcItemId = qi.id
            where cp.id in (%s)''' % problem_ids
            query1 = session.execute(query_ai_veto_sql)
            ai_veto_data = query1.fetchall()
            ai_veto_dict = {}
            problem_id_list = []
            for item in ai_veto_data:
                problem_id_list.append(str(item[0]))
                ai_veto_dict[item[0]] = {"veto": item[1], "from_ai": item[2], "problem_count": item[3],
                                         "reason": item[4], "comment": item[5], "score": item[6], "is_fix": item[7],
                                         "is_ignore": item[8], "appeal": item[9], "appeal_time": item[10],
                                         "detail": item[11], "doctorCode": item[12], "docId": item[13]}
            problem_ids = ','.join(problem_id_list)
            have_appeal_dict = {}
            if problem_ids:
                query_appeal_sql = '''select problem_id, count(id) cc, sum(is_read) ss from appeal_info
                where problem_id in (%s) and length(must_read_user) > 10 and is_deleted = 0 
                group by problem_id''' % problem_ids
                query2 = session.execute(query_appeal_sql)
                appeal_data = query2.fetchall()
                for item in appeal_data:
                    have_appeal = 1 if item[1] > 0 else 0
                    have_not_read_appeal = 1 if item[1] - item[2] > 0 else 0
                    have_appeal_dict[int(item[0])] = [have_appeal, have_not_read_appeal]
            title_problem_count_dict = {}
            allScore = 0
            vetoProblemCount = 0
            forceProblemCount = 0
            myProblemCount = 0
            allProblemCount = 0
            audit_record_dict = {"id": record_problem_data[7], "timeline": json.loads(record_problem_data[8])}
            title_problem_dict = defaultdict(list)

            for item in problems:
                problemId = item.get("problemId", 0)
                record_time = item.get("recordTime", "")
                record_time = record_time.split(" ")[0] if record_time else "--"
                title = item.get("documentName", "--") + " " + record_time
                problem_data = ai_veto_dict.get(problemId, {})
                from_ai = problem_data.get("from_ai", 0)
                is_force = problem_data.get("veto", 0)
                problemCount = problem_data.get("problem_count", 0)
                reason = problem_data.get("reason", "")
                comment = problem_data.get("comment", "")
                score = float(problem_data.get("score", 0))
                fixedFlag = problem_data.get("is_fix", 0)
                appeal = problem_data.get("appeal", "")
                have_appeal_list = have_appeal_dict.get(int(problemId), [0, 0])
                appealFlag = have_appeal_list[0]
                appealTime = problem_data.get("appeal_time", None)
                ignoreFlag = problem_data.get("is_ignore", 0)
                detail = problem_data.get("detail", "")
                my = 1 if problem_data.get("doctorCode", "") == doctor else 0
                problem_info = {"reason": reason, "comment": comment,
                                "score": score, "problemId": problemId,
                                "fixedFlag": fixedFlag, "appealFlag": appealFlag,
                                "appeal": appeal, "appealTime": appealTime,
                                "ignoreFlag": ignoreFlag, "detail": detail,
                                "problemCount": problemCount, "is_force": is_force,
                                "from_ai": from_ai, "my": my, "docId": problem_data.get("docId", "0")}

                if not title_problem_count_dict.get(title, None):
                    title_problem_count_dict[title] = 0
                title_problem_count_dict[title] += 1
                allScore += score
                allProblemCount += problemCount
                if is_force == 1:
                    forceProblemCount += problemCount
                elif is_force == 2:
                    vetoProblemCount += problemCount
                if my:
                    myProblemCount += problemCount

                title_problem_dict[title].append(problem_info)

            response["caseInfo"]["caseId"]= caseId
            response["caseInfo"]["patientId"]= record_problem_data[12] or record_problem_data[1] or ""
            response["caseInfo"]["name"]= record_problem_data[2] or ""
            response["caseInfo"]["attending"]= record_problem_data[3] or ""
            response["caseInfo"]["dischargeTime"]= record_problem_data[4].strftime("%Y-%m-%d %H:%M:%S") if record_problem_data[4] else ""
            response["caseInfo"]["reviewTime"]= record_problem_data[5].strftime("%Y-%m-%d %H:%M:%S") if record_problem_data[5] else ""
            response["caseInfo"]["reviewer"]= record_problem_data[6] or ""
            response["caseInfo"]["status"]= record_problem_data[9] or 0
            response["caseInfo"]["gender"]= record_problem_data[10] or ""
            response["caseInfo"]["age"]= record_problem_data[11] or 0

            response["caseInfo"]["score"]= 100 - score
            level = "甲" if response["caseInfo"]["score"]>= 90 else "乙"
            response["caseInfo"]["level"]= "丙" if response["caseInfo"]["score"]< 80 else level

            response["problemSummary"]["vetoProblemCount"]= vetoProblemCount
            response["problemSummary"]["forceProblemCount"]= forceProblemCount
            response["problemSummary"]["problemCount"]= allProblemCount
            response["problemSummary"]["myProblemCount"]= myProblemCount
            self.unmarshal_problem_info(title_problem_dict, response)
            self.unmarshal_assign_audit_info(audit_record_dict, refuseTime, response)

    def query_emr_audit_record(self, request, response=None):
        """
        查询当前病历审核流程
        :return:
        """
        caseId = request.caseId
        with self.app.mysqlConnection.session() as session:
            query_audit_record_sql = '''select id, timeline from audit_record 
            where caseId = "%s" order by id desc limit 1''' % caseId
            # self.logger.info("query_emr_audit_record, query_audit_record_sql: %s", query_audit_record_sql)
            query = session.execute(query_audit_record_sql)
            audit_record = query.fetchone()
            timeline = json.loads(audit_record[1])
            auditId = audit_record[0]
            for item in timeline:
                protoItem = {}  # response.data.add()
                protoItem["time"] = item.get("time", "")
                protoItem["doctor"] = item.get("doctor", "")
                protoItem["action"] = item.get("action", "")
                protoItem["auditType"] = item.get("auditType", "")
                protoItem["auditId"] = auditId
                response["data"].append(protoItem)

    def update_problem_fix(self, request, response=None):
        """
        更新问题已整改
        :return:
        """
        problemId = request.problemId
        with self.app.mysqlConnection.session() as session:
            update_problem_fix_sql = 'update caseProblem set is_fix = 1 where id = "%s"' % problemId
            # self.logger.info("update_problem_fix, update_problem_fix_sql: %s", update_problem_fix_sql)
            session.execute(update_problem_fix_sql)
            query = session.query(CaseProblem.caseId, CaseProblem.qcItemId, Case.attendCode, Case.attendDoctor).join(
                Case, CaseProblem.audit_id == Case.audit_id).filter(CaseProblem.id == problemId)
            caseId, qcItemId, attendCode, attendDoctor = query.first()
            self._problemRepository.recordProblemAction(session, caseId, qcItemId, "医生整改完成", attendCode, attendDoctor, "active")

    def update_problem_appeal(self, request, response=None):
        """
        填写申诉信息
        :return:
        """
        problemId = request.problemId
        appealInfo = request.appealInfo
        doctor = request.doctor
        with self.app.mysqlConnection.session() as session:
            now = datetime.now()
            update_problem_appeal_sql = '''update caseProblem set appeal_doctor = "{doctor}", appeal = "{appealInfo}", 
            appeal_time = "{appeal_time}" where id = "{id}"'''.format(doctor=doctor, appealInfo=appealInfo,
                                                                      appeal_time=now, id=problemId)
            # self.logger.info("update_problem_appeal, update_problem_appeal_sql: %s", update_problem_appeal_sql)
            session.execute(update_problem_appeal_sql)

    def update_problem_ignore(self, request, response=None):
        """
        更新问题已忽略
        :return:
        """
        problemId = request.problemId
        with self.app.mysqlConnection.session() as session:
            update_problem_fix_sql = 'update caseProblem set is_ignore = 1 where id = "%s"' % problemId
            # self.logger.info("update_problem_ignore, update_problem_fix_sql: %s", update_problem_fix_sql)
            session.execute(update_problem_fix_sql)
            query = session.query(CaseProblem.caseId, CaseProblem.qcItemId, Case.attendCode, Case.attendDoctor).join(
                Case, CaseProblem.audit_id == Case.audit_id).filter(CaseProblem.id == problemId)
            caseId, qcItemId, attendCode, attendDoctor = query.first()
            self._problemRepository.recordProblemAction(session, caseId, qcItemId, "医生整改完成", attendCode, attendDoctor, "active")

    @classmethod
    def get_order_case_ids(cls, case_info_dict):
        """
        待提交列表排序caseId
        :return:
        """
        force_case_dict = {}
        case_dict = {}
        for case_id in case_info_dict:
            if case_info_dict[case_id]["forceProblemCount"] > 0:
                force_case_dict[case_id] = case_info_dict[case_id]["score"]
            else:
                case_dict[case_id] = case_info_dict[case_id]["score"]
        sort_force_case = sorted(force_case_dict.items(), key=lambda force_case_dict: force_case_dict[1])
        sort_case = sorted(case_dict.items(), key=lambda case_dict: case_dict[1])
        return [item[0] for item in sort_force_case] + [item[0] for item in sort_case]

    def query_submit_apply_case_list(self, request, response, doctor_veto):
        """
        查询提交待申请病历列表
        :return:
        """
        caseIds = request.caseIds or []
        caseIds_str = ','.join(['"%s"' % caseId for caseId in caseIds])
        with self.app.mysqlConnection.session() as session:
            query_case_status_sql = '''select caseId, status from `case` where caseId in (%s)''' % caseIds_str
            query1 = session.execute(query_case_status_sql)
            data1 = query1.fetchall()
            status_5_list = []
            status_13_list = []
            status_other_list = []
            # 保证与病历问题列表展示问题一致
            for item in data1:
                case_status = int(item[1]) if item[1] else 0
                if case_status == 5:
                    status_5_list.append(item[0])
                elif case_status in (1, 3):
                    status_13_list.append(item[0])
                else:
                    status_other_list.append(item[0])
            is_need_query_doc = False
            docIds = ""
            if request.docIds:
                docIds = ",".join(['"%s"' % item for item in request.docIds])
                query_doc_name_sql = '''select documentName from emrInfo where is_deleted = 0 and  caseId = "%s" 
                    and docId in (%s)''' % (caseIds[0], docIds)
                query_doc_name = session.execute(query_doc_name_sql)
                doc_name_data = query_doc_name.fetchall()
                for item in doc_name_data:
                    if "病案首页" in item[0]:
                        is_need_query_doc = True
            query_case_sql = '''select c.caseId, c.patientId, c.name, cp.problem_count, cp.score, qi.veto, c.attendCode, 
            cp.is_fix, cp.is_ignore, c.inpNo from `case` c left join caseProblem cp on c.caseId = cp.caseId 
            and c.audit_id = cp.audit_id and cp.is_deleted = 0 and {0} left join qcItem qi on cp.qcItemId = qi.id 
            where c.caseId in ({1})'''
            if is_need_query_doc and docIds:
                query_case_sql += " and cp.docId in (%s)" % docIds
            query_case_sql += " order by cp.score"
            status_5_data = []
            status_13_data = []
            status_other_data = []
            if status_5_list:
                case_id_str_5 = ','.join(['"%s"' % item for item in status_5_list])
                filter_str_5 = '(cp.refuseFlag = 1 or cp.auditType = "active")'
                query_case_sql_5 = query_case_sql.format(filter_str_5, case_id_str_5)
                query = session.execute(query_case_sql_5)
                status_5_data = query.fetchall()
            if status_13_list:
                case_id_str_13 = ','.join(['"%s"' % item for item in status_13_list])
                filter_str_13 = '1 != 1'
                query_case_sql_13 = query_case_sql.format(filter_str_13, case_id_str_13)
                query = session.execute(query_case_sql_13)
                status_13_data = query.fetchall()
            if status_other_list:
                case_id_str_other = ','.join(['"%s"' % item for item in status_other_list])
                filter_str_other = 'cp.refuseFlag = 1'
                query_case_sql_other = query_case_sql.format(filter_str_other, case_id_str_other)
                query = session.execute(query_case_sql_other)
                status_other_data = query.fetchall()
            case_data = status_5_data + status_13_data + status_other_data
            caseCount = 0
            forceProblemCaseCount = 0
            case_info_dict = {}
            for item in case_data:
                caseId = item[0]
                if not case_info_dict.get(caseId, {}):
                    case_info_dict[caseId] = {"score": 0, "problemCount": 0, "forceProblemCount": 0,
                                              "patientId": item[9] or item[1] or "", "name": item[2] or "",
                                              "attendCode": item[6] or "", "count": 0}
                if (item[5] or 0) == 1 and item[7] == 0 and item[8] == 0:
                    # 强控也要判断是否已整改/已忽略
                    case_info_dict[caseId]["forceProblemCount"] += item[3] or 0
                if item[7] == 0 and item[8] == 0:
                    case_info_dict[caseId]["problemCount"] += item[3] or 0
                    case_info_dict[caseId]["score"] += item[4] or 0
            all_case_ids = self.get_order_case_ids(case_info_dict)
            for case_id in all_case_ids:
                item = case_info_dict[case_id]
                protoItem = {}  # response.data.add()
                protoItem["caseId"] = case_id
                protoItem["patientId"] = item["patientId"]
                protoItem["name"] = item["name"]
                protoItem["attendCode"] = item["attendCode"]
                protoItem["problemCount"] = item["problemCount"]
                protoItem["forceProblemCount"] = item["forceProblemCount"]
                protoItem["score"] = 100 - item["score"]
                level = "甲" if protoItem["score"] >= 90 else "乙"
                protoItem["level"] = "丙" if protoItem["score"] < 80 else level
                caseCount += 1
                if item["forceProblemCount"] != 0:
                    forceProblemCaseCount += 1
                else:
                    # 不存在强制问题时
                    if doctor_veto and protoItem["score"] < 90:
                        # 开启医生端低于90分不可提交强控时
                        forceProblemCaseCount += 1
                response["data"].append(protoItem)

            response["caseCount"] = caseCount or len(caseIds)
            response["forceProblemCaseCount"] = forceProblemCaseCount

    def send_emr_request(self, url, data):
        """
        发送emr接口请求
        :return:
        """
        try:
            headers = {
                'Content-Type': 'application/json',
            }
            self.logger.info("send_emr_request, url: %s", url)
            self.logger.info("send_emr_request, data: %s", json.dumps(data, ensure_ascii=False))
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code != 200:
                raise ValueError("call %s failed, code: %s, resp: %s" % (url, resp.status_code, resp.text))
            response = resp.json()
            self.logger.info(f'send_emr_request, msg-response: {response}')
            if int(response.get("code", -1)) == 0:
                if response.get("body", {}).get("docId", ""):
                    return response["body"]["docId"]
                return True
        except Exception:
            self.logger.error("send_emr_request, error: %s", traceback.format_exc())
            return False

    def emr_doc_save(self, request, response=None):
        """
        emr文书保存
        :return:
        """
        caseId = request.caseId or ""
        if caseId:
            self.send_qcItem_rule_mq(caseId)
        docId = request.docId or ""
        doctorId = request.doctorId or ""
        if not caseId or not docId or not self.app.qcetlRpcUrl:
            self.logger.info("EMRDocSave.emr_doc_save, caseId: %s, docId: %s, qcetlRpcUrl: %s, not continue", caseId, docId, self.app.qcetlRpcUrl)
            return
        if not doctorId:
            self.logger.info("EMRDocSave.emr_doc_save, not doctorId")

        docId_list = docId.split(",")
        self.logger.info("EMRDocSave.emr_doc_save, docId_list: %s", docId_list)

        # cdss_mq
        for item in docId_list:
            self.send_cdss_mq(caseId, item, '')

        # qcItem 自定义质控点规则
        self.send_qcItem_rule_mq(caseId)

        data = {
            "exchange": "qcetl",
            "routing_key": "emr.doc.save",
            "message": {
                "type": "emr.doc.save",
                "body": {
                    "caseId": caseId,
                    "docId": docId,
                    "doctorId": doctorId,
                    "withActiveAI": True,  # qcetl 保存文书之后发送 qc.ai.active 消息
                },
            },
            "sync": True,
            "timeout": 100,
        }
        self.logger.info("EMRDocSave.emr_doc_save, docId_list: %s", docId_list)
        if len(docId_list) > 1:
            data["routing_key"] = "qc.emr.save"
            data["message"]["type"] = "qc.emr.save"
        res = self.send_emr_request(self.app.qcetlRpcUrl, data)  # 发请求保存
        if res and response:
            response.isSuccess = True

    def emr_doc_part_save(self, request, response):
        """
        emr文书部分保存
        :return:
        """
        if not self.app.aiCacheApi:
            response["isSuccess"] = False
            return
        caseId = request.caseId or ""
        docId = request.docId or ""
        if not caseId or not docId:
            response["isSuccess"] = False
            return
        data = {
            "caseId": caseId,
            "docId": docId,
            "sync": True,
            "timeout": 100,
        }
        res = self.send_emr_request(self.app.aiCacheApi, data)
        self.send_cdss_mq(caseId, docId, '')
        response["isSuccess"] = True if res else False

    def emr_doc_delete(self, request, response):
        """
        emr文书删除
        :return:
        """
        caseId = request.caseId
        docId = request.docId
        if not caseId or not docId:
            response["isSuccess"] = False
            response["message"] = "caseId or docId is None"
            return
        with self.app.mysqlConnection.session() as session:
            for _ in range(3):
                update_doc_delete_sql = '''update emrInfo set is_deleted = 1 where caseId = "%s" and docId = "%s"''' % (
                caseId, docId)
                self.logger.info("emr_doc_delete, update_doc_delete_sql: %s", update_doc_delete_sql)
                session.execute(update_doc_delete_sql)
                select_sql = '''select is_deleted from emrInfo where caseId = "%s" and docId = "%s"''' % (caseId, docId)
                query = session.execute(select_sql)
                queryset = query.fetchone()
                if queryset and queryset[0] == 1:
                    break
            else:
                self.logger.error("emr_doc_delete, update emrInfo is_deleted fail, caseId: %s, docId: %s", caseId,
                                  docId)
            insert_sql = '''insert into message_history (type, caseId, created_at, success, body) values ("{0}", "{1}", "{2}", "{3}", '{4}')'''.format(
                "emr.doc.delete", caseId, arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'), 2,
                json.dumps({"docId": docId}))
            self.logger.info("emr_doc_delete, insert_sql: %s", insert_sql)
            session.execute(insert_sql)
            update_case_problem_sql = '''update caseProblem set is_deleted = 1 where caseId = "%s" and docId = "%s"''' % (
            caseId, docId)
            self.logger.info("emr_doc_delete, update_case_problem_sql: %s", update_case_problem_sql)
            session.execute(update_case_problem_sql)

        if not self.app.qcetlRpcUrl:
            response["isSuccess"] = False
            response["message"] = "qcetlRpcUrl is None"
            return
        data = {
            "exchange": "qcetl",
            "routing_key": "qc.ai.active.api",
            "message": {
                "type": "qc.ai.active.api",
                "body": {
                    "caseId": caseId,
                    "docId": docId
                },
            },
            "sync": True,
            "timeout": 100,
        }
        res = self.send_emr_request(self.app.qcetlRpcUrl, data)
        self.send_cdss_mq(caseId, docId, '')
        response["isSuccess"] = True if res else False

    def query_emr_extract_problem_list(self, request, response):
        """
        查询抽检问题
        :return:
        """
        caseId = request.caseId or ""
        doctor = request.doctor or ""
        sample_data = self.query_sample_data(caseId)
        for sample_info in sample_data:
            protoItem = {"auditInfo": {}, "caseInfo": {}, "problemSummary": {}, "problemList": []}  # response.data.add()
            audit_time = sample_info[0].strftime("%Y-%m-%d") if sample_info[0] else ""
            protoItem["auditInfo"]["time"] = audit_time
            protoItem["auditInfo"]["doctor"] = sample_info[2] or ""
            protoItem["auditInfo"]["action"] = "抽检"
            protoItem["auditInfo"]["auditType"] = sample_info[3]

            operator_id = sample_info[1]
            auditType = sample_info[3]
            problem_data, problemCount = self.query_problem_data_by_audit_type(caseId, auditType)

            title_problem_dict, audit_record_dict, vetoProblemCount, forceProblemCount, myProblemCount, \
                score = self.get_title_problem_dict(problem_data, doctor, protoItem, audit_record_dict=1)

            protoItem["caseInfo"]["caseId"] = caseId
            protoItem["caseInfo"]["score"] = 100 - score
            level = "甲" if protoItem["caseInfo"]["score"] >= 90 else "乙"
            protoItem["caseInfo"]["level"] = "丙" if protoItem["caseInfo"]["score"] < 80 else level

            protoItem["problemSummary"]["vetoProblemCount"] = vetoProblemCount
            protoItem["problemSummary"]["forceProblemCount"] = forceProblemCount
            protoItem["problemSummary"]["problemCount"] = problemCount
            protoItem["problemSummary"]["myProblemCount"] = myProblemCount
            self.unmarshal_problem_info(title_problem_dict, protoItem)
            response["data"].append(protoItem)

    def query_sample_data(self, caseId):
        """
        查询抽检数据
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_sample_info_sql = '''select sr.createdAt, sr.operatorId, sr.operatorName, sr.auditType, sri.caseId
            from sample_record sr
            inner join sample_record_item sri on sr.id = sri.recordId
            where sri.caseId = "%s"''' % caseId
            query = session.execute(query_sample_info_sql)
            sample_data = query.fetchall()
        return sample_data

    def query_problem_data_by_audit_type(self, caseId, auditType):
        """
        查询抽检问题数据
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_problem_sql = '''select distinct cp.id, cp.caseId, cp.reason, cp.comment, cp.score, cp.problem_count, 
            cp.is_fix, cp.is_ignore, cp.appeal, cp.appeal_time, cp.auditType, cp.detail, c.patientId, c.name, 
            c.attendDoctor, c.dischargeTime, c.reviewTime, c.reviewer, qi.veto, cp.doctorCode, cp.from_ai, 
            cp.qcItemId, cp.docId, cp.docId, cp.deduct_flag, c.attendCode, c.status, c.gender, c.age, cp.status, qi.tags, c.inpNo, cp.docId, cp.active_save_flag
            from caseProblem cp 
            left join `case` c on cp.audit_id = c.audit_id
            left join qcItem qi on cp.qcItemId = qi.id 
            where c.caseId = "%s" and cp.is_deleted = 0 and cp.auditType = "%s"''' % (caseId, auditType)

            query = session.execute(query_problem_sql)
            problem_data = query.fetchall()
            problemCount = sum([item[5] for item in problem_data])

        return problem_data, problemCount

    def update_extract_case_is_read(self, request, response=None):
        """
        更新抽检病历已读
        :return:
        """
        case_ids = ','.join(['"%s"' % item for item in request.caseIds])
        with self.app.mysqlConnection.session() as session:
            update_sql = '''update sample_record_item set is_read = 1 where caseId in (%s)''' % case_ids
            self.logger.info("update_extract_case_is_read, update_sql: %s", update_sql)
            session.execute(update_sql)

    def case_submit(self, request, response):
        """
        病历外提交
        :param request:
        :param response:
        :return:
        """
        caseIds = request.caseIds
        doctorId = request.doctor
        if not caseIds or not doctorId:
            response["message"] = "必需参数未传"
            return
        with self.app.mysqlConnection.session() as session:
            query_name_branch_sql = '''select name, branch from doctor where id = "%s"''' % doctorId
            query = session.execute(query_name_branch_sql)
            data = query.fetchone()
            doctorName = data[0] or ""
            branch = data[1] or ""

            caseIds_str = ",".join(['"%s"' % caseId for caseId in caseIds])
            update_case_fix_deadline_sql = '''update `case` set fix_deadline = "2099-12-31 23:59:59" where caseId in (%s)''' % caseIds_str
            session.execute(update_case_fix_deadline_sql)
            # 记录首次提交时间、提交医生
            query_case_apply_sql = '''select caseId from `case` where caseId in (%s) and applyTime is null''' % caseIds_str
            query1 = session.execute(query_case_apply_sql)
            caseIds_str1 = ",".join(['"%s"' % item[0] for item in query1.fetchall()])
            if caseIds_str1:
                update_case_apply_info_sql = '''update `case` set applyTime = "%s", applyDoctor = "%s" where caseId in (%s)''' % (arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'), doctorName, caseIds_str1)
                session.execute(update_case_apply_info_sql)
            session.commit()
        
        if self.app.emrAdapterUrl:
            max_attempts = 3
            for _ in range(max_attempts):
                try:
                    data = {"caseIds": caseIds, "userId": doctorId, "userName": doctorName, "branch": branch}
                    headers = {'Content-Type': 'application/json'}
                    res = requests.post(f"{self.app.emrAdapterUrl}/emr/adapter/submit", headers=headers, json=data).json()
                    response["isSuccess"] = res.get("isSuccess") or True
                    response["message"] = res.get("message") or ""
                    break
                except Exception:
                    logging.error(traceback.format_exc())
                    logging.error("retry submitCase")
        else:
            logging.info(f'{doctorId} 提交申请归档，病历号：{caseIds}. no emrAdapterUrl.')

        for caseId in caseIds:
            self.send_cdss_mq(caseId, '', doctorId)

    def get_case_status(self, caseId):
        """
        查询病历状态
        :param caseId:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_status_sql = '''select status from `case` where caseId = "%s"''' % caseId
            query = session.execute(query_status_sql)
            data = query.fetchone()
            status = data[0] if data else 0
        return status

    def send_cdss_mq(self, caseId, docId, doctor):
        # 发送cdss消息
        self.app.mq.publish(
            {
                'type': 'qc.ai.cdss',
                'body': {
                    'docId': docId,
                    'caseId': caseId,
                    'doctor': doctor
                }
            }
        )

    def send_create_msg(self, request):
        """创建文书发送消息"""
        with self.app.mysqlConnection.session() as session:
            self._messageRepository.send_create_msg(session, request)

    def get_case_cdss_info(self, caseIds):
        url = self.app.cdssAddr + '/cdss/list_info'
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            "data": {
                "case_id": list(caseIds),
            }
        }
        result = dict()
        try:
            data = requests.post(url=url, headers=headers, json=data).json().get('data', {})
            node_data = data.get('node_data', [])
            if node_data:
                for data in node_data:
                    result[data.get('caseId')] = data
            return result
        except Exception as e:
            logging.error('cdss 接口错误：%s caseId %s' % (e, ','.join(list(caseIds))))
        finally:
            return result

    def get_doctor_case_list(self, request, response):
        """
        获取医生病历列表
        :param request:
        :param response:
        :return:
        """
        doctorId = request.doctor
        fixDays = request.time
        with self.app.mysqlConnection.session() as session:
            # 返回诊断列表相关
            if fixDays:
                sql = """select c.caseId,c.admitTime from `case` c  where c.dischargeTime is not null and c.attendCode = '%s'""" % doctorId
                case_dict = dict()
                query_set = session.execute(sql)
                case_objs = query_set.fetchall()
                for obj in case_objs:
                    case_dict[obj[0]] = {"admitTime": obj[1].strftime('%Y-%m-%d %H:%M:%S')}
                case_list = list()
                end_time = arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S')
                start_time = arrow.utcnow().to('+08:00').shift(days=-fixDays).naive.strftime(
                    '%Y-%m-%d %H:%M:%S')
                for caseId, item in case_dict.items():
                    if item['admitTime'] > start_time and item['admitTime'] < end_time:
                        case_list.append("'" + caseId + "'")
                if not case_list:
                    return
                case_list_str = '(' + ','.join(case_list) + ')'
                sql_fpdiagnosis = '''select f.caseId, f.icdname from `fpdiagnosis` f where f.caseId in %s''' % case_list_str
                sql_department = '''select dept.std_name from  doctor d left join department dept on d.department = dept.name where d.id = "%s" ''' % doctorId
                query_fpdiagnosis = session.execute(sql_fpdiagnosis)
                data = query_fpdiagnosis.fetchall()
                query_doctor = session.execute(sql_department)
                department = query_doctor.fetchone()
                if department:
                    department = department[0]
                diagnosis_dict = dict()
                for item in data:
                    if item[1] not in diagnosis_dict:
                        diagnosis_dict[item[1]] = 1
                    else:
                        diagnosis_dict[item[1]] += 1
                sort_result = sorted(diagnosis_dict.items(), key=lambda x: x[1], reverse=True)
                result = [item[0] for item in sort_result]
                response["diagnosis"].extend(result)
                response["department"] = department or ""
                return
            query_case_sql = '''select c.caseId, c.patientId, c.name, c.attendDoctor, c.admitTime, c.reviewTime, c.reviewer, c.status, c.originCaseId, c.gender, c.age, o.oper_code, o.oper_name, o.oper_date, o.oper_doctor from `case` c left join operation o on c.caseId = o.caseId where '''
            filter_str = '''c.attendCode = "%s" and c.dischargeTime is null''' % doctorId
            if not request.isOnlyMy:
                # query_department_sql = '''select deptname from dim_dept_statis where statis_name in (select statis_name from dim_dept_statis dds left join doctor d on dds.deptname = d.department where d.id = "%s")''' % doctorId
                query_department_sql = '''select department from  doctor d where d.id = "%s" ''' % doctorId
                query_department = session.execute(query_department_sql)
                data = query_department.fetchall()
                department = "','".join([d[0] for d in data]) if data else ""
                if department:
                    filter_str = '''c.dischargeTime is null and (c.attendCode = "%s" or c.department in ('%s'))''' % (doctorId, department)
            query_case_sql += filter_str
            self.logger.info("get_doctor_case_list, query_case_sql: %s", query_case_sql)
            query_case = session.execute(query_case_sql)
            data = query_case.fetchall()
            case_dict = {}
            for item in data:
                if item[0] not in case_dict:
                    case_dict[item[0]] = {"caseId": item[0], "patientId": item[1], "name": item[2] or "",
                                          "attendDoctor": item[3],
                                          "admitTime": item[4].strftime("%Y-%m-%d %H:%M:%S") if item[4] else "",
                                          "reviewTime": item[5].strftime("%Y-%m-%d %H:%M:%S") if item[5] else "",
                                          "reviewer": item[6] or "", "status": item[7],
                                          "originCaseId": item[8] or "", "gender": item[9] or "", "age": item[10] or 0,
                                          "operation": [{"code": item[11] or "", "name": item[12] or "",
                                                         "time": item[13] or "", "doctor": item[14] or ""}]}
                else:
                    case_dict[item[0]]["operation"].append({"code": item[11] or "", "name": item[12] or "",
                                                            "time": item[13] or "", "doctor": item[14] or ""})
            # cdss_data = self.get_case_cdss_info(case_dict.keys())
            cdss_message_data, num_dict = self.get_cdss_message(session, list(case_dict.keys()))
            case_tags = self.get_case_tags(session)
            colorInfo = {}
            for caseId, item in case_dict.items():
                # data = cdss_data.get(caseId, {})
                tag_data = cdss_message_data.get(caseId, [])
                protoItem = {"colorInfo": []}  # response.items.add()
                protoItem["caseId"] = caseId
                protoItem["patientId"] = item["patientId"] or ''
                protoItem["name"] = item["name"] or ''
                protoItem["attending"] = item["attendDoctor"] or ''
                protoItem["admitTime"] = item["admitTime"] or ''
                protoItem["reviewTime"] = item["reviewTime"] or ''
                protoItem["reviewer"] = item["reviewer"] or ''
                protoItem["status"] = item["status"] or 0
                protoItem["originCaseId"] = item["originCaseId"] or ''
                protoItem["gender"] = item["gender"] or ''
                protoItem["age"] = item["age"] or 0
                for op in item["operation"]:
                    if op["name"]:
                        opInfo = protoItem.operationInfo.add()
                        opInfo.code = op["code"] or ''
                        opInfo.name = op["name"] or ''
                        opInfo.time = op["time"] or ''
                        opInfo.doctor = op["doctor"] or ''
                protoItem["tipsNum"] = num_dict.get(caseId, 0)
                protoItem["colorInfo"].extend([colorInfo(**{"words": color.get("words", ""), "color": str(self.color_dict.get(color.get("words", ""), 0))}) for color in tag_data if color.get("words", "") in case_tags])
                response["items"].append(protoItem)

    @classmethod
    def get_cdss_message(cls, session, caseIds):
        """
        从cdss_message表获取标签数据
        :return:
        """
        caseIds = ",".join(['"%s"' % item for item in caseIds])
        if not caseIds:
            return defaultdict(list), 0
        query_sql = '''select cm.case_id, cm.params from cdss_messages cm inner join rule_detail rd on cm.rule_code = rd.code where rd.status = 1 and rd.is_deleted = 0 and cm.case_id in (%s)''' % caseIds
        query = session.execute(query_sql)
        data = query.fetchall()
        query_num_sql = '''select cm.case_id, count(distinct cm.id) from cdss_messages cm inner join rule_detail rd on cm.rule_code = rd.code where cm.case_id in (%s) and cm.is_historic = 0 and rd.is_deleted = 0 and rd.status = 1 group by cm.case_id;''' % caseIds
        query_num = session.execute(query_num_sql)
        num_data = query_num.fetchall()
        num_dict = {item[0]: item[1] for item in num_data}
        res = defaultdict(list)
        tmp_words = []
        for item in data:
            params = {}
            if item[1] and isinstance(item[1], (bytes, str)):
                params = json.loads(item[1])
            if isinstance(params, (bytes, str)):
                params = json.loads(params)
            if params.get("color_info", []):
                for item1 in params["color_info"]:
                    if item1.get("words", "") in tmp_words:
                        continue
                    res[item[0]].append(item1)
                    tmp_words.append(item1.get("words", ""))
        return res, num_dict

    @classmethod
    def get_case_tags(cls, session):
        """
        获取患者列表可显示的标签
        :param session:
        :return:
        """
        query_sql = '''select word from cdss_color_info where `use` in (0, 1)'''
        query = session.execute(query_sql)
        return [item[0] for item in query.fetchall()]

    def logDebug(self, request, response):
        """
        医生端debug，记录日志
        """
        if request.caseId == "":
            return
        with self.app.mysqlConnection.session() as session:
            model = DebugLog(caseId=request.caseId, doctor=request.doctor, time=request.time, url=request.url,
                             method=request.method, apiName=request.apiName, apiStatus=request.apiStatus,
                             fileName=request.fileName, content=request.content)
            session.add(model)
            session.commit()
        # response.isSuccess = True

    def send_qcItem_rule_mq(self, caseId):
        """
        发送消息至rule engine 检查自定义质控点规则
        :param caseId:
        :return:
        """
        self.app.mq.publish({"caseId": caseId}, routing_key="qcItem.rule")
        self.logger.info("send_qcItem_rule_mq, caseId: %s success", caseId)

    def get_ip_rule(self, remoteAddr):
        """查询ip规则
        """
        with self.app.mysqlConnection.session() as session:
            model = IpRule
            rule = session.query(model).filter(model.ip == remoteAddr).first()
            if rule:
                return rule.rule or 0
        return 0
