# Redis Toolkit
Toolkit for actively monitoring, analyzing and reporting your Redis database.

The toolkit has 2 types of reporting:
* *hit rate* - actively monitors a redis database using the `redis-cli monitor` command (https://redis.io/commands/monitor), stores the commands Redis is running locally and then generates a report.
* *memory* - dumps the contents of the Redis database locally and analyzes the memory distribution per key.

## Installation
A valid docker install is required. 

Clone this repository, go to the clonned directory and run the commands below. The output should be displayed on screen.

```
$ chmod +x ./redis-toolkit
$ ./redis-toolkit install
```

## Update
The tool is under constant development. To update it to the latest version, just run the commands below.

```
$ git pull
$ ./redis-toolkit update
```

## Usage

### Hit Rate report

First you'll have to start monitoring the target Redis server using the command below and following the instructions on screen.

```
$ ./redis-toolkit monitor
Please enter the redis-cli string for the Redis server you wish to monitor: redis-cli -h ... -p ...
```

Once you get enough data, you can run the report. You'll have to give it a name which will be used for storing the report locally in `report/app/data/NAME.hitrate.gob`. This is useful in case you want to see it again at a later time or if you want to play with the various filtering options - you won't need to regenerate the report again.

```
$ ./redis-toolkit report -name NAME -type hitrate -level 2
+----------------------------------------+----------+--------+-------+-------------+-----------+--------------------+----------------------+
|                  KEY                   | NR  KEYS |  GET   |  SET  | HIT RATE(%) | SIZE (KB) | LIFETIME (SECONDS) | NETWORK TRAFFIC (MB) |
+----------------------------------------+----------+--------+-------+-------------+-----------+--------------------+----------------------+
| wp_userslugs:*                         |       89 |     18 |   536 |           3 |      0.12 |               2.50 |                 0.06 |
| wp_useremail:*                         |       88 |     39 |   534 |           6 |      0.12 |               3.67 |                 0.07 |
| post_format_relationships:*            |       12 |     40 |   124 |          24 |      0.11 |              42.58 |                 0.02 |
| resource_tag_relationships:*           |       12 |     13 |    28 |          31 |      0.12 |              77.67 |                 0.00 |
| timeinfo:*                             |        3 |      3 |     3 |          50 |      0.07 | n/a                |                 0.00 |
| wpseo:*                                |       12 |     24 |    22 |          52 |      0.07 |             273.25 |                 0.00 |
| wp_userlogins:*                        |       75 |    673 |   534 |          55 |      0.12 |              68.32 |                 0.13 |
```

When you're done, you can stop the the monitoring process via the command below.

```
$ ./redis-toolkit stop
```

### Memory report

The first is to dump the Redis database locally via the command below.

```
$ ./redis-toolkit dump
Please enter the redis-cli string for the Redis server you wish to monitor: redis-cli -h ... -p ...
```

Once the dump is done. you can run the report. You'll have to give it a name which will be used for storing the report locally in `report/app/data/NAME.memoy.gob`. This is useful in case you want to see it again at a later time or if you want to play with the various filtering options - you won't need to regenerate the report again.

```
$ ./redis-toolkit report -type memory -name NAME
+----------------------------------------+----------+-----------+----------+
|                     KEY                | NR  KEYS | SIZE (MB) | SIZE (%) |
+----------------------------------------+----------+-----------+----------+
| posts:*                                |      500 |      0.56 |     2.79 |
| post_meta:*                            |      440 |     18.48 |    92.78 |
| terms:*                                |      192 |      0.12 |     0.63 |
| options:*                              |      109 |      0.52 |     2.59 |
| term_meta:*                            |       67 |      0.02 |     0.08 |
| product_cat_relationships:*            |       45 |      0.00 |     0.01 |
```

## Options
There are a few of options that can be passed to the both report generators. They are described below. 

```
usage: ./redis-toolkit report [-h] -name NAME -type hitrate|memory [-regenerate] [-level LEVEL] [-prefix PREFIX]

Generates a hitrate or memory report from the Redis keys.

  -level int
    	How many levels deep the report should render. (default 3)
  -name string
    	The name of this report (e.g. -name clientname). This is going to be stored locally so that future reports take less time. (Required)
  -prefix string
    	Filter by prefix.
  -regenerate
    	Regenerate the report.
  -type string
    	The type of report you wish to generate. Possible values: memory, hitrate
```

## Implementation details

### Hit Rate
The output shows the key hitrate (calculated using the following formula `hitrate = (gets / (gets + sets)) * 100`), the number of keys in the group, the number of GET and SET operations, the average size of each key only for SET operations and the key lifetime (calculated as the time passed since the last SET operation - be careful, the only data we have is what we capture; not all keys will be SET during this interval). The result is ordered by hitrate asscending.

### Memory
The memory analysis report shows how big the keys are and how much that represents compared to the total amount of space occupied by the entire data set. Please be aware that Redis has has optimization algorithms that store data in a compressed format. Thus, the actual size in memory will be smaller.

## Running it in production
`redis-cli MONITOR` is a debugging command that streams back every command processed by the Redis server. Running this on a production database comes with a performance cost that's hard to estimate. Use it with caution on production servers.
