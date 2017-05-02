# Redis Monitor
Actively monitors a redis database using the `redis-cli monitor` command (https://redis.io/commands/monitor).

## Installation & Usage
A valid docker install is required. 

Clone this repository, go to the clonned directory and run the commands below. The output should be displayed on screen.

```
$ chmod +x ./redis-monitor
$ ./redis-monitor install
```

## Generate the report
There are 2 types of reports that can be generated: a prefix-only and a full report for all your keys. The default is the full report.

### Running the prefix only report

First you'll have to start monitoring the target Redis server using the command below and following the instructions.

```
$ ./redis-monitor start
Please enter the redis-cli string for the Redis server you wish to monitor: redis-cli -h ... -p ...
```

Once you get enough data, you can run the report.

```
$ ./redis-monitor report --prefix_only
Key                                                                                        Count      GET        SET        Hit Rate (%)    Size (KB)
------------------------------------------------------------------------------------------------------------------------------------------------------
wp_userlogins:600*                                                                         8          5          6          45              0.07
comment:get_comment_child_ids:21099*                                                       280        284        255        52              0.09
comment:2109928*                                                                           14         14         10         58              0.47
post_meta:111*                                                                             20         31         12         72              0.25
product_*                                                                                  96         100        21         82              0.01
posts:1189*                                                                                10         15         0          100             0.0 
```
### Full report

```
$ ./redis-monitor report
Key                                                                                        Count      GET        SET        Hit Rate (%)    Size (KB)           
------------------------------------------------------------------------------------------------------------------------------------------------------
comment:get_comments:df74a34315b3a68d6e6298fc14e62eea:0.317725001493527301                 1          1          1          50              0.13                
comment:get_comments:df626590f0126c6a7b88dfc205d6f7bf:0.317725001493527301                 1          1          1          50              0.09                
------------------------------------------------------------------------------------------------------------------------------------------------------
comment:get_comments:df*                                                                   2          2          2          50              0.11 

Key                                                                                        Count      GET        SET        Hit Rate (%)    Size (KB)           
------------------------------------------------------------------------------------------------------------------------------------------------------
keyword_relationships:238739                                                               1          1          0          100             0.0                 
keyword_relationships:238735                                                               1          2          0          100             0.0                 
keyword_relationships:238739                                                               1          1          0          100             0.0                 
keyword_relationships:238730                                                               1          2          0          100             0.0                 
keyword_relationships:238739                                                               1          1          0          100             0.0                 
keyword_relationships:238732                                                               1          1          0          100             0.0                 
------------------------------------------------------------------------------------------------------------------------------------------------------
keyword_relationships:23873*                                                               6          8          0          100             0.0   
```

When you're done, you can stop the the monitoring process via the command below.

```
$ ./redis-monitor stop
```

## Options
There are a few of options that can be passed to the report generator. They are described below. The SIMILARITY_DEGREE parameter is used for calculating the similarity degree between these groups using the Levenshtein distance algorithm. You can set any value between 0 and 1:

* values close to 0 will try to create many groups with very little differences between them 
* values close to 1 will try to create less groups with many differences between strings but a smaller common prefix

If you want to redirect the output to a file (`via > /path/to/report.log`) you should add the `--hide_progress_bar` to not polute the report with the progress bar information.

```
usage: ./redis-monitor report [-h] [--prefix_only] [-s SIMILARITY_DEGREE]
                 [--hide_progress_bar]

Generates a hit rate report from the Redis keys

optional arguments:
  -h, --help            show this help message and exit
  --prefix_only         Only show the groups of keys.
  -s SIMILARITY_DEGREE, --similarity_degree SIMILARITY_DEGREE
                        Manually calibrate the similarity degree. Default is 0.5
                            - values close to 0 will try to create many groups with very little differences between them.
                            - values close to 1 will try to create less groups with many differences between strings but a smaller common prefix.
  --hide_progress_bar   Hides the progress bar in case you want to redirect the output to a file.
```

## Implementation details
The output shows the key hitrate (calculated using the following formula `hitrate = (gets / (gets + sets)) * 100`), the number of keys in the group, the number of GET and SET operations and the average size of each key only for SET operations. The result is ordered by hitrate asscending.

## Running it in production
`redis-cli MONITOR` is a debugging command that streams back every command processed by the Redis server. Running this on a production database comes with a performance cost that's hard to estimate. Use it with caution on production servers.
