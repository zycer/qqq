#!/usr/bin/env python3

from qcaudit.domain.domainbase import DomainBase


class LabReport(DomainBase):

    def __init__(self, model, contentModels=None):
        super().__init__(model)
        self.contents = contentModels

    def expunge(self, session):
        for item in self.contents:
            self.expungeInstance(session, item)
        self.expungeInstance(session, self.model)

    def getReportId(self):
        return self.model.id
