# coding: utf-8
"""
单病种上报相关的表结构

"""
from sqlalchemy import Column, DateTime, Enum, Index, JSON, String, TIMESTAMP, Text, text
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, INTEGER, SMALLINT, TINYINT

from sqlalchemylib.sqlalchemylib.connection import Base


class DiseaseAuditor(Base):
    __tablename__ = 'disease_auditors'

    id = Column(INTEGER(11), primary_key=True)
    user_id = Column(String(200))
    user_name = Column(String(200))
    user_loginname = Column(String(200))
    department = Column(String(200))
    department_id = Column(String(200))
    departments = Column(JSON)
    diseases = Column(JSON)
    status = Column(TINYINT(4))
    create_at = Column(TIMESTAMP)
    update_at = Column(TIMESTAMP)


class DiseaseDesc(Base):
    __tablename__ = 'disease_desc'
    __table_args__ = {
        'comment': '疾病描述表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    disease_id = Column(String(200), server_default='', comment='疾病id')
    title = Column(String(255), server_default='', comment='标题')
    disease_num = Column(INTEGER(10), server_default='0', comment='填报数量')
    create_at = Column(TIMESTAMP, comment='创建时间')
    update_at = Column(TIMESTAMP, comment='修改时间')


class DiseaseItemDesc(Base):
    __tablename__ = 'disease_item_desc'
    __table_args__ = {
        'comment': '疾病条目描述表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    item_key = Column(String(255), server_default='', comment='条目id')
    item_name = Column(String(255), server_default='', comment='条目名称')
    item_type = Column(Enum('字符串', '数值', '数组'), server_default='字符串', comment='值类型')
    disease_id = Column(String(200), server_default='', comment='疾病id')
    item_source = Column(String(255), server_default='', comment='提取来源')
    item_notnull = Column(TINYINT(4), nullable=False, server_default='1', comment='1不能空2可以空')
    item_hastable = Column(TINYINT(4), nullable=False, server_default='1', comment='1不下拉2下拉')
    item_example = Column(String(32), nullable=False, server_default='', comment='example')
    item_list = Column(Text, nullable=False, comment='下拉json')
    create_at = Column(TIMESTAMP, comment='创建时间')
    update_at = Column(TIMESTAMP, comment='修改时间')


class DiseaseReportItem(Base):
    __tablename__ = 'disease_report_items'
    __table_args__ = {
        'comment': '疾病上报条目',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    visit_no = Column(String(255), server_default='', comment='住院号')
    patient_id = Column(String(200), server_default='', comment='患者id')
    disease_id = Column(String(200), server_default='', comment='疾病id')
    item_id = Column(String(200), nullable=False, server_default='', comment='条目id')
    item_content = Column(String(255), server_default='', comment='条目内容')
    item_content_text = Column(String(255), server_default='', comment='内容备注')
    item_content_manual = Column(String(255), server_default='', comment='手动条目内容')
    item_content_text_manual = Column(String(255), server_default='', comment='内容备注')
    type = Column(TINYINT(4), server_default='1', comment='填充类型1ai2manul')
    user_id = Column(String(255), server_default='', comment='填写人')
    user_name = Column(String(255), server_default='', comment='填写人名')
    create_at = Column(TIMESTAMP, comment='创建时间')
    update_at = Column(TIMESTAMP, comment='修改时间')
    status = Column(TINYINT(4), nullable=False)

    Index("idx_disease_report_items_vnodis", visit_no, disease_id, unique=False)


class DiseaseReporter(Base):
    __tablename__ = 'disease_reporters'
    __table_args__ = {
        'comment': '填报员表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    user_id = Column(String(200), server_default='', comment='用户id')
    user_name = Column(String(200), server_default='', comment='用户名')
    user_loginname = Column(String(200), nullable=False, server_default='', comment='登录名')
    work_no = Column(String(200), nullable=False, server_default='', comment='工号')
    department = Column(String(200), server_default='', comment='科室名')
    department_id = Column(String(200), server_default='', comment='科室id')
    doctors = Column(String(1000), nullable=False, server_default='', comment='负责医生')
    departments = Column(JSON, comment='负责科室')
    departments_ids = Column(String(255), server_default='', comment='负责科室ids')
    diseases = Column(JSON, comment='负责病种')
    diseases_ids = Column(String(255), server_default='', comment='负责病种ids')
    status = Column(TINYINT(4), server_default='1', comment='状态1正常2作废')
    create_at = Column(TIMESTAMP, comment='创建时间')
    update_at = Column(TIMESTAMP, comment='修改时间')


class FillItemsLog(Base):
    __tablename__ = 'fill_items_log'
    __table_args__ = {
        'comment': '条目填写日志',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    visit_no = Column(String(255), nullable=False, server_default='', comment='住院号')
    disease_id = Column(String(200), server_default='', comment='疾病id')
    patient_id = Column(String(200), server_default='', comment='患者id')
    item_id = Column(String(200), nullable=False, server_default='', comment='条目id')
    item_content_manual = Column(String(255), server_default='', comment='条目内容')
    item_content_text_manual = Column(String(255), server_default='', comment='条目内容备注')
    user_id = Column(String(200), server_default='', comment='用户id')
    user_name = Column(String(200), server_default='', comment='用户名')
    create_at = Column(DateTime, comment='创建时间')
    update_at = Column(DateTime, comment='修改时间')

    Index("idx_fill_items_log_fillid", visit_no, unique=False)


class PatientBaseInfo(Base):
    __tablename__ = 'patient_baseInfo'

    id = Column(INTEGER(11), primary_key=True)
    create_time = Column(DATETIME(fsp=6), nullable=False)
    modify_time = Column(DATETIME(fsp=6), nullable=False)
    record_id = Column(String(50), nullable=False)
    inpatient_no = Column(String(50), nullable=False)
    patient_id = Column(String(50), nullable=False)
    patient_name = Column(String(20), nullable=False)
    sex = Column(String(2), nullable=False)
    age = Column(String(5), nullable=False)
    in_type = Column(String(10), nullable=False)
    emr_status = Column(String(1), nullable=False)
    resident_doctor = Column(String(20))
    resident_doctor_code = Column(String(50))
    attending_doctor = Column(String(20))
    attending_doctor_code = Column(String(50))
    director_doctor = Column(String(20))
    director_doctor_code = Column(String(50))
    inp_date = Column(DATETIME(fsp=6), nullable=False)
    inp_dept = Column(String(50), nullable=False)
    inp_code = Column(String(50))
    outp_date = Column(DATETIME(fsp=6))
    outp_dept = Column(String(50))
    outp_code = Column(String(50))
    disease = Column(String(50), nullable=False)
    disease_code = Column(String(50))


class TimeOutConf(Base):
    __tablename__ = 'time_out_conf'
    __table_args__ = {
        'comment': '超时配置表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(BIGINT(20), primary_key=True)
    business = Column(INTEGER(11), server_default='0', comment='1上报')
    type = Column(SMALLINT(6), server_default='0', comment='1提交,2审核,3上报时限')
    warn_time = Column(INTEGER(11), server_default='0', comment='预警时间')
    out_time = Column(INTEGER(11), server_default='0', comment='超时时间')
    unit = Column(TINYINT(4), server_default='0', comment='1工作日2自然日')
    status = Column(TINYINT(4), server_default='1', comment='状态1正常2作废')
    create_at = Column(TIMESTAMP, comment='创建时间')
    update_at = Column(TIMESTAMP, comment='修改时间')


class ScriptLog(Base):
    __tablename__ = 'script_log'
    __table_args__ = {
        'comment': '脚本日志表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    type = Column(INTEGER(11), server_default='0', comment='类型1:消息')
    res_id = Column(String(255), server_default='', comment='资源id')
    val = Column(String(255), server_default='', comment='值')
    create_at = Column(TIMESTAMP, comment='创建时间')
    update_at = Column(TIMESTAMP, comment='修改时间')


class ReportTracelog(Base):
    __tablename__ = 'report_tracelog'
    __table_args__ = {
        'comment': '操作追踪日志',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    report_id = Column(INTEGER(11), nullable=False, server_default='0', comment='填报id')
    visit_no = Column(String(255), server_default='', comment='住院号')
    patient_id = Column(String(200), server_default='', comment='患者id')
    disease_id = Column(String(200), server_default='', comment='疾病id')
    operator_id = Column(String(200), nullable=False, server_default='0', comment='操作者')
    operator_name = Column(String(200), server_default='', comment='操作者姓名')
    action_desc = Column(String(255), server_default='', comment='动作描述')
    report_status = Column(TINYINT(4), nullable=False, server_default='1',
                           comment='上报状态:1待选择2填报3已取消4待审核5审核通过6审核驳回7上报失败8上报成功9填表')
    status = Column(TINYINT(4), nullable=False, server_default='1', comment='状态:1显示2隐藏')
    report_status_detail = Column(TINYINT(4), nullable=False, server_default='2',
                                  comment='上报状态:2选择填报3取消上报4提交5审核通过6审核驳回7上报失败8上报成功9填表'
                                          '15提交预警16提交超时17审核预警18审核超时19上报预警20上报超时21上报前置机成功')
    report_mark_show = Column(String(1000), nullable=False, server_default='', comment='[{}]')
    report_mark_code = Column(String(255), nullable=False, server_default='0', comment='-1其他')
    upload_items_json = Column(Text, nullable=False, comment='上传条目列表')
    create_at = Column(TIMESTAMP, comment='创建时间')

    Index("idx_case_diseases_vno", visit_no, unique=False)


class ReasonConf(Base):
    __tablename__ = 'reason_conf'
    __table_args__ = {
        'comment': '原因配置表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    business = Column(INTEGER(11), server_default='0', comment='1取消填报')
    content = Column(String(255), server_default='', comment='原因内容')
    status = Column(TINYINT(4), server_default='1', comment='状态1正常2作废')
    create_at = Column(TIMESTAMP, comment='创建时间')
    update_at = Column(TIMESTAMP, comment='修改时间')


class CaseDisease(Base):
    __tablename__ = 'case_diseases'

    id = Column(INTEGER(11), primary_key=True)
    visit_no = Column(String(255))
    patient_id = Column(String(200))
    patient_name = Column(String(200))
    patient_sex = Column(TINYINT(4))
    patient_age = Column(SMALLINT(6))
    disease_id = Column(String(200))
    disease_num = Column(TINYINT(4))
    title = Column(String(255))
    fill_num = Column(INTEGER(10))
    total_num = Column(INTEGER(10))
    should_num = Column(INTEGER(10))
    report_status = Column(TINYINT(4))
    report_status_detail = Column(TINYINT(4))
    report_mark = Column(Text)
    report_mark_show = Column(String(1000))
    report_mark_code = Column(String(255))
    quality_doctor_id = Column(String(200))
    quality_doctor = Column(String(200))
    duty_doctor_id = Column(String(200))
    duty_doctor = Column(String(200))
    in_dep_id = Column(String(200))
    in_dep = Column(String(200))
    out_dep_id = Column(String(200))
    out_dep = Column(String(200))
    out_at = Column(DateTime)
    in_day = Column(INTEGER(10))
    clinic_type = Column(TINYINT(4))
    user_id = Column(String(200))
    user_name = Column(String(200))
    time_rule_tips = Column(String(255))
    create_at = Column(TIMESTAMP)
    update_at = Column(TIMESTAMP)
    major_doctor_id = Column(String(200), nullable=False, server_default='', comment='主治医生')
    major_doctor = Column(String(200), nullable=False, server_default='', comment='主治医生')
    upload_err = Column(Text, comment='上报返回')

    Index("idx_case_diseases_vno", visit_no, unique=False)
