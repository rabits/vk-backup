#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup UIApi

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Can interact with vk UI API
Required:    python3.5
'''

import sys
import time, json
import urllib.request
from urllib.parse import urlencode

from . import Common as c
from . import vk_auth

c.log('debug', 'Init UIApi')

# Getting curl parameters to initialize the headers to access UI API
if '--' not in sys.argv:
    c.log('error', 'Unable to locate "--" parameter which separates vk-backup params from curl params, please read README on how to use vk-backup')
    sys.exit(1)

curl_params_index = sys.argv.index('--') + 1
if sys.argv[curl_params_index] != 'curl':
    c.log('error', 'Unable to locate "curl" parameter which starts curl params to access VK UI API, please read README on how to use vk-backup')
    sys.exit(1)

_HEADERS = {}
needed_headers = ['Authorization', 'Cookie']
process_arg = curl_params_index # Starting with curl_params_index to not process vk-backup params
while process_arg < len(sys.argv)-1:
    process_arg += 1
    if sys.argv[process_arg] != '-H':
        continue

    process_arg += 1
    # This argument is a header, check with the needed headers list
    if any([ True for h in needed_headers if sys.argv[process_arg].startswith(h+': ') ]):
        (k, v) = sys.argv[process_arg].split(': ', 1)
        _HEADERS[k] = v

if len(_HEADERS) < len(needed_headers):
    c.log('error', 'Not all the required headers was found in the provided curl request')
    sys.exit(1)

# Last time api call to prevent service overloading
_LAST_API_CALL = 0

def _requestJson(url, data):
    data_en = urlencode(data).encode()

    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0')
    for k, v in _HEADERS.items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, data_en) as ret:
        encoding = ret.info().get_content_charset('utf-8')
        ret_data = ret.read().decode(encoding)
    if ret_data.startswith('<!--'):
        ret_data = ret_data[4:]

    response = json.loads(ret_data)

    return response

def dumpData(data):
    return json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True)

def request(method, params):
    global _LAST_API_CALL
    diff = time.time() - _LAST_API_CALL
    if diff < 0.4:
        time.sleep(0.4)
    _LAST_API_CALL = time.time()

    data = {}
    for retry in range(5):
        try:
            url = "https://vk.com/" + method
            data = _requestJson(url, params)
            if 'payload' not in data:
                raise Exception('Incorrect response while calling UI API method "%s", data: %s' % (method, data))
            break
        except Exception as e:
            c.log('warning', 'Retry request %s %i (5): %s' % (method, retry, str(e)))
            time.sleep(2.0*(retry+1))

    if 'payload' not in data:
        c.log('error', 'Unable to process request')
        return None

    return data['payload']
