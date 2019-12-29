# -*- coding: utf-8 -*-

from xbmc import Monitor as xbmc_Monitor, Player as xbmc_Player, getInfoLabel
from resources.lib.xbmc_helper import xbmc_helper
from resources.lib.lib_joyn import lib_joyn


class service_monitor(xbmc_Monitor):
	def __init__(self, player):
		from xbmcaddon import Addon

		self.player = player
		self.last_tracked_position = None
		self.last_played_file = None
		self.asset_id = None
		self.duration = None
		self.start_tracking = False
		self.addon_path = 'plugin://' + Addon().getAddonInfo('id')
		xbmc_helper().set_addon(Addon())
		xbmc_Monitor.__init__(self)

	def onNotification(self, sender, method, data):
		if method == 'Player.OnPlay':
			from xbmcgui import Window, getCurrentWindowId
			window_id = getCurrentWindowId()
			asset_id = Window(window_id).getProperty('joyn_video_id')
			if getInfoLabel('Container.FolderPath').startswith(self.addon_path) and asset_id is not None and len(asset_id) != 0:
				self.asset_id = asset_id
				self.start_tracking = True
				xbmc_helper().log_debug('Start tracking - asset : {}', asset_id)
			else:
				self.reset_tracking()
			Window(window_id).clearProperty('joyn_video_id')

		elif method == 'Player.OnStop':
			if self.start_tracking is True and self.asset_id is not None and self.last_tracked_position is not None and self.duration is not None:
				try:
					if lib_joyn().get_auth_token(force_reload_cache=True).get('has_account', False) is True:
						xbmc_helper().log_debug('Set resume - asset: {} - pos {}', self.asset_id, self.last_tracked_position)
						if self.last_tracked_position >= (self.duration - xbmc_helper().get_int_setting('del_resume_pos_secs')):
							lib_joyn().get_graphql_response('SET_RESUME_POSITION', {'assetId': self.asset_id, 'position': 0})
						else:
							lib_joyn().get_graphql_response('SET_RESUME_POSITION', {
							        'assetId': self.asset_id,
							        'position': self.last_tracked_position
							})
				except Exception as e:
					xbmc_helper().log_error('Exception when setting resume postion: {}', e)
					pass

			# delete local mpd file - if exists
			if self.last_played_file is not None and self.last_played_file.startswith('/'):
				filename = self.last_played_file.split('/')[-1]
				xbmc_helper().log_debug('Delete local mpd file: {}', self.last_played_file)
				xbmc_helper().del_data(filename, 'TEMP_DIR')

			self.reset_tracking()

	def track_position(self):

		if self.player.isPlayingVideo():
			try:
				self.last_played_file = str(self.player.getPlayingFile())
				cur_pos = int(self.player.getTime())
				if self.start_tracking is True and self.asset_id is not None and self.last_played_file.find(
				        self.asset_id) != -1 and cur_pos >= xbmc_helper().get_int_setting('start_set_resume_pos_secs'):
					self.last_tracked_position = cur_pos
					self.duration = int(self.player.getTotalTime())

			except Exception as e:
				xbmc_helper().log_debug('Exception when trying to set last_tracked_position: {}', e)
				pass

	def reset_tracking(self):
		self.start_tracking = False
		self.asset_id = None
		self.last_tracked_position = None
		self.last_played_file = None
		self.duration = None


if xbmc_helper().get_bool_setting('dont_verify_ssl_certificates') is True:

	import ssl
	try:
		_create_unverified_https_context = ssl._create_unverified_context
	except AttributeError:
		pass
	else:
		ssl._create_default_https_context = _create_unverified_https_context

servicemonitor = service_monitor(xbmc_Player())
xbmc_helper().log_notice('Monitor started')

while not servicemonitor.abortRequested():
	servicemonitor.track_position()
	servicemonitor.waitForAbort(2)

service_monitor = None
xbmc_helper().log_notice('Monitor stopped')
