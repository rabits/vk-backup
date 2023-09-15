#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup ChatsUI

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Chats UI API management
Required:    python3.5
'''

from . import Common as c

from .Database import Database

from . import UIApi
from . import MessagesUI
from .Users import S as Users

class Chats(Database):
    def requestChatInfo(self, chat_id):
        real_chat_id = chat_id - 2000000000 if chat_id > 2000000000 else chat_id
        if str(real_chat_id) not in self.data:
            self.data[str(real_chat_id)] = {
                'id':  chat_id,
                'log': []
            }

        # Getting additional data about chat
        # payload:
        #   - <ignore>
        #   - - name: <title:str>
        #       memberIds: <users:list:int>
        #       ownerId: <admin_id:int>
        chat = UIApi.request('al_im.php', {
            "_smt": "im:1",
            "act": "a_start",
            "al": "1",
            "block": "true",
            "gid": "0",
            "history": "0", # We don't need history here, just chat data
            "im_v": "3",
            "msgid": "0",
            "peer": str(chat_id),
            "prevpeer": "0",
        })
        if chat == None:
            return
        if not isinstance(chat[1][0], dict):
            c.log('error', 'VK returned malformed payload, please make sure provided curl session token is not expired: %s' % (chat,))
            return
        data = {
            'id': chat_id,
            'admin_id': chat[1][0].get('ownerId', 0),
            'title': chat[1][0].get('name', ''),
            'type': 'chat',
            'users': chat[1][0].get('memberIds', []) or [],
        }
        if len(data['users']) > 0:
            Users.requestUsers(data['users'])
        self.data[str(real_chat_id)]['data'] = data

        return self.data[str(real_chat_id)]

    def requestChatMessages(self, chat_id):
        chat = self.getChat(chat_id)
        if chat:
            c.log('info', 'Requesting chat messages for chat %s "%s"' % (chat_id, chat['data']['title']))
        else:
            c.log('info', 'Requesting chat messages for chat %s' % (chat_id,))

        real_chat_id = chat_id - 2000000000 if chat_id > 2000000000 else chat_id
        MessagesUI.requestMessages(chat_id, self.data[str(real_chat_id)])

    def getChat(self, chat_id):
        real_chat_id = chat_id - 2000000000 if chat_id > 2000000000 else chat_id
        if str(real_chat_id) not in self.data:
            self.requestChatInfo(chat_id)
        return self.data[str(real_chat_id)]

S = Chats()
