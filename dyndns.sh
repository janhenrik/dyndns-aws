#!/bin/bash
myPublicIP=`dig +short myip.opendns.com @resolver1.opendns.com`
hash=$(printf "$myPublicIP$SET_HOSTNAME$SHARED_SECRET" | shasum -a 256 | awk '{print $1}')
curl -q -s -H "x-api-key: $apiKey" $DYNDNS_URL?hash=$hash
