#!/bin/bash
eval $(echo "$REDIS_CLI MONITOR | python3 injector.py")