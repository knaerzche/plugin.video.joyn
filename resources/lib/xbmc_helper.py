#!/usr/bin/python
# -*- coding: utf-8 -*-

import os.path
from sys import argv
from xbmc import translatePath, executeJSONRPC, executebuiltin, getCondVisibility, getInfoLabel, getSkinDir, log, sleep as xbmc_sleep, LOGERROR, LOGDEBUG, LOGNOTICE
from xbmcplugin import setContent, endOfDirectory, addDirectoryItems, setPluginCategory
from xbmcvfs import mkdirs, exists, rmdir, listdir, delete
from xbmcaddon import Addon
from xbmcgui import Dialog, NOTIFICATION_ERROR
from json import loads, dumps
from . import compat as compat
from .const import CONST

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

def get_media_filepath(filename):
	return translatePath(os.path.join(addon.getAddonInfo('path'), 'resources', 'media', filename)).encode('utf-8').decode('utf-8')

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


def set_folder(list_items, pluginurl, pluginhandle, pluginquery, folder_type, title=None):

	folder_defs = CONST['FOLDERS'].get(folder_type)
	addDirectoryItems(pluginhandle, list_items, len(list_items))

	if title is not None:
		setPluginCategory(pluginhandle, title)

	if 'content_type' in folder_defs.keys():
		log_debug('set_folder: set content_type: ' + folder_defs['content_type'])
		setContent(pluginhandle, folder_defs['content_type'])
	endOfDirectory(handle=pluginhandle,cacheToDisc=(folder_defs.get('cacheable', False) and (get_bool_setting('disable_foldercache') is False)))

	wait_for_container(pluginurl, pluginquery)

	if 'view_mode' in folder_defs.keys():
		set_view_mode(folder_defs['view_mode'])

	if 'sort' in folder_defs.keys():
		set_folder_sort(folder_defs['sort'])
def set_folder_sort(folder_sort_def):

	order = get_setting(folder_sort_def['setting_id'])
	log_debug('set_folder_sort ' + dumps(folder_sort_def) + ' : ' + order)

	if order != CONST['SETTING_VALS']['SORT_ORDER_DEFAULT']:
		executebuiltin('Container.SetSortMethod({:s})'.format(str(folder_sort_def['order_type'])))

		if ((order == CONST['SETTING_VALS']['SORT_ORDER_DESC'] and str(getCondVisibility('Container.SortDirection(ascending)')) == '1') or
			(order == CONST['SETTING_VALS']['SORT_ORDER_ASC'] and str(getCondVisibility('Container.SortDirection(descending)')) == '1')):
			executebuiltin('Container.SetSortDirection()')


def set_view_mode(setting_id):

	skin_name = str(getSkinDir())

	if get_bool_setting('enable_viewmodes') is True:


		setting_val = get_setting(setting_id)

		if setting_val == 'Custom':
			viewmode = get_setting(setting_id + '_custom')
			log_debug('Viewmode custom')
		else:
			log_debug('Viewmode ' + dumps(CONST['VIEW_MODES'].get(setting_val, {})))
			viewmode = CONST['VIEW_MODES'].get(setting_val, {}).get(skin_name, '0')

		log_debug('--> Viewmode ' + str(setting_id) + ' : ' + setting_val + ' : ' + viewmode + ' : ' + skin_name )

		if viewmode is not '0':
			executebuiltin('Container.SetViewMode({:s})'.format(viewmode))


def wait_for_container(pluginurl, pluginquery):

	#sadly it's necesary to wait until kodi has the new Container ...
	#this is necessary to make sure that all upcoming transactions are done with the correct container
	#provided the previous container had a differnd pluginurl/pluginquery
	pluginpath = pluginurl + pluginquery

	log_debug('wait_for_container pluginurl ' + str(pluginpath))

	counter = 0
	while counter <= 100:
		counter += 1
		xbmc_sleep(5)
		folder_path = str(getInfoLabel('Container.FolderPath'))
		if folder_path == pluginpath:
			break

	log_debug('wait_for_container no of loops: ' + str(counter));


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
