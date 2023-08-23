#!/usr/bin/env python3
from typing import List
from qcaudit.app import Application
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.domain.report.score_report import ScoreReportTemplate, ScoreReportItems, ScoreReport


class ScoreReportRepository(RepositoryBase):

    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.tplModel = ScoreReportTemplate.getModel(app)
        self.itemsModel = ScoreReportItems.getModel(app)

    def get(self, session, tplCode):
        template = session.query(self.tplModel).filter_by(code=tplCode).first()
        if not template:
            return None
        items = session.query(self.itemsModel).filter_by(code=tplCode).all()
        return ScoreReport(template, items)
