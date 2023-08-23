# coding: utf-8
"""
cdss项目相关的表结构

"""

from sqlalchemy import Column, DateTime, JSON, String, Text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT

from sqlalchemylib.sqlalchemylib.connection import Base


class CdssColorInfo(Base):
    __tablename__ = 'cdss_color_info'
    __table_args__ = {
        'comment': 'cdss色值信息表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    sub_type = Column(String(255), nullable=False, server_default='', comment='所属规则类别')
    word = Column(String(255), nullable=False, server_default='', comment='标签内容')
    color_cn = Column(String(255), nullable=False, server_default='', comment='颜色[中文]')
    color = Column(INTEGER(11), nullable=False, server_default='0',
                   comment='卡片颜色, 默认0-白色, 1-红色, 2-黄色, 3-绿色, 4-蓝色, 11-红色实心')
    use = Column(INTEGER(11), nullable=False, server_default='0', comment='用途, 0-全部, 1-患者列表, 2-患者的任务列表')


class CdssMessage(Base):
    __tablename__ = 'cdss_messages'

    id = Column(INTEGER(11), primary_key=True)
    case_id = Column(String(64), comment='病历号')
    rule_code = Column(String(64), comment='规则编码')
    rule_name = Column(String(255), comment='规则名称')
    type = Column(String(255), comment='提示类别, 推荐/预警/知识')
    sub_type = Column(String(255), comment='子类别, 相似病例/知识速递/推荐检验/推荐检查/特殊疾病预警/医疗风险预警/病情变化预警')
    doc_type = Column(String(64), comment='对应的文书类型')
    doc_id = Column(String(255), comment='对应的文书id')
    source = Column(String(16), comment='消息源，ai/custom')
    name = Column(String(255), comment='关联项目名称')
    iri = Column(String(255), comment='知识库索引地址')
    tags = Column(JSON, comment='标签')
    date = Column(DateTime, comment='创建日期')
    content = Column(String(10240), comment='消息主体内容')
    params = Column(JSON, comment='通用扩展项, 可以存储一些特殊元素的值')
    is_historic = Column(TINYINT(1), nullable=False, server_default='0',
                         comment='是否是过往提示, 默认0-否, 1-是(可恢复), 2-是(永久过往提示)')
    rule_status = Column(INTEGER(11), nullable=False, server_default='1', comment='规则触发时的启用状态, 1-启用, 2-停用')
    formular_result_id = Column(String(64), nullable=False, server_default='', comment='量表result id')
    doctor_id = Column(String(128), nullable=False, server_default='', comment='触发该规则的医生id[冒泡消息的接收医生id]')
    cdss_type = Column(INTEGER(11), nullable=False, server_default='0', comment='CDSS类型, 默认0-通用CDSS, 1-单病种CDSS')
    tip_type = Column(INTEGER(11), nullable=False, server_default='1',
                      comment='消息提示类型, 1-提示[闪退], 2-警告[常驻], 3-禁止[拦截]')


class ExamPosition(Base):
    """患者画像 检查部位字典"""
    __tablename__ = 'exam_position'

    id = Column(INTEGER(11), primary_key=True)
    examname = Column(String(255), comment='检查名称')
    position = Column(String(255), comment='部位')
    
    
class CDSSKsData(Base):
    """cdss 知识库"""
    __tablename__ = 'cdss_ks_data'

    id = Column(INTEGER(11), primary_key=True)
    type = Column(String(255), comment='类型')
    name = Column(String(255), comment='名称')
    iri = Column(String(255), comment='iri')
    describe = Column(Text, comment='iri')
    date = Column(DateTime, comment='日期')
    source = Column(String(255), comment='source')
    keyword = Column(String(255), comment='关键字')
    file_url = Column(String(1024), comment='文件url')
    
    
class CDSSActionLog(Base):
    """cdss 操作日志表"""
    __tablename__ = 'cdss_action_log'

    id = Column(INTEGER(11), primary_key=True)
    doctor_id = Column(String(255), comment='操作人id')
    first_type = Column(String(255), comment='一级类型')
    second_type = Column(String(255), comment='二级类型')
    createTime = Column(DateTime, comment='操作时间')
    department = Column(String(255), comment='科室')
