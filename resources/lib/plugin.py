#!/usr/bin/python
# -*- coding: utf-8 -*-

from sys import argv, exit
import os.path
from xbmc import translatePath, executebuiltin, sleep as xbmc_sleep
from  xbmcgui import Dialog, ListItem, INPUT_ALPHANUM
from xbmcplugin import endOfDirectory, setResolvedUrl, setContent, addDirectoryItem
from xbmcaddon import Addon
from datetime import datetime
from time import time
from json import dumps, loads
from inputstreamhelper import Helper
from resources.lib.const import CONST
import resources.lib.compat as compat
import resources.lib.cache as cache
import resources.lib.xbmc_helper as xbmc_helper
import resources.lib.request_helper as request_helper
from resources.lib.lib_joyn import lib_joyn as lib_joyn


if compat.PY2:
	from urllib import urlencode, quote
	from HTMLParser import HTMLParser
elif compat.PY3:
	from urllib.parse import urlencode, quote
	from html.parser import HTMLParser


try:
	from multiprocessing.dummy import Pool as ThreadPool
	from multiprocessing import cpu_count
	from functools import partial
	multi_threading = True
except ImportError:
	multi_threading = False
	pass


def get_lastseen():

	lastseen = xbmc_helper.get_json_data('lastseen')

	if lastseen is not None and len(lastseen) > 0:
		return sorted(lastseen, key=lambda k: k['lastseen'], reverse=True)

	return []


def add_lastseen(tv_show_id, season_id, max_lastseen):

	if max_lastseen > 0:
		found_in_lastseen = False
		lastseen = get_lastseen()

		if lastseen is None:
			lastseen = []

		for idx, lastseen_item in enumerate(lastseen):
			if lastseen_item['tv_show_id'] == tv_show_id and lastseen_item['season_id'] == season_id:
				lastseen[idx]['lastseen'] = time()
				found_in_lastseen = True
				break

		if found_in_lastseen is False:
			lastseen.append({'tv_show_id' : tv_show_id, 'season_id' : season_id, 'lastseen' : time()})

		lastseen = sorted(lastseen, key=lambda k: k['lastseen'], reverse=True)

		if len(lastseen) > max_lastseen:
			lastseen = lastseen[:(max_lastseen-1)]

		xbmc_helper.set_json_data('lastseen', lastseen)


def drop_lastseen(tv_show_id, season_id):

	found_in_lastseen = False
	lastseen = get_lastseen()

	for lastseen_item in lastseen:
		if lastseen_item['tv_show_id'] == tv_show_id and lastseen_item['season_id'] == season_id:
			lastseen.remove(lastseen_item)

	xbmc_helper.set_json_data('lastseen', lastseen)


def get_favorites():
	favorites = xbmc_helper.get_json_data('favorites')

	if favorites is not None:
		return favorites

	return []


def add_favorites(favorite_item):

	if check_favorites(favorite_item) is False:
		favorites = get_favorites()
		favorites.append(favorite_item)
		favorites = xbmc_helper.set_json_data('favorites', favorites)

		executebuiltin("Container.Refresh")
		xbmc_sleep(100)
		xbmc_helper.notification('Favoriten', 'Zu Favoriten hinzugefügt', default_icon)


def drop_favorites(favorite_item, siltent=False):

	favorites = get_favorites()
	found = False

	for favorite in favorites:
		if 'tv_show_id' in favorite_item.keys() and 'tv_show_id' in favorite.keys():
			if favorite_item['tv_show_id'] == favorite['tv_show_id'] and favorite_item['season_id'] == favorite['season_id']:
				favorites.remove(favorite_item)
				found = True
		elif 'channel_id' in favorite_item.keys() and 'channel_id' in favorite.keys():
			if favorite_item['channel_id'] == favorite['channel_id']:
				favorites.remove(favorite_item)
				found = True
		elif 'category_name' in favorite_item.keys() and 'category_name' in favorite.keys():
			if favorite_item['category_name'] == favorite['category_name']:
				favorites.remove(favorite_item)
				found = True

	favorites = xbmc_helper.set_json_data('favorites', favorites)

	if siltent == False and found is True:
		xbmc_helper.notification('Favoriten', 'Aus Favoriten entfernt', default_icon)
		executebuiltin("Container.Refresh")
		xbmc_sleep(100)


