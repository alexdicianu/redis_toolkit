import sys
import os
import redis
import pickle

from argparse import ArgumentParser, RawTextHelpFormatter

from collections import defaultdict, Counter

class Node(object):

    '''
    Each node has:
        - a key which acts as a prefix for its children.
        - a leaf_count property where the number of all leaf nodes is being stored (not children!!).
        - a list of Node objects as children.
    '''
    
    def __init__(self, key):
        """Sets some default values for the object.""" 

        # The key name. If the key is not a leaf node, the name is it's prefix.
        self.key = key

        # How many leaves does the node have.
        self.leaf_count = 0

        # The node's children
        self.children = []

        # The number of GET operations.
        self.get = 0

        # The number of SET operations
        self.set = 0

        # The key size. Non-leaf nodes have a total size calculated as the sum of all sizes.
        self.size = 0

        # The number of keys that actually have a size value. Useful for an accurate average key size.
        self.size_count = 0

        # The life time defined as the time between 2 consecutive sets.
        self.lifetime = 0

        # The number of keys that actually have a lifetime value. Useful for an accurate average life time.
        self.lifetime_count = 0

    def add_child(self, key, parent_key=None):
        """Adds a child node to the tree by recursively searching for its parent."""

        child_keys = self.get_children_keys()
        
        # If I reached the parent.
        if parent_key == self.key:
            if key not in child_keys:
                self.children.append(Node(key))
        else:
            if self.children is not None:
                for child in self.children:
                    # Check if we are on the right branch. We don't want to scan the entire tree.
                    if parent_key.startswith(child.key):
                        child.add_child(key, parent_key)

    def build_tree(self, keys):
        """Builds the tree from a list of keys and shows a progress bar."""

        index = 0
        total_keys = len(keys)

        for key in keys:
            prefixes = self.build_prefixes(key)
            for i, prefix in enumerate(prefixes):
                if i == 0: 
                    parent_key = 'ROOT'
                else:
                    parent_key = prefixes[i-1]

                root.add_child(prefix, parent_key)

            index += 1
            progress(index, total_keys)
            
    def split(self, key):
        """Splits a key based a the colon character (:). Redis key buckets are separated by it. E.g. options:alloptions"""
        return key.split(':')

    def build_prefixes(self, key):
        """
        Builds a list of prefixes each of them one level bigger than its predecesor. 
        Example:
            - pantheon-redis
            - pantheon-redis:cache_page
            - pantheon-redis:cache_page:www.example.com
        """
        key_parts = self.split(key)

        i = 0
        n = len(key_parts)

        prefixes = []
        
        for i in range(i, n):
            key_part = ":".join(key_parts[:i+1])
            prefixes.append(key_part)
            i += 1

        return prefixes

    def populate(self, node=None):
        """
        Populates the nodes with the data (nr. of gets, sets, hitrate, avg size, lifetime) from the local redis.
        @return a tuple (leaf_count, nr. of gets, nr. of sets)
        """
        if node == None: node = self

        for i, child in enumerate(node.children):
            if child.is_leaf():
                # This is where I query Redis for the key information (gets, set, hitrate, etc).
                data = redis_hgetall(child.key)
                
                child.leaf_count = 1

                try: 
                    child.get  = int(data['get'])
                    child.set  = int(data['set'])
                    # Only leaf nodes have fixed sizes and lifetimes (directly from Redis).
                    child.size = float(data['size'])
                    child.lifetime = float(data['lifetime'])
                except KeyError:
                    pass
                    # Sometimes not all the keys are set ... Just using defaults.
                    #sys.stderr.write('Error on line {}. {}, {}'.format(sys.exc_info()[-1].tb_lineno, type(e), e))

                # For average calculation.
                if child.size > 0:
                    child.size_count = 1

                if child.lifetime > 0:
                    child.lifetime_count = 1

                # Increment leaf count.
                node.leaf_count += 1

                # Increment the number of gets and sets.
                node.get += child.get
                node.set += child.set

                # Increment the total size and size_count.
                node.size += child.size
                if child.size > 0:
                    node.size_count += 1

                node.lifetime += child.lifetime
                if child.lifetime > 0:
                    node.lifetime_count += 1

            else:
                obj = self.populate(child)
                
                node.leaf_count += obj['leaf_count']

                node.get += obj['get']
                node.set += obj['set']

                node.size       += float(obj['size'])
                node.size_count += obj['size_count']

                node.lifetime       += float(obj['lifetime'])
                node.lifetime_count += obj['lifetime_count']

        return {
            'leaf_count': node.leaf_count,
            'get': node.get,
            'set': node.set,
            'size': node.size,
            'size_count': node.size_count,
            'lifetime': node.lifetime,
            'lifetime_count': node.lifetime_count,
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
                'get': node.get,
                'set': node.set,
                'leaf_count': node.leaf_count,
                'hitrate': node.get_hitrate(),
                'size': node.get_size(),
                'lifetime': node.get_lifetime()
            }
        
        if node.children is not None:
            for child in node.children:
                self.build_report(child, levels=levels - 1)

    def get_children_keys(self):
        """Returns a list of child key names for the current object."""
        keys = []

        for child in self.children:   
            keys.append(child.key)

        return keys

    def is_leaf(self):
        """Checks if the current node is a leaf (leaf nodes have no children)."""
        if len(self.children) == 0:
            return True
        return False

    def get_hitrate(self):
        """Calculate the hitrate for the current node."""
        hitrate = 0
        gets = float(self.get)
        sets = float(self.set)

        if gets + sets > 0:
            hitrate = (gets / (gets + sets)) * 100

        return str(int(hitrate))

    def get_size(self):
        """Calculate the average size and convert it from Bytes to KB and round the result."""

        if self.size_count == 0: return 'n/a'

        avg_size = float(self.size) / float(self.size_count)
        size = round(float(avg_size) / float(1024), 2)

        if size <= 0: return 'n/a'
        return size

    def get_lifetime(self):
        """Proper format for the lifetime"""

        if self.lifetime_count == 0: return 'n/a'

        avg_lifetime = float(self.lifetime) / float(self.lifetime_count)

        lifetime = round(float(avg_lifetime), 2)
        if lifetime <= 0: return 'n/a'
        return lifetime


