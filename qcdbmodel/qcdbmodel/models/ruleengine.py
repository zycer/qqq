# coding: utf-8
"""
rule engine

"""
from sqlalchemy import Column, Float, String, Text, text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT

from sqlalchemylib.sqlalchemylib.connection import Base


class RuleBindScene(Base):
    __tablename__ = 'rule_bind_scene'
    __table_args__ = {
        'comment': '规则详情与规则场景code绑定明细表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    rule_detail_code = Column(String(255), nullable=False, index=True, server_default='',
                              comment='规则详情表code, rule_detail.code')
    rule_scene_code = Column(String(255), nullable=False, server_default='', comment='规则场景code')


class RuleDetail(Base):
    __tablename__ = 'rule_detail'
    __table_args__ = {
        'comment': 'cdss-规则细项表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    sub_type = Column(String(255), nullable=False, server_default='',
                      comment='规则二级类型, 推荐检查、推荐检验、病情变化预警、特殊疾病预警等')
    type = Column(String(128), nullable=False, server_default='',
                  comment='规则类型[预警-医疗风险预警下的规则三级类型]: 智能检验、智能检查、智能手术、合理用药、ai-不存在code自动创建')
    code = Column(String(255), nullable=False, index=True, server_default='', comment='规则编码')
    name = Column(String(255), nullable=False, server_default='', comment='规则名称')
    related_dict = Column(String(255), nullable=False, server_default='', comment='关联字典项目')
    message_type = Column(String(16), nullable=False, server_default='', comment='消息类型')
    rule_scene = Column(String(255), nullable=False, index=True, server_default='', comment='规则场景名称')
    status = Column(INTEGER(11), nullable=False, server_default='0', comment='规则状态, 0-无状态, 1-启用, 2-停用')
    is_online = Column(INTEGER(11), nullable=False, server_default='0', comment='上线标识, 0-待上线, 1-已上线')
    is_deleted = Column(INTEGER(11), nullable=False, server_default='0', comment='删除标识, 1-已删除')
    check_rule = Column(Text, comment='检验规则')
    message_content = Column(Text, comment='消息提示内容')
    rule_from = Column(Text, comment='规则出处')
    create_source = Column(INTEGER(11), nullable=False, server_default='0', comment='创建来源, 默认0-系统创建, 1-医院自主创建')
    message_title = Column(Text, comment='消息提示标题')


