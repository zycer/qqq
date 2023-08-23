#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-07 17:40:23

'''


from qcaudit.app import Application
from qcaudit.domain.domainbase import DomainBase, MongoDomainBase


class RepositoryBase(object):

    def __init__(self, app: Application, auditType=''):
        self.app = app
        self.auditType = auditType

    def add(self, session, item: DomainBase):
        session.add(item.model)

class MongoRepositoryBase(RepositoryBase):

    def update(self, obj: MongoDomainBase, upsert=False):
        obj.getCollection(self.app.mongo).update_one(
            {
                '_id': obj.doc['_id']
            },
            obj.doc,
            upsert=upsert
        )
    
    def add(self, obj: MongoDomainBase):
        obj.getCollection(self.app.mongo).insert_one(
            obj.doc
        )
    
    def delete(self, obj: MongoDomainBase):
        obj.getCollection(self.app.mongo).deleteOne(
            {'_id': obj.doc['_id']}
        )
