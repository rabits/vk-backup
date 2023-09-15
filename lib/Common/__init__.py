#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''Common Library 1.0

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: Common script tools
Required:    python2.7

Reserved options:
  --config-file
  --config-example
  --log-file
  -v --verbose
  -q --quiet

Usage:
  #!/usr/bin/python
  # -*- coding: UTF-8 -*-
  """Script Name 0.9
  Some additional description
  """
  from lib import Common as c
  c.init_begin(__doc__)
  c.option('-u', '--user', type='string', dest='user', metavar='NAME', default=None, help='Username (required)')
  c.init_end()

  c.log('info', 'Script %s v%s was started, %s!' % (c.name(), c.version(), c.cfg('user')))
'''

from . import Common as C

## init_begin(doc)
# Begin block of common library init
#
def init_begin(doc):
    global option
    C.init_begin(doc)
    option = C.option

## init_end()
# End block of common library init
#
def init_end():
    global log
    C.init_end()
    log = C.log

## log(logtype, message)
# Log message types:
#  debug - displayed only in verbose mode
#  ...   - any other messages you want
#  error - displayed even if verbose set to quiet
#
log = C.log

## option(...) link to OptParser.add_option(...)
# Set options data in init block
#
option = C.option

## cfg(key, val = None)
# Return cmd or config option
# Will replace cfg with key by val if val is set
#
def cfg(key, val = None):
    if val != None:
        C._CFG[key] = val
    return C._CFG[key]

## args()
# Return script input args
#
def args():
    return C._ARGS

## name()
# Return script name from __doc__
#
def name():
    return C._NAME

## version()
# Return script version from __doc__
#
def version():
    return C._VERSION

