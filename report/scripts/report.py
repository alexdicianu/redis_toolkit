import sys
import redis

from collections import defaultdict, Counter
from argparse import ArgumentParser, RawTextHelpFormatter
from textwrap import dedent

import Levenshtein

class Report(object):
    """
    Running a key analysis of the keys found in the Redis database.
        - calculates the hitrate based on the following formula: hitrate = (gets / (gets + sets)) * 100
        - uses the Levenshtein distance to group keys together
    """

    def __init__(self):
        """Initiates a connection to the Redis server.""" 
        pool = redis.ConnectionPool(host='redis_monitor_db', port=6379, db=0)
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

    def get_matching_groups(self, keys, similarity_degree=0.2, hide_progress_bar=False):
        "Given a list of keys, group them together based on their similarity using the Levenshtein distance"

        groups      = defaultdict(dict)
        processed   = defaultdict(dict)

        similarity_degree = float(similarity_degree)

        i = 0
        n = len(keys)
                
        for i in range(0, n):

            if processed[keys[i]]: continue

            for j in range(i+1, n):
                # Don't process keys that have already been assigned in groups.
                if processed[keys[j]]: continue

                l_d     = float(Levenshtein.distance(keys[i], keys[j]))
                min_len = len(min([keys[i], keys[j]], key=len))

                prefix = self.common_prefix([keys[i], keys[j]])

                # Biggest string length compared to the total Levenshtein distance.
                if min_len * similarity_degree >= l_d:
                    
                    prefix_threshold = (float(len(prefix)) / float(min_len))
                    # We need to check this as well to avoid having very different strings with a low Levenshtein distance.
                    # E.g.
                    #   - pantheon-redis:cache_path:fitness/50-bodyweight-exercises-you-can-do-anywhere-030612
                    #   - pantheon-redis:cache_page:http://www.test.com/fitness/50-bodyweight-exercises-you-can-do-anywhere-030612
                    if prefix_threshold > 1 - similarity_degree:
                        processed[keys[j]] = True
                        groups[prefix][len(groups[prefix]) + 1] = keys[j]
                j+= 1
                
            processed[keys[i]] = True
            groups[prefix][len(groups[prefix]) + 1] = keys[i]
            
            # For long running reports show some progress feedback.
            if not hide_progress_bar: progress(i, n)

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
                        "size": 0,
                        "hitrate": 0
                    }

                hitrate = 0
                gets = float(obj['get'])
                sets = float(obj['set'])
                if gets + sets > 0:
                    hitrate = (gets / (gets + sets)) * 100
                    
                report[key]             = obj
                report[key]['hitrate']  = int(hitrate)
                report[key]['get']      = int(report[key]['get'])
                report[key]['set']      = int(report[key]['set'])
                report[key]['size']     = int(float(report[key]['size']))

            return report
        except Exception as e:
            print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e), e

def print_report_header():
    print '{:<90}'.format('Key'),
    print '{:<10}'.format('Count'),
    print '{:<10}'.format('GET'),
    print '{:<10}'.format('SET'),
    print '{:<15}'.format('Hit Rate (%)'),
    print '{:<15}'.format('Avg Size (KB)'),
    print '{:<20}'.format('Lifetime (seconds)')
    print '{:<170}'.format('-' * 170)


