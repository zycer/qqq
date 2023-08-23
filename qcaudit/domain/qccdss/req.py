from dataclasses import dataclass
from qcaudit.domain.req import ListRequestBase

@dataclass
class GetAuditInfoBaseRequest(ListRequestBase):
	caseId: str = ''
	withContent: bool = True
	dataModified: str = ''
	size: int = 10000
	is_export: int = 1