def check_favorites(favorite_item, season_id=None):

	favorites = get_favorites()
	for favorite in favorites:
		if 'tv_show_id' in favorite_item.keys() and 'tv_show_id' in favorite.keys():
			if favorite_item['tv_show_id'] == favorite['tv_show_id'] and favorite_item['season_id'] == favorite['season_id']:
				return True
		elif 'channel_id' in favorite_item.keys() and 'channel_id' in favorite.keys():
			if favorite_item['channel_id'] == favorite['channel_id']:
				return True
		elif 'category_name' in favorite_item.keys() and 'category_name' in favorite.keys():
			if favorite_item['category_name'] == favorite['category_name']:
				return True

	return False


def show_lastseen(max_lastseen_count):

	lastseen = get_lastseen()

	if len(lastseen) > max_lastseen_count:
		if max_lastseen_count == 0:
			lastseen = []
		else:
			lastseen = lastseen[:(max_lastseen_count-1)]

	if len(lastseen) > 0:
		tvshow_ids = []
		season_ids = []
		for lastseen_item in lastseen:
			tvshow_ids.append(lastseen_item['tv_show_id'])
			season_ids.append(lastseen_item['season_id'])

		tvshow_data = libjoyn.get_json_by_type('TVSHOWS', {'ids' : ','.join(tvshow_ids)})
		season_data = libjoyn.get_json_by_type('SEASONS', {'ids' : ','.join(season_ids)})

		for lastseen_item in lastseen:
			found = False
			for tvshow_item in tvshow_data['data']:
				if tvshow_item['id'] == lastseen_item['tv_show_id'] and 'metadata' in tvshow_item.keys() and 'de' in tvshow_item['metadata']:
					extracted_tvshow_metadata = libjoyn.extract_metadata(metadata=tvshow_item['metadata']['de'], selection_type='TVSHOWS')
					for season_item in season_data['data']:
						if season_item['id'] == lastseen_item['season_id'] and 'metadata' in season_item.keys() and 'de' in season_item['metadata']:
							extracted_season_metadata = libjoyn.extract_metadata(metadata=season_item['metadata']['de'], selection_type='SEASON')
							found = True
							add_dir(mode='video', season_id=lastseen_item['season_id'], tv_show_id=lastseen_item['tv_show_id'],
								metadata=libjoyn.combine_tvshow_season_data(extracted_tvshow_metadata, extracted_season_metadata), parent_fanart=default_fanart)

			if found is False:
				drop_lastseen(lastseen_item['tv_show_id'], lastseen_item['season_id'])

