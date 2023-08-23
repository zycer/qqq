# coding=utf-8
import argparse
import datetime
import logging
from argparse import ArgumentParser
from pymongo import MongoClient
import pandas as pd

logging.basicConfig(level=logging.INFO)


class ImportManager(object):

    def __init__(self, db_url):
        self.db_url = db_url
        self.mongo = MongoClient(db_url)
        self.database = 'hospitaluser'
        self.collection = 'department'

    def import_hospuser_department(self, dataframe: pd.DataFrame):

        collection = self.mongo[self.database][self.collection]
        result = ""
        departments = []

        for idx, data in dataframe.iterrows():
            code = data['编号']
            name = data['科室']
            # validate
            # if pd.isnull(code) or not code:
            #     logging.info(f'exception empty code, column: {idx}')
            #     continue
            if pd.isnull(name) or not name:
                logging.info(f'exception empty item-name, column: {idx}')
                continue
            dept = collection.find_one({'name': name})
            if dept:
                result += f"""
                {name} 已存在，跳过
                """
                continue
            departments.append({'name': name})

        if departments:
            collection.insert_many(departments)
            for d in departments:
                result += f'''
                {d} 添加成功
                '''

        logging.info('import finished!!')
        return result


def getArgs():
    parser = ArgumentParser(prog='用户管理科室导入', description='导入科室')
    parser.add_argument('-f', dest='file', help='上传一个文件', type=argparse.FileType(mode='r', encoding='utf-8'))
    parser.add_argument('--db-url', dest='dbUrl', default='mongodb://mongodb.infra-default:27017/?replicaSet=default')
    return parser


def STREAMLIT_FUNCTION(args):
    if args.file:
        tmpdata = pd.read_csv(args.file.name)
        m = ImportManager(args.dbUrl)
        return m.import_hospuser_department(tmpdata)


STREAMLIT_PARSER = getArgs()
