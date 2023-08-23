#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 19:28:53

'''

from typing import List
from qcaudit.domain.domainbase import DomainBase

class RefuseHistory(DomainBase):

    TABLE_NAME = 'refuse_history'

    def __init__(self, model):
        super().__init__(model)
    
    def getRefuseDoctors(self) -> List[str]:
        """获取驳回给哪些医生

        Returns:
            List[str]: [description]
        """
        if not self.problems:
            return []
        return list(set([
            p.get('refuseCode') for p in self.problems if p.get('refuseCode')
        ]))
                