class RuleQuery(Base):
    __tablename__ = 'rule_query'
    __table_args__ = {
        'comment': '规则脑图条件保存表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(255), nullable=False, server_default='', comment='规则编码code')
    includeQuery = Column(Text, comment='纳入条件原始json数据')
    excludeQuery = Column(Text, comment='排除条件原始json数据')
    includeSql = Column(Text, comment='纳入条件处理后sql')
    excludeSql = Column(Text, comment='排除条件处理后sql')
    is_deleted = Column(INTEGER(11), nullable=False, server_default='0', comment='删除标记')


class RuleScene(Base):
    __tablename__ = 'rule_scene'
    __table_args__ = {
        'comment': '规则场景表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(255), nullable=False, server_default='', comment='规则场景编码')
    name = Column(String(255), nullable=False, server_default='', comment='规则场景名称')
    content = Column(Text, comment='规则场景说明')
    is_deleted = Column(INTEGER(11), nullable=False, server_default='0', comment='是否删除标识, 1-已删除')
    doctors = Column(Text, comment='规则场景绑定医生')


class RuleSystem(Base):
    __tablename__ = 'rule_system'
    __table_args__ = {
        'comment': '系统规则条件数据表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(255), nullable=False, comment='规则id')
    rules = Column(Text, comment='规则条件数据')


class QcItemRule(Base):
    __tablename__ = 'qcItem_rule'
    __table_args__ = {
        'comment': '质控点脑图规则表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    qcItemId = Column(INTEGER(11), nullable=False, server_default='0', comment='质控点id')
    field = Column(String(255), nullable=False, server_default='', comment='提醒事件字段, 入院时间等')
    firstHour = Column(Float(asdecimal=True), server_default=text("'0'"), comment='首次提醒在多少小时后')
    overHour = Column(Float(asdecimal=True), nullable=False, server_default=text("'0'"), comment='截止提醒在多少小时后')
    includeQuery = Column(Text, comment='脑图规则纳入条件')
    excludeQuery = Column(Text, comment='脑图规则排除条件')
    qcItemCode = Column(String(255), nullable=False, server_default='', comment='质控点code')
    instruction = Column(String(1024), nullable=False, server_default='', comment='问题描述')


class Keyword(Base):
    __tablename__ = 'keywords'
    __table_args__ = {
        'comment': '脑图查询关键词表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    kword_id = Column(String(255), nullable=False, server_default='', comment='关键字ID, 用于区分不同关键字不同处理方法')
    type = Column(String(32), nullable=False, server_default='', comment='一级分类, 例如：基本信息，疾病、症状、化验等）')
    category = Column(String(32), nullable=False, server_default='', comment='二级分类')
    sub_category = Column(String(32), nullable=False, server_default='', comment='三级分类')
    name = Column(String(64), nullable=False, server_default='', comment='界面展示的字段名称, 不提供则使用字段名')
    field = Column(String(64), nullable=False, server_default='', comment='字段名称')
    fieldtype = Column(String(32), nullable=False, server_default='',
                       comment='字段类型, 可选项: string, integer, boolean, float, datetime')
    table_name = Column(String(64), nullable=False, server_default='', comment='字段来源表名')
    min_value = Column(INTEGER(11), nullable=False, server_default='0', comment='数值字段的最小值')
    max_value = Column(INTEGER(11), nullable=False, server_default='0', comment='数值字段的最大值')
    operators = Column(String(255), nullable=False, server_default='',
                       comment='所有支持的运算符, 可选项: eq,gt,gte,lt,lte,bw,exclude,include,is,isnot')
    default_operator = Column(String(32), nullable=False, server_default='', comment='默认运算符')
    default_value = Column(String(255), nullable=False, server_default='', comment='默认值, 用于界面显示')
    choices = Column(String(255), nullable=False, server_default='', comment='可选项, 逗号分隔')
    enableSug = Column(TINYINT(1), nullable=False, server_default='0', comment='是否启用sug搜索, 暂时不使用')
    unitChoices = Column(String(255), nullable=False, server_default='', comment='可选单位, 逗号分隔')
    unit = Column(String(32), nullable=False, server_default='', comment='默认单位, 可为空')
    comment = Column(String(60))


class QcKeyword(Base):
    __tablename__ = 'qc_keywords'
    __table_args__ = {
        'comment': '脑图查询关键词表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    kword_id = Column(String(255), nullable=False, server_default='', comment='关键字ID, 用于区分不同关键字不同处理方法')
    type = Column(String(32), nullable=False, server_default='', comment='一级分类, 例如：基本信息，疾病、症状、化验等）')
    category = Column(String(32), nullable=False, server_default='', comment='二级分类')
    sub_category = Column(String(32), nullable=False, server_default='', comment='三级分类')
    name = Column(String(64), nullable=False, server_default='', comment='界面展示的字段名称, 不提供则使用字段名')
    field = Column(String(64), nullable=False, server_default='', comment='字段名称')
    fieldtype = Column(String(32), nullable=False, server_default='',
                       comment='字段类型, 可选项: string, integer, boolean, float, datetime')
    table_name = Column(String(64), nullable=False, server_default='', comment='字段来源表名')
    min_value = Column(INTEGER(11), nullable=False, server_default='0', comment='数值字段的最小值')
    max_value = Column(INTEGER(11), nullable=False, server_default='0', comment='数值字段的最大值')
    operators = Column(String(255), nullable=False, server_default='',
                       comment='所有支持的运算符, 可选项: eq,gt,gte,lt,lte,bw,exclude,include,is,isnot')
    default_operator = Column(String(32), nullable=False, server_default='', comment='默认运算符')
    default_value = Column(String(255), nullable=False, server_default='', comment='默认值, 用于界面显示')
    choices = Column(String(255), nullable=False, server_default='', comment='可选项, 逗号分隔')
    enableSug = Column(TINYINT(1), nullable=False, server_default='0', comment='是否启用sug搜索, 暂时不使用')
    unitChoices = Column(String(255), nullable=False, server_default='', comment='可选单位, 逗号分隔')
    unit = Column(String(32), nullable=False, server_default='', comment='默认单位, 可为空')
    comment = Column(String(60))
