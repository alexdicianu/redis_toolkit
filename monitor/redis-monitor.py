import time
import sys
import redis
from operator import itemgetter
from collections import defaultdict, Counter

# Only insterested in GET/SET for now.
operations = ['GET', 'SET']

def get_header():
    print '{:<110}'.format('Key'),
    print '{:<10}'.format('Gets'),
    print '{:<10}'.format('Sets'),
    print '{:<10}'.format('Hit Rate (%)'),
    print "\n"

if __name__ == '__main__':
    r = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)
    report = defaultdict(int)
    report_sorted = defaultdict(int)
    
    try:
        report.clear()
        del report_sorted

        keys = r.keys('*')

        for key in keys:
            
            obj = r.hgetall(key)

            if not obj:
                obj = {
                    "get": 0,
                    "set": 0,
                    "hitrate": 0
                }

            hitrate = 0
            gets = float(obj['get'])
            sets = float(obj['set'])
            if gets + sets > 0:
                hitrate = (gets / (gets + sets)) * 100
                
            report[key] = obj
            report[key]['hitrate'] = int(hitrate)
            report[key]['get'] = int(report[key]['get'])
            report[key]['set'] = int(report[key]['set'])

        report_sorted = sorted(report.items(), key=lambda item: int(item[1]['hitrate']))
        
        get_header()

        for key, value in report_sorted:
            print '{:<110}'.format(key),
            print '{:<10}'.format(value['get']),
            print '{:<10}'.format(value['set']),
            print '{:<10}'.format(value['hitrate'])
            
        print "\n"
    except Exception as e:
        print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e), e
    