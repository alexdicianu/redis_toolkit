# Redis Monitor
Actively monitors a redis database using the `redis-cli monitor` command (https://redis.io/commands/monitor), stores the commands Redis is running locally and then generates a report.

## Installation & Usage
A valid docker install is required. 

Clone this repository, go to the clonned directory and run the commands below. The output should be displayed on screen.

```
$ chmod +x ./redis-monitor
$ ./redis-monitor install
```

## Usage

First you'll have to start monitoring the target Redis server using the command below and following the instructions.

```
$ ./redis-monitor start
Please enter the redis-cli string for the Redis server you wish to monitor: redis-cli -h ... -p ...
```

Once you get enough data, you can run the report.

```
$ ./redis-monitor report 
Key                                                                                        Nr. keys   GET        SET        Hit Rate (%)    Avg Size (KB)   Lifetime (seconds)
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
pantheon-redis:cache_token:*                                                               2          5          4          55              10.02           3.74
pantheon-redis:lock:*                                                                      1          3          2          60              0.09            3.67
pantheon-redis:cache_path:*                                                                7          33         4          89              0.13            n/a
pantheon-redis:cache_field:*                                                               10         112        5          95              3.95            63.74
pantheon-redis:cache_bootstrap:*                                                           7          180        1          99              10.3            n/a
pantheon-redis:cache_menu:*                                                                49         221        0          100             n/a             n/a
pantheon-redis:cache:*                                                                     21         226        0          100             n/a             n/a
pantheon-redis:cache_apachesolr:*                                                          1          1          0          100             n/a             n/a
pantheon-redis:cache_views:*                                                               14         28         0          100             n/a             n/a
```

When you're done, you can stop the the monitoring process via the command below.

```
$ ./redis-monitor stop
```

## Options
There are a few of options that can be passed to the report generator. They are described below. 

```
usage: ./redis-monitor report [-h] [--no_cache] [-l LEVEL] [-p PREFIX]

Generates a hit rate report from the Redis keys

optional arguments:
  -h, --help            show this help message and exit
  --no_cache            Flush the previous report from cache.
  -l LEVEL, --level LEVEL
                        How many levels deep the report should render.
  -p PREFIX, --prefix PREFIX
                        Filter by prefix.
```

## Implementation details
The output shows the key hitrate (calculated using the following formula `hitrate = (gets / (gets + sets)) * 100`), the number of keys in the group, the number of GET and SET operations, the average size of each key only for SET operations and the key lifetime (calculated as the time difference between 2 consecutive SET operations - be careful, the only data we have is what we capture; not all keys will be SET twice during this interval). The result is ordered by hitrate asscending.

## Running it in production
`redis-cli MONITOR` is a debugging command that streams back every command processed by the Redis server. Running this on a production database comes with a performance cost that's hard to estimate. Use it with caution on production servers.
