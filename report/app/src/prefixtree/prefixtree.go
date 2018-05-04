package prefixtree

import (
    "fmt"
    "strconv"
    "strings"
    "log"
    "github.com/mediocregopher/radix.v2/redis"
    //"errors"
    "sort"
)

type Node struct {
    // String representing the Redis key name.
    Key string

    // How many leaves does this node have. If this is a leaf node, the value will be 1.
    LeafCount int

    // The number of bytes this key's value is occupying in memory.
    Size int

    // The number of keys that actually have a size value. Useful for an accurate average key size.
    SizeCount int

    // The number of GET operations.
    Get int

    // The number of SET operations
    Set int

    // The time between 2 consecutive sets.
    Lifetime int

    // The number of keys that actually have a lifetime value. Useful for an accurate average life time.
    LifetimeCount int

    // The total amount of network traffic (in Bytes) that went in and out of this node.
    NetworkTraffic int

    // Pointer to Children nodes.
    Children []*Node
}

func BuildSubtree(subTree chan Node, keys []string) {
    var parent_key string

    node := Node{Key: "ROOT"}
    for _, key := range keys {
        prefixes := buildPrefixes(key)
        for i, prefix := range prefixes {
            if i == 0 {
                parent_key = "ROOT"
            } else {
                parent_key = prefixes[i-1]
            }
            node.addChild(prefix, parent_key)
        }
    }
    subTree <- node
}

func getNextBranchIndex(keys []string, startFromIndex int) int {
    
    candidateIndex, keyCount, level := startFromIndex, len(keys), 0

    //fmt.Println("Level: ", level)


    for {
        //fmt.Println("candidateIndex: ", candidateIndex)
        //fmt.Println("keyCount: ", keyCount)

        if candidateIndex >= keyCount - 1 {
            // We reached the end without finding any difference. Go to the next level and reset the candidate index.
            candidateIndex = startFromIndex
            level++
        }

        currentKeyParts := strings.Split(keys[candidateIndex], ":")
        nextKeyParts    := strings.Split(keys[candidateIndex + 1], ":")

        //fmt.Println("candidate key: ", currentKeyParts[level])
        //fmt.Println("next key: ", nextKeyParts[level])

        if currentKeyParts[level] != nextKeyParts[level] {
            // Return the index for the next different key for better splitting.
            return candidateIndex + 1
        }

        candidateIndex += 1
    }
}

// Builds the trie (or prefix tree) recursively after it decomposes the key by prefix.
func (node *Node) BuildTreeFaster(keys []string) {
    //var splitIndex int

    sort.Sort(sort.StringSlice(keys))
    
    //for i, k := range keys {
    //   fmt.Println(i, k)
    //}

    totalKeys := len(keys)
    
    /*for i:=0; i<5; i++ {
        splitIndex, e := getNextBranchIndex(keys, totalKeys / 2, i)
        if e != nil {
            fmt.Println("Failed splitting the keys.", e)
        } else {
            fmt.Println("worked, found split index:", splitIndex)
            break
        }

    }*/

    splitIndex := getNextBranchIndex(keys, totalKeys / 2)

    //fmt.Printf("\nFound half index: %d\nkey: %s\n\n", splitIndex, keys[splitIndex])

    t1 := make(chan Node)
    t2 := make(chan Node)

    go BuildSubtree(t1, keys[0:splitIndex])
    go BuildSubtree(t2, keys[splitIndex+1:totalKeys])

    for i := 0; i < 2; i++ {
        // Rebuild the tree.
        select {
            case n1Ready := <-t1:
                node.Children = append(node.Children, n1Ready.Children...)
                //node.MergeTree(&n1Ready)
            case n2Ready := <-t2:
                node.Children = append(node.Children, n2Ready.Children...)
                //node.MergeTree(&n2Ready)
        }
    }
}

