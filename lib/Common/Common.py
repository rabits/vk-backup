#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''Common 1.0.1

Author:      Rabit <home@rabits.org>
License:     GPL v3
Description: A part of Common Library
Required:    python2.7
'''

from sys import stderr, stdout, exit as sysexit
from os import name as os_name
if os_name == 'nt':
    geteuid = lambda: 1
else:
    from os import geteuid
from time import strftime, time, localtime

from optparse import OptionParser
import configparser

def init_begin(doc):
    # Check that script not runned by root
    if geteuid() == 0:
        log('error', 'Script is running by the root user, but this is really dangerous! Please use unprivileged user.')
    #    sysexit(1)

    # Get name & version from doc
    try:
        tmp = doc.split('\n', 1)[0].split(' ')
        global _VERSION, _NAME
        _VERSION = tmp.pop()
        _NAME = ' '.join(tmp)
    except:
        log('warning', 'Unable to get script "%s %s" from provided doc: "%s"' % (_NAME, _VERSION, doc))

    # Prepare optparser
    global _PARSER, option
    _PARSER = OptionParser(usage='./%prog [options]', version=_VERSION)
    option = _PARSER.add_option

def init_end():
    # Add default options and parse cmd
    option('--config-file', type='string', dest='config-file', metavar='FILE',
       default=None, help='get configuration from ini file (replaced by command line parameters) [%default]')
    option('--config-example', action='callback', callback=_exampleini,
       default=None, help='print example ini config file to stdout')
    option('--log-file', type='string', dest='log-file', metavar='FILE',
       default=None, help='copy log output to file [%default]')
    option('-v', '--verbose', action='store_true', dest='verbose',
       help='verbose mode - moar output to stdout')
    option('-q', '--quiet', action='store_false', dest='verbose',
       help='silent mode - no output to stdout')
    global _PARSER, _CFG, _ARGS
    (_CFG, _ARGS) = _PARSER.parse_args()
    _CFG = vars(_CFG)

    # Parsing config file
    if _CFG['config-file'] != None:
        try:
            config = configparser.ConfigParser()
            config.read(_CFG['config-file'])

            for key in _PARSER.option_list:
                if None not in [key.dest, key.type]:
                    if _CFG[key.dest] is key.default:
                        try:
                            if key.type in ['int', 'float', 'boolean']:
                                val = getattr(config, 'get%s' % key.type)(_NAME, key.dest)
                            else:
                                val = config.get(_NAME, key.dest)
                            _CFG[key.dest] = val
                        except configparser.NoOptionError:
                            continue
        except:
            _PARSER.error('Unable to parse config file. Please specify header and available options')

    # LOGGING
    if _CFG['log-file'] != None:
        class Tee(object):
            def __init__(self, *files):
                self.files = files
            def write(self, obj):
                for f in self.files:
                    f.write(obj)
                    f.flush()

        import codecs
        logfile = codecs.open(_CFG['log-file'], 'a', 'utf-8')
        global stdout, stderr
        stdout = Tee(stdout, logfile)
        stderr = Tee(stderr, logfile)

    global log
    if _CFG['verbose'] == True:
        # Debug log
        import inspect
        def newlog(logtype, message):
            func = inspect.currentframe().f_back
            log_time = time()
            if logtype != 'error':
                stdout.write('[%s.%s %s, line:%03u]:\t %s\n' % (strftime('%H:%M:%S', localtime(log_time)), str(log_time % 1)[2:8], logtype.upper(), func.f_lineno, '  ' * (len(inspect.stack()) - 1) + message))
            else:
                stderr.write('[%s.%s %s, line:%03u]:\t %s\n' % (strftime('%H:%M:%S', localtime(log_time)), str(log_time % 1)[2:8], logtype.upper(), func.f_lineno, '  ' * (len(inspect.stack()) - 1) + message))
        log = newlog
    elif _CFG['verbose'] == False:
        # Only error log
        def newlog(logtype, message):
            if logtype.lower() == 'error':
                stderr.write('[%s %s]:\t %s\n' % (strftime('%H:%M:%S'), logtype.upper(), message))
        log = newlog

def log(logtype, message):
    # Default non-debug log
    if logtype.lower() != 'debug':
        if logtype.lower() != 'error':
            stdout.write('[%s %s]:\t %s\n' % (strftime('%H:%M:%S'), logtype.upper(), message))
        else:
            stderr.write('[%s %s]:\t %s\n' % (strftime('%H:%M:%S'), logtype.upper(), message))

def option():
    log('error', 'Unable to use option before init_start(__doc__) execution.')
    sysexit(1)

_NAME = '<name>'
_VERSION = '<version>'
_PARSER = None
_CFG = {}
_ARGS = []

def _exampleini(option, opt, value, parser):
    print('[%s]' % _NAME)
    for key in parser.option_list:
        if None not in [key.dest, key.type] and key.dest != 'config-file':
            print('%s: %s' % (key.dest, key.default))
    sysexit()
