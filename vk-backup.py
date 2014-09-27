#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup 0.2

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Script can backup your VK profile to your storage
Required:    python2.7

Usage:
  $ ./vk-backup.py --help
'''

from lib import Common as c
from lib import vk_auth

from urllib import urlencode
import time
import getpass, codecs, urllib2, json
import os

c.init_begin(__doc__)
c.option('-u', '--user', type='string', dest='user', metavar='EMAIL', default=None, help='vk.com account user email (<user>@<host>) (required)')
c.option('-p', '--password', type='string', dest='password', metavar='PASSWORD', default=None, help='vk.com account password (will be requested if not set)')
c.init_end()

if c.cfg('user') == None:
    parser.error('Unable to get email from the user option')
if c.cfg('password') == None:
    c.cfg('password', getpass.getpass())

lastcall = 0

def call_api(method, params, token):
    global lastcall
    diff = time.time() - lastcall
    if diff < 0.4:
        time.sleep(0.4)
    lastcall = time.time()

    for retry in xrange(3):
        params.append(("access_token", token))
        url = "https://api.vk.com/method/%s?%s" % (method, urlencode(params))
        data = json.loads(urllib2.urlopen(url).read())
        if 'response' in data:
            break
        c.log('WARNING', 'got error while calling api method "%s" (retry %i):' % (method, retry))
        c.log('WARNING', '  %s' % data)
        time.sleep(2.0*(retry+1))

    return data["response"]

def get_users(user_ids, token):
    return call_api("users.get", [("user_ids", ','.join(user_ids)), ("fields", "photo_max_orig")], token)

def get_chats(chat_ids, token):
    return call_api("messages.getChat", [("chat_ids", ','.join(chat_ids))], token)

def get_dialogs(offset, token):
    return call_api("messages.getDialogs", [('count', 200), ('preview_length', 1), ('offset', offset)], token)

def get_messages(user_id, offset, token):
    return call_api("messages.getHistory", [("user_id", user_id), ('count', 200), ('rev', 1), ('offset', offset)], token)

client_id = "2951857" # Vk application ID
token, user_id = vk_auth.auth(c.cfg('user'), c.cfg('password'), client_id, "messages")

now = long(time.time())

counter = 0

chats = {}
users = {}
while True:
    dialogs = get_dialogs(counter, token)
    count = long(dialogs.pop(0))
    for dialog in dialogs:
        if 'chat_id' in dialog:
            chats[str(dialog['chat_id'])] = True
        else:
            if long(dialog['uid']) != long(user_id):
                users[str(dialog['uid'])] = True
            else:
                c.log('INFO', 'Found self user_id')

    counter += 200
    if counter >= count:
        counter = 0
        break

users_ids = users.keys()
c.log('INFO', 'Getting dialog users: %i' % len(users_ids))
while True:
    data = get_users(users_ids[counter:counter+1000], token)
    for user in data:
        c.log('DEBUG', '  %i %s %s' % (user['uid'], user['first_name'], user['last_name']))
        users[str(user['uid'])] = user

    counter += 1000
    if counter >= len(users_ids):
        counter = 0
        break

chats_ids = chats.keys()
c.log('INFO', 'Getting chat info: %i' % len(chats_ids))
while True:
    data = get_chats(chats_ids[counter:counter+200], token)
    for chat in data:
        c.log('DEBUG', '  %i %s' % (chat['chat_id'], chat['title']))
        chats[str(chat['chat_id'])] = chat

    counter += 200
    if counter >= len(chats_ids):
        counter = 0
        break

if not os.path.isdir("backup/dialogs"):
    os.makedirs("backup/dialogs") 

c.log('INFO', 'Loading dialogs...')
for key, user in users.items():
    c.log('INFO', '  %i %s %s:' % (user['uid'], user['first_name'], user['last_name']))

    filename = "backup/dialogs/%i.json" % (user['uid'])

    newdata = {
        'first_name'  : user['first_name'],
        'last_name'   : user['last_name'],
        'photo'       : user['photo_max_orig'],
    }

    if os.path.isfile(filename):
        data = json.load(open(filename))
        # Check that latest user data is correct
        tmp = data['user'].keys()
        tmp.sort()
        if len(set(data['user'][tmp[-1]].items()) & set(newdata.items())) != len(newdata):
            c.log('INFO', '    found user data changes - adding new data')
            data['user'][now] = newdata
    else:
        data = {
            'id'      : user['uid'],
            'user'    : { now : newdata },
            'dialogs' : [], # Dialogs massive
        }

    counter = len(data['dialogs'])
    while True:
        msgs = get_messages(user['uid'], counter, token)
        overall = msgs.pop(0)
        counter += len(msgs)
        c.log('INFO', '    loaded %i from %i' % (counter, overall))

        # Removing no needed keys from data
        for msg in msgs:
            msg.pop('uid', None)
            msg.pop('read_state', None)
            msg.pop('from_id', None)

        data['dialogs'].extend(msgs)

        if counter >= overall:
            break

    with codecs.open(filename, "w", "utf-8") as outfile:
        json.dump(data, outfile, indent=1, ensure_ascii=False)

c.log('INFO', 'DONE')
