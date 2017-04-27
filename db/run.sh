#!/bin/bash

redis-server /etc/redis.conf
sleep 5
redis-cli flushall