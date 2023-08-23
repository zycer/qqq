#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 13:50:57

'''

from typing import Any
from qcaudit.app import Application
from qcaudit.infra.util import ModelUtil
import copy
import json
from sqlalchemy.exc import InvalidRequestError


class DomainBase(object):
    """领域对象的基类, 按照以下原则进行基础设施层(Repository)/领域层(Domain)/应用层(application)的划分:
    1. 基础设施层
        处理所有的增删改查操作, 操作数据库, 其他层均不直接操作数据库, 而是通过Repository来操作数据库.
        尽量避免在这里写逻辑, 仅暴露增删改查函数即可.
    2. 领域层: 
        1) Domain: 只处理单个对象内部的属性变更, 不涉及其他对象,也不涉及多对象, 不涉及对Repository的调用.
        2) DomainService: 可处理同一类对象的操作, 但不操作其他领域, DomainService中可以访问Repository
    3. 应用层
        实现跨领域的业务逻辑.
    4. 接口层: 这一层就是grpc生成的Service类, 主要是完成三个工作
        1) 参数检查, 将请求参数转换成上面三层的函数入参
        2) 调用上面3层的函数处理请求.
        3) 并将返回结果填充到grpc的response中.
        注意: 在接口层尽量不编写业务逻辑, 如果不是调用函数直接能拿到结果的, 就在应用层增加函数来封装业务逻辑.
    """

    # 数据库中对应的表名
    TABLE_NAME = ''

    def __init__(self, model):
        self.model = model
    
    def expungeInstance(self, session, *instances):
        for instance in instances:
            if not instance:
                continue
            try:
                session.expunge(instance)
            except InvalidRequestError as e:
                pass

    def expunge(self, session):
        """sqlalchemy的对象在session被销毁后便不可访问属性, 需要执行expunge来解除与session的关系.若子类使用了不止一个model对象则需要重写此函数将所有的model对象都expunge掉, 否则只能在session存活期间使用.

        Args:
            session ([type]): [description]
        """
        self.expungeInstance(session, self.model)
    
    def __getattr__(self, key):
        return getattr(self.model, key)
    
    def setModel(self, **kwargs):
        """设置对应model的值, 注意model是查询得到的将会在commit后直接修改数据库
        """
        for name, value in kwargs.items():
            setattr(self.model, name, value)

    def asDict(self):
        return ModelUtil.asDict(self.model)
    
    def asJson(self):
        return ModelUtil.asJson(self.model)
    
    @classmethod
    def getModel(cls, app: Application):
        return app.mysqlConnection[cls.TABLE_NAME]

    @classmethod
    def newObject(cls, app, **kwargs) -> Any:
        """创建一个新的实例

        Args:
            app ([type]): [description]

        Returns:
            [type]: [description]
        """
        item = cls(app.mysqlConnection[cls.TABLE_NAME]())
        if kwargs:
            item.setModel(**kwargs)
        return item
    
    def validate(self) -> bool:
        """参数校验

        Returns:
            bool: [description]
        """
        raise NotImplementedError()

class MongoDomainBase(object):

    DATABASE = ''
    COLLECTION = ''

    def __init__(self, doc):
        self.doc = doc

    def __getattr__(self, key):
        if self.doc:
            return self.doc.get(key)
        return ""
    
    def setModel(self, name: str, value: Any):
        self.doc[name] = value
    
    def asDict(self):
        return copy.deepcopy(self.doc)
    
    def asJson(self):
        return json.dumps(self.doc, ensure_ascii=False)

    @classmethod
    def getCollection(cls, client):
        return client[cls.DATABASE][cls.COLLECTION]

    @classmethod
    def getById(cls, client, id):
        col = cls.getCollection(client)
        doc = col.find_one({'_id': id})
        return cls(doc)
