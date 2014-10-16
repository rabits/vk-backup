#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup 0.6

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
from urlparse import urlparse
import time
import getpass, codecs, urllib2, json
import os

c.init_begin(__doc__)
c.option('-u', '--user', type='string', dest='user', metavar='EMAIL', default=None, help='vk.com account user email (<user>@<host>) (required)')
c.option('-p', '--password', type='string', dest='password', metavar='PASSWORD', default=None, help='vk.com account password (will be requested if not set)')
c.option('-d', '--backup-dir', type='string', dest='backup-dir', metavar='PATH', default='backup', help='directory to store data')
c.init_end()

if c.cfg('user') == None:
    parser.error('Unable to get email from the user option')

if c.cfg('password') == None:
    c.cfg('password', getpass.getpass())

class Api:
    '''
    Can interact with vk api
    '''
    def __init__(self):
        c.log('debug', 'Api init')

        # Vk application ID
        self.client_id = "2951857"

        # Get token & user_id by login
        self.token, self.user_id = vk_auth.auth(c.cfg('user'), c.cfg('password'), self.client_id, "messages")

        # Last time api call to prevent service overloading
        self.last_api_call = 0

    def request(self, method, params):
        diff = time.time() - self.last_api_call
        if diff < 0.4:
            time.sleep(0.4)
        self.last_api_call = time.time()

        for retry in xrange(3):
            try:
                params['access_token'] = self.token
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

    def getUserId(self):
        return str(self.user_id)


class Media:
    '''
    Media download
    '''
    def __init__(self):
        c.log('debug', 'Media init')

        self.path = os.path.join(c.cfg('backup-dir'), 'media')

        # Create directory
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

    def loadAttachments(self, data):
        attachments = []
        if 'attachments' in data:
            attachments.extend(data['attachments'])
        if 'attachment' in data:
            attachments.append(data['attachment'])
        for attach in attachments:
            c.log('debug', 'Processing %s' % attach['type'])
            funcname = "process" + attach['type'].title()
            if funcname in dir(self):
                getattr(self, funcname)(attach[attach['type']])
            else:
                c.log('error', '  unable to find attachment processing function "Media.%s"' % funcname)
                c.log('debug', str(attach))

    def download(self, url, path = None):
        if url == '':
            c.log('warning', 'Skipping empty url')
            return path

        if path == None:
            path = self.path + urlparse(url).path

        if os.path.isfile(path):
            c.log('debug', 'Skipping, file %s already exists' % path)
            return path

        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)

        for retry in xrange(3):
            try:
                u = urllib2.urlopen(url)
                with open(path, "wb") as outfile:
                    size = int(u.info().getheaders("Content-Length")[0])
                    c.log('debug', 'Downloading %s to %s (%ib)' % (url, path, size))
                    size_dl = 0
                    while True:
                        b = u.read(8192)
                        if not b:
                            break
                        size_dl += len(b)
                        outfile.write(b)
                break
            except Exception as e:
                c.log('warning', 'Retry request %i (3): %s' % (retry, str(e)))
                time.sleep(2.0*(retry+1))

        return path

    def processPhoto(self, data):
        url = None
        size = 0
        for key in data.keys():
            if key.startswith('photo_') and int(key.split('_')[1]) > size:
                size = int(key.split('_')[1])
                url = data.pop(key, None)

        if url == None:
            c.log('warning', 'Valid url not found in %s' % str(data))
            return

        data['url'] = url
        data['localpath'] = self.download(data['url'])

    def processDoc(self, data):
        data['localpath'] = self.download(data['url'])

    def processAudio(self, data):
        data['localpath'] = self.download(data['url'])

    def processWall(self, data):
        c.log('debug', 'Processing wall attachments')
        self.loadAttachments(data)

    def processGeo(self, data):
        c.log('debug', 'Skipping geo attachment - no data to download')

    def processVideo(self, data):
        c.log('debug', 'Skipping video attachment - size of the file is too big')

    def processSticker(self, data):
        c.log('debug', 'Skipping sticker attachment - idiotizm')

    def processLink(self, data):
        c.log('debug', 'Skipping link attachment - no data to download')

    def processPoll(self, data):
        c.log('debug', 'Skipping poll attachment - no data to download')

    def processNote(self, data):
        c.log('debug', 'Skipping poll attachment - no data to download')


# Common messages function for Chats & Dialogs
def processMessages(data):
    for d in data:
        d.pop('user_id', None)
        d.pop('read_state', None)
        d.pop('chat_id', None)
        media.loadAttachments(d)
        if 'fwd_messages' in d:
            processMessages(d['fwd_messages'])


