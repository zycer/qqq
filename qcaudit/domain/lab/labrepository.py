from qcaudit.domain.lab.labreport import LabReport
from qcaudit.domain.lab.req import GetLabListRequest
from qcaudit.domain.repobase import RepositoryBase
from qcaudit.app import Application


class LabRepository(RepositoryBase):
    def __init__(self, app: Application, auditType: str):
        super().__init__(app, auditType)
        self.labInfoModel = app.mysqlConnection['labInfo']
        self.labContentModel = app.mysqlConnection['labContent']

    def getLabReportList(self, session, req: GetLabListRequest):
        """
        获取化验报告数据
        """
        query = session.query(self.labInfoModel, self.labContentModel). \
            join(self.labContentModel, self.labInfoModel.id == self.labContentModel.reportId). \
            filter(self.labInfoModel.caseId == req.caseId, self.labContentModel.caseId == req.caseId). \
            filter(self.labInfoModel.is_deleted == 0). \
            order_by(self.labInfoModel.reportTime.is_(None), self.labInfoModel.reportTime.asc())
        result = []
        count = 0
        report_index = {}  # 记录reportId-index对照关系
        # todo 分页优化
        for row in query.all():
            if report_index.get(row[0].id) is None:
                result.append(LabReport(row[0], [row[1]]))
                report_index[row[0].id] = len(result) - 1
                count += 1
            else:
                result[report_index[row[0].id]].contents.append(row[1])
        return result[req.start: req.start + req.size], count
