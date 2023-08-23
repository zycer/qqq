# coding=utf-8
import argparse
import re
import sys
import datetime
import platform
import logging
from argparse import ArgumentParser

from . import QCDataBaseManager as _QCDataBaseManager

import pandas as pd

logging.basicConfig(level=logging.INFO)


PYTHON_VERSION = platform.python_version()
is_python3 = PYTHON_VERSION.startswith('3')
if not is_python3:
    reload(sys)
    sys.setdefaultencoding('utf-8')


class QCDataBaseManager(_QCDataBaseManager):

    def importQcItems(self, dataframe: pd.DataFrame):
        item_categories = {
            '时效性': 1,
            '一致性': 2,
            '完整性': 3,
            '正确性': 4,
        }
        with self.session() as session:
            for idx, data in dataframe.iterrows():
                code = data['质控点编号']
                name = data['质控点名称']
                # validate
                if pd.isnull(code) or not code:
                    logging.info(f'exception empty code, column: {idx}')
                    continue
                if pd.isnull(name) or not name:
                    logging.info(f'exception empty item-name, column: {idx}')
                    continue
                # get data or set default
                emr = data['报警文书']
                if pd.isnull(emr) or '缺' in emr:
                    emr = '0'
                instruction = '' if pd.isnull(data['报警提示信息']) else str(data['报警提示信息']).replace('\n', ' ').strip()
                rule = '' if pd.isnull(data['质控点规则']) else str(data['质控点规则']).replace('\n', ' ').strip()
                score = '1' if pd.isnull(data['分数']) else str(re.search(r'\d+\.?\d*', f'{data["分数"]} 默认1分').group())
                category = '0' if pd.isnull(data['类别']) else item_categories.get(data['类别'])
                veto = data['是否强控']
                enable = data['是否开启']
                veto = '1' if not pd.isnull(veto) and veto == '是' else '0'
                enable = '2' if not pd.isnull(enable) and enable == '是' else '1'
                # 查询质控点是否存在
                qcItem = session.query(self.models['qcItem']).filter_by(code=code).first()
                if not qcItem:
                    obj = {
                        "code": code,
                        "standard_emr": emr,
                        "requirement": name,
                        "instruction": instruction if instruction else name,
                        "rule": rule,
                        "score": score,
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "operator_id": 'admin',
                        "operator_name": 'admin',
                        "score_value": float(score),
                        "veto": veto if veto else 0,
                        "enable": enable if enable else 1,
                        "category": category,
                        "isVerified": 1,
                        "ai_support": 1,
                        "counting": 0,
                        "custom": 0,
                        "is_deleted": 0,
                        "autoRefuseFlag": 0,
                        "approve_status": 2,
                        "flexTipFlag": 1,
                        'is_firstpage': 1 if emr == '病案首页' else 0,
                        'type': 1,
                        "linkEmr": '',
                        "source": '',
                        "comment": '',
                        "creator": '',
                        "tags": '',
                    }
                    row = self.models['qcItem'](**obj)
                    session.add(row)
                else:
                    if qcItem.standard_emr != '0':
                        qcItem.standard_emr = emr
                    qcItem.requirement = name
                    if instruction == '' and not qcItem.instruction:
                        qcItem.instruction = name
                    else:
                        qcItem.instruction = instruction
                    qcItem.score = score
                    qcItem.score_value = float(score)
                    qcItem.veto = veto if veto else 0
                    qcItem.enable = enable if enable else 1
                    qcItem.rule = rule
                    qcItem.is_firstpage = 1 if emr == '病案首页' else 0
                    qcItem.category = category
        logging.info('import finished!!')


def getArgs():
    parser = ArgumentParser(prog='质控点设置', description='导入质控点')
    parser.add_argument('-f', dest='file', help='上传一个文件, 输出文件前10行', type=argparse.FileType(mode='r', encoding='utf-8'))
    parser.add_argument('--db-url', dest='dbUrl', default='mysql+pymysql://root:rxthinkingmysql@mysql.infra-default:3306/qcmanager?charset=utf8mb4', help='数据库url, Default:%(default)s')
    return parser


def STREAMLIT_FUNCTION(args):
    if args.file:
        empdata = pd.read_csv(args.file.name)
        db = QCDataBaseManager(args.dbUrl)
        db.importQcItems(empdata)


STREAMLIT_PARSER = getArgs()
