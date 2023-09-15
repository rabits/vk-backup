#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Messages

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Module provided common message requests
Required:    python3.5
'''

from . import Common as c

from . import Api
from .Media import S as Media

def requestMessages(request, msgs_data):
    request['count'] = 200
    request['offset'] = -200
    if len(msgs_data['log']) == 0:
        request['rev'] = 1
        request['offset'] = 0
    else:
        request['start_message_id'] = msgs_data['log'][-1]['id']

    while True:
        data = Api.request('messages.getHistory', request)
        if data == None:
            return
        count = data['count']
        data = data['items']

        if len(data) == 0:
            c.log('info', '  no new messages %i (%i)' % (len(msgs_data['log']), count))
            break

        # Switch to get history by message id
        if 'start_message_id' not in request:
            request['offset'] = -200
            request.pop('rev', None)
        else:
            data.reverse()

        processMessages(data)
        msgs_data['log'].extend(data)

        request['start_message_id'] = data[-1]['id']
        c.log('info', '  loaded %i, stored %i (%i)' % (len(data), len(msgs_data['log']), count))
        if len(data) < 200:
            c.log('info', '  done')
            break

def processMessages(data):
    for d in data:
        d.pop('user_id', None)
        d.pop('read_state', None)
        d.pop('chat_id', None)
        Media.loadAttachments(d)
        if 'fwd_messages' in d:
            processMessages(d['fwd_messages'])
