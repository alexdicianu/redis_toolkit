import sys
import redis
import time
from collections import defaultdict, Counter

def redis_get():
    return [
        'GET',
        'MGET',
        'HGET',
        'HMGET',
        'HGETALL'
    ]

def redis_set():
    return [
        'SET',
        'HMSET',
        'HSET',
        'HSETNX',
        'LSET',
        'MSET',
        'MSETNX',
        'PSETEX',
        'SETEX',
        'SETNX',
        'SETRANGE'
    ]

def redis_del():
    return [
        'DEL',
        'HDEL',
        'UNLINK'
    ]

def get_op(operation):
    if operation in redis_get(): return 'get'
    if operation in redis_set(): return 'set'
    if operation in redis_del(): return 'del'
    return None

def get_lifetime(last_set, lifetime=0):
    last_set = float(last_set)
    current_lifetime = float(lifetime)

    current_timestamp = time.time()
    new_lifetime      = current_timestamp - last_set

    # Check if we have an existing lifetime and calculate the average if there is one.
    if current_lifetime > 0:
        new_lifetime = (new_lifetime + current_lifetime) / 2
        
    return new_lifetime
    
    
if __name__ == '__main__':
    pool = redis.ConnectionPool(host='redis_toolkit_db', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)
    
    for line in sys.stdin:
        try:
            try:
                l = line.split()
                operation, key = l[3].strip('"'), l[4].strip('"')
                
                # Only logging GET/SET calls.
                op = get_op(operation)
                if op is None: 
                    continue
                
            except Exception as e:
                print("Error on line {}. Command: {}".format(sys.exc_info()[-1].tb_lineno, line), type(e), e)
                continue

            obj = r.hgetall(key)

            if not obj:
                obj = {
                    "get": 0,
                    "set": 0,
                    "size": 0,
                    "last_set": 0,
                    "lifetime": 0
                }
                
            if op is 'get':
                obj['get'] = int(obj['get']) + 1

                # Check the last time the object was set for calculating lifetime.
                obj['last_set'] = float(obj['last_set'])
                if obj['last_set'] > 0:
                    # By default the new lifetime is the difference from when the object was last set until now.
                    obj['lifetime'] = get_lifetime(obj['last_set'], obj['lifetime'])

            elif op is 'set':
                obj['set'] = int(obj['set']) + 1

                # Average size of this key.
                size = len(line)
                if obj['size'] == 0: 
                    obj['size'] = size
                else:
                    obj['size'] = float(obj['size'])
                    size = float(size)
                    obj['size'] = (obj['size'] + size) / 2

                # Lifetime - just set the timestamp of the last SET operation.
                obj['last_set'] = time.time()

            elif op is 'del':
                # Calculate lifetime until this moment and reset it.
                last_set = float(obj['last_set'])
                if last_set > 0:
                    # By default the new lifetime is the difference from when the object was last set until now.
                    new_lifetime = get_lifetime(last_set, obj['lifetime'])

                obj['last_set'] = 0
                obj['lifetime'] = new_lifetime


            #print op, key, obj
            r.hmset(key, obj)
            
        except Exception as e:
            print("Error on line {}".format(sys.exc_info()[-1].tb_lineno), type(e), e)
            continue

