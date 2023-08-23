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

    def importQcRules(self, dataframe: pd.DataFrame):
        with self.session() as session:
            #
            CategoryModel = self.models['qcCategory']
            CateItemsModel = self.models['qcCateItems']
            # 规则组
            group_dict = {}
            for group in session.query(self.models['qcGroup']).all():
                group_dict[group.name] = group.id
            # 质控点
            qcitem_dict = {}
            for item in session.query(self.models['qcItem']).all():
                qcitem_dict[item.code] = item.id
            # 处理数据
            for idx, data in dataframe.iterrows():
                group = data['规则组']
                category = data['规则组分类']
                code = data['质控点编号']
                score = data['每处扣分']
                maxScore = data['最高分']
                # validate
                if pd.isnull(group) or not group:
                    logging.info(f'exception empty group, column: {idx}')
                    continue
                if pd.isnull(code) or not code:
                    logging.info(f'exception empty item-code, column: {idx}')
                    continue
                if pd.isnull(category) or not category:
                    category = ''
                # 分数
                if pd.isnull(score) or not score:
                    score = 1
                if pd.isnull(maxScore) or not maxScore:
                    maxScore = 100
                score = re.search(r'\d+\.?\d*', f'{score} 默认1分').group()
                maxScore = re.search(r'\d+\.?\d*', f'{maxScore} 默认100分').group()
                # 规则组id
                if not group_dict.get(group):
                    logging.info(f'exception wrong group, column: {idx}, group: {group}')
                    continue
                groupId = group_dict.get(group)
                # 质控点
                if not qcitem_dict.get(code):
                    logging.info(f'exception wrong qcItem-code, column: {idx}')
                    continue
                qcitemId = qcitem_dict.get(code)
                # 规则组类别
                categoryId = 0
                if category:
                    qc_category = session.query(CategoryModel).filter_by(groupId=groupId, name=category).first()
                    if not qc_category:
                        tmp = session.query(CategoryModel).filter_by(groupId=groupId).first()
                        qc_category = CategoryModel(name=category, groupId=groupId, parentId=tmp.id, maxScore=100,
                                                    created_at=datetime.datetime.now(), is_deleted=0)
                        session.add(qc_category)
                        session.commit()
                    categoryId = qc_category.id
                else:
                    qc_category = session.query(CategoryModel).filter_by(groupId=groupId).first()
                    categoryId = qc_category.id
                # 分数
                if maxScore and score and float(maxScore) < float(score):
                    maxScore = score
                # 质控规则
                qcCateItem = session.query(CateItemsModel).filter_by(groupId=groupId, itemId=qcitemId).first()
                if not qcCateItem:
                    row = CateItemsModel(groupId=groupId, categoryId=categoryId, itemId=qcitemId, score=float(score),
                                         maxScore=float(maxScore))
                    session.add(row)
                else:
                    qcCateItem.categoryId = categoryId
                    qcCateItem.score = float(score)
                    qcCateItem.maxScore = float(maxScore)
        logging.info('import finished!!')
        return """
        导入完成。
        
        *特别说明：
        - 质控点扣分分值从给定的设置中正则匹配第一个数值，默认质控点扣分1分，默认最高分100分。
        - 规则组类别如果不存在会自动创建。
        - 只会更新规则组设置，没有删除操作。
        """


def getArgs():
    parser = ArgumentParser(prog='规则组设置', description='导入规则组')
    parser.add_argument('-f', dest='file', help='上传规则组设置', type=argparse.FileType(mode='r', encoding='utf-8'))
    parser.add_argument('--db-url', dest='dbUrl',
                        default='mysql+pymysql://root:rxthinkingmysql@mysql.infra-default:3306/qcmanager?charset=utf8mb4',
                        help='数据库url, Default:%(default)s')
    return parser


def STREAMLIT_FUNCTION(args):
    if args.file:
        tmpdata = pd.read_csv(args.file.name)
        db = QCDataBaseManager(args.dbUrl)
        return db.importQcRules(tmpdata)


STREAMLIT_PARSER = getArgs()
