# coding: utf-8
"""
qcevent 相关的表结构

"""
from sqlalchemy import Column, DateTime, JSON, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import INTEGER

from sqlalchemylib.sqlalchemylib.connection import Base


class CaseEvent(Base):
    __tablename__ = 'caseEvent'
    __table_args__ = {
        'comment': '消息接口日志记录表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    patientId = Column(String(255))
    visitId = Column(String(255), comment="就诊号")
    docFlowId = Column(String(255))
    eventObject = Column(String(255))
    eventType = Column(String(255))
    eventStatus = Column(String(255))
    operationId = Column(String(255))
    operationName = Column(String(255))
    operationTime = Column(String(255))
    status = Column(INTEGER(11), server_default='0')
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    is_deleted = Column(INTEGER(11))


class DoctorActionLog(Base):
    __tablename__ = 'doctor_action_log'

    id = Column(INTEGER(11), primary_key=True)
    patientId = Column(String(255))
    caseId = Column(String(255))
    action = Column(String(255), comment="action")
    doctorId = Column(String(255), comment="医生编号")
    doctorName = Column(String(255), comment="医生姓名")
    deptCode = Column(String(255), comment="科室编号")
    deptName = Column(String(255), comment="科室名称")
    params = Column(JSON, comment="具体调用参数")
    created_at = Column(DateTime)
