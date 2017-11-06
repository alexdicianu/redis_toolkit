package prefixtree

import (
    "fmt"
    "strconv"
    "strings"
    "github.com/mediocregopher/radix.v2/redis"
    "log"
)

type Node struct {
    // String representing the Redis key name.
    Key string

    // How many leaves does this node have. If this is a leaf node, the value will be 1.
    LeafCount int

    // The number of bytes this key's value is occupying in memory.
    Size int

    // Pointer to Children nodes.
    Children []*Node
}

// Builds the trie (or prefix tree) recursively after it decomposes the key by prefix.
func (node *Node) BuildTree(keys []string){
    var parent_key string

    totalKeys := len(keys)

    for i, key := range keys {
        prefixes := buildPrefixes(key)
        for i, prefix := range prefixes {
            if i == 0 {
                parent_key = "ROOT"
            } else {
                parent_key = prefixes[i-1]
            }

            node.addChild(prefix, parent_key)
        }
        showProgress(float64(i + 1), float64(totalKeys))
    }
}

// Adds child nodes to the trie.
func (node *Node) addChild(key string, parent_key string) {
    child_keys := node.getChildrenKeys()

    // If I reached the parent.
    if parent_key == node.Key {
        if !contains(child_keys, key) {
            node.Children = append(node.Children, &Node{Key: key})
        }
    } else {
        if len(node.Children) > 0 {
            for _, child := range node.Children {
                if strings.HasPrefix(parent_key, child.Key) {
                    child.addChild(key, parent_key)
                }
            }
        }
    }
}

// Returns a list of children keys.
func (node *Node) getChildrenKeys() []string {
    var keys []string

    if len(node.Children) > 0 {
        for _, child := range node.Children {
            keys = append(keys, child.Key)
        }
    }
    
    return keys
}

// Executes one last pass through the finished tree for populating it with additional information.
func (node *Node) Populate(conn *redis.Client) map[string]int {
    for _, child := range node.Children {
        if child.IsLeaf() {
            // Query Redis for the key information (gets, set, hitrate, etc).
            size := redisKeySize(conn, child.Key)

            child.Size      = size
            child.LeafCount = 1

            // Increment leaf count, size.
            node.LeafCount  += 1
            node.Size       += child.Size
        } else {
            //node.LeafCount += child.Populate(conn)

            r := child.Populate(conn)

            node.LeafCount += r["LeafCount"]
            node.Size      += r["Size"]
        }
    }
    
    return map[string]int{
        "LeafCount": node.LeafCount,
        "Size": node.Size,
    }

    //return node.LeafCount
}

// Checks if node is leaf.
func (node *Node) IsLeaf() bool {
    if (len(node.Children) == 0) {
        return true
    }
    return false
}

func (node *Node) DumpTree(level int) {
    var info string

    if node.IsLeaf() {
        info = " - (leaf)"
    } else {
        info = " - (leaves: " + strconv.Itoa(node.LeafCount) + ")"
    }

    fmt.Println(node.Key, info)

    if (len(node.Children) > 0) {
        for _, child := range node.Children {
            fmt.Printf(strings.Repeat("----", level))
            child.DumpTree(level+1)
        }
    }
}

// Builds a list of prefixes, each of them one level deeper than its predecesor. 
// Example:
//           - pantheon-redis
//           - pantheon-redis:cache_page
//           - pantheon-redis:cache_page:www.example.com
func buildPrefixes(key string) []string {
    var prefixes []string

    key_parts := strings.Split(key, ":")

    for i, key := range key_parts {
        if i == 0 {
            prefixes = append(prefixes, key)
        } else {
            prefixes = append(prefixes, prefixes[i-1] + ":" + key)            
        }
    }

    return prefixes
}

func contains(slice []string, item string) bool {
    set := make(map[string]struct{}, len(slice))
    for _, s := range slice {
        set[s] = struct{}{}
    }

    _, ok := set[item] 
    return ok
}

func showProgress(count float64, total float64) {
    barLen := 60
    filledLen := float64(barLen) * count / total

    percents := int((100 * count) / total)
    bar := strings.Repeat("#", int(filledLen)) + strings.Repeat("_", (int(barLen) - int(filledLen)))

    fmt.Printf("Building report tree [%s] %d%%\r", bar, percents)
}

// Returns the key size of a specific key. Depending on the key's type, different commands need to be executed.
func redisKeySize(conn *redis.Client, key string) int {
    var object_size int
    var data []string
    
    keyType, err := conn.Cmd("TYPE", key).Str()
    
    if err != nil {
        log.Print(err)
    }

    switch keyType {
        case "hash":
            data, err = conn.Cmd("HGETALL", key).List()
            if err != nil {
                log.Print(err)
            }
            for _, k := range data {
                object_size += len(k)
            }
            
        case "set":
            data, err = conn.Cmd("SMEMBERS", key).List()
            if err != nil {
                log.Print(err)
            }

            for _, k := range data {
                object_size += len(k)
            }
            
        case "string":
            data, err := conn.Cmd("GET", key).Str()
            if err != nil {
                log.Print(err)
            }

            object_size = len(data)
    }

    

    return object_size
}