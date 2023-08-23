# coding=utf-8
import argparse
import datetime
import re
import logging
from argparse import ArgumentParser

from . import QCDataBaseManager as _QCDataBaseManager

import pandas as pd

logging.basicConfig(level=logging.INFO)


class QCDataBaseManager(_QCDataBaseManager):

    def importConfigItems(self, dataframe: pd.DataFrame):
        new_count = 0
        with self.session() as session:
            #
            ConfigItemModel = self.models['configItem']

            # 处理数据
            for idx, data in dataframe.iterrows():
                name = data['配置项']
                value = data['配置值']
                message = data['配置项用法备注']

                # validate
                if pd.isnull(name) or not name:
                    logging.info(f'exception empty group, column: {idx}')
                    continue
                if pd.isnull(value) or not value:
                    value = ''
                if pd.isnull(message) or not message:
                    message = ''

                # 配置项
                config = session.query(ConfigItemModel).filter_by(name=name).first()
                if not config:
                    row = ConfigItemModel(name=name, value=value, message=message)
                    session.add(row)
                    new_count += 1
                else:
                    config.value = value
                    config.message = message
        logging.info('import finished!!')
        return f"""
        导入完成，新增{new_count}个配置项。
        
        *特别说明：
        - 配置项如果存在，更新值。
        - 配置项不存在，新增配置。
        - 只会更新配置项，没有删除操作。
        """


def getArgs():
    parser = ArgumentParser(prog='系统配置项', description='导入配置项')
    parser.add_argument('-f', dest='file', help='上传配置项设置', type=argparse.FileType(mode='r', encoding='utf-8'))
    parser.add_argument('--db-host', dest='dbHost', default='mysql.infra-default:3306', help='数据库地址+端口')
    parser.add_argument('--db-name', dest='dbName', default='qcmanager', help='数据库名')
    parser.add_argument('--db-url', dest='dbUrl',
                        default='mysql+pymysql://root:rxthinkingmysql@{dbHost}/{dbName}?charset=utf8mb4', help='数据库Url')
    return parser


def STREAMLIT_FUNCTION(args):
    if args.file:
        tmpdata = pd.read_csv(args.file.name)
        dbUrl = args.dbUrl.format(dbHost=args.dbHost, dbName=args.dbName)
        db = QCDataBaseManager(dbUrl)
        return db.importConfigItems(tmpdata)


STREAMLIT_PARSER = getArgs()
