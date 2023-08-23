#!/usr/bin/env python3
import re

from qcaudit.domain.domainbase import DomainBase


class ScoreReportTemplate(DomainBase):

    TABLE_NAME = 'score_report_template'


class ScoreReportItems(DomainBase):

    TABLE_NAME = 'score_report_qcitems'


class ScoreReport(DomainBase):

    def __init__(self, model, itemsModel=None):
        super().__init__(model)
        self.items = itemsModel

    def generateReport(self, case_detail, problems):
        items_dict = {}
        details = {}
        details_count = {}
        for tmp in self.items:
            if not tmp.qcitems:
                continue
            for item in tmp.qcitems.split(','):
                items_dict[str(item)] = tmp.name
        for p in problems:
            marker = items_dict.get(str(p.qcItemId))
            if not marker or p.getScore() <= 0:
                continue
            if not details.get(marker):
                details[marker] = ''
                details_count[marker] = 0
            score = '{:g}'.format(float(p.getScore()))
            details[marker] += f'{details_count[marker] + 1}.{p.reason}。{p.comment}【-{score}】<br/>'
            details_count[marker] += 1
        report = self.mapKeyword(self.model.template, case_detail)
        report = self.mapKeyword(report, details)
        # 清理不存在字段的标志
        report = re.sub(r'\{[A-z_0-9]{1,}\}', '', report)
        return report

    def mapKeyword(self, template, details):
        if not template:
            template = self.model.template or ''
        for k, v in details.items():
            keyword = "{%s}" % k
            if not v:
                v = ''
            if not isinstance(v, str):
                v = str(v)
            template = template.replace(keyword, v)
        return template