// Merges the tree given as a parameter to the main tree.
/*func (node *Node) MergeTree(subtree *Node) bool {
    if len(subtree.Children) <= 0 {
        return false
    }

    var targetChildren []string 
    for _, n := range node.Children {
        targetChildren = append(targetChildren, n.Key)
        fmt.Println("Target children: ", targetChildren)
    }

    for _, child := range subtree.Children {
        fmt.Println("Child.Key: ", child.Key)

        if !contains(targetChildren, child.Key) {
            fmt.Println("Adding key to node: ", child.Key, node.Key)
            //node.Children = append(node.Children, &Node{Key: child.Key})
            node.addChild(child.Key, node.Key)
        } else {
            fmt.Println("Going one level deeper")
            for _, targetChild := range node.Children {
                targetChild.MergeTree(child)
            }
        }
    }
    return true
}*/

/*func BuildHalfTree(keys []string, node *Node, wait sync.WaitGroup) {
    var parent_key string

    for _, key := range keys {
        prefixes := buildPrefixes(key)
        for i, prefix := range prefixes {
            if i == 0 {
                parent_key = "ROOT"
            } else {
                parent_key = prefixes[i-1]
            }
            //fmt.Println("Locking ", key)
            node.Lock()
            node.addChild(prefix, parent_key)
            node.Unlock()
            //fmt.Println("Unlocking ", key)
        }
    }
    wait.Done()
}*/

/*func BuildTreeFastish(keys []string, node *Node) {
    var parent_key string
    var halfIndex int
    var wait sync.WaitGroup
    wait.Add(2)

    totalKeys := len(keys)
    
    sort.Sort(sort.StringSlice(keys))
    
    //for _, k := range keys {
    //    fmt.Println(k)
    //}

    candidateHalfIndex := totalKeys / 2
    for {
        currentKeyParts := strings.Split(keys[candidateHalfIndex], ":")
        nextKeyParts    := strings.Split(keys[candidateHalfIndex + 1], ":")

        currentKeyPrefix := strings.Join(currentKeyParts[:len(currentKeyParts) - 1], "")
        nextKeyPrefix    := strings.Join(nextKeyParts[:len(nextKeyParts) - 1], "")

        if currentKeyPrefix != nextKeyPrefix {
            halfIndex = candidateHalfIndex
            break
        }

        candidateHalfIndex += 1
    }

    //fmt.Printf("\nFound half index: %d, key: %s\n", halfIndex, keys[halfIndex])

    //go BuildHalfTree(keys[0:halfIndex], node, wait)
    //go BuildHalfTree(keys[halfIndex+1:totalKeys], node, wait)
    go func(keys []string, node *Node){
        for _, key := range keys {
            prefixes := buildPrefixes(key)
            for i, prefix := range prefixes {
                if i == 0 {
                    parent_key = "ROOT"
                } else {
                    parent_key = prefixes[i-1]
                }
                //fmt.Println("Locking ", key)
                node.Lock()
                addChild(prefix, parent_key, node)
                node.Unlock()
                //fmt.Println("Unlocking ", key)
            }
        }
        wait.Done()
    }(keys[0:halfIndex], node)
    
    
}*/

// Builds the trie (or prefix tree) recursively after it decomposes the key by prefix.
func (node *Node) BuildTree(keys []string) {
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
        ProgressBar(float64(i + 1), float64(totalKeys))
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


// Executes one last pass through the finished tree. Populating the tree for running a memory distribution report.
func (node *Node) PopulateForMemoryReport(conn *redis.Client) map[string]int {
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
            r := child.PopulateForMemoryReport(conn)

            node.LeafCount += r["LeafCount"]
            node.Size      += r["Size"]
        }
    }
    
    return map[string]int{
        "LeafCount": node.LeafCount,
        "Size": node.Size,
    }
}

