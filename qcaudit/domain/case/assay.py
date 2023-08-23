from typing import List
from qcaudit.domain.domainbase import DomainBase


class AssayDocument(DomainBase):

	def __init__(self, model, contentModel=None):
		super().__init__(model)
		self.content = contentModel

	def expunge(self, session):
		self.expungeInstance(session, self.model, self.content)

	@property
	def assayCode(self):
		return self.content.code

	@property
	def assayResult(self):
		return self.content.result

	@property
	def assayReference(self):
		return self.content.valrange

	@property
	def assayUnit(self):
		return self.content.unit

	@property
	def assayAbnormal(self):
		return self.content.abnormalFlag