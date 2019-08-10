#!/usr/bin/python
# -*- coding: utf-8 -*-

from sys import argv, exit
import os.path
from xbmc import translatePath
from  xbmcgui import Dialog, ListItem, INPUT_ALPHANUM
from xbmcplugin import endOfDirectory, setResolvedUrl, setContent, addDirectoryItem
from xbmcaddon import Addon
from datetime import datetime
from inputstreamhelper import Helper
from resources.lib.const import CONST
import resources.lib.compat as compat
import resources.lib.cache as cache
import resources.lib.xbmc_helper as xbmc_helper
import resources.lib.request_helper as request_helper
from resources.lib.lib_joyn import lib_joyn as lib_joyn

if compat.PY2:
	from urllib import urlencode
	from HTMLParser import HTMLParser
elif compat.PY3:
	from urllib.parse import urlencode
	from html.parser import HTMLParser


try:
	from multiprocessing.dummy import Pool as ThreadPool
	from multiprocessing import cpu_count
	from functools import partial
	multi_threading = True
except ImportError:
	multi_threading = False
	pass

def index():

	add_dir(metadata={'infoLabels': {'Title' : 'Mediatheken', 'Plot' : 'Mediatheken von www.joyn.de'},'art': {}}, mode='channels', stream_type='VOD')
	add_dir(metadata={'infoLabels': {'Title' : 'Rubriken', 'Plot' : 'Mediatheken gruppiert in Rubriken'}, 'art': {}}, mode='categories', stream_type='VOD')
	add_dir(metadata={'infoLabels': {'Title' : 'Suche', 'Plot' : 'Suche in den Mediatheken'}, 'art': {}}, mode='search')
	add_dir(metadata={'infoLabels': {'Title' : 'Live TV', 'Plot' : 'Live TV'}, 'art': {}}, mode='channels',stream_type='LIVE')

	endOfDirectory(pluginhandle)


def channels(stream_type):

	cached_brands = cache.get_json('BRANDS')
	if cached_brands['data'] is not None and cached_brands['is_expired'] is False:
		brands = cached_brands['data']
	else:
		brands = libjoyn.get_json_by_type('BRAND')
		cache.set_json('BRANDS', brands)

	if stream_type == 'LIVE':
		cached_epg =  cache.get_json('EPG')

		if cached_epg['data'] is not None and cached_epg['is_expired'] is False:
			epg = cached_epg['data']
		else:
			epg = libjoyn.get_epg()
			cache.set_json('EPG',epg)

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

	endOfDirectory(pluginhandle)


def play_video(video_id, stream_type='VOD'):

	xbmc_helper.log_debug('play_video: video_id: ' + video_id)
	list_item = ListItem()
	video_data = libjoyn.get_video_data(video_id, stream_type)

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

	else:
		return list_item.setPath(path=video_data['videoUrl'] + '|' + request_helper.get_header_string({'User-Agent' : libjoyn.config['USER_AGENT']}))

	setResolvedUrl(pluginhandle, True, list_item)


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

	cats = libjoyn.get_joyn_json_response(CONST['MIDDLEWARE_URL']  + 'ui?path=/')
	if 'blocks' in cats.keys():
		for block in cats['blocks']:
			if 'type' in block.keys() and 'configuration' in block.keys() and block['type'] == 'StandardLane':
				cat_name = block['configuration']['Headline']
				fetch_ids = []
				for block_item in block['items']:
					fetch_ids.append(block_item['fetch']['id'])
				add_dir(metadata={'infoLabels': {'Title' : cat_name, 'description' : ''}, 'art': {}}, mode='fetch_categories', fetch_ids=','.join(fetch_ids))

		endOfDirectory(handle=pluginhandle)


def fetch_categories(categories, stream_type='VOD'):

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
	endOfDirectory(handle=pluginhandle)


def add_dir(mode, metadata, channel_id='', tv_show_id='', season_id='', video_id='', stream_type='VOD', fetch_ids='', parent_fanart=''):

	params = {
		'mode' : mode,
		'tv_show_id': tv_show_id,
		'season_id' : season_id,
		'video_id': video_id,
		'stream_type': stream_type,
		'channel_id': channel_id,
		'fetch_ids' : fetch_ids
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



def add_link(mode, video_id, metadata, stream_type='VOD', parent_fanart=''):

	url = pluginurl+'?'
	url += urlencode({
		'video_id': video_id,
		'mode' : mode,
		'stream_type': stream_type,
	})

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

	if 'fanart' in metadata['art'] and parent_fanart is not '':
		metadata['art'].update({'fanart': parent_fanart})

	list_item.setArt(metadata['art'])
	list_item.setProperty('IsPlayable', 'True')

	return addDirectoryItem(handle=pluginhandle, url=url, listitem=list_item)

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
	elif mode == 'fetch_categories' and 'fetch_ids' in param_keys:
		fetch_categories(params['fetch_ids'].split(','), stream_type)
	else:
		index()
else:
	index()