// Executes one last pass through the finished tree. Populating the tree for running a hit rate report.
func (node *Node) PopulateForHitrateReport(conn *redis.Client) map[string]int {
    for _, child := range node.Children {
        if child.IsLeaf() {
            // Query Redis for the key information (gets, set, hitrate, etc).
            data, err := conn.Cmd("HGETALL", child.Key).Map()
            if err != nil {
                log.Print(err)
            }

            child.LeafCount = 1

            child.Get, _ = strconv.Atoi(data["get"])
            child.Set, _ = strconv.Atoi(data["set"])

            sizeBytes, _ := strconv.ParseFloat(data["size"], 64)
            child.Size = int(sizeBytes)

            lifetime, _ := strconv.ParseFloat(data["lifetime"], 64)
            child.Lifetime = int(lifetime)

            // For average calculation.
            if child.Size > 0 {
                child.SizeCount = 1
                node.SizeCount += 1

                child.NetworkTraffic = (child.Get + child.Set) * child.Size
            }

            if child.Lifetime > 0 {
                child.LifetimeCount = 1
                node.LifetimeCount += 1
            }
            
            // Increment parent leaf count, get, set, size.
            node.LeafCount += 1

            // Increment the number of gets and sets.
            node.Get       += child.Get
            node.Set       += child.Set

            // Increment the total size and size_count.
            node.Size      += child.Size

            // Increment parent node lifetime.
            node.Lifetime += child.Lifetime

            node.NetworkTraffic += child.NetworkTraffic

        } else {
            r := child.PopulateForHitrateReport(conn)

            node.LeafCount += r["LeafCount"]
            node.Get       += r["Get"]
            node.Set       += r["Set"]

            node.Size      += r["Size"]
            node.SizeCount += r["SizeCount"]

            node.Lifetime       += r["Lifetime"]
            node.LifetimeCount  += r["LifetimeCount"]

            node.NetworkTraffic += r["NetworkTraffic"]            
        }
    }
    
    return map[string]int{
        "LeafCount": node.LeafCount,
        "Get": node.Get,
        "Set": node.Set,
        "Size": node.Size,
        "SizeCount": node.SizeCount,
        "Lifetime": node.Lifetime,
        "LifetimeCount": node.LifetimeCount,
        "NetworkTraffic": node.NetworkTraffic,
    }
}

// Returns the key size of a specific key. Depending on the key's type, different commands need to be executed.
func redisKeySize(conn *redis.Client, key string) int {
    var object_size int
    var data []string
    
    keyType, err := conn.Cmd("TYPE", key).Str()
    
    if err != nil {
        log.Print("CMD: TYPE, Key: ", key)
        log.Print(err)
    }

    switch keyType {
        case "hash":
            data, err = conn.Cmd("HGETALL", key).List()
            if err != nil {
                log.Print("CMD: HGETALL, Key: ", key)
                log.Print(err)
            }
            for _, k := range data {
                object_size += len(k)
            }
            
        case "set":
            data, err = conn.Cmd("SMEMBERS", key).List()
            if err != nil {
                log.Print("CMD: SMEMBERS, Key: ", key)
                log.Print(err)
            }

            for _, k := range data {
                object_size += len(k)
            }
            
        case "string":
            data, err := conn.Cmd("GET", key).Str()
            if err != nil {
                log.Print("CMD: GET, Key: ", key)
                log.Print(err)
            }

            object_size = len(data)
    }

    return object_size
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

// Shows visual progress in the form of a loading bar.
func ProgressBar(count float64, total float64, suffix ...string) {
    barLen := 60
    filledLen := float64(barLen) * count / total

    percents := int((100 * count) / total)
    bar := strings.Repeat("#", int(filledLen)) + strings.Repeat("_", (int(barLen) - int(filledLen)))

    if suffix == nil {
        fmt.Printf("Building report tree [%s] %d%%\r", bar, percents)    
    } else {
        fmt.Printf("Building report tree [%s] %d%% %s\r", bar, percents, suffix)
    }
    
}