#!/usr/bin/env python3

from qcaudit_lxrmyy.audit.caseapplication import CaseApplication
from qcaudit.common.const import AUDIT_TYPE_DEPARTMENT, AUDIT_TYPE_EXPERT, AUDIT_TYPE_FIRSTPAGE, AUDIT_TYPE_HOSPITAL
from qcaudit.context import Context as _Context
from qcaudit_lxrmyy.audit.auditapplication import AuditApplication


class FirstpageAuditApplication(AuditApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_FIRSTPAGE)


class HospitalAuditApplication(AuditApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_HOSPITAL)


class ExpertAuditApplication(AuditApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_EXPERT)


class HospitalCaseApplication(CaseApplication):
    def __init__(self, app):
        super().__init__(app, AUDIT_TYPE_HOSPITAL)


class Context(_Context):
    def __init__(self, app):
        super().__init__(app)
        self.customizeApplication()

    def customizeApplication(self):
        self._auditApps[AUDIT_TYPE_HOSPITAL] = HospitalAuditApplication(self.app)
        self._auditApps[AUDIT_TYPE_FIRSTPAGE] = FirstpageAuditApplication(self.app)
        self._auditApps[AUDIT_TYPE_EXPERT] = ExpertAuditApplication(self.app)
        self._caseApps[AUDIT_TYPE_HOSPITAL] = HospitalCaseApplication(self.app)


