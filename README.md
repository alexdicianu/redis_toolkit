# Redis Toolkit
Toolkit for actively monitoring, analyzing and reporting your Redis database.

The toolkit has 2 types of reporting:
* monitor_report - actively monitors a redis database using the `redis-cli monitor` command (https://redis.io/commands/monitor), stores the commands Redis is running locally and then generates a report.
* memory_report - dumps the contents of the Redis database locally and analyzes the memory distribution per key.

## Installation
A valid docker install is required. 

Clone this repository, go to the clonned directory and run the commands below. The output should be displayed on screen.

```
$ chmod +x ./redis-monitor
$ ./redis-monitor install
```

## Usage

### Monitor report

First you'll have to start monitoring the target Redis server using the command below and following the instructions on screen.

```
$ ./redis-monitor monitor_start
Please enter the redis-cli string for the Redis server you wish to monitor: redis-cli -h ... -p ...
```

Once you get enough data, you can run the report. You'll have to give it a name which will be used for storing the report locally in `report/data/REPORT_NAME.pkl`. This is useful in case you want to see it again at a later time or if you want to play with the various filtering options - you won't need to regenerate the report again.

```
$ ./redis-monitor monitor_report --name test_report
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
$ ./redis-monitor monitor_stop
```

#### Options
There are a few of options that can be passed to the report generator. They are described below. 

```
usage: ./redis-monitor report [-h] --name NAME [--regenerate] [--level LEVEL]
                 [--prefix PREFIX]

Generates a hit rate report from the Redis keys

optional arguments:
  -h, --help       show this help message and exit
  --name NAME      The name of this report (e.g. --name clientname). This is going to be stored locally so that future reports take less time.
  --regenerate     Regenerate the report.
  --level LEVEL    How many levels deep the report should render.
  --prefix PREFIX  Filter by prefix.
```

## Implementation details
The output shows the key hitrate (calculated using the following formula `hitrate = (gets / (gets + sets)) * 100`), the number of keys in the group, the number of GET and SET operations, the average size of each key only for SET operations and the key lifetime (calculated as the time difference between 2 consecutive SET operations - be careful, the only data we have is what we capture; not all keys will be SET twice during this interval). The result is ordered by hitrate asscending.

## Running it in production
`redis-cli MONITOR` is a debugging command that streams back every command processed by the Redis server. Running this on a production database comes with a performance cost that's hard to estimate. Use it with caution on production servers.