def show_favorites():

	favorites = get_favorites()
	xbmc_helper.log_debug('show_favorites ' + dumps(favorites))

	if len(favorites) == 0:
		xbmc_helper.notification('Favoriten', 'Bisher keine Favoriten angelegt', default_icon)
	else:
		tvshow_ids = []
		season_ids = []
		channel_ids = []
		category_names = []
		needs_drop = False
		for favorite_item in favorites:
			if 'tv_show_id' in favorite_item.keys():
				tvshow_ids.append(favorite_item['tv_show_id'])
				if favorite_item['season_id'] is not None:
					season_ids.append(favorite_item['season_id'])
			elif 'channel_id' in favorite_item.keys():
				channel_ids.append(favorite_item['channel_id'])
			elif 'category_name' in favorite_item.keys():
				category_names.append(favorite_item['category_name'])

		if len(tvshow_ids) > 0:
			tvshow_data = libjoyn.get_json_by_type('TVSHOWS', {'ids' : ','.join(tvshow_ids)})
		if len(season_ids) > 0:
			season_data = libjoyn.get_json_by_type('SEASONS', {'ids' : ','.join(season_ids)})
		if len(channel_ids) > 0:
			brands = libjoyn.get_brands()
		if len(category_names) > 0:
			categories = libjoyn.get_categories()

		for favorite_item in favorites:
			found = False
			if 'tv_show_id' in favorite_item.keys():
				for tvshow_item in tvshow_data['data']:
					if tvshow_item['id'] == favorite_item['tv_show_id'] and 'metadata' in tvshow_item.keys() and 'de' in tvshow_item['metadata']:
						extracted_tvshow_metadata = libjoyn.extract_metadata(metadata=tvshow_item['metadata']['de'], selection_type='TVSHOWS')
						if favorite_item['season_id'] is not None:
							for season_item in season_data['data']:
								if season_item['id'] == favorite_item['season_id'] and 'metadata' in season_item.keys() and 'de' in season_item['metadata']:
									extracted_season_metadata = libjoyn.extract_metadata(metadata=season_item['metadata']['de'], selection_type='SEASON')
									found = True
									add_dir(mode='video', season_id=favorite_item['season_id'], tv_show_id=favorite_item['tv_show_id'],
										metadata=libjoyn.combine_tvshow_season_data(extracted_tvshow_metadata,
											extracted_season_metadata), parent_fanart=default_fanart)
									break
						else:
							found = True
							add_dir(mode='season', tv_show_id=favorite_item['tv_show_id'], metadata=extracted_tvshow_metadata, parent_fanart=default_fanart)
						break

			elif 'channel_id' in favorite_item.keys():
				for channel_item in brands['data']:
					xbmc_helper.log_debug('CHANNEL_ITEM ' + str(type(channel_item['channelId'])) + ' --- ' +  str(type(favorite_item['channel_id'])))
					if  str(channel_item['channelId']) == favorite_item['channel_id']:
						found = True
						extracted_channel_metadata = libjoyn.extract_metadata(metadata=channel_item['metadata']['de'], selection_type='BRAND')
						add_dir(mode='tvshows', channel_id=channel_item['channelId'], metadata=extracted_channel_metadata)
						break

			elif 'category_name' in favorite_item.keys():
				for category_name, category_ids in categories.items():
					if category_name == favorite_item['category_name']:
						add_dir(metadata={'infoLabels': {'Title' : 'Rubrik: ' + category_name, 'description' : ''}, 'art': {}}, mode='fetch_categories',
							fetch_ids=','.join(category_ids), category_name=compat._encode(category_name))
						found = True
						break
			if found is False:
				needs_drop = True
				drop_favorites(favorite_item, True)

		if needs_drop is True:
			xbmc_helper.notification('Favoriten', 'Einige Favoriten wurden nicht mehr gefunden - sie wurden automatisch entfernt.', default_icon)

		endOfDirectory(pluginhandle)


def get_uepg_params():

	params = 'json=' +  quote(dumps(libjoyn.get_uepg_data(pluginurl)))
	params += '&refresh_path=' + quote(pluginurl + '?mode=epg')
	params += '&refresh_interval=' + quote('7200')
	params += '&row_count=' + quote('5')

	return params

def index():

	show_lastseen(xbmc_helper.get_int_setting('max_lastseen'))
	add_dir(metadata={'infoLabels': {'Title' : 'Mediatheken', 'Plot' : 'Mediatheken von www.joyn.de'},'art': {}}, mode='channels', stream_type='VOD')
	add_dir(metadata={'infoLabels': {'Title' : 'Rubriken', 'Plot' : 'Mediatheken gruppiert in Rubriken'}, 'art': {}}, mode='categories', stream_type='VOD')
	add_dir(metadata={'infoLabels': {'Title' : 'Favoriten', 'Plot' : 'Favoriten'}, 'art': {}}, mode='show_favs')
	add_dir(metadata={'infoLabels': {'Title' : 'Suche', 'Plot' : 'Suche in den Mediatheken'}, 'art': {}}, mode='search')
	add_dir(metadata={'infoLabels': {'Title' : 'Live TV', 'Plot' : 'Live TV'}, 'art': {}}, mode='channels',stream_type='LIVE')
	add_dir(metadata={'infoLabels': {'Title' : 'EPG', 'Plot' : 'EPG'}, 'art': {}}, mode='epg',stream_type='LIVE')

	endOfDirectory(handle=pluginhandle,cacheToDisc=False)


def channels(stream_type):

	brands = libjoyn.get_brands()

	if stream_type == 'LIVE':
		epg = libjoyn.get_epg()

	for brand in brands['data']:
		channel_id = str(brand['channelId'])
		for metadata_lang, metadata in brand['metadata'].items():
			if metadata_lang == 'de':
				extracted_metadata = libjoyn.extract_metadata(metadata=metadata, selection_type='BRAND')
				if stream_type == 'VOD' and metadata['hasVodContent'] == True:
					add_dir(mode='tvshows', stream_type=stream_type, channel_id=channel_id,metadata=extracted_metadata)
				elif stream_type == 'LIVE' and 'livestreams' in metadata.keys():
					for livestream in metadata['livestreams']:
						stream_id = livestream['streamId']
						if channel_id in epg.keys():
							epg_metadata = libjoyn.extract_metadata_from_epg(epg[channel_id])
							extracted_metadata['infoLabels'].update(epg_metadata['infoLabels'])
							extracted_metadata['art'].update(epg_metadata['art'])
						add_link(metadata=extracted_metadata,mode='play_video', video_id=stream_id, stream_type='LIVE')
				break
	endOfDirectory(handle=pluginhandle,cacheToDisc=False)


