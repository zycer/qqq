#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-02-17 13:33:37

'''

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Index, JSON, LargeBinary, String, TIMESTAMP, Table, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT, VARCHAR, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from argparse import ArgumentParser

from sqlalchemy.sql.sqltypes import BOOLEAN, NUMERIC, Integer
import arrow
from sqlalchemylib.sqlalchemylib.connection import Base, metadata, Connection


def now() -> datetime:
    tmp = arrow.utcnow().to('+08:00').naive
    return tmp


class KeywordModel(Base):
    """关键词表
    """
    __tablename__ = 'keywords'

    id = Column(INTEGER(11), primary_key=True, autoincrement=True)
    kword_id = Column(String(255), comment="关键字ID, 用于区分不同关键字不同处理方法")
    type = Column(String(32), comment="例如：基本信息，疾病、症状、化验等）, 就是一级分类")
    category = Column(String(32), comment='二级分类')
    sub_category = Column(String(32), comment='三级分类')
    name = Column(String(64), comment='界面展示的字段名称, 不提供则使用字段名')
    field = Column(String(64), comment='字段名称')
    fieldtype = Column(String(32), comment='字段类型, 可选项: string, integer, boolean, float, datetime')
    table_name = Column(String(64), comment='字段来源表名')
    min_value = Column(INTEGER(11), comment='数值字段的最小值')
    max_value = Column(INTEGER(11), comment='数值字段的最大值')
    operators = Column(String(255), comment='所有支持的运算符, 逗号分隔, 不填则基于字段类型自动使用所有可能项目, 可选项: eq,gt,gte,lt,lte,bw,exclude,include,is,isnot')
    default_operator = Column(String(32), comment='默认运算符')
    defaultValue = Column(String(255), comment='默认值, 用于界面显示')
    choices = Column(String(255), comment='可选项, 逗号分隔')
    enableSug = Column(Boolean(), comment='是否启用sug搜索, 暂时不使用')
    unitChoices = Column(String(255), comment='可选单位, 逗号分隔')
    unit = Column(String(32), comment='默认单位, 可为空')


def getFieldKeywords(url, tables=[], ignore_tables=[], includeSdgReport=False):
    """基于sqlalchemy获取数据库中所有表的字段并生成keyword

    Args:
        url (str): sqlalchemy接受的url
    """
    from sqlalchemy.schema import MetaData
    from sqlalchemy.schema import CreateTable
    from sqlalchemy import create_engine, Table
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(bind=engine)
    for table in meta.sorted_tables:
        if tables and table.name not in tables:
            continue
        if ignore_tables and table.name in ignore_tables:
            continue
        #print(type(table), table)
        for column in table.columns:
            fieldtype = 'string'
            coltype = str(column.type).lower()
            if 'int' in coltype:
                fieldtype = 'integer'
            elif 'float' in coltype or 'double' in coltype:
                fieldtype = 'float'
            elif 'bool' in coltype:
                fieldtype = 'boolean'
            elif 'time' in coltype or 'date' in coltype:
                fieldtype = 'datetime'
            else:
                fieldtype = 'string'
            #print(f'{table.name}\t{column.name}\t{fieldtype}\t{column.comment or ""}')
            yield KeywordModel(
                kword_id='rdb_field',
                table_name=table.name,
                field=column.name,
                fieldtype=fieldtype,
                name=column.comment or column.name,
                type=table.name
            )
    if includeSdgReport:
        # 包含单病种上报指标
        conn = Connection(url)
        sql = '''
select item.item_key, item.item_name, item.item_type, d.title 
from disease_item_desc item left join disease_desc d on item.disease_id = d.disease_id  
        '''
        for row in conn.iterResult(sql):
            yield KeywordModel(
                kword_id='rdb_field',
                table_name='_disease_report',
                field=row['item_key'],
                name=row.get('item_name', row.get('item_key')),
                type='单病种上报指标',
                category=row['title'],
                fieldtype={
                    '数值': 'float',
                    '数组': 'list',
                    '字符串': 'string'
                }.get(row['item_type'])
            )
            
        #print(dir(table))
        
if __name__ == '__main__':
    def getArgs():
        parser = ArgumentParser()
        parser.add_argument('--url')
        parser.add_argument('--tables', nargs='*')
        parser.add_argument('--ignore', nargs='*')
        parser.add_argument('--include-sdg-report-items', action='store_true', dest='includeSDGReportItems')
        parser.add_argument('-f', dest='file', help='输出文件', default='kwords.txt')
        return parser.parse_args()
    
    args = getArgs()
    # 普通表字段
    with open(args.file, 'w') as df:
        print(f'type\tcategory\tname\tkword_id\tfield\tfieldtype\ttable_name', file=df)
        for row in getFieldKeywords(args.url, args.tables, args.ignore, args.includeSDGReportItems):
            print(f'{row.type}\t{row.category or ""}\t{row.name or ""}\t{row.kword_id}\t{row.field}\t{row.fieldtype}\t{row.table_name}', file=df)
            