#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Chats

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Chats management
Required:    python2.7
'''

import Common as c

from Database import Database

import Api
import Messages
from Users import S as Users

class Chats(Database):
    def requestChatInfo(self, chat_id):
        if chat_id not in self.data:
            self.data[chat_id] = {
                'id':  chat_id,
                'log': []
            }
        data = Api.request('messages.getChat', {'chat_id': chat_id})
        if len(data['users']) > 0:
            Users.requestUsers([ str(u) for u in data['users'] ])
        self.data[chat_id]['data'] = data

    def requestChatMessages(self, chat_id):
        chat = self.getChat(chat_id)
        c.log('info', 'Requesting chat messages for chat %s "%s"' % (chat_id, chat['data']['title']))

        Messages.requestMessages({'chat_id': chat_id}, self.data[chat_id])

    def getChat(self, chat_id):
        if chat_id not in self.data:
            self.requestChatInfo(chat_id)
        return self.data[chat_id]

S = Chats()
