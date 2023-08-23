import json
import logging
import os
import arrow
import html
from . import *
from qcaudit.env_config.pre_req import *
from qcaudit.common.const import *
from qcaudit.service.protomarshaler import *
from qcaudit.config import Config
from qcdbmodel.qcdbmodel.models.qcevent import CaseEvent, DoctorActionLog
from qcdbmodel.qcdbmodel.models.basedata import Case as CaseInfo
from rabbitmqlib.rabbitmqlib.message import Message


class ReceiveEvent(MyResource):

    @pre_request(request, ReceiveEventReq)
    def post(self):
        """通用接收消息推送接口，给第三方用，兰溪人民医院
        """
        response = {}
        try:
            event = CaseEvent()

            event.patientId = request.patientId
            event.visitId = request.caseId
            event.docFlowId = request.docId
            event.eventType = request.eventType
            event.operationId = request.operationId
            event.operationName = request.operationName
            event.operationTime = request.operationTime

            mq_type = ""
            mq_body = {}
            if event.eventType == "文书保存":
                # 提交文书
                mq_type = "emr.doc.save"
                mq_body = {
                    "patientId": event.patientId,
                    "caseId": event.visitId,
                    "docId": event.docFlowId,
                    "OperationId": event.operationId,
                    "OperationName": event.operationName,
                    "OperationTime": event.operationTime
                }
            elif event.eventType == "重新申请":
                # 归档申请
                mq_type = "emr.archive"
                mq_body = {
                    "patientId": event.patientId,
                    "caseId": event.visitId,
                    "OperationId": event.operationId,
                    "OperationName": event.operationName,
                    "OperationTime": event.operationTime
                }
            elif event.eventType == "申请归档" or event.eventType == "病案室签收":
                # 归档申请
                mq_type = "emr.archive"
                mq_body = {
                    "patientId": event.patientId,
                    "caseId": event.visitId,
                    "OperationId": event.operationId,
                    "OperationName": event.operationName,
                    "OperationTime": event.operationTime
                }
            elif event.eventType == "病历提交":
                # 兰溪临床医生提交申请
                mq_type = "emr.archive.apply"
                mq_body = {
                    "patientId": event.patientId,
                    "caseId": event.visitId,
                    "OperationId": event.operationId,
                    "OperationName": event.operationName,
                    "OperationTime": event.operationTime
                }
            elif event.eventType == "文书取消":
                # 文书取消
                mq_type = "emr.doc.cancel"
                mq_body = {
                    "patientId": event.patientId,
                    "caseId": event.visitId,
                    "docId": event.docFlowId,
                    "OperationId": event.operationId,
                    "OperationName": event.operationName,
                    "OperationTime": event.operationTime
                }
            elif event.eventType == "撤销申请" or event.eventType == "取消签收":
                # 归档申请撤回
                mq_type = "emr.archive.cancel"
                mq_body = {
                    "patientId": event.patientId,
                    "caseId": event.visitId,
                    "OperationId": event.operationId,
                    "OperationName": event.operationName,
                    "OperationTime": event.operationTime
                }
            # else:
            #     # 比如出院，取消出院，只需要同步数据
            #     mq_type = "qc.archive"
            #     mq_body = {
            #         "patientId": event.patientId,
            #         "caseId": event.visitId,
            #         "OperationId": event.operationId,
            #         "OperationName": event.operationName,
            #         "OperationTime": event.operationTime
            #     }
            message = Message({
                "type": mq_type,
                "body": mq_body
            })
            # 传参保存到数据库
            with self.app.mysqlConnection.session() as session:
                session.add(event)
                session.commit()
            try:
                if mq_type:
                    self.app.producer.publish(message, exchange="qcetl", routingKey=mq_type)
            except Exception as e:
                self.logger.error("publish failed, err: " + str(e))

            response["isSuccess"] = "1"
            response["message"] = "处理成功"

        except Exception as e:
            response["isSuccess"] = "0"
            response["message"] = "处理失败"
            self.logger.error("save event failed, err: %s" % str(e))
        return response


