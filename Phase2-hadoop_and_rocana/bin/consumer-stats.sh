#!/bin/bash

export CONSUMER_HOST=127.0.0.1

watch -n 10 'echo "metadata consumer";curl -s http://${CONSUMER_HOST}:17318/metrics?pretty=true | grep -A5 events\" | egrep "events|m1_"; \
echo "metrics consumer"; curl -s http://${CONSUMER_HOST}:17317/metrics?pretty=true | grep -A5 events\" | egrep "events|m1_"; \
echo "echo"; curl -s http://${CONSUMER_HOST}:17314/metrics?pretty=true | grep -A5 events\" | egrep "events|m1_"; \
echo "hdfs consumer";curl -s http://${CONSUMER_HOST}:17310/metrics?pretty=true | grep -A5 events\" | egrep "events|m1_";'