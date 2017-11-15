package main

import (
    "fmt"
    "log"
    "encoding/gob"
    "os"
    "flag"
    "strings"

    "github.com/mediocregopher/radix.v2/redis"
    
    "prefixtree"
    "report/hitrate"
    "report/memory"
)

// Encode via Gob to file. simple way to dump an already built object to a local file.
func Save(path string, object interface{}) error {
    file, err := os.Create(path)
    if err == nil {
        encoder := gob.NewEncoder(file)
        encoder.Encode(object)
    }
    file.Close()
    return err
 }

// Decode Gob file.
func Load(path string, object interface{}) error {
    file, err := os.Open(path)
    if err == nil {
        decoder := gob.NewDecoder(file)
        err = decoder.Decode(object)
    }
    file.Close()
    return err
}

func main() {
    var prefix_filter string
    var level_filter int

    name       := flag.String("name", "", "The name of this report (e.g. -name clientname). This is going to be stored locally so that future reports take less time. (Required)")
    reportType := flag.String("type", "", "The type of report you wish to generate. Possible values: memory, hitrate")
    level      := flag.Int("level", 3, "How many levels deep the report should render.")
    regenerate := flag.Bool("regenerate", false, "Regenerate the report.")
    prefix     := flag.String("prefix", "", "Filter by prefix.")
    
    flag.Parse()

    // Parameter -name is mandatory.
    if *name == "" || (*reportType != "memory" && *reportType != "hitrate") {
        fmt.Printf("Usage: ./main -name CLIENT_NAME -report REPORT_TYPE [-level LEVEL] [-regenerate] [-prefix PREFIX:*]\n\n")
        flag.PrintDefaults()
        os.Exit(1)
    }

    file := "./data/" + *name + "." + *reportType + ".gob"

    // Flush the cache file if the -regenerate parameter is present.
    if *regenerate {
        err := os.Remove(file)
        if err != nil {
            log.Print("No local cache found.")
            //log.Print(err)
        }
    }

    level_filter = *level

    // Prefix filter.
    if *prefix != "" {
        prefix_filter = *prefix
        if strings.HasSuffix(*prefix, "*") {
            prefix_filter = prefix_filter[:len(prefix_filter) - 1]
        }
        level_filter = len(strings.Split(prefix_filter, ":")) + 1
    }

    root := prefixtree.Node{Key: "ROOT"}

    if _, err := os.Stat(file); os.IsNotExist(err) {
        // File does not exist (cache miss). Create cache.
        
        // Connecting to the local Redis container and fetching all the keys for building the report.
        var keys []string

        conn, err := redis.Dial("tcp", "redis_toolkit_db:6379")
        if err != nil {
            log.Fatal(err)
        }
        defer conn.Close()

        keys, err = conn.Cmd("KEYS", "*").List()
        if err != nil {
            log.Fatal(err)
        }

        // Build the bare prefix tree.
        root.BuildTree(keys)

        // Populate the tree based on the type of report we wish to run.
        prefixtree.ProgressBar(100, 100, "Populating the report. Please wait ...")
        if *reportType == "memory" {
            root.PopulateForMemoryReport(conn)
        } else {
            root.PopulateForHitrateReport(conn)
        }

        // Save the report to the local cache.
        err = Save(file, &root)
        if err != nil {
            log.Print(err)
        }
    } else {
        // File exists (cache hit). Load from cache
        err := Load(file, &root)
        if err != nil {
            log.Print(err)
        }
    }
    
    if *reportType == "memory" {
        memory.RunMemoryReport(&root, level_filter, prefix_filter)    
    } else {
        hitrate.RunHitrateReport(&root, level_filter, prefix_filter)
    }
    
}


