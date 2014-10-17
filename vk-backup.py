#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''VK-Backup 0.6.1

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Script can backup your VK profile to your storage
Required:    python2.7

Usage:
  $ ./vk-backup.py --help
'''

from lib import Common as c
from lib import vk_auth

import getpass
import os

c.init_begin(__doc__)
c.option('-u', '--user', type='string', dest='user', metavar='EMAIL', default=None, help='vk.com account user email (<user>@<host>) (required)')
c.option('-p', '--password', type='string', dest='password', metavar='PASSWORD', default=None, help='vk.com account password (will be requested if not set)')
c.option('-d', '--backup-dir', type='string', dest='backup-dir', metavar='PATH', default='backup', help='directory to store data')
c.init_end()

if c.cfg('user') == None:
    parser.error('Unable to get email from the user option')

if c.cfg('password') == None:
    c.cfg('password', getpass.getpass())

from lib import Api
from lib.Users import S as Users
from lib.Dialogs import S as Dialogs
from lib.Chats import S as Chats

class Backup:
    '''
    Basic init class
    '''
    def __init__(self):
        c.log('debug', 'Init Backup')

        self.path = c.cfg('backup-dir')

        # Create directory
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

    def store(self):
        c.log('debug', 'Store data')

        Users.store()
        Dialogs.store()
        Chats.store()

    def process(self):
        c.log('debug', 'Start processing')

        # Get current user info
        Users.requestUsers([Api.getUserId()])
        # Get friends of current user & load users
        Users.requestUsers(Users.requestFriends(Api.getUserId()))

        # Get dialogs info
        Dialogs.requestDialogs()

backup = Backup()
backup.process()
backup.store()

c.log('info', 'DONE')
