import csv 
from statistics import mean, median
from columnar import columnar

import requests
from datetime import datetime
import os, errno
import sys

import urllib3
import logging

logging.basicConfig(format='%(message)s', filename='benchmark.log', level=logging.INFO)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#logging.basicConfig(filename='benchmark.log', level=logging.DEBUG)

APIHOST = 'https://192.168.7.42:31001'
AUTH_KEY = '23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP'
NAMESPACE = '_'
BLOCKING = 'true'
RESULT = 'false'
ACTION = 'cdAction'

url = f'{APIHOST}/api/v1/namespaces/{NAMESPACE}/actions/{ACTION}'
user_pass = AUTH_KEY.split(':')
alias = "DKB"
BENCHLOGS = "benchlogs"
CONTR_REPLICAS_NUM = 4
INVOKER_REPLICAS_NUM = 4

CHUNK_SIZE = sys.argv[1] if len(sys.argv) > 1 else 1
LIMIT = sys.argv[2] if len(sys.argv) > 2 and int(sys.argv[2]) > 0 else None
TEST_NAME = sys.argv[3] if len(sys.argv) > 3 else ''
sep = '\n----------------------------------\n'
logging.info(f'\n{sep}{TEST_NAME}{sep}CHUNK_SIZE: {CHUNK_SIZE} LIMIT: {LIMIT}{sep}')

def getLogs():
    #get controller logs
    try:
        os.mkdir(BENCHLOGS)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    for i in range(CONTR_REPLICAS_NUM):
        os.system(f'kubectl -n openwhisk logs owdev-controller-{i}>{BENCHLOGS}/owdev-controller-{i}.log')
    for i in range(INVOKER_REPLICAS_NUM):
        os.system(f'kubectl -n openwhisk logs owdev-invoker-{i}>{BENCHLOGS}/owdev-invoker-{i}.log')
#    i='86r72'
#    os.system(f'kubectl -n openwhisk logs owdev-invoker-{i}>{BENCHLOGS}/owdev-invoker-{i}.log')

def findInLogs(strToSearch, lineSplitIndex, getFilenameOnly=False, optionalStrToSearch=None, allOccurencesArray=None):
    benchlogs = os.listdir(BENCHLOGS)

    for fname in benchlogs:
        if os.path.isfile(BENCHLOGS + os.sep + fname):
            with open(BENCHLOGS + os.sep + fname) as f:
                for line in f:
                    if strToSearch in line or (optionalStrToSearch and optionalStrToSearch in line):
                        if getFilenameOnly:
                            return fname[:-4]
                        if lineSplitIndex < 0:
                            if allOccurencesArray:
                                allOccurencesArray.append(line)
                            else:
                                return line
                        else:
                            return line.split()[lineSplitIndex]

def find_in_activation_log(log, strToSearch, lineSplitIndex, all_occurences=False):
    res = []

    for line in log:
        if strToSearch in line:
          if lineSplitIndex < 0:
            if all_occurences:
              res.append(line)
            else:
              return line
          else:
            return line.split()[lineSplitIndex]
    return res if res else ''

def getActivationLogs(aid):
    url = f'{APIHOST}/api/v1/namespaces/{NAMESPACE}/activations/{aid}'
    response = requests.get(url, auth=(user_pass[0], user_pass[1]), verify=False)
    return response.json()['logs']