def tvshows(channel_id, fanart_img):

	tvshows = libjoyn.get_json_by_type('TVSHOW', {'channelId': channel_id})

	for tvshow in tvshows['data']:
		tv_show_id = str(tvshow['id'])
		for metadata_lang, metadata in tvshow['metadata'].items():
			if metadata_lang == 'de':
				extracted_metadata = libjoyn.extract_metadata(metadata, 'TVSHOW')
				add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata, parent_fanart=fanart_img)
	favorite_item = {'channel_id' : channel_id}

	if check_favorites(favorite_item) is False:
		add_link(metadata={'infoLabels': {'Title' : 'Zu Favoriten hinzufügen', 'Plot' : 'Mediathek zu Favoriten hinzufügen'}, 'art': {}}, mode='add_fav', favorite_item=favorite_item)
	else:
		add_link(metadata={'infoLabels': {'Title' : 'Aus Favoriten entfernen', 'Plot' : 'Mediathek aus Favoriten entfernen'}, 'art': {}}, mode='drop_fav', favorite_item=favorite_item)

	endOfDirectory(pluginhandle)


def seasons(tv_show_id, parent_fanart_img, parent_img):

	seasons = libjoyn.get_json_by_type('SEASON', {'tvShowId' : tv_show_id})
	for season in seasons['data']:
		season_id = season['id']
		for metadata_lang, metadata in season['metadata'].items():
			if metadata_lang == 'de':
				extracted_metadata = libjoyn.extract_metadata(metadata,'SEASON');
				extracted_metadata['art'].update({'thumb' : parent_img, 'fanart' : parent_fanart_img});
				add_dir(mode='video', season_id=season_id, tv_show_id=tv_show_id,metadata=extracted_metadata)
				break

	favorite_item={'tv_show_id' : tv_show_id, 'season_id': None}
	if check_favorites(favorite_item) is False:
		add_link(metadata={'infoLabels': {'Title' : 'Zu Favoriten hinzufügen', 'Plot' : 'Serie zu Favoriten hinzufügen'}, 'art': {}}, mode='add_fav', favorite_item=favorite_item)
	else:
		add_link(metadata={'infoLabels': {'Title' : 'Aus Favoriten entfernen', 'Plot' : 'Serie aus Favoriten entfernen'}, 'art': {}}, mode='drop_fav', favorite_item=favorite_item)

	endOfDirectory(pluginhandle)


