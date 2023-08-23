# coding: utf-8
"""
知识库相关的表结构
"""

from sqlalchemy import Column, DateTime, LargeBinary, String, Text, text, Index
from sqlalchemy.dialects.mysql import INTEGER

from sqlalchemylib.sqlalchemylib.connection import Base


class KnowledgeCatalog(Base):
    __tablename__ = 'knowledge_catalog'
    __table_args__ = {
        'comment': '知识目录表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    parent = Column(INTEGER(11), comment='父节点')
    name = Column(String(255), comment='名称')
    knowledge_type = Column(INTEGER(11), comment='目录所属类别')
    read_only = Column(INTEGER(11), server_default='0')
    is_delete = Column(INTEGER(11), server_default='0', comment='是否删除')

    Index("knowledge_catalog_parent_index", parent, unique=False)


class KnowledgeDetail(Base):
    __tablename__ = 'knowledge_detail'
    __table_args__ = {
        'comment': '知识详情',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(255), comment='字段名称')
    content = Column(Text, comment='内容')
    knowledge_id = Column(INTEGER(11), comment='知识id')
    parent = Column(INTEGER(11), comment='级别')


class KnowledgeFile(Base):
    __tablename__ = 'knowledge_file'
    __table_args__ = {
        'comment': '知识指南路径',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci',
    }

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(255), comment='名称')
    type = Column(INTEGER(11), comment='所属类型')
    first_type = Column(INTEGER(11), comment='一级类型(目录)')
    second_type = Column(INTEGER(11), comment='二级类型(目录)')
    folder_id = Column(INTEGER(11), comment='所属目录')
    special_column = Column(String(255), comment='知识专栏')
    disease = Column(String(255), comment='关联疾病')
    create_time = Column(DateTime, comment='创建时间')
    update_time = Column(DateTime, comment='更新时间')
    file_url = Column(String(255), comment='文件地址')
    is_delete = Column(INTEGER(11), server_default='0')


class KnowledgeType(Base):
    __tablename__ = 'knowledge_type'

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(66), comment='类型名称')
    icon = Column(LargeBinary, comment='图标')
    release_time = Column(DateTime)


class Knowledge(Base):
    __tablename__ = 'knowledge'

    id = Column(INTEGER(11), primary_key=True)
    name = Column(String(255), comment='疾病名称')
    create_time = Column(DateTime, comment='创建时间')
    update_time = Column(DateTime, comment='更新时间')
    operator = Column(String(255), comment='操作人')
    operator_id = Column(String(255), comment='操作人id')
    knowledge_type = Column(INTEGER(11), comment='知识类型')
    folder_id = Column(INTEGER(11), comment='所属文件夹')
    read_only = Column(INTEGER(11), server_default='0')
    is_delete = Column(INTEGER(11), server_default='0', comment='是否删除')

    Index("knowledge_folder_id_index", folder_id, unique=False)
