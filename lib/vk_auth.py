#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import getpass
from urllib.parse import urlparse
from html.parser import HTMLParser

# Asks user to enter the auth URL in browser and put back the auth link
def auth(email, password, client_id, scope):
    def split_key_value(kv_pair):
        kv = kv_pair.split("=")
        return kv[0], kv[1]

    # Authorization form
    def auth_user(email, password, client_id, scope):
        print("Please open this link in browser, login and paste back here the URL after login:")
        print("http://oauth.vk.com/oauth/authorize?" + \
            "redirect_uri=http://oauth.vk.com/blank.html&response_type=token&" + \
            "client_id=%s&scope=%s&display=page" % (client_id, ",".join(scope)))
        return getpass.getpass('\n')


    if not isinstance(scope, list):
        scope = [scope]
    url = auth_user(email, password, client_id, scope)
    if urlparse(url).path != "/blank.html":
        raise RuntimeError("Incorrect auth URL provided by user")
    answer = dict(split_key_value(kv_pair) for kv_pair in urlparse(url).fragment.split("&"))
    if "access_token" not in answer or "user_id" not in answer:
        raise RuntimeError("Missing some values in answer")
    return answer["access_token"], answer["user_id"]
