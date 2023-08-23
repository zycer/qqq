#!/usr/bin/env python3
"""
  规则组
"""
import logging
from typing import List
from qcaudit.domain.domainbase import DomainBase
from qcaudit.domain.problem.problem import Problem
from qcaudit.domain.qcgroup.score_calculator import ScoreNode


class QcCategory(DomainBase):
    """规则组-类别
    """
    TABLE_NAME = 'qcCategory'


class QcCateItems(DomainBase):
    """规则组-规则项
    """
    TABLE_NAME = 'qcCateItems'

    def __init__(self, model, qcItemModel=None):
        super().__init__(model)
        self.qcItemModel = qcItemModel


class QcGroup(DomainBase):
    TABLE_NAME = 'qcGroup'

    def __init__(self, model, qcCategories=None, qcItems=None):
        super().__init__(model)
        self.categories = qcCategories
        self.items = qcItems
        self.initCalculator()

    def initCalculator(self):
        """构建分数计算器
        """
        self.scoreCalculator = ScoreNode(nid=0, parentId=0, score=0, maxScore=100, name="root", ntype="规则组")
        for c in self.categories:
            self.scoreCalculator.addChild(ScoreNode(nid=c.id, parentId=c.parentId, maxScore=c.maxScore, name=c.name, ntype="规则分组"))
        for i in self.items:
            self.scoreCalculator.addChild(ScoreNode(nid=f'qci-{i.id}', parentId=i.categoryId, maxScore=float(i.maxScore), name=f'质控点{i.itemId}', ntype="qcItem"))

    def getItem(self, itemId: int):
        """查询质控规则项
        """
        for item in self.items:
            if item.itemId == itemId:
                return item
        return None

    def addProblems(self, problems: List[Problem]):
        """挂载质控问题
        """
        for p in problems:
            categoryId = 0
            maxScore = 0
            qc_cate_item = self.getItem(p.getQcItemId())
            if not qc_cate_item:
                # logging.info(f'规则组中不包含{p.getQcItemId()}')
                maxScore = p.getScore()
                continue
            else:
                # logging.info(f'规则组包含{p.getQcItemId()}')
                categoryId = qc_cate_item.categoryId
                maxScore = qc_cate_item.maxScore
            self.scoreCalculator.addChild(ScoreNode(nid=-1, parentId=f'qci-{qc_cate_item.id}',
                                                    score=p.getScore() if p.getDeductFlag() else 0,
                                                    maxScore=maxScore,
                                                    name=p.getReason(),
                                                    ext={
                                                        'docId': p.getDocId(),
                                                        'singleScore': p.getSingleScore(),
                                                        'problemCount': p.getProblemCount(),
                                                        'createTime': p.getCreateTime(),
                                                        'operatorName': p.getOperatorName()
                                                    }))

    def getCurrentScore(self):
        """当前得分
        """
        return self.scoreCalculator.maxScore - self.scoreCalculator.getScore()

    def printCalculator(self):
        self.scoreCalculator.print_tree()

    def getDeductDetail(self):
        return self.scoreCalculator.getDeductDetail()
