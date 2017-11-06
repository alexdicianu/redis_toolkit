package main

import (
    "fmt"
    "log"
    "prefixtree"
    "github.com/mediocregopher/radix.v2/redis"
    "memoryreport"
    "encoding/gob"
    "os"
    "flag"
    "strings"
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
    level      := flag.Int("level", 3, "How many levels deep the report should render.")
    regenerate := flag.Bool("regenerate", false, "Regenerate the report.")
    prefix     := flag.String("prefix", "", "Filter by prefix.")
    
    flag.Parse()

    // Parameter -name is mandatory.
    if *name == "" {
        fmt.Printf("Usage: ./main -name CLIENT_NAME [-level LEVEL] [-regenerate]")
        flag.PrintDefaults()
        os.Exit(1)
    }

    file := "./data/" + *name + ".gob"

    // Flush the cache file if the -regenerate parameter is present.
    if *regenerate {
        err := os.Remove(file)
        if err != nil {
            log.Fatal(err)
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

        conn, err := redis.Dial("tcp", "localhost:6379")
        if err != nil {
            log.Fatal(err)
        }
        defer conn.Close()

        keys, err = conn.Cmd("KEYS", "*").List()
        if err != nil {
            log.Fatal(err)
        }

        root.BuildTree(keys)
        root.Populate(conn)

        fmt.Println()

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
    
    //root.DumpTree(1)
    memoryreport.BuildReport(&root, level_filter, prefix_filter)
}