#!/usr/bin/env python3
import logging
from decimal import Decimal


class ScoreNode:
    logger = logging.getLogger('score_calculator')

    def __init__(self, nid, parentId, score=None, maxScore=None, name=None, ext=None, ntype=None):
        self.id = nid
        self.parentId = parentId or 0
        self.score = score or 0
        self.maxScore = maxScore or 0
        self.subNodes = []
        self.name = name or ""
        self.ext = ext or {}
        self.type = ntype or ""
        pass

    def addChild(self, node):
        # self.logger.info("add node: %s - %s - %s - %s - %s" % (node.parentId, node.id, node.name, node.maxScore, node.score))
        if self.id == -1:
            return
        if self.id == node.parentId:
            # TODO 考虑一下相同质控点是否需要合并
            self.subNodes.append(node)
            return
        for item in self.subNodes:
            item.addChild(node)

    def getScore(self):
        if len(self.subNodes) <= 0:
            return self.score if self.score <= self.maxScore else self.maxScore
        sub_sum = 0
        for item in self.subNodes:
            sub_sum += Decimal(item.getScore()) if item.getScore() else 0
        return sub_sum if sub_sum <= self.maxScore else self.maxScore

    def print_tree(self):
        self.logger.info("%s - %s - %s - %s - %s" % (self.parentId, self.id, self.name, self.maxScore, self.score))
        for item in self.subNodes:
            item.print_tree()

    def getDeductDetail(self):
        """质控问题扣分明细
        """
        problems = []
        if self.id == -1:
            problems.append({
                'name': self.name,
                'score': self.getScore(),
                'ext': self.ext
            })
            return problems
        for item in self.subNodes:
            problems.extend(item.getDeductDetail())
        return problems

    def getDeductQcItems(self):
        """质控点扣分明细
        """


