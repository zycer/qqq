#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-08 14:05:35

'''

from dataclasses import dataclass
from typing import Iterable, List
from qcaudit.domain.case.order import Order, DrugTag
from qcaudit.domain.case.req import GetOrderListRequest
from qcaudit.domain.repobase import RepositoryBase

@dataclass
class OrderType:

    code: str
    name: str    


class OrderRepository(RepositoryBase):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.model = Order.getModel(app)
        self.drugTagModel = DrugTag.getModel(app)

    def getList(self, caseId, category):
        """获取医嘱列表

        Args:
            caseId ([type]): [description]
            category ([type]): [description]
        """
        raise NotImplementedError()
    
    def search(self, session, req: GetOrderListRequest) -> List[Order]:
        orders = []
        query = session.query(self.model)
        query = req.apply(query, self.app.mysqlConnection)
        for row in query:
            session.expunge(row)
            orders.append(Order(row))
        return orders
    
    def count(self, session, req: GetOrderListRequest) -> int:
        query = session.query(self.model)
        query = req.applyFilter(query, self.app.mysqlConnection)
        return query.count()

    def getOrderTypes(self, session, caseId) -> List[OrderType]:
        """获取这个病历中所有的医嘱类型

        Args:
            caseId ([type]): [description]
        """
        result = []
        for row in session.query(self.model.order_flag, self.model.order_flag_name).filter_by(
            caseId=caseId
        ):
            result.append(OrderType(row[0], row[1]))
        return result

    def getDrugTags(self, session):
        result = dict()
        for row in session.query(self.drugTagModel.name, self.drugTagModel.category).filter(
            self.drugTagModel.category != 'N'
        ):
            result[row.name] = row.category
        return result
