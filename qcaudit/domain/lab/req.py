
from dataclasses import dataclass
from qcaudit.domain.req import ListRequestBase


@dataclass
class GetLabListRequest(ListRequestBase):
    caseId: str = ''
    withContent: bool = False
    size: int = 10000
