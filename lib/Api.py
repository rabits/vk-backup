#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Api

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Can interact with vk api
Required:    python3.5
'''

import time, json
import urllib.request
from urllib.parse import urlencode

from . import Common as c
from . import vk_auth

c.log('debug', 'Init Api')

# Session start time
_START_TIME = int(time.time())

# Vk application ID
_CLIENT_ID = '4603710'

# Get token & user_id by login
(_TOKEN, _USER_ID) = vk_auth.auth(c.cfg('user'), c.cfg('password'), _CLIENT_ID, "messages,audio,docs,video,photos,wall,friends,stories")

# Last time api call to prevent service overloading
_LAST_API_CALL = 0

def request(method, params):
    global _LAST_API_CALL
    diff = time.time() - _LAST_API_CALL
    if diff < 0.4:
        time.sleep(0.4)
    _LAST_API_CALL = time.time()

    data = {}
    for retry in range(5):
        try:
            params['access_token'] = _TOKEN
            params['v'] = '5.81'
            url = "https://api.vk.com/method/" + method
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, urlencode(params).encode()) as ret:
                encoding = ret.info().get_content_charset('utf-8')
                data = json.loads(ret.read().decode(encoding))
            if 'response' not in data:
                if 'error' in data:
                    c.log('warning', 'Api responded error: %s' % data['error']['error_msg'])
                    if data['error']['error_code'] in [7, 15, 212, 801]:
                        # 7 - No rights to execute this method
                        # 15 - Access denied
                        # 212 - Access to post comments denied
                        # 801 - Comments for this video are closed
                        return
                    elif data['error']['error_code'] in [10]:
                        continue
                    else:
                        raise Exception('unknown error code %i, "%s", data: %s' % (data['error']['error_code'], method, data))
                else:
                    raise Exception('no correct response while calling api method "%s", data: %s' % (method, data))
            break
        except Exception as e:
            c.log('warning', 'Retry request %s %i (5): %s' % (method, retry, str(e)))
            time.sleep(2.0*(retry+1))

    if 'response' not in data:
        c.log('error', 'Unable to process request')
        return None

    return data['response']

def getUserId():
    return _USER_ID

def getStartTime():
    return _START_TIME

