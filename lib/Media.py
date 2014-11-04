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
import threading
from Queue import Queue

import Common as c

from Database import Database

import Api

class Media(Database):
    class Downloader(threading.Thread):
        def __init__(self, queue, report):
            threading.Thread.__init__(self)
            self.queue = queue
            self.report = report
            self.waiting = True
            self._stop = threading.Event()

        def run(self):
            c.log('debug', 'Downloader thread started')
            while not self._stop.isSet():
                if not self.queue.empty():
                    self.waiting = False
                    url = self.queue.get()
                    response = url.download()
                    if response == False and url.tried < 3:
                        self.queue.put(url)
                    elif response == False and url.tried == 3:
                        self.report['failure'].append(url)
                    elif response == True:
                        self.report['success'].append(url)
                    self.queue.task_done()
                else:
                    self.waiting = True
                    time.sleep(2)
            c.log('debug', 'Downloader thread stopped')

        def stop(self):
            self._stop.set()

    class Download(object):
        def __init__(self, url, destination):
            self.url = url
            self.destination = destination
            self.tried = 0
            self.success = False
            self.error = None

        def download(self):
            if self.tried > 0:
                time.sleep(self.tried * 2)
            self.tried += 1
            try:
                directory = os.path.dirname(self.destination)
                if not os.path.isdir(directory):
                    os.makedirs(directory)

                u = urllib2.urlopen(self.url, None, 30)
                with open(self.destination, 'wb') as outfile:
                    # TODO: limit by size
                    size = int(u.info().getheaders('Content-Length')[0])
                    while True:
                        b = u.read(8192)
                        if not b:
                            break
                        outfile.write(b)

                self.success = True

            except Exception as e:
                self.error = e

            return self.success

    def stopDownloads(self):
        c.log('debug', 'Stopping download threads (%i)' % len(self.threads))
        for i in self.threads:
            i.stop()

    def __init__(self):
        Database.__init__(self)

        self.total_downloads = 0
        self.queue = Queue(0)
        self.report = {'success':[], 'failure':[]}
        self.threads = []

        for i in range(c.cfg('download-threads')):
            thread = self.Downloader(self.queue, self.report)
            thread.start()
            self.threads.append(thread)
        if self.queue.qsize() > 0:
            self.queue.join()

    def store(self):
        c.log('info', 'Waiting downloads complete: ~%i...' % self.queue.qsize())
        while not self.queue.empty():
            c.log('info', '[%s] %i left' % (''.join([str(int(not t.waiting)) for t in self.threads]), self.queue.qsize()))
            time.sleep(5)

        self.stopDownloads()

        c.log('info', 'Downloaded %i of %i' % (len(self.report['success']), self.total_downloads))
        if len(self.report['failure']) > 0:
            c.log('warning', '  failed: %i' % len(self.report['failure']))
            for url in self.report['failure']:
                c.log('debug', '    %s' % url.url)

        Database.store(self)

    def loadAttachments(self, data):
        attachments = []
        if 'attachments' in data:
            attachments.extend(data['attachments'])
        if 'attachment' in data:
            attachments.append(data['attachment'])
        if 'copy_history' in data:
            for subdata in data['copy_history']:
                self.loadAttachments(subdata)
        for attach in attachments:
            c.log('debug', 'Processing %s' % attach['type'])
            funcname = 'process' + attach['type'].title()
            if funcname in dir(self):
                getattr(self, funcname)(attach[attach['type']])
            else:
                c.log('error', '  media processing function "Media.%s" is not implemented' % funcname)
                c.log('debug', str(attach))

    def addDownload(self, url, path = None):
        if url == '':
            c.log('warning', 'Skipping empty url')
            return path

        if path == None:
            path = os.path.join(self.path, 'storage') + urlparse(url).path

        if os.path.isfile(path):
            c.log('debug', 'Skipping, file %s already exists' % path)
            return path

        c.log('debug', 'Adding media to queue "%s"' % url)
        self.total_downloads += 1
        self.queue.put(self.Download(url, path))

        return path

    def preprocess(self, data, data_type):
        # TODO: limit by type
        mydata = data.copy()
        data.clear()
        data['id'] = mydata['id']
        if 'owner_id' in mydata:
            path = os.path.join(data_type, str(mydata['owner_id']), str(mydata['id']))
            data['owner_id'] = mydata['owner_id']
        else:
            path = os.path.join(data_type, str(mydata['id']))

        if path in self.data:
            return path

        self.data[path] = mydata

        return path

    def requestComments(self, data, data_type, owner_id):
        if str(owner_id) != Api.getUserId():
            return

        c.log('debug', 'Requesting comments for %s %i' % (data_type, data['id']))

        if data_type == 'photo':
            api_method = 'photos.getComments'
            api_id_name = 'photo_id'
        elif data_type == 'video':
            api_method = 'video.getComments'
            api_id_name = 'video_id'
        elif data_type == 'wall':
            api_method = 'wall.getComments'
            api_id_name = 'post_id'
        else:
            c.log('warning', 'Unable to request comments for %s %i - not implemented' % (data_type, data['id']))
            return

        if 'comments' not in data:
            data['comments'] = {}
        if not isinstance(data['comments'], dict):
            data['comments'] = {}

        req_data = {'owner_id': int(owner_id), api_id_name: int(data['id']), 'count': 100, 'offset': 0}

        while True:
            subdata = Api.request(api_method, req_data)
            if subdata == None:
                return
            count = subdata['count']
            subdata = subdata['items']
            for d in subdata:
                data['comments'][str(d['date'])] = d
                self.loadAttachments(data['comments'][str(d['date'])])

            req_data['offset'] += 100
            if req_data['offset'] >= count:
                break

    def processPhoto(self, data):
        c.log('debug', 'Processing photo media')
        path = self.preprocess(data, 'photo')
        if 'localpath' not in self.data[path]:
            url = None
            if 'url' in self.data[path]:
                url = self.data[path]['url']
            size = 0
            for key in self.data[path].keys():
                if key.startswith('photo_'):
                    if int(key.split('_')[1]) > size:
                        size = int(key.split('_')[1])
                        url = self.data[path].pop(key, None)
                    self.data[path].pop(key, None)

            if url == None:
                c.log('warning', 'Valid url not found in %s' % str(self.data[path]))
                return

            self.data[path]['url'] = url
            self.data[path]['localpath'] = self.addDownload(self.data[path]['url'])
        self.requestComments(self.data[path], 'photo', self.data[path]['owner_id'])

    def processDoc(self, data):
        c.log('debug', 'Processing doc media')
        path = self.preprocess(data, 'doc')
        if 'localpath' not in self.data[path]:
            self.data[path]['localpath'] = self.addDownload(self.data[path]['url'])

    def processAudio(self, data):
        c.log('debug', 'Processing audio media')
        path = self.preprocess(data, 'audio')
        if 'localpath' not in self.data[path]:
            self.data[path]['localpath'] = self.addDownload(self.data[path]['url'])

    def processWall(self, data):
        c.log('debug', 'Processing wall media')
        data['comments'].pop('count', None)
        data['comments'].pop('can_post', None)
        self.requestComments(data, 'wall', data['from_id'])
        self.loadAttachments(data)

    def processGeo(self, data):
        self.preprocess(data, 'geo')
        c.log('debug', 'Skipping geo media - no data to download')

    def processVideo(self, data):
        path = self.preprocess(data, 'video')
        self.requestComments(self.data[path], 'video', self.data[path]['owner_id'])
        c.log('debug', 'Skipping video media - size of the file is too big')

    def processSticker(self, data):
        self.preprocess(data, 'sticker')
        c.log('debug', 'Skipping sticker media - idiotizm')

    def processLink(self, data):
        c.log('debug', 'Skipping link media - no data to download')

    def processPoll(self, data):
        self.preprocess(data, 'poll')
        c.log('debug', 'Skipping poll media - no data to download')

    def processNote(self, data):
        self.preprocess(data, 'note')
        c.log('debug', 'Skipping note media - no data to download')

    def processPresent(self, data):
        self.preprocess(data, 'present')
        c.log('debug', 'Skipping present media - stupid present')

S = Media()
