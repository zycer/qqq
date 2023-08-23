# coding=utf-8
import argparse
import sys
import datetime
import platform
import logging
from argparse import ArgumentParser

from . import QCDataBaseManager as _QCDataBaseManager

import pandas as pd

logging.basicConfig(level=logging.INFO)


class QCDataBaseManager(_QCDataBaseManager):

    def importScoreReportQcitems(self, dataframe: pd.DataFrame):
        template = {
            '病案首页': 'd1_problems',
            '入院记录': {
                '书写时限': 'd2c1_problems',
                '其他': '',
                '主诉': 'd2c2_problems',
                '现病史': 'd2c3_problems',
                '既往史': 'd2c4_problems',
                '个人史,婚育史,月经史,家族史': 'd2c5_problems',
                '专项评估': 'd2c6_problems',
                '体格检查': 'd2c7_problems',
                '辅助检查': 'd2c8_problems',
                '诊断': 'd2c9_problems',
            },
            '病程记录': {
                '首次病程录': 'd3_problems',
                '上级医师查房记录': 'd4c1_problems',
                '日常病程记录': 'd4c2_problems',
                '围手术期相关记录': 'd4c3_problems',
                '出院（死亡）记录': 'd4c4_problems',
            },
            '知情同意书': 'd5_problems',
            '会诊记录': 'd6_problems',
            '医嘱单': '',
            '书写基本要求': 'd7_problems',
        }

        template_code = 'zhejiang2021'

        with self.session() as session:
            # 质控点列表
            qcitem_dict = {}
            for item in session.query(self.models['qcItem']).all():
                qcitem_dict[str(item.code)] = item.id
            # 质控评分表与质控点对照关系
            srqmodel = self.models['score_report_qcitems']
            # 先清空之前的设置
            session.query(srqmodel).filter(srqmodel.code == template_code).delete()
            session.commit()
            # 处理数据
            for idx, data in dataframe.iterrows():
                emr_name = data['文书']
                item_name = data['项目']
                # validate
                if pd.isnull(emr_name) or not emr_name:
                    logging.info(f'exception empty emr_name, column: {idx}')
                    continue
                if pd.isnull(item_name) or not item_name:
                    logging.info(f'exception empty item-name, column: {idx}')
                    continue
                # 模板占位符
                item_name = item_name.replace('\t', ',').replace('\n', ',').replace(' ', ',')
                item_key = ''
                if isinstance(template.get(emr_name), str):
                    item_key = template.get(emr_name)
                elif isinstance(template.get(emr_name), dict):
                    item_key = template[emr_name].get(item_name, '')
                if not item_key:
                    logging.info(f'cannot find template key, emr-name: {emr_name}, item-name:{item_name}')
                    continue
                # 质控点集合
                items = []
                for tmp in [data['质控点1'], data['质控点2'], data['质控点3']]:
                    if pd.isnull(tmp):
                        continue
                    codes = tmp.replace('\t', ',').replace('\n', ',').replace(' ', ',').split(',')
                    items.extend([code for code in codes if code])
                if not items:
                    logging.info(f'empty qcItems, emr-name: {emr_name}, item-name: {item_name}')
                    continue
                # 保存数据
                count = 0
                data_qcitems = ''
                data_message = ''
                for code in items:
                    if not qcitem_dict.get(code):
                        continue
                    if data_qcitems:
                        data_qcitems += ','
                        data_message += ','
                    data_qcitems += str(qcitem_dict[code])
                    data_message += code
                    count += 1
                    if count % 10 == 0:
                        obj = {
                            'code': template_code,
                            'name': item_key,
                            'qcitems': data_qcitems,
                            'message': data_message,
                        }
                        row = srqmodel(**obj)
                        session.add(row)
                        data_message = ''
                        data_qcitems = ''
                if data_qcitems:
                    obj = {
                        'code': template_code,
                        'name': item_key,
                        'qcitems': data_qcitems,
                        'message': data_message,
                    }
                    row = srqmodel(**obj)
                    session.add(row)
                    session.commit()
        logging.info('import finished!!')


def getArgs():
    parser = ArgumentParser(prog='质控评分表与质控点对照导入', description='导入质控点')
    parser.add_argument('-f', dest='file', help='上传一个文件', type=argparse.FileType(mode='r', encoding='utf-8'))
    parser.add_argument('--db-url', dest='dbUrl', help='数据库url, Default:%(default)s',
                        default='mysql+pymysql://root:rxthinkingmysql@mysql.infra-default:3306/qcmanager?charset=utf8mb4')
    return parser


def STREAMLIT_FUNCTION(args):
    if args.file:
        tmpdata = pd.read_csv(args.file.name)
        db = QCDataBaseManager(args.dbUrl)
        db.importScoreReportQcitems(tmpdata)


STREAMLIT_PARSER = getArgs()
