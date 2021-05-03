#!/bin/bash

REDIS_HOST=`kubectl -n openwhisk get svc|grep redis|awk '{print $3}'`
NODES="41 43 44 45"
RUNTIME_NAME=192.168.7.40:5000/kpavel/lithops_runtime:14.0
PROJECTS_ROOT_DIR="${HOME}"
source ${PROJECTS_ROOT_DIR}/venv/bin/activate
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

#echo "Forcing docker image update in the cluster"
#cd ${PROJECTS_ROOT_DIR}/trajectory-prediction
#kubectl apply -f udeployment.yaml
#kubectl rollout status deployment/upd-dep
#
#echo "Deleting deployment"
#kubectl delete deploy upd-dep

echo "Creating lithops runtime"
lithops runtime create $RUNTIME_NAME --memory 512

echo "Stopping running runtimes"
docker ps -a | grep kpavel_lithops|awk '{print $1 }'| xargs -I {} docker unpause {}
docker ps -a | grep kpavel_lithops|awk '{print $1 }'| xargs -I {} docker rm -f {}

if true; then
    kubectl -n openwhisk delete pod owdev-invoker-0
    kubectl -n openwhisk delete pod owdev-invoker-1
    kubectl -n openwhisk delete pod owdev-invoker-2
    kubectl -n openwhisk delete pod owdev-invoker-3
    kubectl -n openwhisk delete pod owdev-controller-0
    kubectl -n openwhisk delete pod owdev-controller-1
    kubectl -n openwhisk delete pod owdev-controller-2
    kubectl -n openwhisk delete pod owdev-controller-3
    sleep 30
fi

echo -n "Updating runtimes"
tp_runtime=`lithops runtime extend $RUNTIME_NAME --filepath /home/class/collision-detection/map_tp.py --function traj_pred_v2_wrapper --exclude_modules CityNS 2>&1 | grep "Extended runtime:" | awk -F'Extended runtime: ' '{print $2}'`
echo TP_RUNTIME=${tp_runtime}

cd_runtime=`lithops runtime extend $RUNTIME_NAME --filepath /home/class/collision-detection/centr_cd.py --function detect_collision_centralized 2>&1 | grep "Extended runtime:" | awk -F'Extended runtime: ' '{print $2}'`
echo CD_RUNTIME=${cd_runtime}

echo "Refreshing runtimes docker images in the cluster"
for node in $NODES; do
   ssh $node docker pull $tp_runtime
   ssh $node docker pull $cd_runtime
   ssh $node docker pull $RUNTIME_NAME
done

#echo -n "Update trajectory prediction OW action"
#rm classAction.zip
#zip -r classAction.zip __main__.py .lithops_config cfgfiles/ stubs/ lithopsRunner.py tp
#
#wsk -i action update tpAction --docker $RUNTIME_NAME --timeout 300000 -p ALIAS DKB -p CHUNK_SIZE 3 -p REDIS_HOST ${REDIS_HOST} --memory 512 -p OPERATION tp -p RUNTIME ${tp_runtime} classAction.zip

echo -n "Update collision detection OW action"
cd ${PROJECTS_ROOT_DIR}/collision-detection
rm classAction.zip
zip -r classAction.zip __main__.py .lithops_config cfgfiles/ stubs/ lithops_runner.py cd tp map_tp.py centr_cd.py dist_cd.py
wsk -i action update cdAction --docker $RUNTIME_NAME --timeout 300000  -p ALIAS DKB -p CHUNK_SIZE 3 -p REDIS_HOST ${REDIS_HOST} --memory 512 -p OPERATION cd -p RUNTIME ${cd_runtime} classAction.zip
wsk -i action update tpAction --docker $RUNTIME_NAME --timeout 300000  -p ALIAS DKB -p CHUNK_SIZE 3 -p REDIS_HOST ${REDIS_HOST} --memory 512 -p OPERATION tp -p RUNTIME ${tp_runtime} classAction.zip

wsk -i rule create cdtimerrule cdtimer /guest/cdAction
wsk -i rule create tp-rule tp-trigger tpAction

echo '\n=================================================================================='
echo TP_RUNTIME=${tp_runtime}
echo CD_RUNTIME=${cd_runtime}
echo '=================================================================================='