def videos(tv_show_id, season_id, fanart_img):

	xbmc_helper.log_debug('video : tv_show_id: ' + tv_show_id + 'season_id: ' + season_id)
	videos = libjoyn.get_json_by_type('VIDEO', {'tvShowId' : tv_show_id, 'seasonId' : season_id})

	for video in videos['data']:
		video_id = video['id']

		for metadata_lang, metadata_values in video['metadata'].items():
			if metadata_lang == 'de':
				extracted_metadata = libjoyn.extract_metadata(metadata=metadata_values,selection_type='VIDEO');
				if 'broadcastDate' in metadata_values.keys():
					extracted_metadata['infoLabels'].update({'Aired' : datetime.utcfromtimestamp(metadata_values['broadcastDate']).strftime('%Y-%m-%d')})
				break

		extracted_metadata['infoLabels'].update({'Genre' : []})
		if 'tvShow' in video.keys():
			if 'genres' in video['tvShow'].keys():
				for genre in video['tvShow']['genres']:
					extracted_metadata['infoLabels']['Genre'].append(genre['title'])
			if 'titles' in video['tvShow'].keys():
				for title_key, title_value in video['tvShow']['titles'].items():
					if title_key == 'default':
						extracted_metadata['infoLabels'].update({'TVShowTitle' : HTMLParser().unescape(title_value)})
						break

		if 'season' in video.keys():
			if 'titles' in video['season'].keys():
				for season_title_key, season_title_value in video['season']['titles'].items():
					if season_title_key == 'default':
						extracted_metadata['infoLabels'].update({'Season' : season_title_value})
						break

		if 'episode' in video.keys() and 'number' in video['episode'].keys():
			extracted_metadata['infoLabels'].update({'Episode' : 'Episode ' + str(video['episode']['number'])})

		if 'duration' in video.keys():
			extracted_metadata['infoLabels'].update({'Duration' : (video['duration']/1000)})

		extracted_metadata['infoLabels'].update({'mediatype' : 'episode'});
		add_link(mode='play_video', metadata=extracted_metadata, video_id=video_id,parent_fanart=fanart_img)

	favorite_item = {'tv_show_id' : tv_show_id , 'season_id' : season_id}
	if check_favorites(favorite_item) is False:
		add_link(metadata={'infoLabels': {'Title' : 'Zu Favoriten hinzufügen', 'Plot' : 'Staffel zu Favoriten hinzufügen'}, 'art': {}}, mode='add_fav', favorite_item=favorite_item)
	else:
		add_link(metadata={'infoLabels': {'Title' : 'Aus Favoriten entfernen', 'Plot' : 'Staffel aus Favoriten entfernen'}, 'art': {}}, mode='drop_fav', favorite_item=favorite_item)
	endOfDirectory(pluginhandle)


def play_video(video_id, stream_type='VOD'):

	xbmc_helper.log_debug('play_video: video_id: ' + video_id)
	list_item = ListItem()
	video_data = libjoyn.get_video_data(video_id, stream_type)
	succeeded = True

	if (video_data['streamingFormat'] == 'dash'):
		if libjoyn.set_mpd_props(list_item, video_data['videoUrl'], stream_type) is not False:
			if 'drm' in video_data.keys() and video_data['drm'] == 'widevine' and 'licenseUrl' in video_data.keys():
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.license_type', 'com.widevine.alpha')
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.license_key', video_data['licenseUrl'] + '|' +
					request_helper.get_header_string({'User-Agent' : libjoyn.config['USER_AGENT'], 'Content-Type': 'application/octet-stream'}) + '|R{SSM}|')
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.stream_headers',  request_helper.get_header_string({'User-Agent' : libjoyn.config['USER_AGENT']}))
				if xbmc_helper.get_bool_setting('checkdrmcert') is True and 'certificateUrl' in video_data.keys():
					list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.server_certificate', video_data['certificateUrl'] + '|'
						+  request_helper.get_header_string({'User-Agent' : libjoyn.config['USER_AGENT']}))
		else:
			xbmc_helper.notification('Fehler', 'Konnte keine gültigen Video-Stream finden.', default_icon)
			xbmc_helper.log_error('Could not get valid MPD')
			succeeded = False

	else:
		return list_item.setPath(path=video_data['videoUrl'] + '|' + request_helper.get_header_string({'User-Agent' : libjoyn.config['USER_AGENT']}))

	if succeeded is True and 'tv_show_id' in video_data.keys() and 'season_id' in video_data.keys():
		add_lastseen(video_data['tv_show_id'], video_data['season_id'], CONST['LASTSEEN_ITEM_COUNT'])

	setResolvedUrl(pluginhandle, succeeded, list_item)


def search(stream_type='VOD'):

	dialog = Dialog()
	search_term = dialog.input('Suche', type=INPUT_ALPHANUM)

	if len(search_term) > 0:
		request_params = {'search': search_term.lower(), 'hasVodContent': 'true'}
		tvshows = libjoyn.get_json_by_type(path_type='TVSHOW',additional_params=request_params)
		if len(tvshows['data']) > 0:
			for tvshow in tvshows['data']:
				tv_show_id = str(tvshow['id'])
				if 'metadata' in tvshow.keys() and 'de' in tvshow['metadata'].keys():
					extracted_metadata = libjoyn.extract_metadata(metadata=tvshow['metadata']['de'], selection_type='TVSHOW')
					add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata,parent_fanart=default_fanart)
			endOfDirectory(handle=pluginhandle)
		else:
			xbmc_helper.notification('Keine Ergebnisse', 'für "' + search_term + '" gefunden', default_icon)