def toDatetime(timestamp):
    try:
      res = datetime.strptime(timestamp.rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    except Exception as e:
      import pdb;pdb.set_trace()
      print(timestamp)
    return res

def time_diff_milli(d1, d2):
    return round(abs(d1.timestamp() * 1000 - d2.timestamp() * 1000), 2)


cdHeaders = ['cd_req_e2e', 'imports_time', 'before_dc_get_all', 'dataclay_req', 'map_to_invoke', 'map_time', 'wait', 'run_to_return', 'contr_post_e2e', 'invoker_e2e', 'controller_id', 'invoker_id', 'all_upload', 'data_upload', 'func_upload']
def getCDTimes(start, end, aid):
    cdTimes = get_activation_invocation_times(aid)
    req_end_to_end = round(end.timestamp() * 1000 - start.timestamp() * 1000, 1)

    timestamps = {}

    def get_timestamp_if_in_line(pattern, line, key):
        if pattern in line:
            timestamps[key] = toDatetime(line.split()[0][:26])

    logs = getActivationLogs(aid)
    for line in logs:
        get_timestamp_if_in_line('before imports', line, 'before_imports')
        get_timestamp_if_in_line('after imports', line, 'after_imports')
        get_timestamp_if_in_line('in run' ,line, 'in_run')
        get_timestamp_if_in_line('creating dm instance' ,line, 'before_dm_instance')
        get_timestamp_if_in_line('after dm.getAllObjects' ,line, 'after_dm_get_all')
        get_timestamp_if_in_line("before lithops fexec.map" ,line, 'before_map')
        get_timestamp_if_in_line('3Starting function invocation' ,line, 'before_invoke_all')
        get_timestamp_if_in_line("after lithops fexec.map" ,line, 'after_map')
        get_timestamp_if_in_line("lithops finished" ,line, 'lithops_finished')
        get_timestamp_if_in_line("returning from lithops function" ,line, 'returning')

        get_timestamp_if_in_line("Uploading function and data", line, 'start_uploading')
        get_timestamp_if_in_line("Finished uploading data", line, 'finished_uploading_data')
        get_timestamp_if_in_line("Finished uploading function and data", line, 'finished_uploading_all')

    imports_time = -1
    if 'after_imports' in timestamps and 'before_imports' in timestamps:
        imports_time = time_diff_milli(timestamps['after_imports'], timestamps['before_imports'])
    before_dc_get_all = time_diff_milli(timestamps['in_run'], timestamps['after_dm_get_all'])
    dataclay_req = time_diff_milli(timestamps['before_dm_instance'], timestamps['after_dm_get_all'])
    map_to_invoke = time_diff_milli(timestamps['before_map'], timestamps['before_invoke_all'])
    map_time = time_diff_milli(timestamps['before_map'], timestamps['after_map'])
    wait = time_diff_milli(timestamps['lithops_finished'], timestamps['after_map'])
    run_to_return = time_diff_milli(timestamps['returning'], timestamps['in_run'])

    data_upload = time_diff_milli(timestamps['finished_uploading_data'], timestamps['start_uploading'])
    func_upload = time_diff_milli(timestamps['finished_uploading_data'], timestamps['finished_uploading_all'])
    all_upload = time_diff_milli(timestamps['start_uploading'], timestamps['finished_uploading_all'])


    data = [[req_end_to_end, imports_time, before_dc_get_all, dataclay_req, map_to_invoke, map_time, wait, run_to_return, cdTimes[0], cdTimes[1], cdTimes[2], cdTimes[3], all_upload, data_upload, func_upload]]
    return data

def getLithopsRuntimesActivationIDS(aid):

    activations = []
    logs = getActivationLogs(aid)
    lithops_activation_start = None
    for line in logs:
        if 'in run' in line:
            lithops_activation_start = toDatetime(line.split()[0][:26])

        if "A_INVOKE_CALL_" in line:
            invoke_timestamp = toDatetime(line.split()[0][:26])
#            import pdb;pdb.set_trace()
            if line.count("A_INVOKE_CALL_") > 1:
                raise Exception(f"Sorry, something very wrong on this line! {line}")

            call_id = line.split()[7].split('A_INVOKE_CALL_')[1]
            for line in logs:
                if f"A_INVOKE_BACK_{call_id}" in line:
                    invoke_back_timestamp = toDatetime(line.split()[0][:26])

                    if f"A_INVOKE_BACK_{call_id}" not in line.split()[7]:
                        raise Exception(f"Sorry, something very wrong on this line! {line}")

                    _aid = line.split()[7].split('_')[4]
                    activations.append((time_diff_milli(invoke_timestamp, lithops_activation_start), time_diff_milli(invoke_back_timestamp, lithops_activation_start), _aid))
                    break

    return activations

TD_FORMAT = '[%Y-%m-%dT%H:%M:%S.%fZ]'

def get_invocation_times(aid):
    logs = getActivationLogs(aid)

    times = get_activation_invocation_times(aid)

    pairs_num = find_in_activation_log(logs, f'PAIRS_NUM:', 2).split(':')[1]

    before_cd = find_in_activation_log(logs, f'before call collision_detection=', -1, all_occurences=True)

    cd_res = {}

    for b_cd in before_cd:
        pair = b_cd.split()[4].split('=')[1:]

        b_ts = toDatetime(b_cd.split()[0][:26])

#        import pdb;pdb.set_trace()
        a_ts_str = find_in_activation_log(logs, f'after call collision_detection={pair[0]}', 0)
        a_ts = toDatetime(a_ts_str.split()[0][:26])

        cd_time = time_diff_milli(b_ts, a_ts)
        cd_res[cd_time] = pair


#    import pdb;pdb.set_trace()

    min_cd = round(min(cd_res), 2) if cd_res else float('inf') 
    min_cd = f'{min_cd} {cd_res[min_cd]}' if cd_res else f'{min_cd}'
    max_cd = round(max(cd_res), 2) if cd_res else float('-inf')
    max_cd = f'{max_cd} {cd_res[max_cd]}' if cd_res else f'{max_cd}'
    mean_cd = round(mean(cd_res), 2) if cd_res else 0
    median_cd = round(median(cd_res), 2) if cd_res else 0

    before_mqtt = find_in_activation_log(logs, f'Collision detected, before mqtt=', -1, all_occurences=True)
    mq_res = {}

    for b_mq in before_mqtt:
        pair = b_mq.split()[5].split('=')[1:]

        b_ts = toDatetime(b_mq.split()[0][:26])

        a_ts_str = find_in_activation_log(logs, f'Collision detected, after mqtt={pair[0]}', 0)
        a_ts = toDatetime(a_ts_str.split()[0][:26])

        mq_time = time_diff_milli(b_ts, a_ts)
        mq_res[cd_time] = pair

    min_mq = round(min(mq_res), 2) if mq_res else -1
    min_mq = f'{min_mq} {mq_res[min_mq]}' if mq_res else -1
    max_mq = round(max(mq_res), 2) if mq_res else -1
    max_mq = f'{max_mq} {mq_res[max_mq]}' if mq_res else -1
#    mean_mq = round(mean(mq_res), 2)

    collisions_num = len(before_mqtt)

    
    g_func_data_start = find_in_activation_log(logs, f'Getting function data', 0)
    g_func_data_finish = find_in_activation_log(logs, f'Finished getting Function data', 0)
    if g_func_data_start:
        g_func_data_start = toDatetime(find_in_activation_log(logs, f'Getting function data', 0).split()[0][:26])
        g_func_data_finish = toDatetime(find_in_activation_log(logs, f'Finished getting Function data', 0).split()[0][:26])

    g_func_modules_start = toDatetime(find_in_activation_log(logs, f'Getting function and modules', 0).split()[0][:26])
    g_func_modules_finish = toDatetime(find_in_activation_log(logs, f'Getting function and modules download finished', 0).split()[0][:26])

    load_all_start = toDatetime(find_in_activation_log(logs, f'Process started', 0).split()[0][:26])
    load_all_finish = toDatetime(find_in_activation_log(logs, f'-- FUNCTION LOG ---', 0).split()[0][:26])

    write_to_storage_start_1 = toDatetime(find_in_activation_log(logs, f'handler.py -- sending event __init__', 0).split()[0][:26])
    write_to_storage_finish_1 = toDatetime(find_in_activation_log(logs, f'done sending event __init__', 0).split()[0][:26])

    write_to_storage_start_2 = find_in_activation_log(logs, f'Storing function result - Size', 0)
    write_to_storage_finish_2 = find_in_activation_log(logs, f'Finished storing function result', 0)

    if write_to_storage_start_2:
        write_to_storage_start_2 = toDatetime(find_in_activation_log(logs, f'Storing function result - Size', 0).split()[0][:26])
        write_to_storage_finish_2 = toDatetime(find_in_activation_log(logs, f'Finished storing function result', 0).split()[0][:26])

    write_to_storage_start_3 = toDatetime(find_in_activation_log(logs, f'handler.py -- sending event __end__', 0).split()[0][:26])
    write_to_storage_finish_3 = find_in_activation_log(logs, f'done sending event __end__', 0)
    if write_to_storage_finish_3:
        write_to_storage_finish_3 = toDatetime(find_in_activation_log(logs, f'done sending event __end__', 0).split()[0][:26])

    before_cd_loop = toDatetime(find_in_activation_log(logs, f'PAIRS_NUM:', 0).split()[0][:26])
    after_cd_loop = toDatetime(find_in_activation_log(logs, f'after for cc in cc_in_wa', 0).split()[0][:26])
    cd_all = time_diff_milli(before_cd_loop, after_cd_loop)


    worker_start = toDatetime(find_in_activation_log(logs, f'Starting OpenWhisk execution', 0).split()[0][:26])
    worker_time_netto = time_diff_milli(worker_start, write_to_storage_finish_3) if write_to_storage_finish_3 else time_diff_milli(worker_start, write_to_storage_start_3)

    ow_ex_start_to_process_start = time_diff_milli(worker_start, load_all_start)

    g_func_data = time_diff_milli(g_func_data_start, g_func_data_finish) if g_func_data_start else 0
    g_func_modules = time_diff_milli(g_func_modules_start, g_func_modules_finish)

    load_all = time_diff_milli(load_all_start, load_all_finish)

    write_to_storage_1 = time_diff_milli(write_to_storage_start_1, write_to_storage_finish_1)
    write_to_storage_2 = time_diff_milli(write_to_storage_start_2, write_to_storage_finish_2) if write_to_storage_start_2 else 0
    write_to_storage_3 = time_diff_milli(write_to_storage_start_3, write_to_storage_finish_3) if write_to_storage_finish_3 else -1

    return times + (pairs_num, min_cd, max_cd, mean_cd, median_cd,  collisions_num, min_mq, max_mq,  worker_start, g_func_data, g_func_modules, load_all, write_to_storage_1, write_to_storage_2, write_to_storage_3, cd_all, ow_ex_start_to_process_start, worker_time_netto)

def get_activation_invocation_times(aid):
    tid = findInLogs(aid, 2)

    try:
      controller_instance = findInLogs(f'{tid} POST', 0, getFilenameOnly=True)
      invoker_instance = findInLogs(f'{tid} [InvokerReactive]  [marker:invoker_activation_start', 0, getFilenameOnly=True)

      post_controller = findInLogs(f'{tid} POST', 0)
      d_post_controller = datetime.strptime(post_controller, TD_FORMAT)

      post_invoker = findInLogs(f'{tid} [ShardingContainerPoolBalancer] posted to invoker', 0, optionalStrToSearch=f'{tid} [LeanBalancer] posted to invoker')
      d_post_invoker = datetime.strptime(post_invoker, TD_FORMAT)

      post_finish_controller = findInLogs(f'{tid} [BasicHttpService] [marker:http_post.200_counter', 0, optionalStrToSearch=f'{tid} [BasicHttpService] [marker:http_post.202_counter')
      d_post_finish_controller = datetime.strptime(post_finish_controller, TD_FORMAT)

      a_invoker_start = findInLogs(f'{tid} [InvokerReactive]  [marker:invoker_activation_start', 0)
      d_a_invoker_start = datetime.strptime(a_invoker_start, TD_FORMAT)

      a_invoker_finish = findInLogs(f'{tid} [KubernetesContainer] running result: ok [marker:invoker_activationRun_finish', 0, optionalStrToSearch=f'{tid} [DockerContainer] running result: ok [marker:invoker_activationRun_finish')
      d_a_invoker_finish = datetime.strptime(a_invoker_finish, TD_FORMAT)
    except Exception as e:
        print(f"Exception {e} occured while processing tid: {tid}, aid: {aid}")

    post_controller_time = d_post_finish_controller.timestamp() * 1000 - d_post_controller.timestamp() * 1000
    total_invoker_time = d_a_invoker_finish.timestamp() * 1000 - d_a_invoker_start.timestamp() * 1000

    return post_controller_time, total_invoker_time, controller_instance, invoker_instance



#print(f'{datetime.now()} {ACTION} post')
req_start = datetime.now()
data={"ALIAS": str(alias), "CHUNK_SIZE": CHUNK_SIZE}
if LIMIT:
    data["LIMIT"] = LIMIT

response = requests.post(url, params={'blocking':BLOCKING, 'result':RESULT}, json=data, auth=(user_pass[0], user_pass[1]), verify=False)

req_end = datetime.now()
getLogs()

aid = response.json()["activationId"]

cdTimes = getCDTimes(req_start, req_end, aid)

table = columnar(cdTimes, cdHeaders, no_borders=False)
print(table)
logging.info(table)

#cdTimes = (req_end.timestamp() * 1000 - req_start.timestamp() * 1000,) + cdTimes

activations = getLithopsRuntimesActivationIDS(aid)
activationsData = []
activations_times = []
for activation in activations:
#    import pdb;pdb.set_trace()
    try:
        activation_invocation_times = get_invocation_times(activation[2])
    except Exception as e:
        import pdb;pdb.set_trace()
        activation_invocation_times = get_invocation_times(activation[2])
        print(e)


    activation_invocation_times = activation[:2] + activation_invocation_times

    activations_times.append(activation_invocation_times)
    data = []
    for i, at in enumerate(activation_invocation_times):
        data.append(at)
    activationsData.append(data)

runtimeHeaders = ['start->inv', 'start->inv_back', 'post_cont_time', 'invoker_time', 'controller_id', 'invoker_id', 'pairs', 'min_cd', 'max_cd', 'mean_cd', 'med_cd', 'cd_num', 'min_mq', 'max_mq', 'worker_start', 'g_func_data', 'g_func_modules', 'load_all', 'w_to_s_1', 'w_to_s_2', 'w_to_s_3', 'cd_netto', 'ow_ex_start_to_process_start', 'worker_time_netto']
table = columnar(activationsData, runtimeHeaders, no_borders=False)
print(table)
logging.info(table)

def column(matrix, i):
    return [row[i] for row in matrix]

min_worker_start = min(column(activationsData, 14))
max_worker_start = max(column(activationsData, 14))
#import pdb;pdb.set_trace()
min_max_worker_start = time_diff_milli(min_worker_start, max_worker_start)

min_worker = min(column(activationsData, 0))
max_worker = max(column(activationsData, 0))

#import pdb;pdb.set_trace()
cd_min_time_ids = min(column(activationsData, 7))
cd_max_time_ids = max(column(activationsData, 8))
cd_avg = mean(column(activationsData, 9))

mqtt_publish_min_col = column(activationsData, 12)
mqtt_publish_min_arr = []
ids = []
for item in mqtt_publish_min_col:
    item1, *item2 = str(item).split()
    mqtt_publish_min_arr.append(item1)
    if item2:
        ids.append(item2[0])
    else:
        ids.append(None)

mqtt_publish_min = min(mqtt_publish_min_arr)
mqtt_publish_min_ids = ids[mqtt_publish_min_arr.index(mqtt_publish_min)]


mqtt_publish_max_col = column(activationsData, 13)
mqtt_publish_max_arr = []
ids = []
for item in mqtt_publish_max_col:
    item1, *item2 = str(item).split()
    mqtt_publish_max_arr.append(item1)
    if item2:
        ids.append(item2[0])
    else:
        ids.append(None)

#import pdb;pdb.set_trace()
mqtt_publish_max = max(mqtt_publish_max_arr)
mqtt_publish_max_ids = ids[mqtt_publish_max_arr.index(mqtt_publish_max)]

detections = column(activationsData, 11)
detections_num = sum(detections)

summaryHeaders = ['first2last_worker', 'min_max_worker_start', 'chunk_size', 'cd_min_time_ids', 'cd_max_time_ids', 'cd_avg', 'mqtt_publish_min', 'mqtt_publish_max', 'detections_num']
summaryData = [[round(max_worker - min_worker, 2), min_max_worker_start, CHUNK_SIZE, cd_min_time_ids, cd_max_time_ids, round(cd_avg, 2), f'{mqtt_publish_min} {mqtt_publish_min_ids}', f'{mqtt_publish_max} {mqtt_publish_max_ids}', detections_num]]
if TEST_NAME:
    summaryHeaders.insert(0, 'test name')
    summaryData[0].insert(0, TEST_NAME)

table = columnar(summaryData, summaryHeaders, no_borders=False)
print(table)
logging.info(table)

csv_file_name = f'{CHUNK_SIZE}_{"_".join(TEST_NAME.split())}_benchmark.csv' 

with open(csv_file_name, mode='w') as f:
    writer = csv.writer(f)
    
    writer.writerow(cdHeaders)
    writer.writerows(cdTimes)

    writer.writerow(runtimeHeaders)
    writer.writerows(activationsData)

    writer.writerow(summaryHeaders)
    writer.writerows(summaryData)

logging.info('=================================================================\n\n')

#from tabulate import tabulate
#print(tabulate(activationsData, runtimeHeaders))

#print(f'CD headers:')
#print(f'request_end_to_end | post_controller_time | activation_controller_time | total_invoker_time | controller_instance | invoker_instance')

#print(f'{cdTimes}')

#print(f'ACTIVATIONS headers:')
#print(f'lithops_start_to_invoke | lithops_start_to_invoke_back | post_controller_time | activation_controller_time | total_invoker_time | controller_instance | invoker_instance')
#import pdb;pdb.set_trace()
#for atime in activations_times:
#    print(f'{atime}')


#print(f'total_req_time {total_req_time} post_controller_time {post_controller_time} activation_controller_time {a_controller_time} total_invoker_time {total_invoker_time}')
#print(f'{datetime.now()} {ACTION} post done')
#print(response.text)
