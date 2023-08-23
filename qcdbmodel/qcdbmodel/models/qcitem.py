# coding: utf-8
"""
质控点管理

"""
from sqlalchemy import Column, DateTime, Float, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import INTEGER, TINYINT

from sqlalchemylib.sqlalchemylib.connection import Base


class QcGroup(Base):
    __tablename__ = 'qcGroup'
    __table_args__ = {
        'comment': '质控规则组',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(32))


class QcCategory(Base):
    __tablename__ = 'qcCategory'
    __table_args__ = {
        'comment': '质控类型分组',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(255), comment="类型组名称")
    groupId = Column(INTEGER(11), comment="规则组id")
    parentId = Column(INTEGER(11), comment="嵌套父类型组id")
    maxScore = Column(Float, comment="最高分")
    created_at = Column(DateTime)
    is_deleted = Column(INTEGER(11))


class QcCateItem(Base):
    __tablename__ = 'qcCateItems'
    __table_args__ = {
        'comment': '规则组和质控点对照关系表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    groupId = Column(INTEGER(11), comment="规则组id")
    categoryId = Column(INTEGER(11), index=True, comment="类型组id")
    itemId = Column(INTEGER(11), index=True, comment="质控点id")
    maxScore = Column(Float, comment="质控点最高扣分")
    score = Column(Float, comment="质控点每处扣分")
    highlight = Column(INTEGER(11), server_default='0', comment="邵逸夫医院，是否是重点强控的质控点")


class QcItem(Base):
    __tablename__ = 'qcItem'

    id = Column(INTEGER(11), primary_key=True)
    code = Column(String(50), index=True)
    standard_emr = Column(String(255), comment='质控文书')
    linkEmr = Column(String(255))
    requirement = Column(String(255))
    rule = Column(String(1024), comment='规则')
    instruction = Column(String(255), comment='报错说明')
    source = Column(String(255), comment='来源')
    comment = Column(String(255))
    ai_support = Column(TINYINT(1), server_default='0')
    score = Column(String(255))
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    is_deleted = Column(TINYINT(1), server_default='0')
    operator_id = Column(String(255))
    operator_name = Column(String(255))
    autoRefuseFlag = Column(INTEGER(11))
    approve_status = Column(INTEGER(11), server_default='0')
    flexTipFlag = Column(INTEGER(11), server_default='0', comment='是否用问题的详细原因覆盖指控点报错说明')
    score_value = Column(Float, server_default=text("'0'"))
    creator = Column(String(255))
    custom = Column(INTEGER(11), server_default='0')
    enable = Column(INTEGER(11), server_default='0')
    enableType = Column(INTEGER(11), server_default='1', comment="质控状态 1=质控问题 2=提示问题")
    isVerified = Column(INTEGER(11), server_default='0')
    tags = Column(String(255))
    counting = Column(INTEGER(11), server_default='0')
    veto = Column(INTEGER(11), server_default='0', comment='强制类型，1表示强控，2表示否决')
    category = Column(INTEGER(11), server_default='0', comment='时效性=1，一致性=2，完整性=3，正确性=4')
    type = Column(INTEGER(11), server_default='0', comment='质控点类型，0通用质控点，1表示专科质控点，2表示专病质控点')
    departments = Column(String(255), comment='专科质控点适用科室')
    disease = Column(String(255), comment='专病质控点，适用诊断列表')
    is_firstpage = Column(INTEGER(11), server_default='0', comment='是否是病案首页问题')
    is_fprequired = Column(INTEGER(11), server_default='0', comment='是否是首页必填项问题')
    cautionModel = Column(String(255))
