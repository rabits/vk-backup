#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Messages UI

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Module provided common message requests through UI API
Required:    python3.5
'''

from . import Common as c

from . import Api
from . import UIApi
from .Media import S as Media

from html.parser import HTMLParser

# This class will find the needed attribute inside a block with specific attribute=value
# The result will be stored in found_data as [(<to_find:dict>, <tag>, <attr_value>)]
class BlockDataHTMLParser(HTMLParser):
    def __init__(self, to_find, to_get):
        HTMLParser.__init__(self)

        # What attribute and value to find
        self.to_find = dict( (k, str(v)) for k, v in to_find.items() )

        # Which attributes contains data to harvest
        self.to_get = to_get

        # Contains data to track the insides of the block
        self.in_block = None
        self.in_block_tag = None
        self.in_block_counter = 0

        self.found_data = []

    def _checkFindAttrs(self, tag, attrs):
        for attr, value in self.to_find.items():
            if attr in attrs and attrs[attr] == value:
                c.log('debug', 'Found starting block tag: %s %s' % (tag, attrs))
                self.in_block = {attr: value}
                self.in_block_tag = tag

    def _checkGetAttrs(self, attrs):
        for attr in self.to_get:
            if attr in attrs:
                c.log('debug', 'Found needed data attr: %s %s' % (attr, attrs[attr]))
                self.found_data.append((self.in_block, self.in_block_tag, attrs[attr]))

    def handle_starttag(self, tag, attrs):
        attrs = dict((name.lower(), value) for name, value in attrs)
        if self.in_block:
            self.in_block_counter += 1
        else:
            self._checkFindAttrs(tag, attrs)

        if self.in_block:
            self._checkGetAttrs(attrs)

    def handle_startendtag(self, tag, attrs):
        attrs = dict((name.lower(), value) for name, value in attrs)
        # TODO: In theory it could be the block start/end tag, so need to start block and finish it
        if self.in_block:
            self._checkGetAttrs(attrs)

    def handle_endtag(self, tag):
        if self.in_block:
            # In theory we need to validate tag as well - but you know those html devs...
            if self.in_block_counter == 0:
                c.log('debug', 'Found the end tag of the block: %s' % (tag,))
                self.in_block = None
                self.in_block_tag = None

            self.in_block_counter -= 1

# Getting messages for the user id
# is received in batches starting from last batch
# Processed format:
# payload:
#   - <ignore>
#   - - <html:str>
#     - <id:str>:
#         - <msg_id:int>
#         - <bitmap> - second bit is out
#         - <user_id:int>
#         - <unixtime:int>
#         - <msg:str>
#         - attach<int>_type: <attach_n_type:str> (ex: "photo", "video", "audio", "doc")
#           attach<int>: <attach_n_owner_id:str> (ex: "-192626588_456239023", "-192626588_457241236")
def requestMessages(user_id, msgs_data):
    # We don't have to process everything - just till the last downloaded message ID
    stop_msg_id = msgs_data['log'][-1]['id'] if len(msgs_data['log']) > 0 else None

    new_user_messages = []

    # Continue to request messages until the end
    continue_process = True
    while continue_process:
        msgs = UIApi.request('al_im.php', {
            "_smt": "im:3",
            "act": "a_history",
            "al": "1",
            "gid": "0",
            "im_v": "3",
            "offset": str(len(new_user_messages)),
            "peer": str(user_id),
            "toend": "0",
            "whole": "0",
        })

        if not msgs or not isinstance(msgs[1][1], dict):
            c.log('warning', 'Messages of the user are not in dict format, skipping: %s' % (msgs,))
            break

        # Sorting messages in reverse order to process the latest first
        msgs_list = list(msgs[1][1].values())

        if len(msgs_list) < 1:
            # There is no messages available
            break

        for msg in msgs_list:
            d = processMessage(msg, msgs[1][0])
            if d['id'] == stop_msg_id:
                # We reached last loaded message, so no need to proceed further
                continue_process = False
                break
            new_user_messages.insert(0, d)

        c.log('debug', '  loaded %i' % (len(new_user_messages,)))

    msgs_data['log'].extend(new_user_messages)
    c.log('info', '  total loaded %i, stored %i' % (len(new_user_messages), len(msgs_data['log'])))

# Processing message from VK JSON
def processMessage(msg, html):
    # msg[1] contains bitmap where second bit is outgoing msg (1 if current user sent, 0 if incoming from remote user)
    out = (msg[1] & 0b10) and 1 # Will output 0 or 1
    # if it's chat - user id will be in msg[5], otherwise if  out == 1 then it's current user, otherwise msg[2]
    from_id = msg[5].get('from') or (Api.getUserId() if out == 1 else msg[2])
    d = {
        "id": msg[0],
        "from_id": int(from_id),
        "date": msg[3],
        "body": msg[4],
        "out": out,
    }

    # Processing attachments
    attachments = {}
    # First - looking for all the data and place it in one
    for key, val in msg[5].items():
        if key.startswith('attach'):
            if key == 'attach_count':
                continue
            att_index = int(key[6:].split('_', 1)[0])
            if att_index not in attachments:
                attachments[att_index] = {'data':{}}

            if key.endswith('_type'):
                attachments[att_index]['type'] = val
            else:
                dkey = key.split('_', 1)
                if len(dkey) < 2:
                    attachments[att_index]['data'][''] = val
                else:
                    attachments[att_index]['data'][dkey[1]] = val

    if len(attachments) > 0:
        d['attachments'] = list(dict(sorted(attachments.items())).values())

        # Processing attachments to properly format them and download if needed
        for ind, att in enumerate(d['attachments']):
            d['attachments'][ind] = processAttachment(att, d['id'], html)

        # We need to process attachments of the message and download available media
        Media.loadAttachments(d)

    return d

# Processing normalized attachment in format:
# type: <str>
# <type>:
#   id: <int>
#   owner_id: <int>
def processAttachment(att, msg_id, html):
    c.log('debug', 'Processing UI attachment for message id: %s' % (msg_id,))
    try:
        # Most of the attachments are not send directly in the response - because UI API is returning
        # html to describe the messages, some of the important vars (forwarded messages for example)
        # are containing only in HTML, so it's kind of downside of using UI API... We need to receive
        # the important data via regular API call and store it in the attachment data.
        if att['type'] in ('photo', 'doc', 'audio', 'video', 'audio_playlist', 'story', 'article', 'wall'):
            (att_own, att_id) = att['data'][''].split('_', 1)
            suffix = ''
            if '_' in att_id: # Some audio id's could look like "1422450_456239108_23dd849dd82775b33e"
                (att_id, suffix) = att_id.split('_', 1)
            att[att['type']] = {
                'id': int(att_id),
                'owner_id': int(att_own),
            }
            if suffix != '':
                att[att['type']]['suffix'] = suffix

            if att['type'] == 'photo':
                photo_data = getUIPhotoData(att['data'][''], msg_id)
                if photo_data:
                    att[att['type']] = photo_data
                else:
                    c.log('warning', 'Received photo data contains no photo record: %s : %s' % (UIApi.dumpData(photo_data), att))
            elif att['type'] == 'wall':
                wall_data = Api.request('wall.getById', {'posts': att['data']['']})
                if wall_data and len(wall_data) == 1:
                    att[att['type']] = wall_data[0]
                else:
                    c.log('warning', 'Received wall data contains no wall record: %s : %s' % (UIApi.dumpData(wall_data), att))
            elif att['type'] == 'story':
                story_data = Api.request('stories.getById', {'stories': att['data']['']})
                if story_data and len(story_data) == 1:
                    att[att['type']] = story_data[0]
                else:
                    c.log('warning', 'Received story data contains no story record: %s : %s' % (UIApi.dumpData(story_data), att))
            elif att['type'] == 'doc':
                if 'kind' in att['data']:
                    if att['data']['kind'] == 'audiomsg':
                        # Locating the mp3 data of audio msg in the provided html
                        parser = BlockDataHTMLParser({'data-msgid': msg_id}, ['data-mp3', 'data-ogg'])
                        parser.feed(html)
                        parser.close()
                        if len(parser.found_data) > 0:
                            att[att['type']]['url'] = parser.found_data[0][2]
                    else:
                        c.log('warning', 'Unable to find UI doc kind processor to get URL for : %s : %s' % (att, html))
                else:
                    # Default doc have just <a href="/doc[doc_fullid]">
                    parser = BlockDataHTMLParser({'data-msgid': msg_id}, ['href'])
                    parser.feed(html)
                    parser.close()
                    for d in parser.found_data:
                        if d[2].startswith('/doc'+att['data']['']):
                            att[att['type']]['url'] = 'https://vk.com'+d[2]
                            break
                if 'url' not in att[att['type']]:
                    c.log('warning', 'Unable to find doc URL for : %s' % (att,))
            elif att['type'] == 'audio':
                # Audio a bit hard to download, so just getting the additional info from data-audio
                # Looks like: '[115130048,48899827,"","Мать твою так","Трупный яд",198,0,0,"",0,2,"im","[]","ee7c995bc3ff6379c7\/\/aea86bbdf7be02f3ac\/\/\/fb6512a8793e3443ab\/","",{"duration":198,"content_id":"48899827_115130048","puid22":11,"account_age_type":3,"_SITEID":276,"vk_id":10170169,"ver":251116},"","","",false,"c86ec74eU35nMQdVLYSxwyMDBdn8HvHsyMFLeXCULiReSHC1eDVfdwa2vpxZLBNYeAI",0,0,true,"f0bbcf1e510c4358f1",false,"",false]'
                parser = BlockDataHTMLParser({'data-msgid': msg_id}, ['data-audio'])
                parser.feed(html)
                parser.close()
                for d in parser.found_data:
                    if d[2].startswith('[%s,%s,' % (att[att['type']]['id'], att[att['type']]['owner_id'])):
                        att[att['type']]['info_str'] = d[2]
                        break
        elif att['type'] == 'link':
            att[att['type']] = {
                'description': att['data'].get('desc'),
                'image_src': att['data'].get('photo'),
                'title': att['data'].get('title'),
                'url': att['data']['url'],
            }
        elif att['type'] == 'call':
            att[att['type']] = {
                'id': att['data'].get(''),
                'initiator_id': int(att['data'].get('call_initiator_id', '0')),
                'receiver_id': int(att['data'].get('call_receiver_id', '0')),
                'state': att['data'].get('call_state'),
                'video': att['data'].get('call_video'),
            }
        elif att['type'] == 'sticker':
            att[att['type']] = {
                'id': int(att['data']['']),
            }
            if 'product_id' in att['data']:
                att[att['type']]['product_id'] = int(att['data']['product_id'])
            if 'kind' in att['data']:
                att[att['type']]['kind'] = att['data']['kind']
        elif att['type'] == 'gift':
            att[att['type']] = {
                'id': int(att['data']['']),
            }
        elif att['type'] == 'poll':
            id_list = att['data'][''].split('_', 1)
            if len(id_list) < 2:
                att[att['type']] = {
                    'id': int(id_list[0]),
                }
            else:
                att[att['type']] = {
                    'id': int(id_list[1]),
                    'owner_id': int(id_list[0]),
                }
        elif att['type'] == 'audio_playlist':
            att[att['type']] = {
                'id': int(att['data']['']),
            }
        else:
            c.log('error', 'Unable to find attachment processor for:')
            c.log('error', '%s' % (UIApi.dumpData(att),))
    except Exception as e:
        c.log('error', 'Exception happened during processing of the next attachment:')
        c.log('error', '%s' % (UIApi.dumpData(att),))
        raise e

    del att['data']

    return att

# Getting photo info through UI for the photo - regular API will not give access usually
# Processed format:
# payload:
#   - <ignore>
#   - - <ignore>
#     - <ignore>
#     - <ignore>
#     - - id: <photo_fullid:str>
#         <type>_src: <url:str>
#         <type>_:
#           - <url:str>
#           - <width:int>
#           - <height:int>
#       ...
def getUIPhotoData(photo_fullid, msg_id):
    c.log('debug', 'Getting UI photo data for %s of message %s' % (photo_fullid, msg_id))

    photos = UIApi.request('al_photos.php', {
        '_smt': 'im:6',
        'act': 'show',
        'al': '1',
        'dmcah': '',
        'gid': '0',
        'list': 'mail'+str(msg_id), # Requires the message id it was attached to
        'module': 'im',
        'photo': str(photo_fullid),
    })

    if not photos or len(photos[1]) < 4 or not isinstance(photos[1][3], list):
        c.log('warning', 'Requested photos returned in bad format: %s' % (photos,))
        return {}

    photo = None
    # Looking in the list of returned photos the one we need - it can return a bunch of them
    for p in photos[1][3]:
        if p['id'] == photo_fullid:
            photo = p
            break

    if not photo:
        c.log('error', 'Requested photo is not present in the returned data: %s' % (photos,))
        return {}

    # Using UI API to reproduce the regular API data format like:
    #  id: 162282203
    #  owner_id: 98371283
    #  album_id: -2
    #  date: 1301912968
    #  post_id: 1012
    #  text: ''
    #  web_view_token: '0628ebc11d1eb2dc01'
    #  sizes:
    #    - height: 0
    #      type: s
    #      width: 0
    #      url: https://sun2-12.userapi.com/c10000/u98371283/-6/s_4992d41b.jpg
    #    ...
    pid = photo_fullid.split('_', 2)
    out = {
        'id': int(pid[1]),
        'owner_id': int(pid[0]),
        # TODO: Parse date of photo
        'text': photo['desc'],
        'sizes': [],
    }
    if len(pid) > 2:
        out['suffix'] = pid[2]
    for t in Media.getPhotoTypes():
        attr = (t+'_')
        if attr in photo:
            if len(photo[attr]) < 3:
                c.log('warning', 'Photo size definition lacks of width/height data: %s' % (photo,))
            out['sizes'].append({
                # Sometimes photo[attr][0] could contain partial url (only path of it, so using <t>_src instead)
                'url': photo[attr][0] if len(photo[attr][0]) > len(photo[attr+'src']) else photo[attr+'src'],
                'width': photo[attr][1] if len(photo[attr]) > 1 else 0,
                'height': photo[attr][2] if len(photo[attr]) > 2 else 0,
            })
    return out
