import redis
import os

from argparse import ArgumentParser, RawTextHelpFormatter
from collections import defaultdict, Counter
from prefixtree import Node, save_object, load_object


class HitrateReportNode(Node):
    """Extending the Node class with some custom attributes specific to the hit rate only."""

    def __init__(self, key):

        # The number of GET operations.
        Node.get = 0

        # The number of SET operations
        Node.set = 0

        # The key size in Bytes. Non-leaf nodes have a total size calculated as the sum of all sizes.
        Node.size = 0

        # The number of keys that actually have a size value. Useful for an accurate average key size.
        Node.size_count = 0

        # The life time defined as the time between 2 consecutive sets.
        Node.lifetime = 0

        # The number of keys that actually have a lifetime value. Useful for an accurate average life time.
        Node.lifetime_count = 0

        # The total amount of network traffic (in Bytes) that went in and out of this node.
        Node.network_traffic = 0

        super(HitrateReportNode, self).__init__(key)

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
                    node.size_count += 1
                    
                    child.network_traffic = (float(child.get) + float(child.set)) * float(child.size)
                    
                if child.lifetime > 0:
                    child.lifetime_count = 1
                    node.lifetime_count += 1

                # Increment leaf count.
                node.leaf_count += 1

                # Increment the number of gets and sets.
                node.get += child.get
                node.set += child.set

                # Increment the total size and size_count.
                node.size += child.size
                
                # Increment parent node lifetime.
                node.lifetime += child.lifetime

                node.network_traffic += child.network_traffic

            else:
                obj = self.populate(child)
                
                node.leaf_count += obj['leaf_count']

                node.get += obj['get']
                node.set += obj['set']

                node.size       += float(obj['size'])
                node.size_count += obj['size_count']

                node.lifetime       += float(obj['lifetime'])
                node.lifetime_count += obj['lifetime_count']

                node.network_traffic += float(obj['network_traffic'])

        return {
            'leaf_count': node.leaf_count,
            'get': node.get,
            'set': node.set,
            'size': node.size,
            'size_count': node.size_count,
            'lifetime': node.lifetime,
            'lifetime_count': node.lifetime_count,
            'network_traffic': node.network_traffic
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
                'hitrate': self.get_hitrate(node),
                'size': self.get_size(node),
                'lifetime': self.get_lifetime(node),
                'network_traffic': self.get_network_traffic(node)
            }
        
        if node.children is not None:
            for child in node.children:
                self.build_report(node=child, levels=levels - 1)

    def get_hitrate(self, node):
        """Calculate the hitrate for the current node."""
        if node == None: node = self

        try:
            hitrate = 0
            gets = float(node.get)
            sets = float(node.set)
        except AttributeError:
            return 0

        if gets + sets > 0:
            hitrate = (gets / (gets + sets)) * 100

        return str(int(hitrate))

    def get_size(self, node):
        """Calculate the average size and convert it from Bytes to KB and round the result."""
        if node == None: node = self

        try:
            if node.size_count == 0: return 'n/a'
        except AttributeError:
            return 'n/a'

        avg_size = float(node.size) / float(node.size_count)
        size = round(float(avg_size) / float(1024), 2)

        if size <= 0: return 'n/a'
        return size

    def get_lifetime(self, node):
        """Proper format for the lifetime"""
        if node == None: node = self

        try:
            if node.lifetime_count == 0: return 'n/a'
        except AttributeError:
            return 'n/a'

        avg_lifetime = float(node.lifetime) / float(node.lifetime_count)

        lifetime = round(float(avg_lifetime), 2)
        if lifetime <= 0: return 'n/a'
        return lifetime

    def get_network_traffic(self, node):
        """Proper format for the network traffic"""
        if node == None: node = self

        try:
            network_traffic = round(float(node.network_traffic) / 1024 / 1024, 2)
        except AttributeError:
            return 'n/a'

        return network_traffic

def print_report_header():
    print
    print '{:<90}'.format('Key'),
    print '{:<10}'.format('Nr. keys'),
    print '{:<10}'.format('GET'),
    print '{:<10}'.format('SET'),
    print '{:<15}'.format('Hit Rate (%)'),
    print '{:<15}'.format('Avg Size (KB)'),
    print '{:<20}'.format('Lifetime (seconds)'),
    print '{:<20}'.format('Network traffic (total MB)')
    print '{:<170}'.format('-' * 190)


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
    parser.add_argument('--name', help='The name of this report (e.g. --name clientname). This is going to be stored locally so that future reports take less time.', required=True)
    parser.add_argument('--regenerate', action='store_true', help='Regenerate the report.', required=False)
    parser.add_argument('--level', help='How many levels deep the report should render.', required=False)
    parser.add_argument('--prefix', help='Filter by prefix.', required=False)
    
    args = vars(parser.parse_args())

    # The report object will be stored locally.
    if args['name']:
        filename = '/data/hitrate_' + args['name'] + '.pkl'

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
    pool = redis.ConnectionPool(host='redis_toolkit_db', port=6379, db=0)

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

        root = HitrateReportNode('ROOT')
        root.build_tree(keys)

        # Show more feedback. Populating takes a few extra seconds.
        root.progress(100, 100, suffix='Almost there, populating report ...')
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
        print "{:<20}".format(line['lifetime']),
        print "{:<20}".format(line['network_traffic'])
 
    
        