def categories(stream_type='VOD'):

	categories = libjoyn.get_categories()

	for category_name, category_ids in categories.items():
		add_dir(metadata={'infoLabels': {'Title' : category_name, 'description' : ''}, 'art': {}}, mode='fetch_categories', fetch_ids=','.join(category_ids),
			category_name=compat._encode(category_name))

	endOfDirectory(handle=pluginhandle)


def fetch_categories(categories, category_name, stream_type='VOD'):

	xbmc_helper.log_debug('fetch_categories - multithreading : ' + str(multi_threading))
	fetch_results = []

	#before threading can be done, the first request needs to be done seperatly to initialize the thread context for urlib and stuff
	frst_fetch_result = libjoyn.get_json_by_type('FETCH', {}, {}, categories[0])
	if len(categories) > 1:
		if multi_threading is True:
			thread_count = cpu_count() -1
			xbmc_helper.log_debug('fetch_categories - number of threads : ' + str(thread_count))
			thread_pool = ThreadPool(thread_count)
			fetch_results = thread_pool.map(partial(libjoyn.get_json_by_type, 'FETCH', {}, {}), categories[1:])
			thread_pool.close()
			thread_pool.join()
		else:
			for category in categories[1:]:
				fetch_results.append(libjoyn.get_json_by_type('FETCH', {}, {},category))

		fetch_results.insert(0, frst_fetch_result)
	else:
		fetch_results = [frst_fetch_result]

	for category in fetch_results:
		for tvshow in category['data']:
			tv_show_id = str(tvshow['id'])
			if 'metadata' in tvshow.keys() and 'de' in tvshow['metadata'].keys():
				extracted_metadata = libjoyn.extract_metadata(metadata=tvshow['metadata']['de'], selection_type='TVSHOW')
				add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata,parent_fanart=default_fanart)

	favorite_item = {'category_name' : category_name }
	if check_favorites(favorite_item) is False:
		add_link(metadata={'infoLabels': {'Title' : 'Zu Favoriten hinzufügen', 'Plot' : 'Rubrik zu Favoriten hinzufügen'}, 'art': {}}, mode='add_fav', favorite_item=favorite_item)
	else:
		add_link(metadata={'infoLabels': {'Title' : 'Aus Favoriten entfernen', 'Plot' : 'Rubrik aus Favoriten entfernen'}, 'art': {}}, mode='drop_fav', favorite_item=favorite_item)

	endOfDirectory(handle=pluginhandle)


def add_dir(mode, metadata, channel_id='', tv_show_id='', season_id='', video_id='', stream_type='VOD', fetch_ids='', parent_fanart='', category_name=''):

	params = {
		'mode' : mode,
		'tv_show_id': tv_show_id,
		'season_id' : season_id,
		'video_id': video_id,
		'stream_type': stream_type,
		'channel_id': channel_id,
		'fetch_ids' : fetch_ids,
		'category_name' : category_name,
	}

	list_item = ListItem(metadata['infoLabels']['Title'])
	list_item.setInfo(type='Video', infoLabels=metadata['infoLabels'])

	if 'poster' not in metadata['art'] and 'thumb' in metadata['art']:
		metadata['art'].update({'poster' : metadata['art']['thumb']})
	elif 'thumb' not in metadata['art']:
		metadata['art'].update({ 'thumb' : default_logo})
		metadata['art'].update({ 'poster' : default_logo})

	if 'icon' not in metadata['art']:
		metadata['art'].update({ 'icon' : default_icon})

	if 'fanart' not in metadata['art']:
		if parent_fanart is not '':
			metadata['art'].update({'fanart': parent_fanart})
		else:
			metadata['art'].update({'fanart': default_fanart})

	params.update({'parent_img': metadata['art']['poster']})
	params.update({'parent_fanart': metadata['art']['fanart']})

	if 'fanart' in metadata['art'] and parent_fanart is not '':
		metadata['art'].update({'fanart': parent_fanart})

	list_item.setArt(metadata['art'])

	url = pluginurl+'?'
	url += urlencode(params)

	return addDirectoryItem(handle=pluginhandle, url=url, listitem=list_item, isFolder=True)



