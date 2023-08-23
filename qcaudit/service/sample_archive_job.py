#!/usr/bin/env python3
import json
import logging

import redis

from qcaudit.common.const import SAMPLE_ARCHIVE_REDIS_LIST_KEY


class SampleArchiveJob:

    def __init__(self, context):
        self.context = context

    def task(self):

        r = redis.Redis(connection_pool=self.context.app.redis_pool)

        data = r.blpop(SAMPLE_ARCHIVE_REDIS_LIST_KEY, 10)
        while data:
            try:
                logging.info(f"sample archive, data = {data}")
                req = json.loads(data[1])
                auditType = req.get("auditType")
                caseId = req.get("caseId")
                operatorId = req.get("operatorId")

                if not auditType or not caseId:
                    continue

                app = self.context.getAuditApplication(auditType)
                if not app:
                    continue
                app.archiveSampleCase(auditType, caseId, operatorId)

            except Exception as e:
                logging.info("load data failed, err: %s, data: %s" % (e, data))

            finally:
                data = r.blpop(SAMPLE_ARCHIVE_REDIS_LIST_KEY, 10)

        logging.info("sample archive task finished.")



