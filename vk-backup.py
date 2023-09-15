#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
'''VK-Backup 0.9.0

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Script can backup your VK profile to your storage
Required:    python3.5

Usage:
  $ ./vk-backup.py --help
'''

from lib import Common as c

import getpass, os
import traceback
from sys import exit

c.init_begin(__doc__)
c.option('-u', '--user', type='string', dest='user', metavar='EMAIL', default=None, help='vk.com account user email (<user>@<host>) (required)')
c.option('-p', '--password', type='string', dest='password', metavar='PASSWORD', default=None, help='vk.com account password (will be requested if not set)')
c.option('-d', '--backup-dir', type='string', dest='backup-dir', metavar='PATH', default='backup', help='directory to store data [%default]')
c.option('--download-threads', type='int', dest='download-threads', metavar='NUM', default=16, help='number of simultaneous media downloads, 0 - disables download at all [%default]')
c.init_end()

if c.cfg('user') == None:
    c.log('error', 'Unable to get email from the user option')
    exit(1)

if c.cfg('password') == None:
    c.cfg('password', getpass.getpass())

if c.cfg('download-threads') < 1:
    c.log('error', 'Number of download threads can\'t be lower then one')
    exit(1)

class Backup:
    def __init__(self):
        c.log('debug', 'Init Backup')

        self.path = c.cfg('backup-dir')

    def store(self):
        c.log('debug', 'Store data')

        Users.store()
        Dialogs.store()
        Chats.store()
        Media.store()

        with open(os.path.join(self.path, 'backup.id'), 'w') as outfile:
            outfile.write(str(Api.getUserId()))

    def process(self):
        c.log('debug', 'Start processing')

        try:
            Users.requestUsers([Api.getUserId()])

            # Get friends of user & load them
            Users.requestUsers(Users.requestFriends(Api.getUserId()))

            # Get user photos
            Users.requestUserPhotos(Api.getUserId())

            # Get user blog
            #Users.requestBlog(Api.getUserId())

            # Get dialogs info
            # Unfortunately this functionality was blocked by vk.com for the non-trusted apps...
            # So instead please use messages_backup.py to use UI API to get your data from Messages
            Dialogs.requestDialogs()

            # Store data
            backup.store()
        except (Exception, KeyboardInterrupt) as e:
            c.log('error', 'Exception: %s: %s' % (str(e), traceback.format_exc()))
            Media.stopDownloads()

from lib import Api

from lib.Users import S as Users
#from lib.Dialogs import S as Dialogs
#from lib.Chats import S as Chats
from lib.DialogsUI import S as Dialogs
from lib.ChatsUI import S as Chats
from lib.Media import S as Media

backup = Backup()
backup.process()

c.log('info', 'DONE')
