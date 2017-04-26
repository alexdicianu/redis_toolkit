#!/bin/bash
eval $(echo "$REDIS_CLI MONITOR | python /injector.py")