def add_link(mode, video_id='', metadata={}, stream_type='VOD', parent_fanart='', favorite_item=None):

	params = {
		'video_id': video_id,
		'mode' : mode,
		'stream_type': stream_type,
	}

	if favorite_item is not None:
		params.update({'favorite_item' : dumps(favorite_item)})

	url = pluginurl+'?'
	url += urlencode(params)

	list_item = ListItem(metadata['infoLabels']['Title'])
	list_item.setInfo(type='video', infoLabels=metadata['infoLabels'])

	if 'poster' not in metadata['art'] and 'thumb' in metadata['art']:
		metadata['art'].update({'poster' : metadata['art']['thumb']})
	elif 'thumb' not in metadata['art']:
		metadata['art'].update({ 'thumb' : default_logo})
		metadata['art'].update({ 'poster' : default_logo})

	if 'icon' not in metadata['art']:
		metadata['art'].update({ 'icon' : default_icon})

	if 'fanart' not in metadata['art']:
		if parent_fanart is not '':
			metadata['art'].update({'fanart': parent_fanart})
		else:
			metadata['art'].update({'fanart': default_fanart})

	if 'fanart' in metadata['art'] and parent_fanart is not '':
		metadata['art'].update({'fanart': parent_fanart})

	if (mode == 'play_video' and video_id is not ''):
		list_item.setInfo(type='Video', infoLabels=metadata['infoLabels'])
		list_item.setArt(metadata['art'])
		list_item.setProperty('IsPlayable', 'True')

	return addDirectoryItem(handle=pluginhandle, url=url, listitem=list_item, isFolder=False)

pluginurl = argv[0]
pluginhandle = int(argv[1])
pluginquery = argv[2]
addon = Addon()
default_icon = addon.getAddonInfo('icon')
default_fanart = addon.getAddonInfo('fanart')
default_logo = translatePath(os.path.join(addon.getAddonInfo('path'), 'resources','logo.gif')).encode('utf-8').decode('utf-8')
libjoyn = lib_joyn(default_icon)
params = xbmc_helper.get_addon_params(pluginquery)
param_keys = params.keys()
setContent(pluginhandle, 'tvshows')
if not  xbmc_helper.addon_enabled(CONST['INPUTSTREAM_ADDON']):
	xbmc_helper.notification('Inputstream nicht aktiviert', 'Inputstream nicht aktiviert', default_icon)
	exit(0)

is_helper = Helper('mpd', drm='widevine')
if not is_helper.check_inputstream():
	xbmc_helper.notification('Widevine nicht gefunden', 'Ohne Widevine kann das Addon nicht verwendet werden.', default_icon)
	exit(0)

if 'mode' in param_keys:

	mode = params['mode']

	if 'stream_type' in param_keys:
		stream_type = params['stream_type']
	else:
		stream_type = 'VOD'
	if 'parent_img' in param_keys:
		parent_img = params['parent_img']
	else:
		parent_img = ''

	if 'parent_fanart' in param_keys:
		parent_fanart = params['parent_fanart']
	else:
		parent_fanart = ''

	if mode == 'season' and 'tv_show_id' in param_keys:
		seasons(params['tv_show_id'],parent_fanart, parent_img)

	elif mode == 'video' and 'tv_show_id' in param_keys and 'season_id' in param_keys:
		videos(params['tv_show_id'],params['season_id'],parent_fanart)

	elif mode == 'play_video' and 'video_id' in param_keys:
		play_video(params['video_id'], stream_type)

	elif mode == 'channels':
		channels(stream_type)

	elif mode == 'tvshows' and 'channel_id' in param_keys:
		tvshows(params['channel_id'],parent_fanart)

	elif mode == 'search':
		search(stream_type)

	elif mode == 'categories':
		categories(stream_type)

	elif mode == 'fetch_categories' and 'fetch_ids' in param_keys and 'category_name' in param_keys:
		fetch_categories(params['fetch_ids'].split(','), compat._decode(params['category_name']), stream_type)

	elif mode == 'show_favs':
		show_favorites()

	elif mode == 'add_fav' and 'favorite_item' in param_keys:
		add_favorites(loads(params['favorite_item']))

	elif mode == 'drop_fav' and 'favorite_item' in param_keys:
		drop_favorites(loads(params['favorite_item']))
	elif mode == 'epg':
		params = {
			'refresh_path' : pluginurl + '?mode=epg',
			'refresh_interval' : '7200',
			'row_count' : '5',
		}
		executebuiltin('RunScript(script.module.uepg,' + get_uepg_params() + ')')

	else:
		index()
else:
	index()
