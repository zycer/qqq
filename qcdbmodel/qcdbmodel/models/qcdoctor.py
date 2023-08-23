# coding: utf-8
"""
医生端相关的表结构

"""

from sqlalchemy import Column, DateTime, String, Text, text, Index
from sqlalchemy.dialects.mysql import BIGINT, INTEGER

from sqlalchemylib.sqlalchemylib.connection import Base


class AppealInfo(Base):
    __tablename__ = 'appeal_info'
    __table_args__ = {
        'comment': '申诉详情表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), nullable=False)
    patientId = Column(String(255), nullable=False, comment='患者id')
    qcItemId = Column(INTEGER(11), nullable=False, server_default='0', comment='质控点id')
    doc_id = Column(String(255), nullable=False, comment='文书id')
    appeal_doctor = Column(String(255), nullable=False, comment='申诉医生')
    doctor_id = Column(String(255), nullable=False, comment='申诉医生id')
    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    update_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                         comment='更新时间')
    content = Column(Text, comment='申诉内容')
    is_deleted = Column(INTEGER(2), nullable=False, server_default='0', comment='是否被删除, 默认0-未删除, 1-已删除')
    problem_id = Column(BIGINT(20), nullable=False, server_default='0', comment='问题id')
    is_read = Column(INTEGER(2), nullable=False, server_default='0', comment='是否已读, 0-未读, 1-已读')
    department = Column(String(255), nullable=False, comment='申诉人科室')
    must_read_user = Column(String(255), nullable=False, comment='该申诉必读用户(该用户已读后更新为已读状态)')

    Index("appeal_info_caseId_index", caseId, unique=False)
    Index("appeal_info_qcItemId_index", qcItemId, unique=False)
    Index("appeal_info_doc_id_index", doc_id, unique=False)


class DoctorSetting(Base):
    __tablename__ = 'doctor_setting'

    id = Column(INTEGER(11), primary_key=True)
    doctor = Column(String(64))
    tip_setting = Column(INTEGER(11))
    date = Column(BIGINT(20))


class IpRule(Base):
    __tablename__ = 'ip_rule'
    __table_args__ = {
        'comment': '医生端黑白名单设置',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    ip = Column(String(255), unique=True)
    rule = Column(INTEGER(11), server_default='0', comment="ip策略类型，1=黑名单，2=白名单")
    created_at = Column(DateTime)


class DoctorDebugLog(Base):
    __tablename__ = 'doctor_debug_log'

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), index=True)
    doctor = Column(String(255))
    time = Column(String(255))
    url = Column(Text)
    method = Column(String(255))
    apiName = Column(String(255))
    apiStatus = Column(String(255))
    fileName = Column(String(255))
    content = Column(Text)
    created_at = Column(DateTime)

