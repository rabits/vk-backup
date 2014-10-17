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

# Vk application ID
_CLIENT_ID = '2951857'

# Get token & user_id by login
(_TOKEN, _USER_ID) = vk_auth.auth(c.cfg('user'), c.cfg('password'), _CLIENT_ID, "messages")

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
            data = json.loads(urllib2.urlopen(url).read())
            if 'response' not in data:
                raise Exception('no correct response while calling api method "%s", data: %s' % (method, data))
            break
        except Exception as e:
            c.log('warning', 'Retry request %i (3): %s' % (retry, str(e)))
            time.sleep(2.0*(retry+1))

    return data['response']

def getUserId():
    global _USER_ID
    return str(_USER_ID)

