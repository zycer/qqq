#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 22:38:48

'''

from dataclasses import dataclass
from typing import List
from qcaudit.domain.case.case import CaseDoctor
from qcaudit.domain.domainbase import DomainBase

class EmrContent(DomainBase):

    pass

class EmrDocument(DomainBase):

    def __init__(self, model, contentModel=None, doc_types=None):
        super().__init__(model)
        self.content = contentModel
        self.doc_types = doc_types
    
    def expunge(self, session):
        self.expungeInstance(session, self.model, self.content)
    
    def getDoctors(self) -> List[CaseDoctor]:
        """获取病历中涉及到的医生

        Returns:
            List[CaseDoctor]: [description]
        """
        result = []
        if self.doctors:
            for d in self.doctors:
                if isinstance(d, dict):
                    result.append(CaseDoctor(code=d.get('EMPID', '').upper(), name=d.get('NAME', '')))
            return result
        else:
            return []
    
    def setRefuseDoctor(self, refuseCode):
        """设置驳回医生

        Args:
            refuseCode ([type]): [description]
        """
        if refuseCode:
            self.setModel(
                refuseCode=refuseCode
            )

    def getDocumentName(self):
        return self.model.documentName

    def getRefuseDoctor(self):
        return self.model.refuseCode

    def getEmrContentId(self):
        return self.model.emrContentId

    def getEmrHtml(self):
        if self.content:
            return self.content.htmlContent
        return ""

    def getEmrContents(self):
        if self.content:
            return self.content.contents
        return []

    def getUpdateTime(self):
        if self.content:
            return self.content.updateTime
        return ""

    def getMd5(self):
        if self.content:
            return self.content.md5 or ""
        return ""

    def getDocTypes(self):
        return self.doc_types or []

    def getOriginType(self):
        return self.model.originType or ""

    def getSimpleDocumentName(self):
        """去掉文书名称中的空格和括号以及括号之间的内容
        没有处理括号不成对的情况
        病案（123）456）首页 =》 病案456首页
        病案（123首页 =》 病案
        病案（123）首页 =》 病案首页

        截取第一个+号前的名称，
        病案首页+病程记录 =》 病案首页
        病程记录+病案首页 =》 病程记录
        """
        name = ""
        flag = 0
        for item in self.getDocumentName().strip():
            # 括号和括号之间的内容去掉
            if item == '(' or item == '（':
                flag += 1
            if item == ')' or item == '）':
                if flag > 0:
                    flag -= 1
                continue
            if flag:
                continue

            # 只留下第一个+号前面的内容
            if item == '+':
                break
            if item == '\n':
                break
            # # 入ICU记录以及抗生素、生长抑素使用记录 =》 入ICU记录
            # if item == "及" or item == "暨":
            #     if name and name[-1] == "以":
            #         name = name[:-1]
            #     break

            name += item

        return name
