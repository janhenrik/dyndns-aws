#force function to run by changing this: 0
# Dynamic DNS via AWS API Gateway, Lambda & Route 53
# Script variables use lower_case_
import json
import re
import hashlib
import traceback
import os
import logging
import sys
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def json_msg (code, msg, descr) :
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({'return_status': msg, 'return_message': descr})}



def handler (event, context):
    try:
        # Import Lambda environment variables
        route_53_zone_id = os.environ.get('ROUTE_53_ZONE_ID')
        set_hostname = os.environ.get('SET_HOSTNAME')
        shared_secret = os.environ.get('SHARED_SECRET')
        
        logger.info(json.dumps(event))
        source_ip = event['requestContext']['identity']['sourceIp']
        logger.info('Source IP set to ' + source_ip)

        validation_hash = event['queryStringParameters']['hash']
        # Validate that the client passed a sha256 hash
        # regex checks for a 64 character hex string.
        logger.info('Input hash: ' + validation_hash)
        if not re.match(r'[0-9a-fA-F]{64}', validation_hash):
            return_status = 'fail'
            return_message = 'You must pass a valid sha256 hash in the '\
                'hash= argument.'
            return json_msg(500, return_status, return_message)

        # Calculate the validation hash.
        hash_string = source_ip + set_hostname + shared_secret
        calculated_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
        # Compare the validation_hash from the client to the
        # calculated_hash.
        # If they don't match, error out.
        if not calculated_hash == validation_hash:
            return_status = 'fail'
            return_message = 'Validation hashes do not match.'
            return json_msg(500,return_status, return_message)

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



