package hitrate

import (
    "os"
    "strconv"
    "sort"
    "strings"
    "fmt"

    "github.com/olekukonko/tablewriter"

    "prefixtree"
)

type HitrateReport struct {
    // String representing the Redis key name or group if it includes a wildcard.
    Key string

    // How many leaves does this node have. If this is a leaf node, the value will be 1.
    LeafCount int

    // The number of get operations.
    Get int

    // The number of set operations.
    Set int

    // The hit rate defined as (gets / (gets + sets)) * 100
    Hitrate int

    // Total size in KB of the node.
    Size float64

    // The life time defined as the time between 2 consecutive sets.
    Lifetime float64

    // The total amount of network traffic (in MB) that went in and out of this node.
    NetworkTraffic float64
}

// Gathers data and builds a hit rate report.
func RunHitrateReport(root *prefixtree.Node, levels int, prefix string) {
    var report []HitrateReport
    var sizeKB, lifetime, networkTraffic string

    report = buildHitrateReport(root, report, levels)
    sort.Slice(report, func(i, j int) bool { return report[i].Hitrate < report[j].Hitrate })
    
    data := [][]string{}
    for _, item := range report {
        if prefix != "" && !strings.HasPrefix(item.Key, prefix) {
            continue
        }

        if item.Size <= 0 {
            sizeKB = "n/a"
        } else {
            sizeKB = fmt.Sprintf("%.2f", item.Size)
        }

        if item.Lifetime <= 0 {
            lifetime = "n/a"
        } else {
            lifetime = fmt.Sprintf("%.2f", item.Lifetime)
        }

        if item.NetworkTraffic <= 0 {
            networkTraffic = "n/a"
        } else {
            networkTraffic = fmt.Sprintf("%.2f", item.NetworkTraffic)
        }
        
        data = append(data, []string{
            item.Key, 
            strconv.Itoa(item.LeafCount), 
            strconv.Itoa(item.Get),
            strconv.Itoa(item.Set),
            strconv.Itoa(item.Hitrate),
            sizeKB,
            lifetime,
            networkTraffic,
        })
    }

    // Print the report to the console.
    table := tablewriter.NewWriter(os.Stdout)
    table.SetHeader([]string{"Key", "Nr. Keys", "GET", "SET", "Hit Rate(%)", "Size (KB)", "Lifetime (seconds)", "Network Traffic (MB)"})

    for _, v := range data {
        table.Append(v)
    }

    table.Render() // Send output
}


// Traverses the tree on the specified level and gathers the data.
func buildHitrateReport(node *prefixtree.Node, report []HitrateReport, levels int) []HitrateReport {
    key := node.Key

    if !node.IsLeaf() {
        key = key + ":*"
    }
    
    if levels == 0 {
        return report
    }

    if levels == 1 {
        hitrate := calculateHitrate(node.Get, node.Set)

        size := calculateAvg(node.Size, node.SizeCount)
        if size > 0 {
            // Transform the size from bytes to KB
            size = size / float64(1024)
        }

        lifetime := calculateAvg(node.Lifetime, node.LifetimeCount)

        networkTraffic := float64(-1)
        if node.NetworkTraffic > 0 {
            // Convert from bytes to MB.
            networkTraffic = float64(node.NetworkTraffic) / float64(1024) / float64(1024)
        }

        report = append(report, HitrateReport{Key: key, LeafCount: node.LeafCount, Get: node.Get, Set: node.Set, Hitrate: hitrate, Size: size, Lifetime: lifetime, NetworkTraffic: networkTraffic})
    }

    if len(node.Children) > 0 {
        for _, child := range node.Children {
            report = buildHitrateReport(child, report, levels - 1)
        }
    }

    return report
}

// Calculates the hitrate based on the (gets/(gets+sets))*100 formula.
func calculateHitrate(gets int, sets int) int {
    var hitrate float64
    
    hitrate = 0
    
    getsF := float64(gets)
    setsF := float64(sets)

    if gets + sets > 0 {
        hitrate = (getsF / (getsF + setsF)) * 100
    }

    return int(hitrate)
}

// Returns the average of a generic x integer, divided by count.
func calculateAvg(x int, count int) float64 {
    if count == 0 {
        return -1
    }
    return float64(x) / float64(count)
}

