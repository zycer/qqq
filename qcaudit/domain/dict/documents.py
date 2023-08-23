#!/usr/bin/env python3
"""
文书对照关系
"""
from qcaudit.domain.domainbase import DomainBase


class Documents(DomainBase):

    TABLE_NAME = 'documents'

    def getStandardName(self):
        return self.model.standard_name
