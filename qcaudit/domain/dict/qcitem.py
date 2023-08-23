#!/usr/bin/env python3

from qcaudit.domain.domainbase import DomainBase


class QcItem(DomainBase):

    TABLE_NAME = 'qcItem'

    def __init__(self, model, rule=None):
        super().__init__(model)
        self.ruleModel = rule

    def getId(self):
        return self.model.id


class QcItemRule(DomainBase):

    TABLE_NAME = "qcItem_rule"
