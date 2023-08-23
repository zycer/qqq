#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-05-11 10:14:12

'''
from operator import or_
from typing import Dict, Iterable, List
from qcaudit.app import Application
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.domain.dict.doctor import Doctor

class DoctorRepository(RepositoryBase):
    
    def __init__(self, app: Application, auditType):
        super().__init__(app, auditType)
        self.model = Doctor.getModel(app)
    
    def getByCodes(self, session, codes: List[str]) -> List[Doctor]:
        """根据医生编码获取医生

        Args:
            session ([type]): [description]
            codes (str): [description]

        Returns:
            Dict[str, Doctor]: [description]
        """
        doctors = []
        for row in session.query(self.model).filter(self.model.id.in_(codes)):
            doctors.append(Doctor(row))
        return doctors
    
    def get(self, session, code: str):
        """根据id获取医生

        Args:
            session ([type]): [description]
            code (str): [description]

        Returns:
            [type]: [description]
        """
        row = session.query(self.model).filter(
            self.model.id == code
        ).first()
        return Doctor(row)
    
    def search(self, session, kword, attendingFlag=False, department='') -> List[Doctor]:
        """搜索医生

        Args:
            session ([type]): [description]
            kword ([type]): [description]
        """
        query = session.query(self.model).filter(
            or_(self.model.name.contains(kword), self.model.initials.contains(kword.upper()))
        ).filter(self.model.useflag==1)
        if department:
            query = query.filter(self.model.department == department)
        if attendingFlag:
            query = query.filter_by(role='A')
        doctors = []
        for row in query:
            doctors.append(Doctor(row))
        return doctors
