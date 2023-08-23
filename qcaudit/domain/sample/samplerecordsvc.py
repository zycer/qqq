#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2021-04-22 13:51:44

'''
from qcaudit.domain.domainsvc import DomainService
from qcaudit.domain.sample.expertuserrepository import ExpertUserRepository
from qcaudit.domain.sample.samplerecord import SampleRecord
from qcaudit.domain.sample.samplerecordrepository import SampleRecordRepository
# from qcaudit.common.exception import GrpcInvalidArgumentException


class SampleRecordService(DomainService):

    def __init__(self, app, auditType):
        super().__init__(app, auditType)
        self.repo = SampleRecordRepository(app, auditType)
        self.expertRepo = ExpertUserRepository(app, auditType)

    def assignExpert(self, session, sampleRecordId: int, caseType: str, assignType: str, auditType: str = ""):
        """给抽取结果分配专家

        Args:
            session ([type]): [description]
            sampleRecordId ([int]): [description]
            caseType ([str]): [description]
            assignType ([str]): [description]
            auditType ([str]): [description]
        """
        # if assignType == SampleRecord.ASSIGN_TYPE_AVG:
        #     # 获取所有的专家
        #     users = list(self.expertRepo.getList(session, caseType))
        #     userCount = len(users)
        #     if userCount == 0:
        #         raise ValueError('没有可分配的专家')
        #     items = list(self.repo.getItemList(session, sampleRecordId, auditType))
        #     items = [x for x in items if x.isMannalAssigned not in (1, 2)]  # 1-指定分配, 2-病区分配
        #     for i in range(0, len(items)):
        #         # 决定哪个专家审核
        #         index = i % userCount
        #         item = items[i]
        #         item.assignExpert(users[index].userId, users[index].userName)
        #         if i % 100 == 0:
        #             # 中途提交, 防止数量太多
        #             session.commit()
        # else:
        #     self.assignExpertAuto(sampleRecordId)
        #
        # sampleModel = self.repo.getRecordById(session, sampleRecordId)
        # # 修改抽取记录分配状态
        # sampleModel.model.isAssigned = 2
        # session.commit()
        raise NotImplementedError()

    def assignExpertAuto(self, sampleRecordId: int):
        """定制化功能, 根据医院实际需求去实现代码分配

        Args:
            sampleRecordId (int): [description]
        """
        raise NotImplementedError()
