#!/bin/bash

RESPONSE=$(curl -u admin:admin -i -H 'X-Requested-By: ambari' -X ${1} --data-binary "@${2}" ${3})

if [[ $RESPONSE == *"HTTP/1.1 20"* ]] ; then
   exit 0;
else
   echo $RESPONSE
   exit 1;
fi