class ReceiveActionEvent(MyResource):

    @pre_request(request, ReceiveActionEventReq)
    def post(self):
        """通用消息接口，给医生端用
        """
        response = {}
        if request.action == "" or request.doctorId == "":
            response["isSuccess"] = "0"
            response["message"] = "参数错误"
            return response
        try:
            logging.info(request.params)
            # 记录医生端操作日志
            action = DoctorActionLog()
            params = dict()
            if request.params:
                if isinstance(request.params, str):
                    params = json.loads(html.unescape(request.params))  # params 字段是 json 字符串
                else:
                    params = dict(request.params)
            if not params and request.options:
                if isinstance(request.options, str):
                    params = json.loads(html.unescape(request.options))  # params 字段是 json 字符串
                else:
                    params = dict(request.options)
            now = arrow.utcnow().to('+08:00')
            action.patientId = params.get('patientId', '')
            action.caseId = params.get('caseId', '')
            action.params = params
            action.action = request.action
            action.doctorId = request.doctorId
            action.doctorName = request.doctorName
            action.deptCode = request.deptCode or request.departmentId
            action.deptName = request.deptName or request.departmentName
            action.created_at = now.naive.strftime('%Y-%m-%d %H:%M:%S')

            # 构造 mq 消息内容，type 是 rabbitmq.routing_key
            mq_type = f'qcetl.action.{request.action}'
            mq_body = dict(params)
            mq_body['doctorId'] = action.doctorId
            mq_body['doctorName'] = action.doctorName
            mq_body['deptCode'] = action.deptCode
            mq_body['deptName'] = action.deptName
            # mq_body['timestamp'] = now.timestamp()
            mq_body['isActive'] = True
            # 消息内容
            message = Message({"type": mq_type, "body": mq_body})

            # 传参保存到数据库
            with self.app.mysqlConnection.session() as session:
                session.add(action)
                session.commit()

            # 创建文书的动作发送消息给消息中心 exchange=qcaudit
            if request.action == "createDoc":
                self.send_createdoc_message(request.doctorId, params.get('caseId', ''), params.get("documentName", ""))
            # 初始化病历操作
            if request.action == "initCase":
                mq_type = "qc.archive"
            # 发送消息给 mq
            if mq_type:
                self.app.producer.publish(message, exchange="qcetl", routingKey=mq_type)

            response["isSuccess"] = "1"
            response["message"] = "处理成功"
        except Exception as e:
            response["isSuccess"] = "0"
            response["message"] = "处理失败"
            self.logger.error("save event failed, err: %s" % str(e))
        return response

    def send_createdoc_message(self, doctor, caseId, emrname):
        """创建文书消息"""
        message = {
            "exchange": "qcaudit",
            "project": "病历质控",
            "title": "病历质控提醒",
            "messageType": "创建文书",
            "tipType": 1,
            "caseId": caseId,
            "send_user": doctor,
            "receive_user": doctor,
            "emrName": emrname or "",
            "send_time": arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S'),
        }
        with self.app.mysqlConnection.session() as session:
            case_info = session.query(CaseInfo).filter(CaseInfo.caseId == caseId).first()
            if not case_info:
                logging.info(f"caseInfo not found, caseId=[{caseId}]")
                return False
            message["message"] = f"【{case_info.name}】{emrname}创建成功！点击查看《{emrname}》质控规则"
            message["name"] = case_info.name
            message["patientType"] = case_info.patientType or '2'
        message = Message(message)
        self.app.producer.publish(message=message, exchange="qcaudit", routingKey="socket_queue")


class ReceiveDataHZh(MyResource):

    @pre_request(request, ["args:dict"])
    def post(self):
        """接口：湖州云病历接收病历数据
        """
        response = {}
        try:
            event = CaseEvent()

            event.patientId = ""
            event.visitId = ""
            event.eventType = "申请归档"
            event.operationId = ""
            event.operationName = ""
            event.operationTime = arrow.utcnow().to('+08:00').naive.strftime('%Y-%m-%d %H:%M:%S')
            args = request.args
            event.docFlowId = args.get('businessPkid')

            mq_type = "emr.archive"
            message = Message({
                "type": mq_type,
                "body": {
                    "caseId": event.docFlowId
                }
            })
            # 传参保存到数据库
            with self.app.mysqlConnection.session() as session:
                session.add(event)
                session.commit()

            self.app.producer.publish(message, exchange="qcetl", routingKey=mq_type)
            response["code"] = "10000"
            response["message"] = "操作成功"

        except Exception as e:
            response["code"] = "10001"
            response["message"] = "处理失败"
            self.logger.error("save event failed, err: %s" % str(e))
        return response
    

