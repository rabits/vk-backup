#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup MessagesUI

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Messages UI API management
Required:    python3.5
'''

from . import Common as c

from .Database import Database

from . import UIApi
from . import MessagesUI
from .Users import S as Users
from .ChatsUI import S as ChatsUI

class Dialogs(Database):
    def requestDialogs(self):
        c.log('debug', 'Requesting dialogs through UI API')

        # Getting the dialogs data
        # Processed format:
        # payload:
        #   - <ignore>
        #   - - - <user_id:int>
        #       - <user_name:str>
        dialogs = UIApi.request('al_im.php', {
            "act":"a_dialogs_preload",
            "al":"1",
            "gid":"0",
            "im_v":"3",
            "rs":"",
        })
        if dialogs == None:
            c.log('error', 'No dialogs returned, please make sure provided curl session token is not expired: %s' % (dialogs,))
            return

        if not isinstance(dialogs[1][0], list):
            c.log('error', 'VK returned malformed payload, please make sure provided curl session token is not expired: %s' % (dialogs,))
            return

        for d in dialogs[1][0]:
            did = d[0]
            dname = d[1]
            c.log('debug', 'Processing messages: %s %s' % (did, dname))

            if did > 2000000000:
                ChatsUI.requestChatMessages(did)
                ChatsUI.store([did - 2000000000])
            else:
                self.requestMessages(did)
                self.store([did])

    def requestMessages(self, dialog_id):
        if dialog_id > 0:
            user = Users.getUser(dialog_id)
            c.log('info', 'Requesting messages for user: %s %s %s' % (dialog_id, user['data'].get('first_name'), user['data'].get('last_name')))
        else:
            c.log('info', 'Requesting messages for group: %s' % (dialog_id,))

        if str(dialog_id) not in self.data:
            self.data[str(dialog_id)] = {
                'id' :  dialog_id,
                'log' : []
            }

        MessagesUI.requestMessages(dialog_id, self.data[str(dialog_id)])

    def getMessages(self, dialog_id):
        if str(dialog_id) not in self.data:
            self.requestMessages(dialog_id)
        return self.data[str(dialog_id)]

S = Dialogs()
