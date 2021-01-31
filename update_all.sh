#!/bin/bash

RUNTIME_NAME=192.168.7.41:5000/kpavel/lithops_runtime:13.0
#RUNTIME_NAME=kpavel/lithops_runtime:13.0

echo -n Password: 
read -s password
echo

wsk -i rule delete /guest/cdtimerrule
wsk -i rule delete /guest/tp-rule

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
spawn scp -r pkravche@192.168.7.32:/m/home/pkravche/dataclay-class/examples/dataclay-class/dataclay-cloud/stubs /m/home/pkravche/trajectory-prediction/ 
match_max 100000
expect "*?assword:*"
send -- "$password\r"
send -- "\r"
expect eof
EOD

cp ~/.lithops_config /m/home/pkravche/trajectory-prediction
cp ~/.lithops_config /m/home/pkravche/collision-detection/
cp ~/.lithops_config /m/home/pkravche/lithops/

echo "Updating stubs for collision detection"
cp -r /m/home/pkravche/trajectory-prediction/stubs /m/home/pkravche/collision-detection/

echo "Updating stubs for lithops core"
cp -r /m/home/pkravche/trajectory-prediction/stubs /m/home/pkravche/lithops/

echo "Updating runtime docker image with new stubs"
cd /m/home/pkravche/lithops
docker build -t $RUNTIME_NAME .
docker push $RUNTIME_NAME
lithops runtime create $RUNTIME_NAME --memory 256

echo "Stopping running runtimes"
docker ps -a | grep kpavel_lithops|awk '{print $1 }'| xargs -I {} docker unpause {}
docker ps -a | grep kpavel_lithops|awk '{print $1 }'| xargs -I {} docker rm -f {}

echo -n "Update trajectory prediction OW action"
cd /m/home/pkravche/trajectory-prediction
zip -r classAction.zip __main__.py .lithops_config cfgfiles/ stubs/ lithopsRunner.py tp
wsk -i action update tpAction --docker $RUNTIME_NAME --timeout 300000 -p ALIAS DKB -p CHUNK_SIZE 100 classAction.zip

echo -n "Update collision detection OW action"
cd /m/home/pkravche/collision-detection
zip -r classAction.zip __main__.py .lithops_config cfgfiles/ stubs/ cdLithopsRunner.py cd
wsk -i action update cdAction --docker $RUNTIME_NAME --timeout 300000  -p ALIAS DKB -p CHUNK_SIZE 100 classAction.zip

wsk -i rule create cdtimerrule cdtimer /guest/cdAction
wsk -i rule create tp-rule tp-trigger tpAction
