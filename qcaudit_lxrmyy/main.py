#!/usr/bin/env python3

""" The hospqc main entry
"""

import logging

from qcaudit.main import main as _main
from qcaudit_lxrmyy.audit.auditservice import AuditService
from qcaudit.service.sampleservice import SampleServicer
from qcaudit.service.stats_service import StatsService
from qcaudit.service.doctor_service import DoctorService
from qcaudit.service.qcitems_service import QCItemsServer


from qcaudit_lxrmyy.context import Context


DefaultFlagVarsPath = "/var/run/rxthinking.com/hospqc/flags"

logger = logging.getLogger('hospqc')
DefaultTimeout = 120.0  # 90s
DefaultMongodbDatabase = "iam"


def main():
    _main(ContextClass=Context, ServiceClasses=[AuditService, SampleServicer, StatsService, DoctorService, QCItemsServer])


