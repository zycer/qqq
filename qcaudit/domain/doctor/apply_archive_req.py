from dataclasses import dataclass, field
from typing import List


@dataclass
class ApplyArchiveRequest:
    """申请归档的请求参数
    """
    caseIds: List[int] = field(default_factory=list)
    doctor: str = ""