class Chats:
    '''
    Chats management
    '''
    def __init__(self):
        c.log('debug', 'Chats init')

        self.data = {}

        self.path = os.path.join(c.cfg('backup-dir'), 'chats')

        # Create directory
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

        # Loading local data from storage
        self.load()

    def store(self):
        c.log('debug', 'Store chats (%i)' % len(self.data))
        for i in self.data:
            with codecs.open(os.path.join(self.path, i + '.json'), "w", "utf-8") as outfile:
                json.dump(self.data[i], outfile, indent=1, ensure_ascii=False)

    def load(self):
        files = [ f for f in os.listdir(self.path) if f.endswith('.json') ]
        c.log('debug', 'Loading chats (%i)' % len(files))
        for f in files:
            filename = os.path.join(self.path, f)
            data = json.load(open(filename))
            self.data[data['id']] = data

    def requestChatInfo(self, chat_id):
        if chat_id not in self.data:
            self.data[chat_id] = {
                'id':  chat_id,
                'log': []
            }
        data = api.request('messages.getChat', {'chat_id': chat_id})
        if len(data['users']) > 0:
            users.requestUsers([ str(u) for u in data['users'] ])
        self.data[chat_id]['data'] = data

    def requestChatMessages(self, chat_id):
        chat = self.getChat(chat_id)
        c.log('info', 'Requesting chat messages for chat %s "%s"' % (chat_id, chat['data']['title']))

        req_data = {'chat_id': chat_id, 'count': 200, 'offset': -200}
        if len(self.data[chat_id]['log']) == 0:
            req_data['rev'] = 1
            req_data['offset'] = 0
        else:
            req_data['start_message_id'] = self.data[chat_id]['log'][-1]['id']

        while True:
            data = api.request('messages.getHistory', req_data)
            count = data['count']
            data = data['items']

            if len(data) == 0:
                c.log('info', '  no new messages %i (%i)' % (len(self.data[chat_id]['log']), count))
                break

            # Switch to get history by message id
            if 'start_message_id' not in req_data:
                req_data['offset'] = -200
                req_data.pop('rev', None)
            else:
                data.reverse()

            processMessages(data)
            self.data[chat_id]['log'].extend(data)

            req_data['start_message_id'] = data[-1]['id']
            c.log('info', '  loaded %i, stored %i (%i)' % (len(data), len(self.data[chat_id]['log']), count))
            if len(data) < 200:
                c.log('info', '  done')
                break

    def getChat(self, chat_id):
        if chat_id not in self.data:
            self.requestChatInfo(chat_id)
        return self.data[chat_id]


class Dialogs:
    '''
    Dialogs management
    '''
    def __init__(self):
        c.log('debug', 'Dialogs init')

        self.data = {}

        self.path = os.path.join(c.cfg('backup-dir'), 'dialogs')

        # Create directory
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

        # Loading local data from storage
        self.load()

    def store(self):
        c.log('debug', 'Store dialogs (%i)' % len(self.data))
        for i in self.data:
            with codecs.open(os.path.join(self.path, i + '.json'), "w", "utf-8") as outfile:
                json.dump(self.data[i], outfile, indent=1, ensure_ascii=False)

    def load(self):
        files = [ f for f in os.listdir(self.path) if f.endswith('.json') ]
        c.log('debug', 'Loading dialogs (%i)' % len(files))
        for f in files:
            filename = os.path.join(self.path, f)
            data = json.load(open(filename))
            self.data[data['id']] = data

    def requestDialogs(self):
        c.log('debug', 'Requesting dialogs')

        req_data = {'count': 200, 'preview_length': 1, 'offset': 0}

        while True:
            data = api.request('messages.getDialogs', req_data)
            count = data['count']
            data = data['items']
            for d in data:
                if 'chat_id' in d['message']:
                    chats.requestChatMessages(str(d['message']['chat_id']))
                else:
                    self.requestMessages(str(d['message']['user_id']))

            req_data['offset'] += 200
            if req_data['offset'] >= count:
                break

    def requestMessages(self, user_id):
        user = users.getUser(user_id)
        c.log('info', 'Requesting messages for user %s %s %s' % (user_id, user['data']['first_name'], user['data']['last_name']))

        req_data = {'user_id': user_id, 'count': 200, 'offset': -200}
        if user_id not in self.data:
            req_data['rev'] = 1
            req_data['offset'] = 0
            self.data[user_id] = {
                'id' :  user_id,
                'log' : []
            }
        elif len(self.data[user_id]['log']) > 0:
            req_data['start_message_id'] = self.data[user_id]['log'][-1]['id']

        while True:
            data = api.request('messages.getHistory', req_data)
            count = data['count']
            data = data['items']

            if len(data) == 0:
                c.log('info', '  no new messages %i (%i)' % (len(self.data[user_id]['log']), count))
                break

            # Switch to get history by message id
            if 'start_message_id' not in req_data:
                req_data['offset'] = -200
                req_data.pop('rev', None)
            else:
                data.reverse()

            processMessages(data)
            self.data[user_id]['log'].extend(data)

            req_data['start_message_id'] = data[-1]['id']
            c.log('info', '  loaded %i, stored %i (%i)' % (len(data), len(self.data[user_id]['log']), count))
            if len(data) < 200:
                c.log('info', '  done')
                break

    def getMessages(self, user_id):
        if user_id not in self.data:
            self.requestMessages(user_id)
        return self.data[user_id]


