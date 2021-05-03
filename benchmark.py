import csv
from statistics import mean, median
from columnar import columnar

import requests
from datetime import datetime
import os, errno
import sys

import urllib3
import logging

import click

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


sep = '\n----------------------------------\n'

#LOG_FILES = []
LOG_FILES_LINES = {}

def getLogs():
    #get controller logs
    try:
        os.mkdir(BENCHLOGS)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    for i in range(CONTR_REPLICAS_NUM):
        os.system(f'kubectl -n openwhisk logs owdev-controller-{i}>{BENCHLOGS}/owdev-controller-{i}.log')
        with open(f"{BENCHLOGS}/owdev-controller-{i}.log", "r") as fp:
            LOG_FILES_LINES[f"owdev-controller-{i}"] = fp.readlines()

    for i in range(INVOKER_REPLICAS_NUM):
        os.system(f'kubectl -n openwhisk logs owdev-invoker-{i}>{BENCHLOGS}/owdev-invoker-{i}.log')
        with open(f"{BENCHLOGS}/owdev-invoker-{i}.log", "r") as fp:
            LOG_FILES_LINES[f"owdev-invoker-{i}"] = fp.readlines()

#    i='86r72'
#    os.system(f'kubectl -n openwhisk logs owdev-invoker-{i}>{BENCHLOGS}/owdev-invoker-{i}.log')


LOG_SEARCH_META = {}
def findInLogs(strToSearch, lineSplitIndex, getFilenameOnly=False, optionalStrToSearch=None, allOccurencesArray=None):
    benchlogs = os.listdir(BENCHLOGS)

#    for fname in benchlogs:
#        if os.path.isfile(BENCHLOGS + os.sep + fname):
#            with open(BENCHLOGS + os.sep + fname) as f:
    for fname, lines in LOG_FILES_LINES.items():
                for i, line in enumerate(lines):
                    if strToSearch in line or (optionalStrToSearch and optionalStrToSearch in line):
                        #import pdb;pdb.set_trace()

                        if getFilenameOnly:
                            return fname
                        if lineSplitIndex < 0:
                            if allOccurencesArray:
                                allOccurencesArray.append(line)
                            else:
                                return line
                        else:
                            return line.split()[lineSplitIndex]

def find_in_activation_log(log, strToSearch, lineSplitIndex, all_occurences=False, find_after=None):
    res = []

    saved_strToSearch = strToSearch
    if find_after:
        strToSearch = find_after

    for line in log:
        if strToSearch in line:
          if find_after:
              find_after = None
              strToSearch = saved_strToSearch
              continue

          if lineSplitIndex < 0:
            if all_occurences:
              res.append(line)
            else:
              return line
          else:
            return line.split()[lineSplitIndex]
    return res if res else ''

def getActivationProperty(aid, name):
    url = f'{APIHOST}/api/v1/namespaces/{NAMESPACE}/activations/{aid}'
    response = requests.get(url, auth=(user_pass[0], user_pass[1]), verify=False)
    return response.json()[name]

def getActivationLogs(aid):
    return getActivationProperty(aid, 'logs')

def getActivationEnd(aid):
    ts = getActivationProperty(aid, 'end')
    return datetime.fromtimestamp(ts / 1000)

