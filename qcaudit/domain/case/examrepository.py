from qcaudit.domain.repobase import RepositoryBase
from qcaudit.app import Application
from qcaudit.domain.case.req import GetExamListRequest
from qcaudit.domain.case.exam import ExamDocument


class ExamRepository(RepositoryBase):
    def __init__(self, app: Application, auditType: str):
        super().__init__(app, auditType)
        self.examInfoModel = app.mysqlConnection['examInfo']
        self.examContentModel = app.mysqlConnection['examContent']

    def getExamList(self, session, req: GetExamListRequest):
        """
        获取检查数据
        """
        query = session.query(self.examInfoModel, self.examContentModel). \
            join(self.examContentModel, self.examInfoModel.id == self.examContentModel.reportId). \
            filter(self.examInfoModel.caseId == req.caseId, self.examContentModel.caseId == req.caseId). \
            filter(self.examInfoModel.is_deleted == 0)
        count = query.count() if req.withTotal else 0
        query = query.order_by(self.examInfoModel.reportTime.is_(None), self.examInfoModel.reportTime.asc()).slice(req.start, req.start + req.size)
        result = []
        for row in query.all():
            result.append(ExamDocument(row[0], row[1]))
        return result, count
