from qcaudit.app import Application
from qcaudit.common.const import EXPORT_FILE_AUDIT_TYPE
from qcaudit.domain.case.caserepository import CaseRepository
from qcaudit.domain.audit.refusehistoryrepository import RefuseHistoryRepository
from qcaudit.domain.audit.auditrecord import AuditRecord
from qcaudit.domain.problem.problem import Problem
from qcaudit.service.protomarshaler import parseRating
from sqlalchemy import func
from datetime import datetime
import arrow
import logging


class MessageRepo(object):
	exchange = 'qcaudit'
	routing_key = 'socket_queue'

	def __init__(self, app: Application, auditType):
		self.app = app
		self.auditType = auditType
		self._caseRepo = CaseRepository(self.app, auditType)
		self._refuseHistoryRepository = RefuseHistoryRepository(app, auditType)
		self.logger = logging.getLogger(__name__)

	def send(self, context={}):
		"""
		发送消息
		context:
			{
				"caseId":caseId
				"send_user": "",
				"message": "",
				"receive_user":"",
				"tipType":, #1-闪退, 2-常驻, 3-拦截
			}
		"""
		message = {
			**context,
			'send_time': arrow.utcnow().to('+08:00').strftime('%Y-%m-%d %H:%M:%S'),
			'title': '病历质控提醒',
			"project": "病历质控",
		}
		self.app.mq.publish(
			exchange=self.exchange,
			routing_key=self.routing_key,
			message=message
		)
		self.logger.info("MessageRepository.sendMessage, message: %s", message)

	def send_refuse_msg(self, case_info, inDays, send_user, lost_score, refuseDoctors, auditType, action):
		"""退回整改发送消息"""
		auditRecord = AuditRecord(case_info.auditRecord)
		msg = "【{name}】被{auditType}质控节点{action}，总扣分{score}分，{level}级。整改时限{fixDays}天！".format(
			auditType=EXPORT_FILE_AUDIT_TYPE.get(auditType, ""),
			name=case_info.name,
			action=action,
			score="%.1f" % lost_score,
			fixDays=inDays,
			level=parseRating(auditRecord.getScore(self.auditType))
		)
		for receive_user in refuseDoctors:
			message = {
				"caseId": case_info.caseId,
				"send_user": send_user,
				"message": msg,
				"receive_user": receive_user,
				"tipType": 1,
				"messageType": "质控退回",
				"name": case_info.name,
				"patientType": case_info.patientType or 2,
			}
			self.send(message)

	def send_new_appeal(self, caseId, qcItemId, send_user, content, problemId, receive_user, patientId, name, reason, patientType):
		"""
		新申诉 发送消息
		:return:
		"""
		content = "【问题沟通回复】{doctorName}: {content}".format(doctorName=send_user, content=content)
		message = {
			"caseId": caseId,
			"send_user": send_user,
			"message": content,
			"receive_user": receive_user,
			"qcItemId": qcItemId,
			"problemId": problemId,
			"problemReason": reason,
			"tipType": 1,
			"patientId": patientId,
			"messageType": "问题沟通回复",
			"name": name,
			"patientType": patientType,
		}
		self.send(message)

	def send_approve_message(self, session, case_info, send_user, auditType):
		"""
		专家质控完成 发送消息
		:return:
		"""
		problemModel = Problem.getModel(self.app)
		s = session.query(func.sum(problemModel.score).label("s")).filter(
			problemModel.caseId == case_info.caseId, problemModel.is_deleted == 0,
			problemModel.auditType == auditType).scalar()
		s = float(s or 0)
		content = "【{name}】被{auditType}质控节点抽检, 总扣分{s}分, {level}级。".format(
			auditType=EXPORT_FILE_AUDIT_TYPE.get(auditType, ""),
			name=case_info.name,
			s="%.1f" % s,
			level=parseRating(100 - s)
		)
		message = {
			"caseId": case_info.caseId,
			"send_user": send_user,
			"message": content,
			"receive_user": case_info.attendCode,
			"tipType": 1,
			"messageType": "质控抽检",
			"name": case_info.name,
			"patientType": case_info.patientType or 2,
		}
		self.send(message)

	def send_create_msg(self, session, request):
		"""创建文书消息"""
		case_info = self._caseRepo.getByCaseId(session, request.caseId)
		name = ''
		if case_info:
			name = case_info.name
		content = "【{name}】{emrName}创建成功！点击查看《{emrName}》质控规则".format(
			name=name,
			emrName=request.emrName
		)
		message = {
			"caseId": case_info.caseId,
			"send_user": request.doctorId,
			"message": content,
			"receive_user": request.doctorId,
			"tipType": 1,
			"messageType": "创建文书",
			"emrName": request.emrName or "",
			"name": case_info.name,
			"patientType": case_info.patientType or 2,
		}
		self.send(message)
