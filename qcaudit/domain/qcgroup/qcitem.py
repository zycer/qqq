#!/usr/bin/env python3
from qcaudit.common.const import QCITEM_TAGS
from qcaudit.domain.domainbase import DomainBase


class QcItem(DomainBase):

    TABLE_NAME = 'qcItem'

    def getId(self):
        return self.model.id

    def getTags(self):
        tags = []

        if self.model.veto == 1:
            tags.append('强控')
        elif self.model.veto == 2:
            tags.append('否决')

        if self.model.tags:
            for tag in self.model.tags.split(','):
                if QCITEM_TAGS.get(tag):
                    tags.append(QCITEM_TAGS.get(tag))
        if self.model.type == 2:
            tags.append('专科')
        elif self.model.type == 3:
            tags.append('专病')
        return tags

    def isFPRequired(self):
        """是否是首页必填项问题
        """
        return self.model.is_fprequired or 0

    def isSingleDisease(self):
        if self.model.tags:
            if 'single' in self.model.tags.split(','):
                return True
        return False

    def isVeto(self):
        if self.model.veto == 2:
            return True
        return False
