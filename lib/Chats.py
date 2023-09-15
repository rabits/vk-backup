#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Chats

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Chats management
Required:    python3.5
'''

from . import Common as c

from .Database import Database

from . import Api
from . import Messages
from .Users import S as Users

class Chats(Database):
    def requestChatInfo(self, chat_id):
        if str(chat_id) not in self.data:
            self.data[str(chat_id)] = {
                'id':  chat_id,
                'log': []
            }
        data = Api.request('messages.getChat', {'chat_id': chat_id})
        if data == None:
            return
        if len(data['users']) > 0:
            Users.requestUsers(data['users'])
        self.data[str(chat_id)]['data'] = data

    def requestChatMessages(self, chat_id):
        chat = self.getChat(chat_id)
        c.log('info', 'Requesting chat messages for chat %s "%s"' % (chat_id, chat['data']['title']))

        Messages.requestMessages({'chat_id': chat_id}, self.data[str(chat_id)])

    def getChat(self, chat_id):
        if str(chat_id) not in self.data:
            self.requestChatInfo(chat_id)
        return self.data[str(chat_id)]

S = Chats()
