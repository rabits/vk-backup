#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Api

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Can interact with vk api
Required:    python2.7
'''

import time, urllib2, json
from urllib import urlencode

import Common as c
import vk_auth

c.log('debug', 'Init Api')

# Session start time
_START_TIME = long(time.time())

# Vk application ID
_CLIENT_ID = '4603710'

# Get token & user_id by login
(_TOKEN, _USER_ID) = vk_auth.auth(c.cfg('user'), c.cfg('password'), _CLIENT_ID, "messages,audio,docs,video,photos,wall,friends")

# Last time api call to prevent service overloading
_LAST_API_CALL = 0

def request(method, params):
    global _TOKEN, _LAST_API_CALL
    diff = time.time() - _LAST_API_CALL
    if diff < 0.4:
        time.sleep(0.4)
    _LAST_API_CALL = time.time()

    for retry in xrange(3):
        try:
            params['access_token'] = _TOKEN
            params['v'] = '5.25'
            url = "https://api.vk.com/method/%s?%s" % (method, urlencode(params))
            data = json.loads(urllib2.urlopen(url, None, 30).read())
            if 'response' not in data:
                if 'error' in data:
                    c.log('warning', 'Api responded error: %s' % data['error']['error_msg'])
                    if data['error']['error_code'] in [7, 15, 212]:
                        return
                    elif data['error']['error_code'] in [10]:
                        continue
                    else:
                        raise Exception('unknown error code %i, "%s", data: %s' % (data['error']['error_code'], method, data))
                else:
                    raise Exception('no correct response while calling api method "%s", data: %s' % (method, data))
            break
        except Exception as e:
            c.log('warning', 'Retry request %i (3): %s' % (retry, str(e)))
            time.sleep(2.0*(retry+1))

    if 'response' not in data:
        c.log('error', 'Unable to process request')
        return None

    return data['response']

def getUserId():
    global _USER_ID
    return str(_USER_ID)

def getStartTime():
    global _START_TIME
    return _START_TIME

