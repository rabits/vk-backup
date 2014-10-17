#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Media

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Media download
Required:    python2.7
'''

import time, urllib2, os
from urlparse import urlparse

import Common as c

class Media:
    def __init__(self):
        c.log('debug', 'Init Media')

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

S = Media()
