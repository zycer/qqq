from qcaudit.domain.domainbase import DomainBase


class Operation(DomainBase):
	TABLE_NAME = 'operation'

	def __init__(self, model, operationDict=None):
		self.model = model
		self.operationDict = operationDict

class CodingOperation(DomainBase):
	"""手术"""
	TABLE_NAME = 'operation_info'

	def __init__(self, model, *args, **kwargs):
		self.model = model
		self.operator = kwargs.get('operator', '')
		self.helperOne = kwargs.get('helperOne', '')
		self.helperTwo = kwargs.get('helperTwo', '')
		self.narcosisDoctor = kwargs.get('narcosisDoctor', '')


class OperationDict(DomainBase):

	TABLE_NAME = "mi_operation_dict"
