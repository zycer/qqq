# coding: utf-8
"""
首页智能编码

"""
from sqlalchemy import Column, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import INTEGER

from sqlalchemylib.sqlalchemylib.connection import Base


class DiagnosisInfo(Base):
    __tablename__ = 'diagnosis_info'
    __table_args__ = {
        'comment': '智能编码-诊断信息表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(64), index=True, comment='病历id')
    isPrimary = Column(INTEGER(2), server_default='0', comment='是否为主诊断标记, 0-否, 1-是')
    code = Column(String(32), comment='诊断ICD编码')
    name = Column(String(255), comment='诊断名称')
    originName = Column(String(255), comment='原始诊断名称')
    situation = Column(String(255), comment='入院病情')
    returnTo = Column(String(255), comment='治疗转归')
    is_deleted = Column(INTEGER(11), server_default='0', comment='是否删除标记, 1-是')
    coder = Column(String(64), comment='编码员')
    coder_id = Column(String(64), comment='编码员id')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    update_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                         comment='更新时间')
    type = Column(INTEGER(2), nullable=False, server_default='0', comment='诊断类型, 默认0-诊断, 1-病理诊断, 2-损伤/中毒诊断')
    orderNum = Column(INTEGER(11), comment='排序序号')


class DiagnosisOriginDict(Base):
    __tablename__ = 'diagnosis_origin_dict'
    __table_args__ = {
        'comment': '诊断-原始诊断对照表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(64), comment='诊断ICD编码')
    name = Column(String(255), comment='诊断名称')
    originName = Column(String(255), index=True, comment='原始诊断名称')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))


class FpInfo(Base):
    __tablename__ = 'fp_info'
    __table_args__ = {
        'comment': '编码作业信息表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(32), index=True, comment='病历id')
    coder = Column(String(32), comment='编码员')
    coder_id = Column(String(255), comment='编码员id')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    code_time = Column(TIMESTAMP, comment='编码时间')


class MiDiagnosisDict(Base):
    __tablename__ = 'mi_diagnosis_dict'
    __table_args__ = {
        'comment': '医保标准诊断字典',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    code = Column(String(64), primary_key=True, comment='诊断编码')
    name = Column(String(128), index=True, comment='诊断名称')
    initials = Column(String(128), index=True, comment='诊断名称首字母')


class MiOperationDict(Base):
    __tablename__ = 'mi_operation_dict'
    __table_args__ = {
        'comment': '医保版本手术字典',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    code = Column(String(64), primary_key=True, comment='手术ICD编码')
    name = Column(String(255), index=True, comment='手术、操作名称')
    type = Column(String(64), index=True, comment='手术、操作类型')
    initials = Column(String(64), index=True, comment='手术、操作名称首字母')


class Narcosi(Base):
    __tablename__ = 'narcosis'
    __table_args__ = {
        'comment': '麻醉类型表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(128), comment='麻醉编码')
    name = Column(String(255), comment='麻醉名称')
    initials = Column(String(255), comment='麻醉名称首字母')


class OperationInfo(Base):
    __tablename__ = 'operation_info'
    __table_args__ = {
        'comment': '智能编码-手术、操作信息表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(32), index=True, comment='病历id')
    type = Column(String(32), comment='类型, 手术, 操作等')
    code = Column(String(32), comment='手术、操作ICD编码')
    name = Column(String(255), comment='手术、操作名称')
    originName = Column(String(255), comment='原始手术、操作名称')
    operation_time = Column(TIMESTAMP, comment='手术时间')
    operator = Column(String(64), comment='术者')
    helperOne = Column(String(64), comment='一助')
    helperTwo = Column(String(64), comment='二助')
    narcosis = Column(String(255), comment='麻醉方式')
    narcosisDoctor = Column(String(64), comment='麻醉医师')
    cut = Column(String(64), comment='切口类型')
    healLevel = Column(String(64), comment='愈合等级')
    level = Column(String(64), comment='手术等级')
    coder = Column(String(64), comment='编码员')
    coder_id = Column(String(64), comment='编码员id')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    update_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                         comment='更新时间')
    is_deleted = Column(INTEGER(2), server_default='0', comment='是否删除标记, 1-是')
    orderNum = Column(INTEGER(11), comment='排序')


class OperationOriginDict(Base):
    __tablename__ = 'operation_origin_dict'
    __table_args__ = {
        'comment': '手术-原始手术对照表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(64), comment='手术、操作ICD编码')
    type = Column(String(128), comment='手术、操作类型')
    name = Column(String(255), comment='手术、操作名称')
    originName = Column(String(255), index=True, comment='原始手术、操作名称')
    create_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))


class CodingOperation(Base):
    __tablename__ = 'coding_operation'
    __table_args__ = {
        'comment': '编码手术',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    caseId = Column(String(255), index=True)
    patientId = Column(String(255))
    oper_code = Column(String(255), comment='手术编码')
    oper_name = Column(String(255), comment='手术名称')
    code_oper_name = Column(String(255), comment='编码手术名称')
    oper_type = Column(String(255), comment='手术类型')
    oper_date = Column(String(255), comment='手术日期')
    oper_level = Column(String(255), comment='手术级别')
    oper_doctor = Column(String(255), comment='手术医生')
    assistant_1 = Column(String(255), comment='1助')
    assistant_2 = Column(String(255), comment='2助')
    cut_level = Column(String(255), comment='切口级别')
    ane_method = Column(String(255), comment='麻醉方式')
    ans_doctor = Column(String(255), comment='麻醉医生')
