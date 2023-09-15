#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Users

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Contains info about known users
Required:    python3.5
'''

import time

from . import Common as c

from . import Api
from .Database import Database

from .Media import S as Media

class Users(Database):
    def requestUsers(self, user_ids):
        proc_user_ids = [ str(u) for u in user_ids ]
        c.log('debug', 'Requesting users (%i)' % len(user_ids))
        while len(proc_user_ids) > 0:
            data = Api.request('users.get', {'user_ids': ','.join(proc_user_ids[0:1000]), 'fields': ''})
            if data == None:
                return
            del proc_user_ids[0:1000]
            for user in data:
                c.log('debug', '  %i %s %s' % (user['id'], user['first_name'], user['last_name']))
                self.addUser(user)
            if len(proc_user_ids) > 0:
                c.log('debug', '  left %i' % len(proc_user_ids))

    def addUser(self, newdata):
        # Add new data to user id if latest is different
        newdata_id = str(newdata.pop('id'))
        if newdata_id not in self.data:
            c.log('debug', 'Adding new user %s' % newdata_id)
            self.data[newdata_id] = {
                'id': newdata_id,
                'data': { str(int(time.time())): newdata },
            }
        else:
            if self.data[newdata_id]['updated'] > Api.getStartTime():
                return
            user_data = self.data[newdata_id]['data']
            if len(set(user_data[str(max( int(k) for k in user_data ))].items()) & set(newdata.items())) != len(newdata):
                c.log('debug', 'Adding new data for user %s' % newdata_id)
                user_data[str(int(time.time()))] = newdata

        self.requestProfilePhotos(newdata_id)
        self.data[newdata_id]['updated'] = int(time.time())

    def requestProfilePhotos(self, user_id):
        c.log('debug', 'Requesting profile photos')
        if 'photos' not in self.data[str(user_id)]:
            self.data[str(user_id)]['photos'] = {}
        req_data = {'owner_id': int(user_id), 'count': 1000, 'offset': 0}

        while True:
            data = Api.request('photos.getProfile', req_data)
            if data == None:
                return
            count = data['count']
            data = data['items']
            for d in data:
                self.data[str(user_id)]['photos'][str(d['date'])] = d
                Media.processPhoto(self.data[str(user_id)]['photos'][str(d['date'])])

            req_data['offset'] += 1000
            if req_data['offset'] >= count:
                break

    def requestUserPhotos(self, user_id):
        c.log('info', 'Requesting user photos')
        if 'user_photos' not in self.data[str(user_id)]:
            self.data[str(user_id)]['user_photos'] = {}
        req_data = {'user_id': int(user_id), 'count': 1000, 'offset': 0}

        while True:
            data = Api.request('photos.getUserPhotos', req_data)
            if data == None:
                return
            count = data['count']
            data = data['items']
            for d in data:
                self.data[str(user_id)]['user_photos'][str(d['date'])] = d
                Media.processPhoto(self.data[str(user_id)]['user_photos'][str(d['date'])])

            req_data['offset'] += 1000
            if req_data['offset'] >= count:
                break

    def requestBlog(self, user_id):
        c.log('info', 'Requesting user blog')
        if 'blog' not in self.data[str(user_id)]:
            self.data[str(user_id)]['blog'] = {}
        req_data = {'owner_id': int(user_id), 'count': 100, 'offset': 0}

        while True:
            data = Api.request('wall.get', req_data)
            if data == None:
                return
            count = data['count']
            data = data['items']
            for d in data:
                self.data[str(user_id)]['blog'][str(d['date'])] = d
                Media.processWall(self.data[str(user_id)]['blog'][str(d['date'])])

            req_data['offset'] += 100
            if req_data['offset'] >= count:
                break

    def requestFriends(self, user_id):
        c.log('info', 'Requesting friends')
        if str(user_id) not in self.data:
            self.data[str(user_id)] = {'id': int(user_id)}

        data = Api.request('friends.get', {'user_id': int(user_id)})
        if data == None:
            return
        friends = [ f for f in data['items'] ]

        if 'friends' not in self.data[str(user_id)]:
            self.data[str(user_id)]['friends'] = { int(time.time()): friends[:] }
        else:
            user_friends = self.data[str(user_id)]['friends']
            if len(set(user_friends[str(max( int(k) for k in user_friends ))]) & set(friends)) != len(friends):
                user_friends[int(time.time())] = friends[:]

        return friends

    def getUser(self, user_id):
        if str(user_id) not in self.data:
            self.requestUsers([user_id])
        if str(user_id) in self.data:
            user = self.data[str(user_id)]
            try:
                return {
                    'id': int(user_id),
                    'data': user['data'][str(max( int(k) for k in user['data'] ))],
                }
            except Exception as e:
                print(user, [int(k) for k in user['data']], max( int(k) for k in user['data'] ))
                raise e
        else:
            c.log('warning', 'Unable to get user: %s' % (user_id,))
            return {
                'id': int(user_id),
                'data': {},
            }

S = Users()
