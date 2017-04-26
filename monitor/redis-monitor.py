import time
import sys
import redis
from operator import itemgetter
from collections import defaultdict, Counter

# Only insterested in GET/SET for now.
operations = ['GET', 'SET']

def get_header():
    output = '{:<128}'.format('Key')
    output += '{:<15}'.format('Gets')
    output += '{:<15}'.format('Sets')
    output += '{:<15}'.format('Hit Rate (%)')
    output += "\n"
    return output

if __name__ == '__main__':
    display_limit = int(sys.argv[1])

    r = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)
    report = defaultdict(int)
    
    while 1:
        try:
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

            s = sorted(report.items(), key=lambda item: int(item[1]['hitrate']))
            
            output = get_header()

            index = 0
            
            for key, value in s:
                output += '{:<128}'.format(key)
                output += '{:<15}'.format(value['get'])
                output += '{:<15}'.format(value['set'])
                output += '{:<15}'.format(value['hitrate'])
                output += "\n"
                
                print output

                index += 1
                if index >= display_limit: break
            
            print "\n"
            time.sleep(5)
        except Exception as e:
            print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e), e
            continue
    