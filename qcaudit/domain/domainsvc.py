#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-08 10:41:29

'''

class DomainService(object):

    def __init__(self, app, auditType):
        self.app = app
        self.auditType = auditType
        