class Users:
    '''
    Contains info about known users
    '''
    def __init__(self):
        c.log('debug', 'Users init')

        self.data = {}
        self.path = os.path.join(c.cfg('backup-dir'), 'users')

        # Create directory
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

        # Loading local data from storage
        self.load()

    def store(self):
        c.log('debug', 'Store users (%i)' % len(self.data))
        for i in self.data:
            with codecs.open(os.path.join(self.path, i + '.json'), "w", "utf-8") as outfile:
                json.dump(self.data[i], outfile, indent=1, ensure_ascii=False)

    def load(self):
        files = [ f for f in os.listdir(self.path) if f.endswith('.json') ]
        c.log('info', 'Loading users (%i)' % len(files))
        for f in files:
            filename = os.path.join(self.path, f)
            data = json.load(open(filename))
            self.data[data['id']] = data

    def requestFriends(self, user_id):
        c.log('debug', 'Requesting friends for %s' % user_id)
        if user_id not in self.data:
            requestUsers([user_id])

        friends = [ str(f) for f in api.request('friends.get', {'user_id': user_id}) ]

        if 'friends' not in self.data[user_id]:
            self.data[user_id]['friends'] = { long(time.time()): friends[:] }
        else:
            user_friends = self.data[user_id]['friends']
            if len(set(user_friends[max(user_friends)]) & set(friends)) != len(friends):
                user_friends[long(time.time())] = friends[:]

        return friends

    def requestUsers(self, user_ids):
        c.log('debug', 'Requesting users (%i)' % len(user_ids))
        while len(user_ids) > 0:
            data = api.request('users.get', {'user_ids': ','.join(user_ids[0:1000]), 'fields': 'photo_max_orig'})
            del user_ids[0:1000]
            for user in data:
                c.log('debug', '  %i %s %s' % (user['id'], user['first_name'], user['last_name']))
                user['id'] = user.pop('id')
                self.addUser(user)
            if len(user_ids) > 0:
                c.log('debug', '  left %i' % len(user_ids))

    def addUser(self, newdata):
        # Add new data to user id if latest is different
        newdata_id = str(newdata.pop('id'))
        if newdata_id not in self.data:
            c.log('debug', 'Adding new user %s' % newdata_id)
            self.data[newdata_id] = {
                'id': newdata_id,
                'data': { long(time.time()): newdata }
            }
        else:
            user_data = self.data[newdata_id]['data']
            if len(set(user_data[max(user_data)].items()) & set(newdata.items())) != len(newdata):
                c.log('debug', 'Adding new data for user %s' % newdata_id)
                user_data[long(time.time())] = newdata

    def getUser(self, user_id):
        if user_id not in self.data:
            self.requestUsers([user_id])
        user = self.data[user_id]
        return {
            'id':       user_id,
            'data': user['data'][max(user['data'])]
        }


class Backup:
    '''
    Basic init class
    '''
    def __init__(self):
        c.log('debug', 'Backup init')

        self.path = c.cfg('backup-dir')

        # Create directory
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

    def store(self):
        c.log('debug', 'Store data')

        users.store()
        dialogs.store()
        chats.store()

    def process(self):
        c.log('debug', 'Start processing')

        # Get current user info
        users.requestUsers([api.getUserId()])
        # Get friends of current user & load users
        users.requestUsers(users.requestFriends(api.getUserId()))

        # Get dialogs info
        dialogs.requestDialogs()

        self.store()

api = Api()

media = Media()
users = Users()
dialogs = Dialogs()
chats = Chats()

backup = Backup()
backup.process()

c.log('info', 'DONE')
