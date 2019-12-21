# -*- coding: utf-8 -*-

from xbmc import Monitor as xbmc_Monitor, Player as xbmc_Player, sleep as xbmc_sleep
from sys import exit
from resources.lib import xbmc_helper
from resources.lib import compat
from resources.lib.lib_joyn import lib_joyn


class service_monitor(xbmc_Monitor):
	def __init__(self, player):
		self.player = player
		self.last_tracked_position = None
		self.last_played_file = None
		self.asset_id = None
		self.duration = None
		self.start_tracking = False
		xbmc_Monitor.__init__(self)

	def onNotification(self, sender, method, data):
		if method == 'Player.OnPlay':
			self.start_tracking = True
			xbmc_helper.log_debug("Start tracking")

		elif method == 'Player.OnStop':
			if self.start_tracking is True and self.asset_id is not None and self.last_tracked_position is not None and self.duration is not None:
				try:
					if lib_joyn().get_auth_token(force_reload_cache=True).get('has_account', False) is True:
						xbmc_helper.log_debug(compat._format('Set resume - asset: {} - pos {}', self.asset_id, self.last_tracked_position))
						if self.last_tracked_position >= (self.duration - xbmc_helper.get_int_setting('del_resume_pos_secs')):
							lib_joyn().get_graphql_response('SET_RESUME_POSITION', {'assetId': self.asset_id, 'position': 0})
						else:
							lib_joyn().get_graphql_response('SET_RESUME_POSITION', {
							        'assetId': self.asset_id,
							        'position': self.last_tracked_position
							})
				except Exception as e:
					xbmc_helper.log_error(compat._format("Exception when setting resume postion: {}", e))
					pass

			# delete local mpd file - if exists
			if self.last_played_file is not None and self.last_played_file.startswith('/'):
				filename = self.last_played_file.split('/')[-1]
				xbmc_helper.log_debug(compat._format('Delete local mpd file: {} data; {}', self.last_played_file, filename))
				xbmc_helper.del_data(filename, 'TEMP_DIR')

			self.reset_tracking()

	def track_position(self):

		if self.start_tracking is True and self.player.isPlaying():
			try:
				pos = int(self.player.getTime())
				total_time = int(self.player.getTotalTime())
				asset_id = str(self.player.getVideoInfoTag().getIMDBNumber())
				self.last_played_file = str(self.player.getPlayingFile())

				if len(asset_id) != 0 and (self.asset_id is None) and pos >= xbmc_helper.get_int_setting('start_set_resume_pos_secs'):
					self.asset_id = asset_id
					self.duration = total_time

				if self.asset_id == asset_id:
					self.last_tracked_position = int(pos)

			except Exception as e:
				xbmc_helper.log_debug(compat._format('Exception when trying to set last_tracked_position: {}', e))
				pass

	def reset_tracking(self):
		self.start_tracking = False
		self.asset_id = None
		self.last_tracked_position = None
		self.last_played_file = None
		self.duration = None


if xbmc_helper.get_bool_setting('dont_verify_ssl_certificates') is True:

	import ssl
	try:
		_create_unverified_https_context = ssl._create_unverified_context
	except AttributeError:
		pass
	else:
		ssl._create_default_https_context = _create_unverified_https_context

servicemonitor = service_monitor(xbmc_Player())
xbmc_helper.log_notice('Monitor started')

while not servicemonitor.abortRequested():
	servicemonitor.track_position()
	servicemonitor.waitForAbort(2)

xbmc_helper.log_notice('Monitor stopped')
exit(0)
