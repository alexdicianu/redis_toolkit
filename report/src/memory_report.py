import redis
import os

import cPickle as pickle

from argparse import ArgumentParser, RawTextHelpFormatter
from collections import defaultdict, Counter
from prefixtree import Node


class MemoryReportNode(Node):
    """Extending the Node class with some custom attributes specific to the hit rate only."""

    def __init__(self, key):

        # The key size. Non-leaf nodes have a total size calculated as the sum of all sizes.
        Node.size = 0

        super(MemoryReportNode, self).__init__(key)

    def populate(self, node=None):
        """
        Populates the nodes with the data (nr. of gets, sets, hitrate, avg size, lifetime) from the local redis.
        @return a tuple (leaf_count, nr. of gets, nr. of sets)
        """
        if node == None: node = self

        for i, child in enumerate(node.children):
            if child.is_leaf():
                # This is where I query Redis for the key information (gets, set, hitrate, etc).
                size = redis_get_size(child.key)

                child.leaf_count = 1
                child.size       = size

                # Increment leaf count.
                node.leaf_count += 1

                # Increment the total size and size_count.
                node.size += child.size
                
            else:
                obj = self.populate(child)
                
                node.leaf_count += obj['leaf_count']
                node.size += obj['size']

        return {
            'leaf_count': node.leaf_count,
            'size': node.size
        }

    def build_report(self, node=None, levels=3):
        """Renders the tree [levels] deep."""
        if node == None: node = self

        if levels == 0: return

        key = node.key
        if not node.is_leaf():
            key = key + ":*"

        # Check to see if we print the key (only print the key and its parent).
        if levels == 1:

            report[key] = {
                'key': key,
                'leaf_count': node.leaf_count,
                'size': self.get_size(node)
            }
        
        if node.children is not None:
            for child in node.children:
                self.build_report(node=child, levels=levels - 1)
    
    def get_size(self, node):
        """Calculate the average size and convert it from Bytes to KB and round the result."""
        if node == None: node = self

        size = round(float(node.size) / float(1024), 2)
        return size

def print_report_header():
    print
    print '{:<90}'.format('Key'),
    print '{:<10}'.format('Nr. keys'),
    print '{:<15}'.format('Size (KB)')
    print '{:<170}'.format('-' * 170)


def redis_keys(keys):
    """Returns all the keys from the Redis server in the global connection pool."""
    r = redis.Redis(connection_pool=pool)
    return r.keys('*')
    
def redis_hgetall(keys):
    """Returns all the keys and their values from the Redis server in the global connection pool."""
    r = redis.Redis(connection_pool=pool)
    return "{}: {}".format(r.type(keys), keys)
    #return r.hgetall(keys)

def redis_get_size(key):
    r = redis.Redis(connection_pool=pool)
    key_type = r.type(key)

    object_size = 0

    if key_type == "hash":
        data = r.hgetall(key)

        for i, k in data.items():
            object_size += len(k)
    elif key_type == "set":
        data = r.smembers(key)

        for k in data:
            object_size += len(k)

    elif key_type == "string":
        data = r.get(key)
        object_size += len(data)

    return object_size

def save_object(obj, filename):
    """Saves an object to a file in a binary form to act as a caching mechanism."""
    with open(filename, 'wb') as o:
        pickle.dump(obj, o, pickle.HIGHEST_PROTOCOL)

def load_object(filename):
    """Loads an object from file."""
    with open(filename, 'rb') as i:
        return pickle.load(i)

if __name__ == '__main__':
    
    parser = ArgumentParser(description='Generates a memory utilization report from the Redis keys', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--name', help='The name of this report (e.g. --name clientname). This is going to be stored locally so that future reports take less time.', required=True)
    parser.add_argument('--regenerate', action='store_true', help='Regenerate the report.', required=False)
    parser.add_argument('--level', help='How many levels deep the report should render.', required=False)
    parser.add_argument('--prefix', help='Filter by prefix.', required=False)
    
    args = vars(parser.parse_args())

    # The report object will be stored locally.
    if args['name']:
        filename = '/data/' + args['name'] + '.pkl'

    # Filter the report by prefix.
    prefix_filter = None
    if args['prefix']:
        prefix_filter = args['prefix']
        # Remove the wildcard in case we detect it.
        if prefix_filter.endswith('*'):
            prefix_filter = prefix_filter[:-1]
            
    # How deep do we want to go.
    levels = 3
    # The argument takes priority.
    if args['level']:
        levels = int(args['level'])
    elif prefix_filter is not None:
        # Try to automatically determine this based on prefix (if we have any).
        levels = len(prefix_filter.split(':')) + 1

    # Global connection pool to the local Redis.
    pool = redis.ConnectionPool(host='redis_monitor_db', port=6379, db=0)

    root = None

    # Flush the local data to regenerate the report.
    if args['regenerate']:
        if os.path.exists(filename): 
            os.remove(filename)

    # Attempts to load from cache.
    if os.path.exists(filename):
        root = load_object(filename)
        
    if not root:
        keys = redis_keys('*')

        root = MemoryReportNode('ROOT')
        root.build_tree(keys)

        # Show more feedback. Populating takes a few extra seconds.
        root.progress(100, 100, suffix='Almost there ...')
        root.populate()

        # Build the cache.
        save_object(root, filename)
    
    # Global variable which will be populated for sorting purposes.
    report = defaultdict(dict)
    root.build_report(levels=levels)
    report_sorted = sorted(report.items(), key=lambda item: int(item[1]['leaf_count']), reverse=True)

    print_report_header()

    for i, line in report_sorted:

        # We have a prefix filter.
        if prefix_filter is not None:
            line_ = line['key']
            if not line_.startswith(prefix_filter): continue

        if len(line['key']) > 80:
            line['key'] = line['key'][:80] + '...'

        print "{:<90}".format(line['key']),
        print "{:<10}".format(line['leaf_count']),
        print "{:<15}".format(line['size'])
        