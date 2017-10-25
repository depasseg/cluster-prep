#!/bin/bash

# simple wrapper script using ansible for start rocana search.  Issues service start

echo "Starting Rocana Search via ansible"
ansible -i hosts hadoop-dn -m shell -a "service rocana-search start" -f 40;

