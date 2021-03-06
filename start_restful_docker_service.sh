#!/bin/bash
aws_config=~/.aws
if [ ! -d ${aws_config} ]; then
  mkdir ${aws_config}
fi

if [[ "$(docker images -q insight/kservice 2> /dev/null)" == "" ]]; then
    docker build -t insight/kservice -f Dockerfile.service .
fi

# setting file inside the container
setting_file=/home/root/insight/package/insight/applications/settings.py

# external port
ext_port=80

docker run --rm -d --name insight-restful -v ${aws_config}:/root/.aws -v ${PWD}/settings.py:${setting_file} -p ${ext_port}:9000 insight/kservice
#docker run --rm --name insight-restful -v ${aws_config}:/root/.aws -v ${PWD}/settings.py:${setting_file} -p ${ext_port}:9000 insight/kservice
