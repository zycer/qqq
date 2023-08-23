from qcaudit.domain.message.message_repository import MessageRepo


class MessageFactory(object):

	@classmethod
	def getMessageRepository(cls, context, auditType) -> MessageRepo:
		return MessageRepo(context, auditType)
