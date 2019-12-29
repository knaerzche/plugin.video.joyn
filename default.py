# -*- coding: utf-8 -*-
# entrypoint

from xbmcaddon import Addon
from sys import argv
from xbmc import log, LOGDEBUG
from time import time
from resources.lib import plugin

start_time = time()
_ADDON=Addon()
plugin.run(_pluginurl=argv[0], _pluginhandle=int(argv[1]) or -1, _pluginquery=argv[2], addon=_ADDON)
_ADDON = None
log('Overall runtime of addon: {}: '.format(time() - start_time), LOGDEBUG)
