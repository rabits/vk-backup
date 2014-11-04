#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup Database

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Database storage class
Required:    python2.7
'''

import Common as c

import codecs, json, os

class Database:
    def __init__(self):
        c.log('debug', 'Init %s' % self.__class__.__name__)

        self.data = {}

        self.path = os.path.join(c.cfg('backup-dir'), self.__class__.__name__)

        # Loading local data from the storage
        self.load()

    def store(self):
        c.log('debug', 'Store %s (%i)' % (self.__class__.__name__, len(self.data)))
        for i in self.data:
            path = os.path.join(self.path, i + '.json')
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with codecs.open(path, 'w', 'utf-8') as outfile:
                json.dump(self.data[i], outfile, indent=1, ensure_ascii=False, sort_keys=True)

    def load(self, subdir = None):
        path = self.path if subdir == None else os.path.join(self.path, subdir)

        if not os.path.isdir(path):
            c.log('debug', 'DB directory "%s" not found' % path)
            return

        listdir = os.listdir(path)
        dirs = [ d for d in listdir if d != 'storage' and os.path.isdir(os.path.join(path, d)) ]

        for d in dirs:
            if subdir == None:
                self.load(d)
            else:
                self.load(os.path.join(subdir, d))

        files = [ f for f in listdir if f.endswith('.json') ]
        c.log('debug', 'Loading files %s %s (%i)' % (self.__class__.__name__, path, len(files)))

        for f in files:
            filename = os.path.join(path, f)
            data_path = os.path.splitext(f)[0] if subdir == None else os.path.join(subdir, os.path.splitext(f)[0])
            data = json.load(open(filename))
            self.data[data_path] = data

