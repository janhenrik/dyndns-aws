#!/bin/bash
myPublicIP=`dig +short myip.opendns.com @resolver1.opendns.com`
hash=$(printf "$myPublicIP$SET_HOSTNAME$SHARED_SECRET" | shasum -a 256 | awk '{print $1}')
curlCmd="curl -H 'x-api-key: $DYNDNS_API_KEY' $DYNDNS_URL?hash=$hash"
eval $curlCmd
