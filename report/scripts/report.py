import time
import sys
import redis
import itertools
import argparse
from operator import itemgetter
from collections import defaultdict, Counter

import Levenshtein

'''
1. Get the groups of keys based on their Levenshtein distance. 
     - Start with levenshtein_dist < len(target_str) / 2 - at least under 50% of the original string. Offer it as an option.
     - once a key goes into the group increment its gets/sets statistics
     - remove it from the list
2. Calculate the common prefix for each group
'''

class Report(object):
    """
    Running a key analysis of the keys found in the Redis database.
        - calculates the hitrate based on the following formula: hitrate = (gets / (gets + sets)) * 100
        - uses the Levenshtein distance to group keys together
    """

    def __init__(self):
        """Initiates a connection to the Redis server.""" 
        pool = redis.ConnectionPool(host='redis', port=6379, db=0)
        self.redis = redis.Redis(connection_pool=pool)

    def common_prefix(self, strings):
        "Given a list of pathnames, returns the longest common leading component"
        if not strings: return ''
        s1 = min(strings)
        s2 = max(strings)
        for i, c in enumerate(s1):
            if c != s2[i]:
                return s1[:i]
        return s1

    def get_keys(self, key_name):
        return self.redis.keys(key_name)

    def get_matching_groups(self, keys, levenshtein_distance=0.5):
        "Given a list of keys, group them together based on their similarity using the Levenshtein distance"

        groups      = defaultdict(dict)
        processed   = defaultdict(dict)

        levenshtein_distance = float(levenshtein_distance)

        i = 0
        n = len(keys)
        
        for i in range(0, n):
            for j in range(i+1, n):

                # Don't process keys that have already been assigned in groups.
                if processed[keys[j]]: 
                    continue

                l_d = float(Levenshtein.distance(keys[i], keys[j]))
                
                min_str = min([keys[i], keys[j]], key=len)
                min_len = len(min_str)

                # 50% minimum string length compared to the total Levenshtein distance.
                if min_len * levenshtein_distance >= l_d:
                    prefix = self.common_prefix([keys[i], keys[j]])
                    
                    groups[prefix][len(groups[prefix]) + 1] = keys[i]
                    groups[prefix][len(groups[prefix]) + 1] = keys[j]
                    
                    processed[keys[j]] = True
                j+= 1
            i += 1

        return groups

    def get_hitrate(self, keys):
        """Given the list of keys, returns a report containing the number of GET/SET and hit rate for each key"""

        report          = defaultdict(int)
        report_sorted   = defaultdict(int)
        
        try:
            report.clear()
            del report_sorted

            for key in keys:
                                
                obj = self.redis.hgetall(key)

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

            return report
        except Exception as e:
            print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e), e

def print_report_header():
    print '{:<90}'.format('Key'),
    print '{:<10}'.format('Count'),
    print '{:<10}'.format('GET'),
    print '{:<10}'.format('SET'),
    print '{:<10}'.format('Hit Rate (%)')
    print '{:<130}'.format('-' * 130)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generates a hit rate report from the Redis keys')
    parser.add_argument('-p','--prefix_only', action='store_true', help='Show individual keys', required=False)
    parser.add_argument('-l','--levenshtein_distance', help='Manually calibrate the Levenshtein distance in percentage of smallest string. Default is 0.5', required=False)

    args = vars(parser.parse_args())

    detailed_report = True
    if args['prefix_only']:
        detailed_report = False

    levenshtein_distance = 0.5
    if args['levenshtein_distance']:
        levenshtein_distance = args['levenshtein_distance']

    report  = Report()
    keys    = report.get_keys('*')
    
    # Getting all keys and their associated GET, SET and Hit Rate.
    hitrate_report = report.get_hitrate(keys)
    hitrate_report_sorted = sorted(hitrate_report.items(), key=lambda item: int(item[1]['hitrate']))

    # Grouping the keys in smaller sets based on their prefix.
    key_groups = report.get_matching_groups(keys, levenshtein_distance)
    
    key_group_report        = defaultdict(int)
    key_group_report_sorted = defaultdict(int)

    # Building a report based on their hit rate.
    for prefix, group in key_groups.items():

        gets = 0
        sets = 0
        hitrate = 0
        
        for i, key in group.items():
            gets += hitrate_report[key]['get']
            sets += hitrate_report[key]['set']

        key_count = len(group)
        gets = float(gets)
        sets = float(sets)

        if gets + sets > 0:
            hitrate = (gets / (gets + sets)) * 100
        
        key_group_report[prefix] = {}
        key_group_report[prefix]['items'] = int(key_count)
        key_group_report[prefix]['gets'] = int(gets)
        key_group_report[prefix]['sets'] = int(sets)
        key_group_report[prefix]['hitrate'] = int(hitrate)

    # Sort the report.
    key_group_report_sorted = sorted(key_group_report.items(), key=lambda item: int(item[1]['hitrate']))

    if not detailed_report:
        print_report_header()

    # Show the report.
    for prefix, value in key_group_report_sorted:

        if detailed_report:

            print_report_header()
            
            # For each prefix ket the associated keys.
            keys = key_groups[prefix]
            for i, key in keys.items():
                key_ = key
                if len(key_) > 90: key_ = key_[:80] + '...'

                print '{:<90}'.format(key_),
                print '{:<10}'.format(1),
                print '{:<10}'.format(hitrate_report[key]['get']),
                print '{:<10}'.format(hitrate_report[key]['set']),
                print '{:<10}'.format(hitrate_report[key]['hitrate'])

            print '{:<130}'.format('-' * 130)

        if len(prefix) > 90: prefix = prefix[:80] + '...'

        prefix_output = ''

        prefix_output += '{:<91}'.format(prefix + "*")
        prefix_output += '{:<11}'.format(value['items'])
        prefix_output += '{:<11}'.format(value['gets'])
        prefix_output += '{:<11}'.format(value['sets'])
        prefix_output += '{:<11}'.format(value['hitrate'])

        # The detailed report gets printed in colors for better readability.
        print prefix_output

        if detailed_report: 
            print
        
    