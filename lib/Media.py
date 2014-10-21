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
        c.log('debug', 'Stopping download threads')
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
            self.loadAttachments(data['copy_history'])
        for attach in attachments:
            c.log('debug', 'Processing %s' % attach['type'])
            funcname = 'process' + attach['type'].title()
            if funcname in dir(self):
                getattr(self, funcname)(attach[attach['type']])
            else:
                c.log('error', '  unable to find attachment processing function "Media.%s"' % funcname)
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
            return None
        self.data[path] = mydata

        return path

    def processPhoto(self, data):
        path = self.preprocess(data, 'photo')
        if path != None:
            url = None
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

    def processDoc(self, data):
        path = self.preprocess(data, 'doc')
        if path != None:
            self.data[path]['localpath'] = self.addDownload(self.data[path]['url'])

    def processAudio(self, data):
        path = self.preprocess(data, 'audio')
        if path != None:
            self.data[path]['localpath'] = self.addDownload(self.data[path]['url'])

    def processWall(self, data):
        c.log('debug', 'Processing wall attachments')
        self.loadAttachments(data)

    def processGeo(self, data):
        self.preprocess(data, 'geo')
        c.log('debug', 'Skipping geo attachment - no data to download')

    def processVideo(self, data):
        self.preprocess(data, 'video')
        c.log('debug', 'Skipping video attachment - size of the file is too big')

    def processSticker(self, data):
        self.preprocess(data, 'sticker')
        c.log('debug', 'Skipping sticker attachment - idiotizm')

    def processLink(self, data):
        c.log('debug', 'Skipping link attachment - no data to download')

    def processPoll(self, data):
        self.preprocess(data, 'poll')
        c.log('debug', 'Skipping poll attachment - no data to download')

    def processNote(self, data):
        self.preprocess(data, 'note')
        c.log('debug', 'Skipping note attachment - no data to download')

    def processPresent(self, data):
        self.preprocess(data, 'present')
        c.log('debug', 'Skipping present attachment - stupid present')

S = Media()
