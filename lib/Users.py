#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Users

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Contains info about known users
Required:    python2.7
'''

import time

import Common as c

import Api
from Database import Database

class Users(Database):
    def requestFriends(self, user_id):
        c.log('debug', 'Requesting friends for %s' % user_id)
        if user_id not in self.data:
            requestUsers([user_id])

        friends = [ str(f) for f in Api.request('friends.get', {'user_id': user_id})['items'] ]

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
            data = Api.request('users.get', {'user_ids': ','.join(user_ids[0:1000]), 'fields': 'photo_max_orig'})
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

S = Users()