def progress(count, total, suffix=''):
    """Generic progressbar for showing group matching progress."""

    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '#' * filled_len + '_' * (bar_len - filled_len)

    sys.stdout.write('Crunching numbers [%s] %s%s %s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()

def size_format(size):
    """Convert the size from Bytes to KB and round the result."""
    size = round(float(size) / float(1024), 2)
    if size <= 0: return 'n/a'
    return size

def lifetime_format(lifetime):
    """Proper format for the lifetime"""
    lifetime = round(float(lifetime), 2)
    if lifetime <= 0: return 'n/a'
    return lifetime

def main(args):
    """Main script function where the report gets printed to stdout."""

    prefix_only = False
    if args['prefix_only']:
        prefix_only = True

    similarity_degree = 0.2
    if args['similarity_degree']:
        similarity_degree = args['similarity_degree']

    hide_progress_bar = False
    if args['hide_progress_bar']:
        hide_progress_bar = True

    report  = Report()
    keys    = report.get_keys('*')
    
    # Getting all keys and their associated GET, SET and Hit Rate.
    hitrate_report = report.get_hitrate(keys)
    hitrate_report_sorted = sorted(hitrate_report.items(), key=lambda item: int(item[1]['hitrate']))

    # Grouping the keys in smaller sets based on their prefix.
    key_groups = report.get_matching_groups(keys, similarity_degree, hide_progress_bar)
    
    key_group_report        = defaultdict(int)
    key_group_report_sorted = defaultdict(int)

    # Building a report based on their hit rate.
    for prefix, group in key_groups.items():

        gets    = 0
        sets    = 0
        hitrate = 0
        # In order to not skew the average, we must ignore keys for which the size is zero.
        size        = 0
        n_size      = 0

        lifetime    = 0
        n_lifetime  = 0
        
        for i, key in group.items():
            gets += hitrate_report[key]['get']
            sets += hitrate_report[key]['set']
            if hitrate_report[key]['size'] > 0:
                n_size      += 1
                size        += hitrate_report[key]['size']
            
            lifetime_ = float(hitrate_report[key]['lifetime'])
            if lifetime_ > 0: 
                n_lifetime  += 1
                lifetime    += lifetime_

        key_count   = len(group)
        gets        = float(gets)
        sets        = float(sets)
        # Converting size to from bytes to KB
        avg_size = 0
        if n_size > 0:
            avg_size = float(size) / float(n_size)

        if gets + sets > 0:
            hitrate = (gets / (gets + sets)) * 100

        avg_lifetime = 0
        if n_lifetime > 0:
            avg_lifetime = float(lifetime) / float(n_lifetime)
        
        key_group_report[prefix] = {}
        key_group_report[prefix]['items']    = int(key_count)
        key_group_report[prefix]['gets']     = int(gets)
        key_group_report[prefix]['sets']     = int(sets)
        key_group_report[prefix]['hitrate']  = int(hitrate)
        key_group_report[prefix]['size']     = size_format(avg_size)
        key_group_report[prefix]['lifetime'] = lifetime_format(avg_lifetime)

    # Sort the report.
    key_group_report_sorted = sorted(key_group_report.items(), key=lambda item: int(item[1]['hitrate']))

    if prefix_only: print_report_header()

    # Show the report.
    for prefix, value in key_group_report_sorted:

        if not prefix_only:

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
                print '{:<15}'.format(hitrate_report[key]['hitrate']),
                # Converting size to from bytes to KB
                size = size_format(hitrate_report[key]['size'])
                print '{:<15}'.format(size),
                
                print '{:<20}'.format(lifetime_format(hitrate_report[key]['lifetime']))

            print '{:<170}'.format('-' * 170)

        if len(prefix) > 90: prefix = prefix[:80] + '...'

        prefix_output = ''

        prefix_output += '{:<91}'.format(prefix + "*")
        prefix_output += '{:<11}'.format(value['items'])
        prefix_output += '{:<11}'.format(value['gets'])
        prefix_output += '{:<11}'.format(value['sets'])
        prefix_output += '{:<16}'.format(value['hitrate'])
        prefix_output += '{:<16}'.format(value['size'])
        prefix_output += '{:<21}'.format(value['lifetime'])

        # The detailed report gets printed in colors for better readability.
        print prefix_output

        if not prefix_only: print

if __name__ == '__main__':

    parser = ArgumentParser(description='Generates a hit rate report from the Redis keys', formatter_class=RawTextHelpFormatter)

    similarity_degree_help = dedent('''\
        Manually calibrate the similarity degree. Default is 0.2
            - values close to 0 will try to create many groups with very little differences between them.
            - values close to 1 will try to create less groups with many differences between strings but a smaller common prefix.
    ''')

    parser.add_argument('--prefix_only', action='store_true', help='Only show the groups of keys.', required=False)
    parser.add_argument('-s', '--similarity_degree', help=similarity_degree_help, required=False)
    parser.add_argument('--hide_progress_bar', action='store_true', help='Hides the progress bar in case you want to redirect the output to a file.', required=False)

    args = vars(parser.parse_args())

    main(args)
