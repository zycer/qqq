#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-05-16 11:35:33

'''

# from unittest.mock import MagicMock, patch
from rabbitmqlib.rabbitmqlib.message import Message


def test_message_marshal():
    """测试消息的marshal和unmarshal"""
    msg = Message(
        body={
            'a': 1,
            'b': 2
        },
        parentId='parentId',
    )    
    msg.setExpiration(60)
    msgStr = msg.marshal(exchange='exchange', withMessageId=True)
    recoveredMsg, exchange, routingKey = Message.unMarshal(msgStr)
    
    assert msg.properties.expiration == recoveredMsg.properties.expiration
    assert msg.a == recoveredMsg.a
    assert msg.ParentId == recoveredMsg.ParentId
    assert msg.MessageId == recoveredMsg.MessageId
    assert exchange == 'exchange'
    msgStr1 = msg.marshal(exchange='exchange', withMessageId=False)
    msgStr2 = msg.marshal(exchange='exchange', withMessageId=False)
    assert msgStr1 == msgStr2