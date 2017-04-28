import time
import curses
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
    
if __name__ == '__main__':
    pool = redis.ConnectionPool(host='redis', port=6379, db=0)
    r = redis.Redis(connection_pool=pool)
    
    for line in sys.stdin:
        try:
            
            l = line.split()

            try:
                operation, key = l[3].strip('"'), l[4].strip('"')
            except Exception as e:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e), e)
                continue

            obj = r.hgetall(key)

            if not obj:
                obj = {
                    "get": 0,
                    "set": 0
                }
                
            if operation in redis_get():
                obj['get'] = int(obj['get']) + 1
            elif operation in redis_set():
                obj['set'] = int(obj['set']) + 1

            r.hmset(key, obj)
            
        except Exception as e:
            print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e), e
            continue

