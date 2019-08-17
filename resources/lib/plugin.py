#!/usr/bin/python
# -*- coding: utf-8 -*-

from sys import argv, exit
import os.path
from xbmc import translatePath, executebuiltin, sleep as xbmc_sleep
from  xbmcgui import Dialog, ListItem, INPUT_ALPHANUM
from xbmcplugin import endOfDirectory, setResolvedUrl, setContent, addDirectoryItem, addSortMethod
from xbmcplugin import SORT_METHOD_UNSORTED, SORT_METHOD_LABEL, SORT_METHOD_DATE, SORT_METHOD_EPISODE, SORT_METHOD_DURATION
from xbmcaddon import Addon
from datetime import datetime
from time import time, strptime
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


def add_favorites(favorite_item, fav_type=''):

	if check_favorites(favorite_item) is False:
		favorites = get_favorites()
		favorite_item.update({'added' :  time()})
		favorites.append(favorite_item)
		favorites = xbmc_helper.set_json_data('favorites', favorites)

		executebuiltin("Container.Refresh")
		xbmc_sleep(100)
		xbmc_helper.notification(xbmc_helper.translation('WATCHLIST'),
			xbmc_helper.translation('WL_TYPE_ADDED').format(fav_type),
			default_icon)


def drop_favorites(favorite_item, siltent=False, fav_type=''):

	favorites = get_favorites()
	found = False

	for favorite in favorites:
		if 'tv_show_id' in favorite_item.keys() and 'tv_show_id' in favorite.keys():
			if favorite_item['tv_show_id'] == favorite['tv_show_id'] and favorite_item['season_id'] == favorite['season_id']:
				favorites.remove(favorite)
				found = True
		elif 'channel_id' in favorite_item.keys() and 'channel_id' in favorite.keys():
			if favorite_item['channel_id'] == favorite['channel_id']:
				favorites.remove(favorite)
				found = True
		elif 'category_name' in favorite_item.keys() and 'category_name' in favorite.keys():
			if favorite_item['category_name'] == favorite['category_name']:
				favorites.remove(favorite)
				found = True

	favorites = xbmc_helper.set_json_data('favorites', favorites)

	if siltent == False and found is True:
		xbmc_helper.notification(xbmc_helper.translation('WATCHLIST'),
			xbmc_helper.translation('WL_TYPE_REMOVED').format(fav_type),
			default_icon)
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
			lastseen = lastseen[:max_lastseen_count]

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
				if tvshow_item['id'] == lastseen_item['tv_show_id'] and 'metadata' in tvshow_item.keys() \
					and CONST['COUNTRIES'][libjoyn.config['country']]['language'] in tvshow_item['metadata']:
					extracted_tvshow_metadata = libjoyn.extract_metadata(
							metadata=tvshow_item['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='TVSHOWS')
					for season_item in season_data['data']:
						if season_item['id'] == lastseen_item['season_id'] and 'metadata' in season_item.keys() \
								and CONST['COUNTRIES'][libjoyn.config['country']]['language'] in season_item['metadata']:

							extracted_season_metadata = libjoyn.extract_metadata(
									metadata=season_item['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='SEASON')
							found = True
							add_dir(mode='video', season_id=lastseen_item['season_id'], tv_show_id=lastseen_item['tv_show_id'],
								metadata=libjoyn.combine_tvshow_season_data(extracted_tvshow_metadata, extracted_season_metadata), parent_fanart=default_fanart)

			if found is False:
				drop_lastseen(lastseen_item['tv_show_id'], lastseen_item['season_id'])

def show_favorites():

	favorites = get_favorites()
	xbmc_helper.log_debug('show_favorites ' + dumps(favorites))

	if len(favorites) == 0:
		return xbmc_helper.notification(
				xbmc_helper.translation('WATCHLIST'),
				xbmc_helper.translation('MSG_NO_FAVS_YET'),
				default_icon)

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

	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DATE)

	for favorite_item in favorites:
		found = False
		if 'tv_show_id' in favorite_item.keys():
			for tvshow_item in tvshow_data['data']:
				if tvshow_item['id'] == favorite_item['tv_show_id'] and 'metadata' in tvshow_item.keys() and \
						CONST['COUNTRIES'][libjoyn.config['country']]['language'] in tvshow_item['metadata']:

					extracted_tvshow_metadata = libjoyn.extract_metadata(
								metadata=tvshow_item['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='TVSHOWS')
					if favorite_item['season_id'] is not None:
						for season_item in season_data['data']:
							if season_item['id'] == favorite_item['season_id'] and 'metadata' in season_item.keys() \
									and CONST['COUNTRIES'][libjoyn.config['country']]['language'] in season_item['metadata']:

								extracted_season_metadata = libjoyn.extract_metadata(
										metadata=season_item['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='SEASON')
								merged_metadata = libjoyn.combine_tvshow_season_data(extracted_tvshow_metadata,
											extracted_season_metadata)
								merged_metadata['infoLabels'].update({'Title' :
												xbmc_helper.translation('SEASON') + ': ' + merged_metadata['infoLabels']['Title']})
								if 'added' in favorite_item.keys():
									merged_metadata['infoLabels'].update({'Date' : datetime.fromtimestamp(favorite_item['added']).strftime('%d.%m.%Y')})
								found = True
								add_dir(mode='video', season_id=favorite_item['season_id'], tv_show_id=favorite_item['tv_show_id'],
									metadata=merged_metadata, parent_fanart=default_fanart)
								break
					else:
						found = True
						extracted_tvshow_metadata['infoLabels'].update({'Title' :
							xbmc_helper.translation('TV_SHOW') + ': ' + extracted_tvshow_metadata['infoLabels']['Title']})
						if 'added' in favorite_item.keys():
							extracted_tvshow_metadata['infoLabels'].update({'Date' : datetime.fromtimestamp(int(favorite_item['added'])).strftime('%d.%m.%Y')})
						add_dir(mode='season', tv_show_id=favorite_item['tv_show_id'], metadata=extracted_tvshow_metadata, parent_fanart=default_fanart)
					break

		elif 'channel_id' in favorite_item.keys():
			for channel_item in brands['data']:
				if  str(channel_item['channelId']) == favorite_item['channel_id']:
					found = True
					extracted_channel_metadata = libjoyn.extract_metadata(
									metadata=channel_item['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='BRAND')
					extracted_channel_metadata['infoLabels'].update({'Title' : xbmc_helper.translation('MEDIA_LIBRARY') + ': ' + extracted_channel_metadata['infoLabels']['Title']})
					if 'added' in favorite_item.keys():
						extracted_channel_metadata['infoLabels'].update({'Date' : datetime.fromtimestamp(int(favorite_item['added'])).strftime('%d.%m.%Y')})
					add_dir(mode='tvshows', channel_id=channel_item['channelId'], metadata=extracted_channel_metadata)
					break

		elif 'category_name' in favorite_item.keys():
			for category_name, category_ids in categories.items():
				if category_name == favorite_item['category_name']:
					metadata={'infoLabels': {'Title' : xbmc_helper.translation('CATEGORY') + ': ' + category_name, 'Plot' : ''}, 'art': {}}
					if 'added' in favorite_item.keys():
						metadata['infoLabels'].update({'Date' : datetime.fromtimestamp(int(favorite_item['added'])).strftime('%d.%m.%Y')})
					add_dir(metadata=metadata, mode='fetch_categories',
						fetch_ids=','.join(category_ids), category_name=compat._encode(category_name))
					found = True
					break
		if found is False:
			needs_drop = True
			drop_favorites(favorite_item, True)

	if needs_drop is True:
		xbmc_helper.notification(
				xbmc_helper.translation('WATCHLIST'),
				xbmc_helper.translation('MSG_FAVS_UNAVAILABLE'),
				default_icon)

	endOfDirectory(handle=pluginhandle,cacheToDisc=False)


def get_uepg_params():

	params = 'json=' +  quote(dumps(libjoyn.get_uepg_data(pluginurl)))
	params += '&refresh_path=' + quote(pluginurl + '?mode=epg')
	params += '&refresh_interval=' + quote(str(CONST['UPEG_REFRESH_INTERVAL']))
	params += '&row_count=' + quote(str(CONST['UPEG_ROWCOUNT']))

	return params

def index():

	show_lastseen(xbmc_helper.get_int_setting('max_lastseen'))

	add_dir(metadata={'infoLabels': {
					'Title' : xbmc_helper.translation('MEDIA_LIBRARIES'),
					'Plot' : xbmc_helper.translation('MEDIA_LIBRARIES_PLOT'),
					},'art': {}}, mode='channels', stream_type='VOD')
	add_dir(metadata={'infoLabels': {
					'Title' : xbmc_helper.translation('CATEGORIES'),
					'Plot' : xbmc_helper.translation('CATEGORIES_PLOT'),
					}, 'art': {}}, mode='categories', stream_type='VOD')
	add_dir(metadata={'infoLabels': {
					'Title' : xbmc_helper.translation('WATCHLIST'),
					'Plot' : xbmc_helper.translation('WATCHLIST_PLOT'),
					}, 'art': {}}, mode='show_favs')
	add_dir(metadata={'infoLabels': {
					'Title' : xbmc_helper.translation('SEARCH'),
					'Plot' : xbmc_helper.translation('SEARCH_PLOT'),
					}, 'art': {}}, mode='search')
	add_dir(metadata={'infoLabels': {
					'Title' : xbmc_helper.translation('LIVE_TV'),
					'Plot' : xbmc_helper.translation('LIVE_TV_PLOT'),
					}, 'art': {}}, mode='channels',stream_type='LIVE')
	add_dir(metadata={'infoLabels': {
					'Title' :  xbmc_helper.translation('TV_GUIDE'),
					'Plot' : xbmc_helper.translation('TV_GUIDE_PLOT'),
					}, 'art': {}}, mode='epg',stream_type='LIVE')

	endOfDirectory(handle=pluginhandle,cacheToDisc=False)


def channels(stream_type):

	brands = libjoyn.get_brands()

	if stream_type == 'LIVE':
		epg = libjoyn.get_epg()

	for brand in brands['data']:
		channel_id = str(brand['channelId'])
		for metadata_lang, metadata in brand['metadata'].items():
			if metadata_lang == CONST['COUNTRIES'][libjoyn.config['country']]['language']:
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
			if metadata_lang == CONST['COUNTRIES'][libjoyn.config['country']]['language']:
				extracted_metadata = libjoyn.extract_metadata(metadata, 'TVSHOW')
				add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata, parent_fanart=fanart_img)
	favorite_item = {'channel_id' : channel_id}

	if check_favorites(favorite_item) is False:
		add_link(metadata={'infoLabels': {
							'Title' : xbmc_helper.translation('ADD_TO_WATCHLIST'),
							'Plot' : xbmc_helper.translation('ADD_TO_WATCHLIST_PRX').format(xbmc_helper.translation('MEDIA_LIBRARY'))
						 }, 'art': {}}, mode='add_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation('MEDIA_LIBRARY'))
	else:
		add_link(metadata={'infoLabels': {
							'Title' : xbmc_helper.translation('REMOVE_FROM_WATCHLIST'),
							'Plot' : xbmc_helper.translation('REMOVE_FROM_WATCHLIST_PRFX').format(xbmc_helper.translation('MEDIA_LIBRARY'))
						}, 'art': {}}, mode='drop_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation('MEDIA_LIBRARY'))

	endOfDirectory(pluginhandle)


def seasons(tv_show_id, parent_fanart_img, parent_img):

	seasons = libjoyn.get_json_by_type('SEASON', {'tvShowId' : tv_show_id})
	for season in seasons['data']:
		xbmc_helper.log_debug('SEASON : ' + dumps(season))
		season_id = season['id']
		for metadata_lang, metadata in season['metadata'].items():
			if metadata_lang == CONST['COUNTRIES'][libjoyn.config['country']]['language']:
				extracted_metadata = libjoyn.extract_metadata(metadata,'SEASON');
				extracted_metadata['art'].update({'thumb' : parent_img, 'fanart' : parent_fanart_img});
				add_dir(mode='video', season_id=season_id, tv_show_id=tv_show_id,metadata=extracted_metadata)
				break

	favorite_item={'tv_show_id' : tv_show_id, 'season_id': None}
	if check_favorites(favorite_item) is False:
		add_link(metadata={'infoLabels': {
							'Title' : xbmc_helper.translation('ADD_TO_WATCHLIST'),
							'Plot' : xbmc_helper.translation('ADD_TO_WATCHLIST_PRX').format(xbmc_helper.translation('TV_SHOW'))
						}, 'art': {}}, mode='add_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation('TV_SHOW'))
	else:
		add_link(metadata={'infoLabels': {
							'Title' : xbmc_helper.translation('REMOVE_FROM_WATCHLIST'),
							'Plot' :  xbmc_helper.translation('REMOVE_FROM_WATCHLIST_PRFX').format(xbmc_helper.translation('TV_SHOW'))
						}, 'art': {}}, mode='drop_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation('TV_SHOW'))

	endOfDirectory(pluginhandle)


def videos(tv_show_id, season_id, fanart_img):

	xbmc_helper.log_debug('video : tv_show_id: ' + tv_show_id + 'season_id: ' + season_id)
	videos = libjoyn.get_json_by_type('VIDEO', {'tvShowId' : tv_show_id, 'seasonId' : season_id})

	sort_methods = set([SORT_METHOD_UNSORTED, SORT_METHOD_LABEL])
	availability_end = None

	for video in videos['data']:
		video_id = video['id']

		for metadata_lang, metadata_values in video['metadata'].items():
			if metadata_lang == CONST['COUNTRIES'][libjoyn.config['country']]['language']:
				extracted_metadata = libjoyn.extract_metadata(metadata=metadata_values,selection_type='VIDEO');
				if 'broadcastDate' in metadata_values.keys():
					broadcastDate = datetime.fromtimestamp(metadata_values['broadcastDate']).strftime('%d.%m.%Y')
					extracted_metadata['infoLabels'].update({'Premiered' : broadcastDate, 'Date': broadcastDate})
					sort_methods.add(SORT_METHOD_DATE)
				if 'video' in metadata_values.keys() and 'ageRatings' in metadata_values['video'].keys():
					for age_rating in metadata_values['video']['ageRatings']:
						if 'minAge' in age_rating:
							fsk = str(age_rating['minAge'])
							if fsk is not '0':
								extracted_metadata['infoLabels'].update({'Mpaa' : xbmc_helper.translation('MIN_AGE').format(fsk)})
								break

				if 'licenses' in metadata_values.keys():
					for license in  metadata_values['licenses']:
						if 'timeslots' in license.keys():
							for timeslot in license['timeslots']:
								if 'end' in timeslot.keys() and timeslot['end'] is not None and str(timeslot['end']).startswith('2286') is False:
									end_date = datetime(*(strptime(timeslot['end'], '%Y-%m-%d %H:%M:%S')[0:6]))
									if availability_end is None or end_date > availability_end:
										availability_end = end_date
				break
		if availability_end is not None:
			extracted_metadata['infoLabels'].update({
							'Plot' : compat._unicode(xbmc_helper.translation('VIDEO_AVAILABLE')).format(availability_end) + extracted_metadata['infoLabels'].get('Plot', '')
				})

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
			if 'brand' in video['tvShow'].keys():
				extracted_metadata['infoLabels'].update({'Studio' : video['tvShow']['brand']})

		if 'season' in video.keys() and 'number' in video['season'].keys():
			extracted_metadata['infoLabels'].update({'Season' : video['season']['number']})

		if 'episode' in video.keys():
			if 'number' in video['episode'].keys():
				extracted_metadata['infoLabels'].update({'Episode' : video['episode']['number']})
				sort_methods.add(SORT_METHOD_EPISODE)
			if 'productionYear' in video['episode'].keys():
				extracted_metadata['infoLabels'].update({'Year' : video['episode']['productionYear']})

		if 'duration' in video.keys():
			extracted_metadata['infoLabels'].update({'Duration' : (video['duration']//1000)})
			sort_methods.add(SORT_METHOD_DURATION)

		extracted_metadata['infoLabels'].update({'mediatype' : 'episode'});
		add_link(mode='play_video', metadata=extracted_metadata, video_id=video_id,parent_fanart=fanart_img)

	favorite_item = {'tv_show_id' : tv_show_id , 'season_id' : season_id}
	if check_favorites(favorite_item) is False:
		add_link(metadata={'infoLabels': {
							'Title' :  xbmc_helper.translation('ADD_TO_WATCHLIST'),
							'Plot' : xbmc_helper.translation('ADD_TO_WATCHLIST_PRX').format(xbmc_helper.translation('SEASON'))
						}, 'art': {}}, mode='add_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation('SEASON'))
	else:
		add_link(metadata={'infoLabels': {
							'Title' :  xbmc_helper.translation('REMOVE_FROM_WATCHLIST'),
							'Plot' : xbmc_helper.translation('REMOVE_FROM_WATCHLIST_PRFX').format(xbmc_helper.translation('SEASON'))
						},'art': {}}, mode='drop_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation('SEASON'))

	for sort_method in sort_methods:
		addSortMethod(pluginhandle, sort_method)

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
					list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.server_certificate',
						request_helper.add_user_agend_header_string(video_data['certificateUrl'], libjoyn.config['USER_AGENT']))
		else:
			xbmc_helper.notification(
						xbmc_helper.translation('ERROR').format('Video-Stream'),
						xbmc_helper.translation('MSG_ERROR_NO_VIDEOSTEAM')
				)
			xbmc_helper.log_error('Could not get valid MPD')
			succeeded = False

	else:
		return list_item.setPath(path=add_user_agend_header_string(video_data['videoUrl'],libjoyn.config['USER_AGENT']))

	if succeeded is True and 'tv_show_id' in video_data.keys() and 'season_id' in video_data.keys():
		add_lastseen(video_data['tv_show_id'], video_data['season_id'], CONST['LASTSEEN_ITEM_COUNT'])

	setResolvedUrl(pluginhandle, succeeded, list_item)


def search(stream_type='VOD'):
	search_term = Dialog().input('Suche', type=INPUT_ALPHANUM)

	if len(search_term) > 0:
		request_params = {'search': search_term.lower(), 'hasVodContent': 'true'}
		tvshows = libjoyn.get_json_by_type(path_type='TVSHOW',additional_params=request_params)
		if len(tvshows['data']) > 0:
			for tvshow in tvshows['data']:
				tv_show_id = str(tvshow['id'])
				if 'metadata' in tvshow.keys() and CONST['COUNTRIES'][libjoyn.config['country']]['language'] in tvshow['metadata'].keys():
					extracted_metadata = libjoyn.extract_metadata(metadata=tvshow['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='TVSHOW')
					add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata,parent_fanart=default_fanart)
			endOfDirectory(handle=pluginhandle)
		else:
			return xbmc_helper.notification(
						xbmc_helper.translation('SEARCH'),
						 xbmc_helper.translation('MSG_NO_SEARCH_RESULTS').format(search_term),
						 default_icon
				)


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
			if 'metadata' in tvshow.keys() and CONST['COUNTRIES'][libjoyn.config['country']]['language'] in tvshow['metadata'].keys():
				extracted_metadata = libjoyn.extract_metadata(metadata=tvshow['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='TVSHOW')
				add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata,parent_fanart=default_fanart)

	favorite_item = {'category_name' : category_name }
	if check_favorites(favorite_item) is False:
		add_link(metadata={'infoLabels': {
						'Title' :  xbmc_helper.translation('ADD_TO_WATCHLIST'),
						'Plot' : xbmc_helper.translation('ADD_TO_WATCHLIST_PRX').format(xbmc_helper.translation('CATEGORY')),
						}, 'art': {}}, mode='add_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation('CATEGORY'))
	else:
		add_link(metadata={'infoLabels': {
						'Title' : xbmc_helper.translation('REMOVE_FROM_WATCHLIST'),
						'Plot' : xbmc_helper.translation('REMOVE_FROM_WATCHLIST_PRFX').format(xbmc_helper.translation('CATEGORY')),
						}, 'art': {}}, mode='drop_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation('CATEGORY'))

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

	if 'clearlogo' not in metadata['art']:
		 metadata['art'].update({ 'clearlogo' : metadata['art']['icon']})

	if 'fanart' not in metadata['art']:
		if parent_fanart is not '':
			metadata['art'].update({'fanart': parent_fanart})
		else:
			metadata['art'].update({'fanart': default_fanart})

	params.update({'parent_img': metadata['art']['poster']})
	params.update({'parent_fanart': metadata['art']['fanart']})

	if 'fanart' in metadata['art'] and parent_fanart is not '':
		metadata['art'].update({'fanart': parent_fanart})

	for art_key, art_value in metadata['art'].items():
		metadata['art'].update({art_key : request_helper.add_user_agend_header_string(art_value, libjoyn.config['USER_AGENT'])})

	list_item.setArt(metadata['art'])

	url = pluginurl+'?'
	url += urlencode(params)

	return addDirectoryItem(handle=pluginhandle, url=url, listitem=list_item, isFolder=True)



def add_link(mode, video_id='', metadata={}, stream_type='VOD', parent_fanart='', favorite_item=None, fav_type=''):

	params = {
		'video_id': video_id,
		'mode' : mode,
		'stream_type': stream_type,
		'fav_type' : fav_type,
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
		list_item.setProperty('IsPlayable', 'True')

	for art_key, art_value in metadata['art'].items():
		metadata['art'].update({art_key : request_helper.add_user_agend_header_string(art_value, libjoyn.config['USER_AGENT'])})

	list_item.setArt(metadata['art'])

	return addDirectoryItem(handle=pluginhandle, url=url, listitem=list_item, isFolder=False)


def clear_cache():
	if xbmc_helper.remove_dir(CONST['CACHE_DIR']) is True:
		xbmc_helper.notification('Cache', xbmc_helper.translation('CACHE_WAS_CLEARED'), default_icon)
	else:
		xbmc_helper.notification('Cache', xbmc_helper.translation('CACHE_COULD_NOT_BE_CLEARED'))


pluginurl = argv[0]
pluginhandle = int(argv[1])
pluginquery = argv[2]
addon = Addon()
default_icon = addon.getAddonInfo('icon')
default_fanart = addon.getAddonInfo('fanart')
default_logo = translatePath(os.path.join(addon.getAddonInfo('path'), 'resources','logo.gif')).encode('utf-8').decode('utf-8')
params = xbmc_helper.get_addon_params(pluginquery)
param_keys = params.keys()
setContent(pluginhandle, 'tvshows')

if not  xbmc_helper.addon_enabled(CONST['INPUTSTREAM_ADDON']):
	xbmc_helper.dialog_id('MSG_INPUSTREAM_NOT_ENABLED')
	exit(0)

is_helper = Helper('mpd', drm='widevine')
if not is_helper.check_inputstream():
	xbmc_helper.dialog_id('MSG_WIDEVINE_NOT_FOUND')
	exit(0)

if 'mode' in param_keys:

	mode = params['mode']

	if mode == 'clear_cache':
		clear_cache()

	elif mode == 'open_foreign_settings' and 'forein_addon_id' in param_keys:
		xbmc_helper.open_foreign_addon_settings(params['forein_addon_id'])

	else:
		libjoyn = lib_joyn(default_icon)

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

		elif mode == 'add_fav' and 'favorite_item' in param_keys and 'fav_type' in param_keys:
			add_favorites(loads(params['favorite_item']), params['fav_type'])

		elif mode == 'drop_fav' and 'favorite_item' in param_keys and 'fav_type' in param_keys:
			drop_favorites(favorite_item=loads(params['favorite_item']),fav_type=params['fav_type'])

		elif mode == 'epg':
			executebuiltin('RunScript(script.module.uepg,' + get_uepg_params() + ')')

		else:
			index()
else:
	libjoyn = lib_joyn(default_icon)
	index()
