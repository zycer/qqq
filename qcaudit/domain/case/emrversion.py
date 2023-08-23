from qcaudit.domain.domainbase import DomainBase


class EmrVersion(DomainBase):
	def __init__(self, model, audit_record=None):
		super().__init__(model)
		self.audit_record = audit_record

	def expunge(self, session):
		self.expungeInstance(session, self.model, self.audit_record)
