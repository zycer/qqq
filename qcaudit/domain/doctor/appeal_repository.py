#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@Author: zhangda@rxthinking.com
@file: appeal_repository.py
@time: 2021/10/12 3:03 下午
@desc:
"""
import logging
import traceback
from datetime import datetime

from dateutil import tz
from sqlalchemy import func, and_

from qcaudit.domain.message.message_repository import MessageRepo
from qcaudit.domain.domainbase import DomainBase
from qcaudit.domain.repobase import RepositoryBase


class AppealInfo(DomainBase):

    TABLE_NAME = 'appeal_info'

    def __init__(self, model):
        super().__init__(model)


class AppealRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.logger = logging.getLogger("qcaudit.appeal")
        self.appeal_model = app.mysqlConnection["appeal_info"]
        self.case_model = app.mysqlConnection["case"]
        self.problem_model = app.mysqlConnection["caseProblem"]
        self.doctor_model = app.mysqlConnection["doctor"]
        self._messageRepository = MessageRepo(app, auditType)

    def query_not_read_count(self, request, response):
        """
        查询未读申诉个数
        :param request:
        :param response:
        :return:
        """
        doctor_id = request.doctorId or ""

        with self.app.mysqlConnection.session() as session:
            total = session.query(self.appeal_model.id).join(
                self.case_model, self.appeal_model.caseId == self.case_model.caseId, isouter=False).filter(
                self.appeal_model.is_deleted == 0, self.appeal_model.is_read == 0,
                self.appeal_model.must_read_user == doctor_id).count()
        response["total"] = total or 0

    def get_not_read_case_list(self, request, response):
        """
        查询未读消息病历列表
        :return:
        """
        doctor_id = request.doctorId or ""

        with self.app.mysqlConnection.session() as session:
            query = session.query(self.appeal_model.caseId, self.case_model.patientId, self.case_model.name,
                                  self.case_model.department, self.case_model.wardName, self.case_model.inpNo,
                                  func.count(self.appeal_model.id).label('cc')).join(
                self.case_model, self.appeal_model.caseId == self.case_model.caseId, isouter=False).filter(
                self.appeal_model.is_deleted == 0, self.appeal_model.is_read == 0,
                self.appeal_model.must_read_user == doctor_id).group_by(
                self.appeal_model.caseId, self.case_model.patientId, self.case_model.name, self.case_model.department,
                self.case_model.wardName).order_by(func.count(self.appeal_model.id).desc())

            res = query.all()
        for item in res:
            protoItem = {}  # response.data.add()
            protoItem["caseId"] = item.caseId or ""
            protoItem["patientId"] = item.inpNo or item.patientId or ""
            protoItem["name"] = item.name or ""
            protoItem["department"] = item.department or ""
            protoItem["inpatientArea"] = item.wardName or ""
            protoItem["count"] = item.cc or 0
            response["data"].append(protoItem)

    def get_problem_list(self, request, response):
        """
        获取申诉问题列表
        :param request:
        :param response:
        :return:
        """
        caseId = request.caseId or ""
        doctor_id = request.doctorId or request.doctorCode or ""

        with self.app.mysqlConnection.session() as session:
            query = session.query(
                self.problem_model.id, self.problem_model.reason, self.problem_model.comment,
                self.problem_model.refuseTime, self.problem_model.qcItemId, self.problem_model.docId).join(
                self.appeal_model, and_(
                    self.problem_model.qcItemId == self.appeal_model.qcItemId,
                    self.problem_model.docId == self.appeal_model.doc_id,
                    self.problem_model.caseId == self.appeal_model.caseId)).filter(
                self.problem_model.caseId == caseId, self.problem_model.is_deleted == 0)
            if request.auditType:
                query = query.filter(self.problem_model.auditType == request.auditType)
            query = query.group_by(
                self.problem_model.id, self.problem_model.qcItemId, self.problem_model.docId).order_by(
                self.problem_model.refuseTime.desc())
            self.logger.info("get_problem_list, query: %s", query)
            res = query.all()
            reason_dict = {item.reason: item.refuseTime for item in res if item.refuseTime}
            reason_count_dict = {}
            for item in res:
                if item.reason not in reason_count_dict:
                    reason_count_dict[item.reason] = 0
                reason_count_dict[item.reason] += 1

            problem_ids = [str(item.id) for item in res]
            have_read_dict = {}
            appeal_create_time_dict = {}
            if problem_ids:
                query_doctor_have_not_read = session.query(
                    self.appeal_model.problem_id, func.count(self.appeal_model.id).label("c")).filter(
                    self.appeal_model.problem_id.in_(problem_ids), self.appeal_model.is_read == 0,
                    self.appeal_model.is_deleted == 0, self.appeal_model.must_read_user == doctor_id).group_by(
                    self.appeal_model.problem_id)
                res1 = query_doctor_have_not_read.all()
                have_read_dict = {item.problem_id: item.c for item in res1}
                query_appeal_create_time = session.query(
                    self.appeal_model.id, self.appeal_model.problem_id, self.appeal_model.create_time).filter(
                    self.appeal_model.problem_id.in_(problem_ids), self.appeal_model.is_deleted == 0)
                res2 = query_appeal_create_time.all()
                appeal_create_time_dict = {item.problem_id: item.create_time.strftime("%Y-%m-%d %H:%M:%S") for item in res2}
        data = []
        have_read_data = []
        for item in res:
            if reason_count_dict.get(item.reason, 0) > 1:
                reason_count_dict[item.reason] -= 1
                continue
            is_read = 1 if have_read_dict.get(item.id, 0) > 0 else 0
            tmp = {"problemId": str(item.id or ""), "reason": item.reason or "", "comment": item.comment or "",
                   "time": reason_dict[item.reason].strftime("%Y-%m-%d") if reason_dict.get(item.reason, None) else "",
                   "isRead": is_read, "create_time": appeal_create_time_dict.get(item.id, "")}
            if is_read == 1:
                have_read_data.append(tmp)
                continue
            data.append(tmp)
        data = sorted(data, key=lambda data: data["create_time"], reverse=True)
        for item in have_read_data:
            data.insert(0, item)
        for item in data:
            protoItem = {}  # response.problemData.add()
            protoItem["problemId"] = item["problemId"]
            protoItem["reason"] = item["reason"]
            protoItem["comment"] = item["comment"]
            protoItem["time"] = item["time"]
            protoItem["isRead"] = item["isRead"]
            response["problemData"].append(protoItem)

    def get_appeal_detail(self, request, response):
        """
        获取申诉问题详情
        :param request:
        :param response:
        :return:
        """
        problem_id = request.problemId or 0
        caseId = request.caseId or ""
        doctorId = request.doctorId or ""

        with self.app.mysqlConnection.session() as session:
            query_item_doc_id = session.query(self.problem_model.qcItemId, self.problem_model.docId).filter(
                self.problem_model.id == request.problemId)
            self.logger.info("get_appeal_detail, query_item_doc_id: %s", query_item_doc_id)
            res1 = query_item_doc_id.all()
            if not res1:
                return response
            qcItemId = res1[-1].qcItemId
            docId = res1[-1].docId
            query = session.query(
                self.appeal_model.id, self.appeal_model.appeal_doctor, self.appeal_model.department,
                self.appeal_model.create_time, self.appeal_model.content, self.appeal_model.doctor_id).filter(
                self.appeal_model.caseId == caseId, self.appeal_model.qcItemId == qcItemId,
                self.appeal_model.doc_id == docId, self.appeal_model.is_deleted == 0)
            self.logger.info("get_appeal_detail, query: %s", query)
            res = query.all()
        can_delete_appeal_id = 0
        if res and res[-1].doctor_id == doctorId:
            can_delete_appeal_id = res[-1][0]
        for item in res:
            protoItem = {}  # response.appealData.add()
            protoItem["appealId"] = str(item.id or "")
            protoItem["appealDoctor"] = item.appeal_doctor or ""
            protoItem["department"] = item.department or ""
            protoItem["appealTime"] = item.create_time.strftime("%Y-%m-%d %H:%M:%S")
            protoItem["content"] = item.content or ""
            protoItem["appealDoctorId"] = item.doctor_id or ""
            if can_delete_appeal_id and can_delete_appeal_id == item.id:
                protoItem["canDelete"] = 1
            response["appealData"].append(protoItem)
        response["problemId"] = problem_id

    def create(self, request, response):
        """
        申诉创建
        :param request:
        :param response:
        :return:
        """
        doctor_id = request.doctorId or ""
        doctorName = request.doctorName or ""
        is_send = 0  # 是否发送消息通知
        try:
            with self.app.mysqlConnection.session() as session:
                query_item_doc_id = session.query(
                    self.problem_model.qcItemId, self.problem_model.docId, self.problem_model.operator_id,
                    self.problem_model.reason, self.problem_model.doctorCode).filter(
                    self.problem_model.id == request.problemId)
                res1 = query_item_doc_id.first()
                if not res1:
                    response["message"] = "问题ID不存在"
                    response["isSuccess"] = "False"
                    return response
                qcItemId = res1.qcItemId
                docId = res1.docId
                operator_id = res1.operator_id
                query_is_exist = session.query(self.appeal_model.doctor_id).filter(
                    self.appeal_model.qcItemId == qcItemId, self.appeal_model.doc_id == docId).order_by(
                    self.appeal_model.create_time)
                res2 = query_is_exist.all()
                doctor_id_list = [item[0] for item in res2]
                query = session.query(
                    self.case_model.patientId, self.case_model.name, self.case_model.department,
                    self.case_model.reviewerId, self.case_model.attendCode, self.problem_model.qcItemId,
                    self.problem_model.docId, self.case_model.patientType, self.case_model.inpNo).join(
                    self.problem_model, and_(self.case_model.caseId == self.problem_model.caseId,
                                             self.problem_model.qcItemId == qcItemId,
                                             self.problem_model.docId == docId)).filter(
                    self.case_model.caseId == request.caseId)
                res = query.first()
                must_read_user = ""
                if doctor_id_list:
                    # 当存在评论时，取上一条非本人评论, 且医生端取管理端医生, 管理端取医生端的doctor_id
                    for index in range(len(doctor_id_list) - 1, -1, -1):
                        new_doctor_id = doctor_id_list[index]
                        if new_doctor_id != doctor_id:
                            if len(doctor_id) > 10:
                                if len(new_doctor_id) < 10:
                                    must_read_user = new_doctor_id
                                    break
                            else:
                                if len(new_doctor_id) > 10:
                                    must_read_user = new_doctor_id
                                    break
                    else:
                        self.logger.info("appeal create have old appeal no new must_read_user")
                if not must_read_user:
                    if not doctorName:
                        # 医生端初次申诉
                        if operator_id and operator_id.upper() != "大数AI":
                            # 当不存在申诉时，优先取caseProblem.operator_id
                            must_read_user = operator_id
                        else:
                            # 当不存在operator_id或为大数AI时，取case.reviewerId
                            must_read_user = res.reviewerId
                    else:
                        # 管理端初次申诉
                        if res1.doctorCode:
                            # 存在驳回医生直接申诉给驳回医生
                            must_read_user = res1.doctorCode
                        else:
                            # 无驳回医生时申诉给责任医生
                            must_read_user = res.attendCode

                if not doctorName:
                    # 未传申诉医生姓名，说明是医生端申诉，需查询医生姓名+科室
                    query_doctor_department = session.query(
                        self.doctor_model.department, self.doctor_model.name).filter(
                        self.doctor_model.id == doctor_id).first()
                    department = res.department
                    doctorName = "--"
                    if query_doctor_department:
                        doctorName = query_doctor_department.name or doctorName
                        department = query_doctor_department.department or department
                else:
                    # 管理端仅查询申诉医生科室
                    query_doctor_department = session.query(
                        self.doctor_model.department).filter(self.doctor_model.name == doctorName).first()
                    department = res.department
                    if query_doctor_department:
                        department = query_doctor_department.department or department
                    is_send = 1

                now = self.getLocalNowTime()
                create_time = now.strftime("%Y-%m-%d %H:%M:%S")
                obj = AppealInfo.newObject(self.app)
                obj.setModel(
                    caseId=request.caseId,
                    qcItemId=res.qcItemId,
                    appeal_doctor=doctorName,
                    content=request.content,
                    problem_id=request.problemId,
                    department=department,
                    doc_id=res.docId,
                    patientId=res.patientId,
                    doctor_id=doctor_id,
                    must_read_user=must_read_user,
                    create_time=create_time,
                )
                self.add(session, obj)
                self.logger.info("AppealCreate, insert success")

            response["isSuccess"] = True
        except Exception:
            self.logger.error("AppealCreate, error: %s", traceback.format_exc())
            response["message"] = "申诉失败"
            response["isSuccess"] = False
        if is_send:
            self._messageRepository.send_new_appeal(request.caseId, res.qcItemId, doctorName, request.content,
                                                    request.problemId, must_read_user, res.inpNo or res.patientId, res.name, res1.reason, res.patientType)

    @classmethod
    def getLocalNowTime(cls):
        """
        指定时区避免时间异常
        """
        tz_sh = tz.gettz('Asia/Shanghai')
        now = datetime.now(tz=tz_sh)
        return now

    def delete(self, request, response):
        """
        申诉删除
        :param request:
        :param response:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query = session.query(self.appeal_model.id).filter(
                self.appeal_model.id == request.appealId, self.appeal_model.doctor_id == request.doctorId)
            res = query.first()
            if not res:
                response["isSuccess"] = False
                response["message"] = "申诉ID不存在或申诉人不匹配"
                return response
            appeal = self.get_appeal(session, request.appealId)
            appeal.setModel(
                is_deleted=1,
            )
            session.commit()
            self.logger.info("appeal delete success, id: %s", request.appealId)
        response["isSuccess"] = True

    def get_appeal(self, session, appeal_id):
        """
        根据id查申诉对象
        :return:
        """
        queryset = session.query(self.appeal_model).filter(self.appeal_model.id == appeal_id).first()
        return AppealInfo(queryset)

    def get_appeal_read(self, session, qcItemId, docId, must_read_user):
        """
        更新已读申诉查询对象
        :return:
        """
        queryset = session.query(self.appeal_model).filter(
            self.appeal_model.qcItemId == qcItemId, self.appeal_model.doc_id == docId,
            self.appeal_model.must_read_user == must_read_user).all()
        for item in queryset:
            yield AppealInfo(item)

    def update_read(self, request, response):
        """
        更新申诉已读
        :param request:
        :param response:
        :return:
        """
        problem_id = request.problemId
        with self.app.mysqlConnection.session() as session:
            query_item_doc_id = session.query(self.problem_model.qcItemId, self.problem_model.docId).filter(
                self.problem_model.id == problem_id)
            res1 = query_item_doc_id.first()
            if not res1:
                response["message"] = "问题ID不存在"
                response["isSuccess"] = False
                return response
            qcItemId = res1.qcItemId
            docId = res1.docId
            query_is_exist = session.query(self.appeal_model.id).filter(
                self.appeal_model.qcItemId == qcItemId, self.appeal_model.doc_id == docId,
                self.appeal_model.is_read == 0, self.appeal_model.must_read_user == request.doctorId)
            res2 = query_is_exist.first()
            if not res2:
                response["message"] = "未读申诉不存在或应读医生不符合"
                response["isSuccess"] = False
                return response
            for appeal in self.get_appeal_read(session, qcItemId, docId, request.doctorId):
                appeal.setModel(
                    is_read=1,
                )
            session.commit()
            self.logger.info("appeal update read success, problem id: %s", problem_id)
        response["isSuccess"] = True

    def modify(self, request, response):
        """
        修改申诉信息
        :param request:
        :param response:
        :return:
        """
        with self.app.mysqlConnection.session() as session:
            query_is_exist = session.query(self.appeal_model.id).filter(
                self.appeal_model.doctor_id == request.doctorId, self.appeal_model.id == request.appealId).first()
            if not query_is_exist:
                response["message"] = "申诉不存在或不可修改"
                response["isSuccess"] = False
                return response
            appeal = self.get_appeal(session, request.appealId)
            appeal.setModel(
                content=request.content,
            )
            session.commit()
            self.logger.info("appeal modify success, id: %s", request.appealId)
        response["isSuccess"] = True

    def get_appeal_dict(self, problem_id_list, caseId=""):
        """
        查询是否有申诉
        :return:
        """
        have_appeal_dict = {}
        with self.app.mysqlConnection.session() as session:
            query_must_user = session.query(self.appeal_model.problem_id, self.appeal_model.must_read_user).filter(self.appeal_model.problem_id.in_(problem_id_list), self.appeal_model.is_read == 0, self.appeal_model.is_deleted == 0).all()
            problem_not_read_dict = {}
            for item in query_must_user:
                if item.must_read_user and len(item.must_read_user) > 10:
                    problem_not_read_dict[item.problem_id] = 1
            query = session.query(self.problem_model.id, func.count(self.appeal_model.id).label('cc')).join(
                self.appeal_model, and_(self.problem_model.qcItemId == self.appeal_model.qcItemId,
                                        self.problem_model.docId == self.appeal_model.doc_id)).filter(
                self.problem_model.id.in_(problem_id_list), self.appeal_model.caseId == caseId).group_by(self.problem_model.id)
            data = query.all()
            for item in data:
                c = item.cc or 0
                have_appeal = 1 if c > 0 else 0
                have_not_read_appeal = problem_not_read_dict.get(item.id, 0)
                have_appeal_dict[item.id] = [have_appeal, have_not_read_appeal]
        return have_appeal_dict
