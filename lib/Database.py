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

        # Create directory
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

        # Loading local data from the storage
        self.load()

    def store(self):
        c.log('debug', 'Store %s (%i)' % (self.__class__.__name__, len(self.data)))
        for i in self.data:
            with codecs.open(os.path.join(self.path, i + '.json'), 'w', 'utf-8') as outfile:
                json.dump(self.data[i], outfile, indent=1, ensure_ascii=False)

    def load(self):
        files = [ f for f in os.listdir(self.path) if f.endswith('.json') ]
        c.log('debug', 'Loading %s (%i)' % (self.__class__.__name__, len(files)))
        for f in files:
            filename = os.path.join(self.path, f)
            data = json.load(open(filename))
            self.data[data['id']] = data