def toDatetime(timestamp):
    try:
      res = datetime.strptime(timestamp.rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
    except Exception as e:
      import pdb;pdb.set_trace()
      print(timestamp)
    return res

def time_diff_milli(d1, d2):
    return round(abs(d1.timestamp() * 1000 - d2.timestamp() * 1000), 2)

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
    before_dm_instance = time_diff_milli(timestamps['in_run'], timestamps['before_dm_instance'])
    dataclay_req = time_diff_milli(timestamps['before_dm_instance'], timestamps['after_dm_get_all'])
    map_to_invoke = time_diff_milli(timestamps['before_map'], timestamps['before_invoke_all'])
    map_time = time_diff_milli(timestamps['before_map'], timestamps['after_map'])

    if not timestamps.get('lithops_finished'):
        timestamps['lithops_finished'] = getActivationEnd(aid)

    if not timestamps.get('returning from lithops function'):
        timestamps['returning'] = getActivationEnd(aid)

    wait = time_diff_milli(timestamps['lithops_finished'], timestamps['after_map'])
    report_time = time_diff_milli(timestamps['lithops_finished'], timestamps['returning'])
    run_to_return = time_diff_milli(timestamps['returning'], timestamps['in_run'])

    data_upload = time_diff_milli(timestamps['finished_uploading_data'], timestamps['start_uploading'])
    func_upload = time_diff_milli(timestamps['finished_uploading_data'], timestamps['finished_uploading_all'])
    all_upload = time_diff_milli(timestamps['start_uploading'], timestamps['finished_uploading_all'])


    data = [[req_end_to_end, imports_time, before_dm_instance, dataclay_req, map_to_invoke, map_time, wait, report_time, run_to_return, cdTimes[0], cdTimes[1], cdTimes[2], cdTimes[3], all_upload, data_upload, func_upload]]
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
import re

def get_tp_invocation_times(aid):
#    import pdb;pdb.set_trace()
    logs = getActivationLogs(aid)

    times = get_activation_invocation_times(aid)

    objects_num = find_in_activation_log(logs, f'objects in chunk:', 5)

    g_func_data_start = find_in_activation_log(logs, f'Getting function data', 0)
    g_func_data_finish = find_in_activation_log(logs, f'Finished getting Function data', 0)
    if g_func_data_start:
        g_func_data_start = toDatetime(find_in_activation_log(logs, f'Getting function data', 0).split()[0][:26])
        g_func_data_finish = toDatetime(find_in_activation_log(logs, f'Finished getting Function data', 0).split()[0][:26])

    g_func_modules_start = toDatetime(find_in_activation_log(logs, f'Getting function and modules', 0).split()[0][:26])
    g_func_modules_finish = toDatetime(find_in_activation_log(logs, f'Getting function and modules download finished', 0).split()[0][:26])

    load_all_start = toDatetime(find_in_activation_log(logs, f'Process started', 0).split()[0][:26])
    load_all_finish = toDatetime(find_in_activation_log(logs, f'-- FUNCTION LOG ---', 0).split()[0][:26])

    write_to_storage_start_1 = toDatetime(find_in_activation_log(logs, f'sending event __init__', 0).split()[0][:26])
    write_to_storage_finish_1 = toDatetime(find_in_activation_log(logs, f'done sending event __init__', 0).split()[0][:26])

    write_to_storage_start_2 = find_in_activation_log(logs, f'Storing function result - Size', 0)
    write_to_storage_finish_2 = find_in_activation_log(logs, f'Finished storing function result', 0)

    if write_to_storage_start_2:
        write_to_storage_start_2 = toDatetime(find_in_activation_log(logs, f'Storing function result - Size', 0).split()[0][:26])
        write_to_storage_finish_2 = toDatetime(find_in_activation_log(logs, f'Finished storing function result', 0).split()[0][:26])

    write_to_storage_start_3 = find_in_activation_log(logs, f'Sending event __end__', 0)
    if not write_to_storage_start_3:
        write_to_storage_3 = -1
    else:
        write_to_storage_start_3 = toDatetime(write_to_storage_start_3.split()[0][:26])
        write_to_storage_finish_3 = find_in_activation_log(logs, f'done sending event __end__', 0, find_after='Sending event __end__')
        if not write_to_storage_finish_3:
            write_to_storage_finish_3 = find_in_activation_log(logs, f'Execution status sent to rabbitmq', 0, find_after='Sending event __end__')
        if write_to_storage_finish_3:
            write_to_storage_finish_3 = toDatetime(write_to_storage_finish_3.split()[0][:26])
        else:
            write_to_storage_finish_3 = getActivationEnd(aid)
        write_to_storage_3 = time_diff_milli(write_to_storage_start_3, write_to_storage_finish_3) if write_to_storage_start_3 else -1

    worker_start = toDatetime(find_in_activation_log(logs, f'Starting OpenWhisk execution', 0).split()[0][:26])
    worker_time_netto = time_diff_milli(worker_start, write_to_storage_finish_3) if write_to_storage_finish_3 else time_diff_milli(worker_start, getActivationEnd(aid))

    ow_ex_start_to_process_start = time_diff_milli(worker_start, load_all_start)

    g_func_data = time_diff_milli(g_func_data_start, g_func_data_finish) if g_func_data_start else 0
    g_func_modules = time_diff_milli(g_func_modules_start, g_func_modules_finish)

    load_all = time_diff_milli(load_all_start, load_all_finish)

    write_to_storage_1 = time_diff_milli(write_to_storage_start_1, write_to_storage_finish_1)
    write_to_storage_2 = time_diff_milli(write_to_storage_start_2, write_to_storage_finish_2) if write_to_storage_start_2 else 0
    if write_to_storage_3 > 10000:
        import pdb;pdb.set_trace()
        write_to_storage_start_3 = toDatetime(find_in_activation_log(logs, f'Sending event __end__', 0).split()[0][:26])
        write_to_storage_finish_3 = find_in_activation_log(logs, f'done sending event __end__', 0, find_after='Sending event __end__')

    func_netto = time_diff_by_labels(logs, '---------------------- FUNCTION LOG ----------------------', 'jobrunner.py -- Success function execution')
    try:
        after_func = time_diff_by_labels(logs, 'jobrunner.py -- Success function execution', 'handler.py -- Finished')
    except Exception as e:
        after_func =  toDatetime(find_in_activation_log(logs, f'jobrunner.py -- Success function execution', 0).split()[0][:26])
        after_func = time_diff_milli(after_func, getActivationEnd(aid))

    return times + (objects_num, worker_start, g_func_data, g_func_modules, load_all, write_to_storage_1, write_to_storage_2, write_to_storage_3, ow_ex_start_to_process_start, worker_time_netto, func_netto, after_func)

def get_cd_invocation_times(aid):
    logs = getActivationLogs(aid)

    times = get_activation_invocation_times(aid)

    pairs_num = find_in_activation_log(logs, f'PAIRS_NUM:', 2).split(':')[1]
    pairs_num = re.search(r"(\d+)", pairs_num).group()

    before_cd = find_in_activation_log(logs, f'before call collision_detection=', -1, all_occurences=True)

    cd_res = {}

    for b_cd in before_cd:
        pair = b_cd.split()[4].split('=')[1:]
        match = re.search(r"(\d+)_(\d+):(\d+)_(\d+)", pair[0])
        pair = match.group()

        b_ts = toDatetime(b_cd.split()[0][:26])

        a_ts_str = find_in_activation_log(logs, f'after call collision_detection={pair}', 0)

        a_ts = toDatetime(a_ts_str.split()[0][:26])

        cd_time = time_diff_milli(b_ts, a_ts)
        cd_res[cd_time] = pair

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

    write_to_storage_start_1 = toDatetime(find_in_activation_log(logs, f'sending event __init__', 0).split()[0][:26])
    write_to_storage_finish_1 = toDatetime(find_in_activation_log(logs, f'done sending event __init__', 0).split()[0][:26])

    write_to_storage_start_2 = find_in_activation_log(logs, f'Storing function result - Size', 0)
    write_to_storage_finish_2 = find_in_activation_log(logs, f'Finished storing function result', 0)

    if write_to_storage_start_2:
        write_to_storage_start_2 = toDatetime(find_in_activation_log(logs, f'Storing function result - Size', 0).split()[0][:26])
        write_to_storage_finish_2 = toDatetime(find_in_activation_log(logs, f'Finished storing function result', 0).split()[0][:26])

    write_to_storage_start_3 = find_in_activation_log(logs, f'Sending event __end__', 0)
    if write_to_storage_start_3:
        write_to_storage_start_3 = toDatetime(find_in_activation_log(logs, f'Sending event __end__', 0).split()[0][:26])
        write_to_storage_finish_3 = find_in_activation_log(logs, f'done sending event __end__', 0, find_after='Sending event __end__')
        if not write_to_storage_finish_3:
            write_to_storage_finish_3 = find_in_activation_log(logs, f'Execution status sent to rabbitmq', 0, find_after='Sending event __end__')
        if write_to_storage_finish_3:
            write_to_storage_finish_3 = toDatetime(write_to_storage_finish_3.split()[0][:26])
        else:
            write_to_storage_finish_3 = getActivationEnd(aid)

    before_cd_loop = toDatetime(find_in_activation_log(logs, f'PAIRS_NUM:', 0).split()[0][:26])
    after_cd_loop = find_in_activation_log(logs, f'after for cc in cc_in_wa', 0)
    if after_cd_loop:
        after_cd_loop = toDatetime(after_cd_loop.split()[0][:26])
    else:
        after_cd_loop = getActivationEnd(aid)

    cd_all = time_diff_milli(before_cd_loop, after_cd_loop)


    worker_start = toDatetime(find_in_activation_log(logs, f'Starting OpenWhisk execution', 0).split()[0][:26])
    worker_time_netto = time_diff_milli(worker_start, write_to_storage_finish_3) if write_to_storage_finish_3 else time_diff_milli(worker_start, getActivationEnd(aid))

    ow_ex_start_to_process_start = time_diff_milli(worker_start, load_all_start)

    g_func_data = time_diff_milli(g_func_data_start, g_func_data_finish) if g_func_data_start else 0
    g_func_modules = time_diff_milli(g_func_modules_start, g_func_modules_finish)

    load_all = time_diff_milli(load_all_start, load_all_finish)

    write_to_storage_1 = time_diff_milli(write_to_storage_start_1, write_to_storage_finish_1)
    write_to_storage_2 = time_diff_milli(write_to_storage_start_2, write_to_storage_finish_2) if write_to_storage_start_2 else 0
    write_to_storage_3 = time_diff_milli(write_to_storage_start_3, write_to_storage_finish_3) if write_to_storage_start_3 else -1
    if write_to_storage_3 > 1000:
        import pdb;pdb.set_trace()
        write_to_storage_start_3 = toDatetime(find_in_activation_log(logs, f'Sending event __end__', 0).split()[0][:26])
        write_to_storage_finish_3 = find_in_activation_log(logs, f'done sending event __end__', 0, find_after='Sending event __end__')

    func_netto = time_diff_by_labels(logs, '---------------------- FUNCTION LOG ----------------------', 'jobrunner.py -- Success function execution') 
    try:
        after_func = time_diff_by_labels(logs, 'jobrunner.py -- Success function execution', 'handler.py -- Finished')
    except Exception as e:
        after_func =  toDatetime(find_in_activation_log(logs, f'jobrunner.py -- Success function execution', 0).split()[0][:26])
        after_func = time_diff_milli(after_func, getActivationEnd(aid))

    return times + (pairs_num, min_cd, max_cd, mean_cd, median_cd,  collisions_num, min_mq, max_mq,  worker_start, g_func_data, g_func_modules, load_all, write_to_storage_1, write_to_storage_2, write_to_storage_3, cd_all, ow_ex_start_to_process_start, worker_time_netto, func_netto, after_func)

def time_diff_by_labels(logs, l1, l2):
    before = toDatetime(find_in_activation_log(logs, l1, 0).split()[0][:26])
    after = toDatetime(find_in_activation_log(logs, l2, 0).split()[0][:26])
    return time_diff_milli(before, after)

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
        import traceback
        traceback.print_exc()
        print(f"Exception {e} occured while processing tid: {tid}, aid: {aid}")
        raise e

    post_controller_time = d_post_finish_controller.timestamp() * 1000 - d_post_controller.timestamp() * 1000
    total_invoker_time = d_a_invoker_finish.timestamp() * 1000 - d_a_invoker_start.timestamp() * 1000

    return post_controller_time, total_invoker_time, controller_instance, invoker_instance

@click.command()
@click.option('--iterations', help='Number of iterations', default=1)
@click.option('--test_name', help='Used to generate uniqueue log files names', default='')
@click.option('--alias', default='DKB')
@click.option('--chunk_size', default=1, help='Size of object chunks, the actual number of chunks will be determined based on object_num / chunk_size', type=int)
@click.option('--chunk_size_range', default=None, help='Comma separated chunk sizes, used for automatic benchmarking', type=str)
@click.option('--limit', default='-1', help='Limits the number of objects. In case number of actual objects is lower it will duplicate objects up to specified limit', type=int)
@click.option('--limit_range', default=None, help='Comma separated limits', type=str)
@click.option('--ccs_limit', default=None, help='Hard limit number of connected cars', type=int)
@click.option('--dc_distributed', help='if specified will use DC in distributed approach', is_flag=True)
@click.option('--dickle', help='If specified set customized_runtime option to True', is_flag=True)
@click.option('--storageless', help='If specified set storage mode to storageless', is_flag=True)
@click.option('--logless', help='If specified no logs can be collected', is_flag=True)
@click.option('--operation', help='Operation type, cd or tp', default='cd')
@click.option('--runtime', help='Lithops runtime docker image to use')
def benchmark(iterations, test_name, alias, chunk_size, chunk_size_range, limit, limit_range, ccs_limit, dc_distributed, dickle, storageless, logless, operation, runtime):
    def iterate():
        #warmup
        try:
          do_benchmark(0, test_name, alias, chunk_size, limit, ccs_limit, dc_distributed, dickle, storageless, logless, operation, runtime)
          do_benchmark(0, test_name, alias, chunk_size, limit, ccs_limit, dc_distributed, dickle, storageless, logless, operation, runtime)
        except Exception as e:
                import traceback
                traceback.print_exc()

                # retry once
                do_benchmark(0, test_name, alias, chunk_size, limit, ccs_limit, dc_distributed, dickle, storageless, logless, operation, runtime)
        #iterate
        for i in range(iterations):
            try:
                do_benchmark(i, test_name, alias, chunk_size, limit, ccs_limit, dc_distributed, dickle, storageless, logless, operation, runtime)
            except Exception as e:
                import traceback
                traceback.print_exc()

                # retry once
                do_benchmark(i, test_name, alias, chunk_size, limit, ccs_limit, dc_distributed, dickle, storageless, logless, operation, runtime)
    
    if chunk_size_range:
        for chunk_size in chunk_size_range.split(','):
            if limit_range:
                for limit in limit_range.split(','):
                    iterate()
    else:
        iterate()

def do_benchmark(iteration, test_name, alias, chunk_size, limit, ccs_limit, dc_distributed, dickle, storageless, logless, operation, runtime):
    TEST_NAME = test_name

    logging.info(f'\n{sep}{test_name}{sep}CHUNK_SIZE: {chunk_size} LIMIT: {limit}{sep}')

    #print(f'{datetime.now()} {ACTION} post')
    req_start = datetime.now()
    data={"ALIAS": alias, "CHUNK_SIZE": chunk_size, "LIMIT": limit, "CCS_LIMIT": ccs_limit,
            'DC_DISTRIBUTED': dc_distributed, 'DICKLE': dickle, 'STORAGELESS': storageless, 'OPERATION': operation, 'RUNTIME': runtime}
            
    response = requests.post(url, params={'blocking':BLOCKING, 'result':RESULT}, json=data, auth=(user_pass[0], user_pass[1]), verify=False)

    req_end = datetime.now()

    if logless:
        req_end_to_end = round(req_end.timestamp() * 1000 - req_start.timestamp() * 1000, 1)
        print(f"no log data can be collected now, the end-to-end time is: {req_end_to_end}")
        return

    getLogs()

    aid = response.json()["activationId"]

    cdHeaders = ['cd_req_e2e', 'imports_time', 'before_dm_instance', 'dataclay_req', 'map_to_invoke', 'map_time', 'wait', 'report_time', 'run_to_return', 'contr_post_e2e', 'invoker_e2e', 'controller_id', 'invoker_id', 'all_upload', 'data_upload', 'func_upload', 'objects_num', 'chunk_size']

    cdTimes = getCDTimes(req_start, req_end, aid)
    cdTimes[0].append(limit)
    cdTimes[0].append(chunk_size)

    table = columnar(cdTimes, cdHeaders, no_borders=False)
    print(table)
    logging.info(table)

    if True:
      
      if not os.path.exists(f"{test_name}/{chunk_size}/{limit}"):
        os.makedirs(f"{test_name}/{chunk_size}/{limit}")
      csv_file_name = f'{iteration}_{chunk_size}_{"_".join(TEST_NAME.split())}_driver.csv'

      with open(f"{test_name}/{chunk_size}/{limit}/{csv_file_name}", mode='w') as f:
        writer = csv.writer(f)

        writer.writerow(cdHeaders)
        writer.writerows(cdTimes)
        return

    
    activations = getLithopsRuntimesActivationIDS(aid)
    activationsData = []
    activations_times = []
    for activation in activations:
    #    import pdb;pdb.set_trace()
        try:
            if operation == 'cd':
                activation_invocation_times = get_cd_invocation_times(activation[2])
            else:
                activation_invocation_times = get_tp_invocation_times(activation[2])
        except Exception as e:
            import pdb;pdb.set_trace()
            #activation_invocation_times = get_invocation_times(activation[2])
            print(e)


        activation_invocation_times = activation[:2] + activation_invocation_times

        activations_times.append(activation_invocation_times)
        data = []
        for i, at in enumerate(activation_invocation_times):
            data.append(at)
        activationsData.append(data)

#    import pdb;pdb.set_trace()
    if operation == 'tp':
        runtimeHeaders = ['start->inv', 'start->inv_back', 'post_cont_time', 'invoker_time', 'controller_id', 'invoker_id', 'objects_num', 'worker_start', 'g_func_data', 'g_func_modules', 'load_all', 'w_to_s_1', 'w_to_s_2', 'w_to_s_3', 'ow_ex_start_to_process_start', 'worker_time_netto', 'func_netto', 'after_func']
    else:
        runtimeHeaders = ['start->inv', 'start->inv_back', 'post_cont_time', 'invoker_time', 'controller_id', 'invoker_id', 'pairs', 'min_cd', 'max_cd', 'mean_cd', 'med_cd', 'cd_num', 'min_mq', 'max_mq', 'worker_start', 'g_func_data', 'g_func_modules', 'load_all', 'w_to_s_1', 'w_to_s_2', 'w_to_s_3', 'cd_netto', 'ow_ex_start_to_process_start', 'worker_time_netto', 'func_netto', 'after_func']
    try:
      table = columnar(activationsData, runtimeHeaders, no_borders=False)
    except Exception as e:
      import pdb;pdb.set_trace()
      table = columnar(activationsData, runtimeHeaders, no_borders=False)

    print(table)
    logging.info(table)

    def column(matrix, i):
        return [row[i] for row in matrix]

    if operation == 'cd':
    #import pdb;pdb.set_trace()
      min_worker_start = min(column(activationsData, 14))
      max_worker_start = max(column(activationsData, 14))
    #import pdb;pdb.set_trace()
      min_max_worker_start = time_diff_milli(min_worker_start, max_worker_start)

      min_worker = min(column(activationsData, 0))
      max_worker = max(column(activationsData, 0))

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
      summaryData = [[round(max_worker - min_worker, 2), min_max_worker_start, chunk_size, cd_min_time_ids, cd_max_time_ids, round(cd_avg, 2), f'{mqtt_publish_min} {mqtt_publish_min_ids}', f'{mqtt_publish_max} {mqtt_publish_max_ids}', detections_num]]
    else:
      min_worker_start = min(column(activationsData, 7))
      max_worker_start = max(column(activationsData, 7))
      #import pdb;pdb.set_trace()
      min_max_worker_start = time_diff_milli(min_worker_start, max_worker_start)

      min_worker = min(column(activationsData, 0))
      max_worker = max(column(activationsData, 0))

      summaryHeaders = ['first2last_worker', 'min_max_worker_start', 'chunk_size']
      summaryData = [[round(max_worker - min_worker, 2), min_max_worker_start, chunk_size]]


    if TEST_NAME:
        summaryHeaders.insert(0, 'test name')
        summaryData[0].insert(0, TEST_NAME)

    table = columnar(summaryData, summaryHeaders, no_borders=False)
    print(table)
    logging.info(table)

    if not os.path.exists(f"{test_name}/{chunk_size}/{limit}"):
        os.makedirs(f"{test_name}/{chunk_size}/{limit}")

    csv_file_name = f'{iteration}_{chunk_size}_{"_".join(TEST_NAME.split())}_driver.csv'

    with open(f"{test_name}/{chunk_size}/{limit}/{csv_file_name}", mode='w') as f:
        writer = csv.writer(f)

        writer.writerow(cdHeaders)
        writer.writerows(cdTimes)

        writer.writerow(summaryHeaders)
        writer.writerows(summaryData)

    csv_file_name = f'{iteration}_{chunk_size}_{"_".join(TEST_NAME.split())}_worker.csv'
    with open(f"{test_name}/{chunk_size}/{limit}/{csv_file_name}", mode='w') as f:
        writer = csv.writer(f)

        writer.writerow(runtimeHeaders)
        writer.writerows(activationsData)

    logging.info('=================================================================\n\n')
	
if __name__ == '__main__':
    benchmark()
