from flask import Flask, request, g
import os, sys
import logging, json, time
from url_route import init_url_route
from werkzeug.routing import BaseConverter
from qcaudit.env_config.pre_req import pre_request, EmrSaveDebugReq


logger = logging.getLogger(__name__)


class RegexConverter(BaseConverter):

    def __init__(self, map, *args):
        self.map = map
        self.regex = args[0]


def create_app():
    """创建app对象

    Returns:
        _type_: _description_
    """
    app = Flask(__name__)
    app.url_map.converters['regex'] = RegexConverter
    init_url_route(app)
    return app


app = create_app()


@app.route("/hosp/qc/v3/doctor/debug", methods=["POST"])
@pre_request(request, EmrSaveDebugReq)
def log_debug():
    """
    医生端debug, 记录日志
    """
    from qcaudit.controller import doctor_repository
    doctor_repository.logDebug(request, g.result)
    return g.result


@app.before_request
def before_request():
    """before中间件
    """
    # logger.info('before_request: %s', {'url': request.url,
    #                        'path': request.path,
    #                        'method': request.method,
    #                        'QUERY_STRING': request.headers.get('QUERY_STRING'),
    #                        'headers': request.headers,
    #                        'HTTP_X_FORWARDED_FOR': request.headers.get('HTTP_X_FORWARDED_FOR'),
    #                        'params': request.args.to_dict()
    #                        })
    g.result = {"isSuccess": "True", "message": "", "data": []}
    requset_data = request.args if request.method.upper() == "GET" else request.json
    request.auditType = requset_data.get("auditType") or "hospital"
    for key, val in requset_data.items():
        setattr(request, key, val)


@app.after_request
def after_request(response):
    # status_code = response._status_code
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'HEAD, OPTIONS, GET, POST, DELETE, PUT')
    response.headers.add('X-Content-Type-Options', 'nosniff')
    allow_headers = "Referer, Accept, Origin, User-Agent, X-Requested-With, Content-Type, CASTGC, Trace_Id"
    response.headers.add('Access-Control-Allow-Headers', allow_headers)
    # if you need the cookie access, uncomment this line
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 80 if not os.getenv("qcaudit_port") else os.getenv("qcaudit_port")

    if len(sys.argv) == 3:
        host, port = sys.argv[1:3]

    app.run(host=host, port=int(port))






