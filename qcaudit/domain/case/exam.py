from qcaudit.domain.domainbase import DomainBase


class ExamDocument(DomainBase):
	def __init__(self, model, contentModel=None):
		super().__init__(model)
		self.content = contentModel

	def expunge(self, session):
		self.expungeInstance(session, self.model, self.content)

	@property
	def examDesc(self):
		return self.content.description

	@property
	def examResult(self):
		return self.content.result


class ExamReport(DomainBase):

	def __init__(self, model, contentModels=None):
		super().__init__(model)
		self.contents = contentModels

	def expunge(self, session):
		for item in self.contents:
			self.expungeInstance(session, item)
		self.expungeInstance(session, self.model)

	def getReportId(self):
		return self.model.id
