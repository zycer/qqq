# hospkpi makefile
WORKDIR=`pwd`
TAG := $(shell date +'%Y%m%d%H%M%S')

.PHONY: build gw

gw:
	go install ./qcaudit-gateway

startlocal:
	python3 -u -m qcaudit --debug --disable-access-control --db-host "123.56.140.160" \
	--db-database "qcmanager" --db-port 32328 --db-uname "root" --db-password "Root001@" \
	--mongodb-uri "123.56.140.160" --iam-database "iam"  --emr-addr "http://127.0.0.1/" \
	--ai-url "http://localhost:30080"  --mq-url "amqp://admin:rxthinking@123.56.140.160:30672/%2F" \
	--emr-adapter "127.0.0.1:6014" --cdss-addr "http://192.168.101.155:40002" --redis-addr "redis://123.56.140.160:6379/0"

startlocal2:
	python3 -u -m qcaudit --port=6025 --debug --disable-access-control --db-host "192.168.101.186" \
	--db-database "qcmanager_v3" --db-port 31444 --db-uname "root" --db-password "rxthinkingmysql" \
	--mongodb-uri "192.168.101.159" --iam-database "iam-qc"  --emr-addr "http://127.0.0.1/" \
	--ai-url "http://localhost:30080"  --mq-url "amqp://rxthinking:gniknihtxr@192.168.101.155:42158/%2F" \
	--redis-addr "redis://192.168.101.155:30667/0"

startTask:
	python3 -u -m qcaudit --debug --disable-access-control --db-host "192.168.101.186" \
	--db-database "qcmanager_v3" --db-port 31444 --db-uname "root" --db-password "rxthinkingmysql" \
	--mongodb-uri "192.168.101.159" --task

startlanxi:
	/home/zhangda/bin/python3/bin/python3.8 -u -m qcaudit_lxrmyy --port=6025 --debug --disable-access-control --db-host "192.168.100.40" \
	--db-database "qcmanager_v3" --db-port 31444 --db-uname "root" --db-password "rxthinkingmysql" \
	--mongodb-uri "192.168.101.159" --iam-database "iam-qc"  --emr-addr "http://127.0.0.1/" \
	--ai-url "http://localhost:30080"  --mq-url "amqp://rxthinking:gniknihtxr@192.168.100.40:42158/%2F" \
	--emr-adapter "192.168.101.185:31644" --qcetl-rpc "http://192.168.101.185:30000/rpc"

starttest:
	python3  -u -m hospqc --debug --db-host "192.168.101.186" \
	--db-database "qcmanager" --db-port 31444 --db-uname "root" --db-password "rxthinkingmysql" \
	--mongodb-uri "192.168.101.159" --emr-addr "http://127.0.0.1/" --ai-url "http://localhost:30080" --pig-addr "192.168.101.158:31215"

startgw:
	qcaudit-gateway

startgw2:
	qcaudit-gateway --api-port=6025 --port=8025
	
build:
	GOOS=linux GOARCH=amd64 go build -o binary/qcaudit-gateway ./qcaudit-gateway

renewmod:
	go get git.bdmd.com/server/public-frameworks/proto@master-py3

hsscript:
	cd scripts/sync_receive_time/ && docker build -f Dockerfile -t dockerdist.bdmd.com/qcaudit-scripts:$(TAG) .
	echo dockerdist.bdmd.com/qcaudit-scripts:$(TAG)
