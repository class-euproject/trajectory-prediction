#!/bin/bash

RUNTIME_NAME=192.168.7.41:5000/kpavel/lithops_runtime:13.0
PROJECTS_ROOT_DIR="${HOME}"
#RUNTIME_NAME=kpavel/lithops_runtime:13.0

echo -n Password: 
read -s password
echo

wsk -i rule delete /guest/cdtimerrule
wsk -i rule delete /guest/tp-rule
wsk -i action delete tpAction
wsk -i action delete cdAction

echo -n "Updating stubs on 192.168.7.32"
/usr/bin/expect <<EOD
spawn ssh pkravche@192.168.7.32 "cd /m/home/pkravche/dataclay-class/examples/dataclay-class/dataclay-cloud/;./GetStubs.sh"
match_max 100000
expect "*?assword:*"
send -- "$password\r"
send -- "\r"
expect eof
EOD

sleep 5

echo -n "Updating stubs from 192.168.7.32 for trajectory prediction"
/usr/bin/expect <<EOD
spawn scp -r pkravche@192.168.7.32:/m/home/pkravche/dataclay-class/examples/dataclay-class/dataclay-cloud/stubs ${PROJECTS_ROOT_DIR}/trajectory-prediction/ 
match_max 100000
expect "*?assword:*"
send -- "$password\r"
send -- "\r"
expect eof
EOD

cp ~/.lithops_config ${PROJECTS_ROOT_DIR}/trajectory-prediction
cp ~/.lithops_config ${PROJECTS_ROOT_DIR}/collision-detection/
cp ~/.lithops_config ${PROJECTS_ROOT_DIR}/lithops/

echo "Updating stubs for collision detection"
cp -r ${PROJECTS_ROOT_DIR}/trajectory-prediction/stubs ${PROJECTS_ROOT_DIR}/collision-detection/

echo "Updating stubs for lithops core"
cp -r ${PROJECTS_ROOT_DIR}/trajectory-prediction/stubs ${PROJECTS_ROOT_DIR}/lithops/

cp -r ${PROJECTS_ROOT_DIR}/trajectory-prediction/cfgfiles ${PROJECTS_ROOT_DIR}/collision-detection/
cp -r ${PROJECTS_ROOT_DIR}/trajectory-prediction/cfgfiles ${PROJECTS_ROOT_DIR}/lithops/

echo "Updating runtime docker image with new stubs"
cd ${PROJECTS_ROOT_DIR}/lithops
docker build -t $RUNTIME_NAME .
docker push $RUNTIME_NAME

echo "Forcing docker image update in the cluster"
cd ${PROJECTS_ROOT_DIR}/trajectory-prediction
kubectl apply -f udeployment.yaml
kubectl rollout status deployment/upd-dep

echo "Deleting deployment"
kubectl delete deploy upd-dep

echo "Creating lithops runtime"
lithops runtime create $RUNTIME_NAME --memory 512

echo "Stopping running runtimes"
docker ps -a | grep kpavel_lithops|awk '{print $1 }'| xargs -I {} docker unpause {}
docker ps -a | grep kpavel_lithops|awk '{print $1 }'| xargs -I {} docker rm -f {}

kubectl -n openwhisk delete pod owdev-kafka-0
kubectl -n openwhisk delete pod owdev-invoker-0
kubectl -n openwhisk delete pod owdev-invoker-1
kubectl -n openwhisk delete pod owdev-invoker-2

echo -n "Update trajectory prediction OW action"
zip -r classAction.zip __main__.py .lithops_config cfgfiles/ stubs/ lithopsRunner.py tp
wsk -i action update tpAction --docker $RUNTIME_NAME --timeout 30000 -p ALIAS DKB -p CHUNK_SIZE 20 --memory 512 classAction.zip

echo -n "Update collision detection OW action"
cd ${PROJECTS_ROOT_DIR}/collision-detection
zip -r classAction.zip __main__.py .lithops_config cfgfiles/ stubs/ cdLithopsRunner.py cd
wsk -i action update cdAction --docker $RUNTIME_NAME --timeout 30000  -p ALIAS DKB -p CHUNK_SIZE 10 --memory 512 classAction.zip

wsk -i rule create cdtimerrule cdtimer /guest/cdAction
wsk -i rule create tp-rule tp-trigger tpAction
