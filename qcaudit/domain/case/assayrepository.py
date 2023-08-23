from qcaudit.domain.repobase import RepositoryBase
from qcaudit.app import Application
from qcaudit.domain.case.req import GetAssayListRequest
from qcaudit.domain.case.assay import AssayDocument


class AssayRepository(RepositoryBase):
	def __init__(self, app: Application, auditType: str):
		super().__init__(app, auditType)
		self.assayInfoModel = app.mysqlConnection['labInfo']
		self.assayContentModel = app.mysqlConnection['labContent']

	def getAssayList(self, session, req: GetAssayListRequest):
		"""
		获取化验数据
		"""
		if req.withContent:
			query = session.query(self.assayInfoModel,self.assayContentModel).join(
				self.assayContentModel, self.assayInfoModel.id == self.assayContentModel.reportId
			)
		else:
			query = session.query(self.assayInfoModel)
		query = req.apply(query, self.app.mysqlConnection)
		result = []
		for row in query.all():
			if req.withContent:
				result.append(AssayDocument(row[0],row[1]))
			else:
				result.append(AssayDocument(row))
		return result
