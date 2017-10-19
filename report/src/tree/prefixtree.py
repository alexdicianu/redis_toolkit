import sys
import cPickle as pickle

class Node(object):
    
    '''
    Generic Trie (or prefix tree) implementation which can be used for multiple types of reports.
    '''
    
    def __init__(self, key):
        """Constructor only sets the key."""

        # The key name. If the key is not a leaf node, the name is it's prefix.
        self.key = key

        # How many leaves does the node have.
        self.leaf_count = 0

        # The node's children
        self.children = []

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

                self.add_child(prefix, parent_key)

            index += 1
            self.progress(index, total_keys)
            
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

    def progress(self, count, total, suffix=''):
        """Generic progressbar for showing group matching progress."""

        bar_len = 60
        filled_len = int(round(bar_len * count / float(total)))

        percents = round(100.0 * count / float(total), 1)
        bar = '#' * filled_len + '_' * (bar_len - filled_len)

        sys.stdout.write('Building report tree [%s] %s%s %s\r' % (bar, percents, '%', suffix))
        sys.stdout.flush()

    def populate(self, node=None):
        """Method used for populating report nodes."""
        raise NotImplementedException("Please Implement this method")

    def build_report(self, node=None, levels=3):
        """Method used for building each type of report."""
        raise NotImplementedException("Please Implement this method")

    def print_tree(self, node=None, level=0):
        if node == None: node = self

        #if level == 0: return

        key = node.key
        if not node.is_leaf():
            key = key + ":*"

        # Check to see if we print the key (only print the key and its parent).
        if level == 0: print '|',
        
        print '_' * level + key
        
        if node.children is not None:
            for child in node.children:
                self.print_tree(node=child, level=level + 1)


def save_object(obj, filename):
    """Saves an object to a file in a binary form to act as a caching mechanism."""
    
    # Trying to prevent hitting the recursion limit for lots of keys.
    sys.setrecursionlimit(10000)

    with open(filename, 'wb') as o:
        pickle.dump(obj, o, pickle.HIGHEST_PROTOCOL)

def load_object(filename):
    """Loads an object from file."""
    with open(filename, 'rb') as i:
        return pickle.load(i)
