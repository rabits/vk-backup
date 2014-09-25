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

from lib import vk_auth

from urllib import urlencode
import time
import getpass, codecs, urllib2, json
from sys import stderr, stdout, exit as sysexit
import os

from optparse import OptionParser
import ConfigParser

if os.geteuid() == 0:
    stderr.write("ERROR: vk-backup is running by the root user, but this is really dangerous! Please use unprivileged user.\n")
    sysexit()

def exampleini(option, opt, value, parser):
    print '[vk-backup]'
    for key in parser.option_list:
        if None not in [key.dest, key.type] and key.dest != 'config-file':
            print '%s: %s' % (key.dest, key.default)
    sysexit()

# Parsing command line options
parser = OptionParser(usage='%prog [options]', version=__doc__.split('\n', 1)[0])
parser.add_option('-u', '--user', type='string', dest='user', metavar='EMAIL',
        default=None, help='vk.com account user email (<user>@<host>) (required)')
parser.add_option('-p', '--password', type='string', dest='password', metavar='PASSWORD',
        default=None, help='vk.com account password (will be requested if not set)')
parser.add_option('-l', '--log-file', type='string', dest='log-file', metavar='FILE',
        default=None, help='copy log output to file [%default]')
parser.add_option('-c', '--config-file', type='string', dest='config-file', metavar='FILE',
        default=None, help='get configuration from ini file (replaced by command line parameters) [%default]')
parser.add_option('-e', '--config-example', action='callback', callback=exampleini,
        default=None, help='print example ini config file to stdout')
parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
        help='verbose mode - moar output to stdout')
parser.add_option('-q', '--quiet', action='store_false', dest='verbose',
        help='silent mode - no output to stdout')
(options, args) = parser.parse_args()
options = vars(options)

# Parsing config file
if options['config-file'] != None:
    try:
        config = ConfigParser.ConfigParser()
        config.read(options['config-file'])

        for key in parser.option_list:
            if None not in [key.dest, key.type]:
                if options[key.dest] is key.default:
                    try:
                        if key.type in ['int', 'float', 'boolean']:
                            val = getattr(config, 'get%s' % key.type)('vk-backup', key.dest)
                        else:
                            val = config.get('vk-backup', key.dest)
                        options[key.dest] = val
                    except ConfigParser.NoOptionError:
                        continue
    except:
        parser.error('Error while parse config file. Please specify header and available options')

if options['user'] == None:
    parser.error('Unable to get email from the user option')
if options['password'] == None:
    options['password'] = getpass.getpass()

# LOGGING
if options['log-file'] != None:
    class Tee(object):
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()

    logfile = open(options['log-file'], 'a')
    stdout = Tee(stdout, logfile)
    stderr = Tee(stderr, logfile)

if options['verbose'] == True:
    import inspect
    def log(logtype, message):
        func = inspect.currentframe().f_back
        log_time = time.time()
        if logtype != "ERROR":
            stdout.write('[%s.%s %s, line:%03u]: %s\n' % (time.strftime('%H:%M:%S', time.localtime(log_time)), str(log_time % 1)[2:8], logtype, func.f_lineno, message))
        else:
            stderr.write('[%s.%s %s, line:%03u]: %s\n' % (time.strftime('%H:%M:%S', time.localtime(log_time)), str(log_time % 1)[2:8], logtype, func.f_lineno, message))
elif options['verbose'] == False:
    def log(logtype, message):
        if logtype == "ERROR":
            stderr.write('[%s %s]: %s\n' % (time.strftime('%H:%M:%S'), logtype, message))
else:
    def log(logtype, message):
        if logtype != "DEBUG":
            if logtype != "ERROR":
                stdout.write('[%s %s]: %s\n' % (time.strftime('%H:%M:%S'), logtype, message))
            else:
                stderr.write('[%s %s]: %s\n' % (time.strftime('%H:%M:%S'), logtype, message))

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
        log('WARNING', 'got error while calling api method "%s" (retry %i):' % (method, retry))
        log('WARNING', '  %s' % data)
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
token, user_id = vk_auth.auth(options['user'], options['password'], client_id, "messages")

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
                log('INFO', 'Found self user_id')

    counter += 200
    if counter >= count:
        counter = 0
        break

users_ids = users.keys()
log('INFO', 'Getting dialog users: %i' % len(users_ids))
while True:
    data = get_users(users_ids[counter:counter+1000], token)
    for user in data:
        log('DEBUG', '  %i %s %s' % (user['uid'], user['first_name'], user['last_name']))
        users[str(user['uid'])] = user

    counter += 1000
    if counter >= len(users_ids):
        counter = 0
        break

chats_ids = chats.keys()
log('INFO', 'Getting chat info: %i' % len(chats_ids))
while True:
    data = get_chats(chats_ids[counter:counter+200], token)
    for chat in data:
        log('DEBUG', '  %i %s' % (chat['chat_id'], chat['title']))
        chats[str(chat['chat_id'])] = chat

    counter += 200
    if counter >= len(chats_ids):
        counter = 0
        break

if not os.path.isdir("backup/dialogs"):
    os.makedirs("backup/dialogs") 

log('INFO', 'Loading dialogs...')
for key, user in users.items():
    log('INFO', '  %i %s %s:' % (user['uid'], user['first_name'], user['last_name']))

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
            log('INFO', '    found user data changes - adding new data')
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
        log('INFO', '    loaded %i from %i' % (counter, overall))

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

log('INFO', 'DONE')
