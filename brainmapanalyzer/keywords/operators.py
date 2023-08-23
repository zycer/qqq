#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-02-15 18:47:09

'''
class Operator(object):
    """The Operator
    """
    def __init__(self, _id, text, operand, key = "", tip = ""):
        """Create a new Operator
        Parameters:
            _id                   
            text   
            operand                    
        """
        self._id = _id
        self.text = text
        self.operand = operand
        # key唯一标识一个oprator对象,为了解决不同数据类型operator,_id一样，text不一样的问题
        self.key = key
        # 操作符的详细说明
        self.tip = tip
    
    @property
    def Id(self):
        return self._id

OPT_IS      = 'is'
OPT_ISNOT   = 'isnot'
OPT_NORM    = 'norm'
OPT_ABNORM  = 'abnorm'
OPT_INCLUDE = 'include'
OPT_EXCLUDE = 'exclude'
OPT_EXACTINCLUDE = 'exactInclude'
OPT_REGEX = 'regex'
OPT_EQ      = 'eq'
OPT_NE      = 'ne'
OPT_GT      = 'gt'
OPT_GTE     = 'gte'
OPT_LT      = 'lt'
OPT_LTE     = 'lte'
OPT_BW      = 'bw'
OPT_BW_FIELD  = 'bwfield'

# The bool operators
isOperator = Operator(_id = OPT_IS, text = u'是', operand = 0, key="isOperator")
isNotOperator = Operator(_id = OPT_ISNOT, text = u'否', operand = 0, key="isNotOperator")

# The normal / abnormal operators
normOperator = Operator(_id = OPT_NORM, text = u'正常', operand = 0, key="normOperator")
abnormOperator = Operator(_id = OPT_ABNORM, text = u'异常', operand = 0, key="abnormOperator")

# The number operators
eqNumOperator = Operator(_id = OPT_EQ, text = u'等于', operand = 1, key="eqNumOperator")
neNumOperator = Operator(_id = OPT_NE, text = u'不等于', operand = 1, key="neNumOperator")
gtNumOperator = Operator(_id = OPT_GT, text = u'大于', operand = 1, key="gtNumOperator")
gteNumOperator = Operator(_id = OPT_GTE, text = u'大于或等于', operand = 1, key="gteNumOperator")
ltNumOperator = Operator(_id = OPT_LT, text = u'小于', operand = 1, key="ltNumOperator")
lteNumOperator = Operator(_id = OPT_LTE, text = u'小于或等于', operand = 1, key="lteNumOperator")
bwNumOperator = Operator(_id = OPT_BW, text = u'介于', operand = 2, key="bwNumOperator")

# The string operators
includeStrOperator = Operator(_id = OPT_INCLUDE, text = u'包含', operand = 1, key="includeStrOperator")
excludeStrOperator = Operator(_id = OPT_EXCLUDE, text = u'不包含', operand = 1, key="excludeStrOperator")
eqStrOperator = Operator(_id = OPT_EQ, text = u'等于', operand = 1, key="eqStrOperator")
neStrOperator = Operator(_id = OPT_NE, text = u'不等于', operand = 1, key="neStrOperator")
exactIncludeStrOperator = Operator(_id = OPT_EXACTINCLUDE, text = u'精确包含', operand = 1, key="exactIncludeStrOperator")
regexStrOperator = Operator(_id = OPT_REGEX, text = u'正则匹配', operand = 1, key="regexStrOperator",
    tip = "注：此正则只有两个特殊字符，#匹配1个字符，*匹配多个字符。示例：#痛变异型*: 痛变异型完全包含，“痛”前面只有1个字符，“型”后面包含其他字符（不限定字符数）")

# The datetime operators
eqTimeOperator = Operator(_id = OPT_EQ, text = u'在', operand = 1, key="eqTimeOperator")
neTimeOperator = Operator(_id = OPT_NE, text = u'不在', operand = 1, key="neTimeOperator")
gtTimeOperator = Operator(_id = OPT_GT, text = u'晚于', operand = 1, key="gtTimeOperator")
gteTimeOperator = Operator(_id = OPT_GTE, text = u'不早于', operand = 1, key="gteTimeOperator")
ltTimeOperator = Operator(_id = OPT_LT, text = u'早于', operand = 1, key="ltTimeOperator")
lteTimeOperator = Operator(_id = OPT_LTE, text = u'不晚于', operand = 1, key="lteTimeOperator")
bwTimeOperator = Operator(_id = OPT_BW, text = u'介于', operand = 2, key="bwTimeOperator")
# 时间在 另一个字段 的 前x天-后y天之间
bwFieldTimeOperator = Operator(_id = OPT_BW_FIELD, text = u'介于(参照字段)', operand = 3, key='bwFieldTimeOperator')

allOperators = [normOperator, abnormOperator,isOperator,isNotOperator,eqNumOperator,
    neNumOperator, gtNumOperator, gteNumOperator, ltNumOperator,lteNumOperator,bwNumOperator,
    includeStrOperator,excludeStrOperator,eqStrOperator,neStrOperator, exactIncludeStrOperator,
    regexStrOperator, eqTimeOperator,neTimeOperator, 
    gtTimeOperator,gteTimeOperator,ltTimeOperator,lteTimeOperator,bwTimeOperator, bwFieldTimeOperator]

allOperatorsMap = {
    op.Id: op for op in allOperators
}