def progress(count, total, suffix=''):
    """Generic progressbar for showing group matching progress."""

    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '#' * filled_len + '_' * (bar_len - filled_len)

    sys.stdout.write('Crunching numbers [%s] %s%s %s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()

def save_object(obj, filename):
    """Saves an object to a file in a binary form to act as a caching mechanism."""
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

def load_object(filename):
    """Loads an object from file."""
    with open(filename, 'rb') as input:
        return pickle.load(input)

def print_report_header():
    print
    print '{:<90}'.format('Key'),
    print '{:<10}'.format('Nr. keys'),
    print '{:<10}'.format('GET'),
    print '{:<10}'.format('SET'),
    print '{:<15}'.format('Hit Rate (%)'),
    print '{:<15}'.format('Avg Size (KB)'),
    print '{:<20}'.format('Lifetime (seconds)')
    print '{:<170}'.format('-' * 170)


def redis_keys(keys):
    """Returns all the keys from the Redis server in the global connection pool."""
    r = redis.Redis(connection_pool=pool)
    return r.keys('*')
    
def redis_hgetall(keys):
    """Returns all the keys and their values from the Redis server in the global connection pool."""
    r = redis.Redis(connection_pool=pool)
    return r.hgetall(keys)

if __name__ == '__main__':
    
    parser = ArgumentParser(description='Generates a hit rate report from the Redis keys', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--no_cache', action='store_true', help='Flush the previous report from cache.', required=False)
    parser.add_argument('-l', '--level', help='How many levels deep the report should render.', required=False)
    parser.add_argument('-p', '--prefix', help='Filter by prefix.', required=False)
    
    args = vars(parser.parse_args())

    # How deep do we want to go.
    levels = 3
    if args['level']:
        levels = int(args['level'])

    filename = '/data/tree.pkl'

    # Flush the cache.
    if args['no_cache']:
        if os.path.exists(filename): 
            os.remove(filename)

    # Filter the report by prefix.
    prefix_filter = None
    if args['prefix']:
        prefix_filter = args['prefix']

    # Global connection pool to the local Redis.
    pool = redis.ConnectionPool(host='redis_monitor_db', port=6379, db=0)

    root = None

    # Attempts to load from cache.
    if os.path.exists(filename):
        root = load_object(filename)

    if not root:
        keys = redis_keys('*')

        root = Node('ROOT')
        root.build_tree(keys)

        root.populate()

        # Build the cache.
        save_object(root, filename)
    
    # Global variable which will be populated for sorting purposes.
    report = defaultdict(dict)
    root.build_report(levels=levels)
    report_sorted = sorted(report.items(), key=lambda item: int(item[1]['hitrate']))

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
        print "{:<10}".format(line['get']),
        print "{:<10}".format(line['set']),
        print "{:<15}".format(line['hitrate']),
        print "{:<15}".format(line['size']),
        print "{:<20}".format(line['lifetime'])
    
    

    
        