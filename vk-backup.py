#!/usr/bin/python
# -*- coding: UTF-8 -*-

from lib import vk_auth
import json
import urllib2
from urllib import urlencode
import os
import getpass
import sys
import codecs
import time
import datetime

def call_api(method, params, token):
    params.append(("access_token", token))
    url = "https://api.vk.com/method/%s?%s" % (method, urlencode(params))
    return json.loads(urllib2.urlopen(url).read())["response"]

def get_users(user_ids, token):
    return call_api("users.get", [("user_ids", ','.join(user_ids)), ("fields", "photo_max_orig")], token)

def get_chats(chat_ids, token):
    return call_api("messages.getChat", [("chat_ids", ','.join(chat_ids))], token)

def get_dialogs(offset, token):
    return call_api("messages.getDialogs", [('count', 200), ('preview_length', 1), ('offset', offset)], token)

def get_messages(user_id, offset, token):
    return call_api("messages.getHistory", [("user_id", user_id), ('count', 200), ('rev', 1), ('offset', offset)], token)

if len(sys.argv) == 2:
    email = sys.argv[1]
else:
    email = raw_input("Email: ")

password = getpass.getpass()
client_id = "2951857" # Vk application ID
token, user_id = vk_auth.auth(email, password, client_id, "messages")

current = 0

chats = {}
users = {}
while True:
    dialogs = get_dialogs(current, token)
    count = long(dialogs.pop(0))
    for dialog in dialogs:
        if 'chat_id' in dialog:
            chats[str(dialog['chat_id'])] = True
        else:
            if long(dialog['uid']) != long(user_id):
                users[str(dialog['uid'])] = True
            else:
                print 'Found self user_id'

    current += 200
    if current > count:
        current = 0
        break

users_ids = users.keys()
print 'Getting dialog users: %i' % len(users_ids)
while True:
    data = get_users(users_ids[current:current+1000], token)
    for user in data:
        print '  %i %s %s' % (user['uid'], user['first_name'], user['last_name'])
        users[str(user['uid'])] = user

    current += 1000
    if current > len(users_ids):
        current = 0
        break

chats_ids = chats.keys()
print 'Getting chat info: %i' % len(chats_ids)
while True:
    data = get_chats(chats_ids[current:current+200], token)
    for chat in data:
        print '  %i %s' % (chat['chat_id'], chat['title'])
        chats[str(chat['chat_id'])] = chat

    current += 200
    if current > len(chats_ids):
        current = 0
        break

print "DONE"
