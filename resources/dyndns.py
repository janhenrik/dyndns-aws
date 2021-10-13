#force function to run by changing this: 0
# Dynamic DNS via AWS API Gateway, Lambda & Route 53
# Script variables use lower_case_
from __future__ import print_function
import json
import re
import hashlib
import boto3
import traceback
import datetime
import os
import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import Lambda environment variables
route_53_zone_id = "Z02438639VH134V380MR"
aws_region = os.environ['AWS_REGION']
set_hostname = "litago.test.gundelsby.com."


def json_msg (code, msg, descr) :
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({'return_status': msg, 'return_message': descr})}



def handler (event, context):
    try:
        # Set event data from the API Gateway to variables.
        source_ip = event['requestContext']['identity']['sourceIp']
        logger.info('Source IP set to ' + source_ip)

        client = boto3.client("route53")

        logger.info('Getting Record set...')
        current_route53_record_set = client.list_resource_record_sets(
            HostedZoneId=route_53_zone_id,
            StartRecordName=set_hostname,
            StartRecordType='A',
            MaxItems='2'
        )
        
        logger.info('Traversing record set...')
        for eachRecord in current_route53_record_set['ResourceRecordSets']:
            if eachRecord['Name'] == set_hostname:
                # If there's a single record, pass it along.
                if len(eachRecord['ResourceRecords']) == 1:
                    for eachSubRecord in eachRecord['ResourceRecords']:
                        if eachSubRecord['Value'] == source_ip:
                            return_status = 'success'
                            return_message = 'IP ' + source_ip + ' already set in DNS A record for ' + set_hostname
                            return json_msg(200, return_status, return_message)
                # Error out if there is more than one value for the record set.
                elif len(eachRecord['ResourceRecords']) > 1:
                    return_status = 'fail'
                    return_message = 'You should only have a single value for'\
                    ' your dynamic record.  You currently have more than one.'
                    return json_msg(200, return_status, return_message)

            logger.info('Changing IP to ' + source_ip)
            response = client.change_resource_record_sets(
            HostedZoneId=route_53_zone_id,
            ChangeBatch={
                "Comment": "Automatic DNS update",
                "Changes": [
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": set_hostname,
                            "Type": "A",
                            "TTL": 180,
                            "ResourceRecords": [
                                {
                                    "Value": source_ip
                                },
                            ],
                        }
                    },
                ]
            }
        )
    except Exception as exp:
            exception_type, exception_value, exception_traceback = sys.exc_info()
            traceback_string = traceback.format_exception(exception_type, exception_value, exception_traceback)
            err_msg = json.dumps({
                "errorType": exception_type.__name__,
                "errorMessage": str(exception_value),
                "stackTrace": traceback_string
            })
            logger.error(err_msg)
            return json_msg(500,'internal error', 'see logs for more information')
    logger.info('Updated DNS A Record for ' + set_hostname + 'to ' + source_ip)
    return json_msg(200, 'success', 'Updated DNS A Record for ' + 
        set_hostname + 'to ' + source_ip)



