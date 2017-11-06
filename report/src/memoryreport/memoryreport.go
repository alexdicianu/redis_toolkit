package memoryreport

import (
    "prefixtree"
    "os"
    "github.com/olekukonko/tablewriter"
    "strconv"
    "sort"
    "strings"
    "fmt"
)

// Report data structure which includes computed fields from the raw data tree.
type MemoryReport struct {
    // String representing the Redis key name or group if it includes a wildcard.
    Key string

    // How many leaves does this node have. If this is a leaf node, the value will be 1.
    LeafCount int

    // The number of bytes this key's value is occupying in memory.
    Size int
}

// Gathers data and builds a memory distribution report.
func BuildReport(root *prefixtree.Node, levels int, prefix string) {
    var report []MemoryReport

    report = gatherData(root, report, levels)
    sort.Slice(report, func(i, j int) bool { return report[i].LeafCount > report[j].LeafCount })
    
    data := [][]string{}
    for _, item := range report {
        if prefix != "" && !strings.HasPrefix(item.Key, prefix) {
            continue
        }
        size_MB      := float64(item.Size) / float64(1024) / float64(1024)
        size_Percent := (float64(item.Size) / float64(root.Size)) * float64(100)

        data = append(data, []string{item.Key, strconv.Itoa(item.LeafCount), fmt.Sprintf("%.2f", size_MB), fmt.Sprintf("%.2f", size_Percent)})
    }

    // Print the report to the console.
    table := tablewriter.NewWriter(os.Stdout)
    table.SetHeader([]string{"Key", "Nr. Keys", "Size (MB)", "Size (%)"})

    for _, v := range data {
        table.Append(v)
    }
    table.Render() // Send output
}

// Traverses the tree on the specified level and gathers the data.
func gatherData(node *prefixtree.Node, report []MemoryReport, levels int) []MemoryReport {
    key := node.Key

    if !node.IsLeaf() {
        key = key + ":*"
    }
    
    if levels == 0 {
        return report
    }

    if levels == 1 {
        report = append(report, MemoryReport{Key: key, LeafCount: node.LeafCount, Size: node.Size})
    }

    if len(node.Children) > 0 {
        for _, child := range node.Children {
            report = gatherData(child, report, levels - 1)
        }
    }

    return report
}
