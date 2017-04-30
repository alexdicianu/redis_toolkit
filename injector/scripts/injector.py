import sys
import redis
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

def get_op(operation):
    if operation in redis_get(): return 'get'
    if operation in redis_set(): return 'set'
    return None
    
if __name__ == '__main__':
    pool = redis.ConnectionPool(host='redis', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)
    
    for line in sys.stdin:
        try:
            #print "\n\n"
            #print "LINE:", line
            try:
                l = line.split()
                operation, key = l[3].strip('"'), l[4].strip('"')
                
                #print "OPERATION:", operation
                #print "KEY:", key

                # Only logging GET/SET calls.
                op = get_op(operation)
                if op is None: 
                    #print "Non GET/SET operation detected:", operation
                    continue
                
                #print "GET/SET operation detected:", operation, key

            except Exception as e:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e), e)
                continue

            obj = r.hgetall(key)

            if not obj:
                obj = {
                    "get": 0,
                    "set": 0,
                    "size": 0
                }
                
            if op is 'get':
                obj['get'] = int(obj['get']) + 1
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

            #print "OBJ:", obj

            r.hmset(key, obj)
            
        except Exception as e:
            print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e), e
            continue

