#!/usr/bin/python
# -*- coding: utf-8 -*-

import os.path
from xbmc import translatePath, executeJSONRPC, executebuiltin, log, LOGERROR, LOGDEBUG, LOGNOTICE
from xbmcvfs import mkdirs, exists, rmdir, listdir, delete
from xbmcaddon import Addon
from xbmcgui import Dialog, NOTIFICATION_ERROR
from json import loads, dumps
import resources.lib.compat as compat
from resources.lib.const import CONST

if compat.PY2:
	from urlparse import parse_qs
elif compat.PY3:
	from urllib.parse import parse_qs

addon = Addon()


def get_file_path(directory, filename):
	xbmc_profile_path = translatePath(addon.getAddonInfo('profile')).encode('utf-8').decode('utf-8')
	xbmc_directory = translatePath(os.path.join(xbmc_profile_path, directory, '')).encode('utf-8').decode('utf-8')

	if not exists(xbmc_directory):
		mkdirs(xbmc_directory)

	return translatePath(os.path.join(xbmc_directory, filename)).encode('utf-8').decode('utf-8')


def remove_dir(directory):

	xbmc_profile_path = translatePath(addon.getAddonInfo('profile')).encode('utf-8').decode('utf-8')
	xbmc_directory = translatePath(os.path.join(xbmc_profile_path, directory)).encode('utf-8').decode('utf-8')

	remove_ok = 1

	dirs, files = listdir(xbmc_directory)
	for file in files:
		file = file.decode("utf-8")
		remove_ok = delete(os.path.join(xbmc_directory, file))

	for directory in dirs:
		if directory != '.' and directory != '..':
			directory = directory.decode("utf-8")
			remove_ok = remove_dir(os.path.join(xbmc_directory, directory))

	return (remove_ok == 1)


def addon_enabled(addon_id):

	result = executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","id":1,\
		"params":{"addonid":"%s", "properties": ["enabled"]}}' % addon_id)
	return False if '"error":' in result or '"enabled":false' in result else True


def get_setting(setting_id):

	return addon.getSetting(setting_id)


def get_bool_setting(setting_id):

	return get_setting(setting_id) == 'true'


def get_int_setting(setting_id):

	setting_val = get_setting(setting_id)
	if setting_val.isdigit():
		return int(setting_val,10)
	else:
		return None

def get_addon_version():

	return addon.getAddonInfo('id') + '-' + addon.getAddonInfo('version')


def open_foreign_addon_settings(foreign_addon_id):

	log_debug('open_foreign_addon_settings ' + foreign_addon_id)
	Addon(foreign_addon_id).openSettings()


def notification(msg, description, icon=NOTIFICATION_ERROR):

	if icon == NOTIFICATION_ERROR:
		time = 10000
	else:
		time = 3000

	return Dialog().notification(msg, description, icon, time)


def dialog(msg, msg_line2=None, msg_line3=None, header=addon.getAddonInfo('name')):
	return Dialog().ok(header, msg, msg_line2, msg_line3)


def dialog_settings(msg,msg_line2=None, msg_line3=None, header=addon.getAddonInfo('name')):

	dialog_res = Dialog().yesno(header, msg, msg_line2, msg_line3, nolabel=translation('CANCEL'), yeslabel=translation('OPEN_ADDON_SETTINGS'))

	if dialog_res is 1:
		addon.openSettings()


def dialog_id(id):
	return dialog(translation(id))


def log_error(content):
	_log(content, LOGERROR)


def log_notice(content):
	_log(content, LOGNOTICE)


def log_debug(content):
	_log(content, LOGDEBUG)


def _log(msg, level=LOGNOTICE):

	msg = compat._encode(msg)
	log('[' + get_addon_version() + ']' + msg, level)


def translation(id):

	return  compat._encode(addon.getLocalizedString(CONST['MSG_IDS'][id]))


def get_addon_params(pluginquery):
	return dict( (k, v if len(v)>1 else v[0] )
           for k, v in parse_qs(pluginquery[1:]).items() )


def get_data(filename, dir_type='DATA_DIR'):

	data_file_path = get_file_path(CONST[dir_type], filename)
	data = None

	if os.path.exists(data_file_path):
		with open(data_file_path, 'r') as data_infile:
			 data = data_infile.read()
	return data


def set_data(filename, data, dir_type='DATA_DIR'):

	data_file_path = get_file_path(CONST[dir_type], filename)

	with open (data_file_path, 'w') as data_outfile:
		data_outfile.write(data)


def get_json_data(filename, dir_type='DATA_DIR'):

	data = get_data(filename, dir_type)

	if data is not None:
		try:
			data = loads(get_data(filename, dir_type))
		except ValueError:
			log('Could not decode data as json: ' + filename )
			pass

	return data


def set_json_data (filename, data, dir_type='DATA_DIR'):

	set_data(filename, dumps(data), dir_type)
