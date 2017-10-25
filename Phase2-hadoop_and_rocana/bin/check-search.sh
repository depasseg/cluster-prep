#!/bin/bash

# simple wrapper script using ansible for start rocana search.  Issues service start

echo "Issuing ps -ef to check for Rocana Search via ansible"
ansible -i ../hosts hadoop-dn -m shell -a "ps -ef | grep rocana-search | grep -v grep" -f 40;

