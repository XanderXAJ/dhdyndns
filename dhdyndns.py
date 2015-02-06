#!/usr/bin/env python3
# dhdyndns : Sets the A record for the given DreamHost domain to the given IP

import argparse
import datetime
import ipaddress
import json
import subprocess   # For calling curl
import sys
import urllib.parse # For URL-encoding parameters

API_URL='https://api.dreamhost.com/'
API_LIST_ARGS={'cmd': 'dns-list_records', 'format': 'json', 'key': '{key}'}
API_REMOVE_ARGS={'cmd': 'dns-remove_record', 'format': 'json', 'key': '{key}', 'record': '{record}', 'type': '{type}', 'value': '{value}'}
API_ADD_ARGS={'cmd': 'dns-add_record', 'format': 'json', 'key': '{key}', 'record': '{record}', 'type': '{type}', 'value': '{value}', 'comment': '{comment}'}

CURL_ARGS=['curl', '-s', '--ciphers', 'RSA']
CURL_INSECURE_ARGS=['-k']

REQ_TIMEOUT=30000
RECORD_TYPE='A'



def makeUrl(base, params):
    """
    Returns a URL formed by adding the base to dict of params

    The keys and values of params will be URL encoded before being appended.  The base will be untouched.
    """
    if params is None or len(params) == 0:
        # No parameters, just return base URL
        return base
    else:
        # Parameters included, return base, ?, URL-encoded parameters
        return base + '?' + urllib.parse.urlencode(params)




def makeRequest(url):
    """
    Makes a request to the passed url

    This is made difficult by the fact that the DH API hangs if there are too many available
    ciphers, therefore we limit ourselves to just one using curl.
    There is a good chance this will need changing in the future.
    """
    # Assemble curl command
    curl_cmd = CURL_ARGS[:]
    if args.insecure: curl_cmd += CURL_INSECURE_ARGS
    curl_cmd += [url]

    if args.verbosity >= 2:
        print("command:", *curl_cmd)

    response = subprocess.check_output(curl_cmd, timeout=REQ_TIMEOUT)

    if args.verbosity >= 2:
        print('Response from', url, ':', response)

    data = json.loads(response.decode('utf-8'))
    return [data.get('result') == 'success', data.get('data')]



# Parse arguments -- we need at least the API key, domain and IP
parser = argparse.ArgumentParser(description='Replaces the A record for the given domain with a record with the given IP')
parser.add_argument('key', help='DreamHost API key')
parser.add_argument('domain', help='Domain A record to update')
parser.add_argument('ip', type=ipaddress.ip_address, help='IP to set the A record to')
parser.add_argument('-v', '--verbosity', action='count', default=0, help='Increases output verbosity; specify multiple times for more')
parser.add_argument('-c', '--comment', default='Updated at {}'.format(datetime.datetime.now().isoformat()), help='Comment to add to record. Defaults to current date and time.')
parser.add_argument('-a', '--add', action='store_true', help='Add record even if no equivalent exists')
parser.add_argument('-k', '--insecure', action='store_true', help='Allows insecure SSL connections. Same as curl\'s -k. Try if command fails with exit status 60 and if you can accept risk.')
args = parser.parse_args()

if args.verbosity >= 1:
    print('key:', args.key)
    print('domain:', args.domain)
    print('ip:', args.ip)
    print('comment:', args.comment)



# Get list of records
list_args = API_LIST_ARGS.copy()
list_args.update({'key': args.key})
success, records = makeRequest(makeUrl(API_URL, list_args))

# Stop now if the request for current records fails
if not success:
    print('Failed to get list of current records', file=sys.stderr)
    sys.exit(1)


if args.verbosity >= 2:
    print('All records:')
    for record in records:
        print(record)



# Find if the record that is to be updated already exists
current_record = next((record for record in records if record['record'] == args.domain and record['type'] == RECORD_TYPE), None)

# This script does not require that the record to be updated already exists.
# However, if there's no record and the add option hasn't been specified, it's an error.
if current_record is None and not args.add:
    print('Matching record not found. Try -vv for more info.', file=sys.stderr)
    sys.exit(1)

if current_record is not None:
    if args.verbosity >= 1:
        print('Found record:', current_record)

    # Only modify the record if it is editable
    if current_record['editable'] != '1':
        print('Record is not editable:', current_record, file=sys.stderr)
        sys.exit(1)

    # The record only needs modifying if the IP addresses differ
    if current_record['value'] == str(args.ip) and args.verbosity >= 1:
        print('IP addresses match, no need to update:', current_record, file=sys.stderr)
        sys.exit(1)

    # The record we've found needs removing, remove it
    remove_args = API_REMOVE_ARGS.copy()
    remove_args.update({'key': args.key, 'record': current_record['record'], 'type': current_record['type'], 'value': current_record['value']})
    success, data = makeRequest(makeUrl(API_URL, remove_args))

    if not success:
        print('Failed to remove current record:', data, file=sys.stderr)
        sys.exit(1)

    if args.verbosity >= 1:
        print('Current record successfully removed:', current_record)



# Add new record
new_record = {'record': args.domain, 'type': RECORD_TYPE, 'value': args.ip, 'comment': args.comment}
add_args = API_ADD_ARGS.copy()
add_args.update(dict(key=args.key, **new_record))
success, data = makeRequest(makeUrl(API_URL, add_args))

if not success:
    print('Failed to add new record:', data, file=sys.stderr)
    sys.exit(1)

if args.verbosity >= 1:
    print('Record successfully added:', new_record)

