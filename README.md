# Redis Monitor
Actively monitors a redis database using the `redis-cli monitor` command (https://redis.io/commands/monitor).

## Installation & Usage
A valid docker install is required. 

Modify docker-compose.yml with the target REDIS_CLI string, then build and run. The output should be displayed on screen. 

```
$ docker-compose build
$ docker-compose up
```

## Implementation details
The output shows the key hitrate, calculated using the following formula `hitrate = (gets / (gets + sets)) * 100`, the number of GET and SET operations. The result is ordered by hitrate asscending and is refreshed every 5 seconds for an (almost) instantaneous feedback about what is going on the live Redis server.

MONITOR is a debugging command that streams back every command processed by the Redis server. Running this on a production database comes with a performance cost that's hard to estimate. Use it with caution on production servers.
