FROM 123.56.140.160:5000/python:v1.5

RUN mkdir -p /usr/local/app
COPY ./  /usr/local/app
RUN chmod +x /usr/local/app/*.sh
# --extra-index-url http://123.56.140.160:9090/simple  --trusted-host http://123.56.140.160 
RUN pip install -r /usr/local/app/requirements.txt

# RUN sh /usr/local/app/start_server.sh
# ENTRYPOINT [ "python3", "/usr/local/app/run.py" ] -w 线程数
ENTRYPOINT [ "/bin/bash", "-ce", "cd /usr/local/app && gunicorn -w 1 -b 0.0.0.0:80 run:app" ]
