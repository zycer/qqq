#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-09 14:45:32

'''

class CommonResult(object):

    def __init__(self, isSuccess=False, message=''):
        self.isSuccess = isSuccess
        self.message = message