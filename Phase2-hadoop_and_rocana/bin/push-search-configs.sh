#!/bin/bash

echo "pushing Rocana Search search.properties"
ansible -i hosts hadoop-dn -m template -a "src=configs/{{ cluster_name }}/rocana-search/search.properties.j2 dest=/etc/rocana-ops/rocana-search/search.properties owner=rocana group=rocana mode=0644" -f 3

echo "pushing Rocana Search commands.d/rocana-search"
ansible -i hosts hadoop-dn -m template -a "src=configs/{{ cluster_name }}/commands.d/rocana-search.j2 dest=/etc/rocana-ops/commands.d/rocana-search owner=rocana group=rocana mode=0644" -f 40
