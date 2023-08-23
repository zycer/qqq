from qcaudit.context import Context
from qcaudit.app import Application
from qcaudit.env_config import *
import logging
from flask import jsonify, make_response, current_app, g, request, send_from_directory
from flask_restful import Resource
from qcaudit.domain.doctor.doctor_repository import DoctorRepository
from qcaudit.domain.doctor.appeal_repository import AppealRepository
from qcaudit.common.const import AUDIT_TYPE_HOSPITAL


app = Application(mysqlUrl, mongodbURI, mqUrl=mqUrl, iamDatabase=iamDatabase,
                emrAdapterUrl=emrAdapterUrl, qcetlRpcUrl=qcetlRpc, aiCacheApi=aiCacheApi,
                cdssAddr=cdssAddr, redisAddr=redisAddr, migrate=migrate)
context = Context(app)
export_path = "/tmp/"
doctor_repository = DoctorRepository(app, AUDIT_TYPE_HOSPITAL)
appeal_repository = AppealRepository(app, AUDIT_TYPE_HOSPITAL)


def get_resp_file(file_dir_name):
    """
    文件返回
    :return: 文件流
    """
    file_name = file_dir_name.rsplit('/')[-1]
    response = make_response(
        send_from_directory(os.path.dirname(file_dir_name), file_name, as_attachment=True))
    response.headers["Content-Disposition"] = "attachment; filename={}".format(file_name.encode().decode('latin-1'))
    return response


def get_error_resp(msg):
    """
    返回错误响应
    """
    g.result["isSuccess"] = "False"
    g.result["message"] = msg
    return make_response(jsonify(g.result), 200)


class MyResource(Resource):

    def __init__(self) -> None:
        super().__init__()
        self.app = app
        self.context = context
        self.logger = logging.getLogger(__name__)