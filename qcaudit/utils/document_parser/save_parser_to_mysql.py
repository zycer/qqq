import json

from rabbitmqlib.rabbitmqlib import RabbitMqManager
from rabbitmqlib.rabbitmqlib.message import Message, MessageResult
from redis import Redis
from sqlalchemy import distinct
import arrow
import logging


class ParserListener():
	def __init__(self, mysqlConnection, redis_pool):
		self.mysqlConnection = mysqlConnection
		self.redis_pool = redis_pool

	def callback(self, message: Message):
		body = json.loads(message.Body)
		error = body.get('error', 'false')
		logging.info('data error %s' % error)
		if error == 'true':
			return MessageResult(False)
		redis_key = body['redis_key']
		case_id = body['case_id']
		self.redis_to_mysql(redis_key, case_id)
		return MessageResult(True)

	def redis_to_mysql(self, redis_key, case_id):
		model = self.mysqlConnection['emrParserResult']
		emrModel = self.mysqlConnection['emrInfo']
		with Redis(connection_pool=self.redis_pool) as redis:
			data = redis.hgetall(redis_key)
		with self.mysqlConnection.session() as session:
			emr_obj = session.query(distinct(emrModel.docId)).filter(emrModel.caseId == case_id).all()
			docIds = [obj[0] for obj in emr_obj]
			logging.info('docIds: %s' % ','.join(docIds))
			for key, value in data.items():
				key = key.decode('utf-8')
				if key in docIds:
					logging.info('start key:%s' % key)
					value = json.loads(value.decode('utf-8'))
					for v in value:
						item = model(
							caseId=case_id,
							docId=key,
							field=json.dumps(v),
							key=v.get('key', None),
							create_time=arrow.utcnow().to('+08:00').naive
						)
						session.add(item)
			logging.info("redis to mysql %s successful" % case_id)

	def listen_parser(self, url):
		manager = RabbitMqManager(url=url)
		manager.listen(name='qc.fnf.finished', exchange='qcetl', callback=self.callback)
		return manager
