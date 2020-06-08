import time

BEGIN = time.time()
start = BEGIN

def timeConsumed(name):
    global start
    print(f'{name} time: {time.time() - start}, current time: {time.time()}')
    start = time.time()
