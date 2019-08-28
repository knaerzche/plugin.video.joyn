#!/usr/bin/python
# -*- coding: utf-8 -*-

from sys import argv, exit
import os.path
from xbmc import translatePath, executebuiltin, sleep as xbmc_sleep
from  xbmcgui import Dialog, ListItem, INPUT_ALPHANUM
from xbmcplugin import setResolvedUrl, addSortMethod
from xbmcplugin import SORT_METHOD_UNSORTED, SORT_METHOD_LABEL, SORT_METHOD_DATE, SORT_METHOD_DATEADDED, SORT_METHOD_EPISODE, SORT_METHOD_DURATION, SORT_METHOD_TITLE
from xbmcaddon import Addon
from datetime import datetime
from time import time
import dateutil.parser
from json import dumps, loads
from inputstreamhelper import Helper
from .const import CONST
from . import compat as compat
from . import cache as cache
from . import xbmc_helper as xbmc_helper
from . import request_helper as request_helper
from .lib_joyn import lib_joyn as lib_joyn


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

	xbmc_helper.log_debug('drop_favorites  - item: ' + dumps(favorite_item))
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
			if compat._encode(favorite_item['category_name']) == compat._encode(favorite['category_name']):
				favorites.remove(favorite)
				found = True

	favorites = xbmc_helper.set_json_data('favorites', favorites)

	if siltent == False and found is True:
		xbmc_helper.notification(xbmc_helper.translation('WATCHLIST'),
			xbmc_helper.translation('WL_TYPE_REMOVED').format(fav_type),
			default_icon)
		executebuiltin("Container.Refresh")
		xbmc_sleep(100)


def check_favorites(favorite_item):

	favorites = get_favorites()
	for favorite in favorites:
		if 'tv_show_id' in favorite_item.keys() and 'tv_show_id' in favorite.keys():
			if favorite_item['tv_show_id'] == favorite['tv_show_id'] and favorite_item['season_id'] == favorite['season_id']:
				return True
		elif 'channel_id' in favorite_item.keys() and 'channel_id' in favorite.keys():
			if favorite_item['channel_id'] == favorite['channel_id']:
				return True
		elif 'category_name' in favorite_item.keys() and 'category_name' in favorite.keys():
			if compat._encode(favorite_item['category_name']) == compat._encode(favorite['category_name']):
				return True

	return False


def show_lastseen(max_lastseen_count):

	lastseen = get_lastseen()
	list_items = []
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

		season_data = libjoyn.get_json_by_type('SEASONS', {'ids' : ','.join(season_ids)})

		for lastseen_item in lastseen:
			if (xbmc_helper.get_bool_setting('dont_show_watchlist_in_lastseen') is True and
				(check_favorites({'tv_show_id' : lastseen_item['tv_show_id'], 'season_id': None}) is True or
				 check_favorites({'tv_show_id' : lastseen_item['tv_show_id'], 'season_id': lastseen_item['season_id']}) is True)):
				continue

			found = False
			for season_item in season_data['data']:
				if season_item['id'] == lastseen_item['season_id'] and 'metadata' in season_item.keys() \
						and CONST['COUNTRIES'][libjoyn.config['country']]['language'] in season_item['metadata']:

					extracted_season_metadata = libjoyn.extract_metadata(
							metadata=season_item['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='SEASON')
					found = True
					if 'tvShow' in season_item.keys() and 'titles' in season_item['tvShow'].keys():
						for title_type, title in season_item['tvShow']['titles'].items():
							extracted_season_metadata['infoLabels'].update({
								'title' : HTMLParser().unescape(title) + ' - ' + extracted_season_metadata['infoLabels'].get('title','')
								})
							break

					extracted_season_metadata.update({'art' : libjoyn.merge_subtype_art('SEASONS', extracted_season_metadata['art'], season_item)})
					list_items.append(get_dir_entry(mode='video', season_id=lastseen_item['season_id'], tv_show_id=lastseen_item['tv_show_id'],
						metadata=extracted_season_metadata, override_fanart=default_fanart))

			if found is False:
				drop_lastseen(lastseen_item['tv_show_id'], lastseen_item['season_id'])

	return list_items

def show_favorites(title):

	favorites = get_favorites()
	list_items = []

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

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DATEADDED)

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
								merged_metadata['infoLabels'].update({'title' :
												xbmc_helper.translation('SEASON') + ': ' + merged_metadata['infoLabels']['title']})
								if 'added' in favorite_item.keys():
									merged_metadata['infoLabels'].update(
										{'dateadded' : datetime.fromtimestamp(favorite_item['added']).strftime('%Y-%m-%d %H:%M:%S')})
								found = True
								list_items.append(get_dir_entry(mode='video', season_id=favorite_item['season_id'], tv_show_id=favorite_item['tv_show_id'],
									metadata=merged_metadata, override_fanart=default_fanart))
								break
					else:
						found = True
						extracted_tvshow_metadata['infoLabels'].update({'title' :
							xbmc_helper.translation('TV_SHOW') + ': ' + extracted_tvshow_metadata['infoLabels']['title']})
						if 'added' in favorite_item.keys():
							extracted_tvshow_metadata['infoLabels'].update({'date' : datetime.fromtimestamp(int(favorite_item['added'])).strftime('%d.%m.%Y')})
						list_items.append(get_dir_entry(mode='season', tv_show_id=favorite_item['tv_show_id'],
							metadata=extracted_tvshow_metadata, override_fanart=default_fanart))
					break

		elif 'channel_id' in favorite_item.keys():
			for channel_item in brands['data']:
				if  str(channel_item['channelId']) == favorite_item['channel_id']:
					found = True
					extracted_channel_metadata = libjoyn.extract_metadata(
									metadata=channel_item['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='BRAND')
					extracted_channel_metadata['infoLabels'].update({'title' : xbmc_helper.translation('MEDIA_LIBRARY') + ': ' + extracted_channel_metadata['infoLabels']['title']})
					if 'added' in favorite_item.keys():
						extracted_channel_metadata['infoLabels'].update({'date' : datetime.fromtimestamp(int(favorite_item['added'])).strftime('%d.%m.%Y')})
					list_items.append(get_dir_entry(mode='tvshows', channel_id=channel_item['channelId'], metadata=extracted_channel_metadata))
					break

		elif 'category_name' in favorite_item.keys():
			for category_name, category_ids in categories.items():
				if category_name == favorite_item['category_name']:
					metadata={'infoLabels': {'title' : xbmc_helper.translation('CATEGORY') + ': ' + category_name, 'plot' : ''}, 'art': {}}
					if 'added' in favorite_item.keys():
						metadata['infoLabels'].update({'date' : datetime.fromtimestamp(int(favorite_item['added'])).strftime('%d.%m.%Y')})
					list_items.append(get_dir_entry(metadata=metadata, mode='fetch_categories',
						fetch_ids=','.join(category_ids), category_name=compat._encode(category_name)))
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

	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'WATCHLIST', title)


def get_uepg_params():

	params = 'json=' +  quote(dumps(libjoyn.get_uepg_data(pluginurl)))
	params += '&refresh_path=' + quote(pluginurl + '?mode=epg')
	params += '&refresh_interval=' + quote(str(CONST['UPEG_REFRESH_INTERVAL']))
	params += '&row_count=' + quote(str(CONST['UPEG_ROWCOUNT']))

	return params

def index():

	if not  xbmc_helper.addon_enabled(CONST['INPUTSTREAM_ADDON']):
		xbmc_helper.dialog_id('MSG_INPUSTREAM_NOT_ENABLED')
		exit(0)

	is_helper = Helper('mpd', drm='widevine')
	if not is_helper.check_inputstream():
		xbmc_helper.dialog_id('MSG_WIDEVINE_NOT_FOUND')
		exit(0)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)

	list_items = show_lastseen(xbmc_helper.get_int_setting('max_lastseen'))

	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title' : xbmc_helper.translation('MEDIA_LIBRARIES'),
					'plot' : xbmc_helper.translation('MEDIA_LIBRARIES_PLOT'),
					},'art': {}}, mode='channels', stream_type='VOD'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title' : xbmc_helper.translation('CATEGORIES'),
					'plot' : xbmc_helper.translation('CATEGORIES_PLOT'),
					}, 'art': {}}, mode='categories', stream_type='VOD'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title' : xbmc_helper.translation('WATCHLIST'),
					'plot' : xbmc_helper.translation('WATCHLIST_PLOT'),
					}, 'art': {}}, mode='show_favs'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title' : xbmc_helper.translation('SEARCH'),
					'plot' : xbmc_helper.translation('SEARCH_PLOT'),
					}, 'art': {}}, mode='search'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title' : xbmc_helper.translation('LIVE_TV'),
					'plot' : xbmc_helper.translation('LIVE_TV_PLOT'),
					}, 'art': {}}, mode='channels',stream_type='LIVE'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title' :  xbmc_helper.translation('TV_GUIDE'),
					'plot' : xbmc_helper.translation('TV_GUIDE_PLOT'),
					}, 'art': {}}, mode='epg',stream_type='LIVE'))

	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'INDEX')

def channels(stream_type, title):

	brands = libjoyn.get_brands()
	list_items = []

	if stream_type == 'LIVE':
		epg = libjoyn.get_epg()

	for brand in brands['data']:
		channel_id = str(brand['channelId'])
		for metadata_lang, metadata in brand['metadata'].items():
			if metadata_lang == CONST['COUNTRIES'][libjoyn.config['country']]['language']:
				extracted_metadata = libjoyn.extract_metadata(metadata=metadata, selection_type='BRAND')
				if stream_type == 'VOD' and metadata['hasVodContent'] == True:
					list_items.append(get_dir_entry(mode='tvshows', stream_type=stream_type, channel_id=channel_id,metadata=extracted_metadata))
				elif stream_type == 'LIVE' and 'livestreams' in metadata.keys():
					for livestream in metadata['livestreams']:
						stream_id = livestream['streamId']
						if channel_id in epg.keys():
							epg_metadata = libjoyn.extract_metadata_from_epg(epg[channel_id])
							extracted_metadata['infoLabels'].update(epg_metadata['infoLabels'])
							extracted_metadata['art'].update(epg_metadata['art'])
						list_items.append(get_dir_entry(is_folder=False, metadata=extracted_metadata,mode='play_video', video_id=stream_id, stream_type='LIVE'))
				break

	if stream_type == 'LIVE':
		xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'LIVE_TV', title)
	else:
		xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEORIES', title)


def tvshows(channel_id, title):

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
        addSortMethod(pluginhandle, SORT_METHOD_LABEL)

	tvshows = libjoyn.get_json_by_type('TVSHOW', {'channelId': channel_id})
	list_items = []

	for tvshow in tvshows['data']:
		tv_show_id = str(tvshow['id'])
		for metadata_lang, metadata in tvshow['metadata'].items():
			if metadata_lang == CONST['COUNTRIES'][libjoyn.config['country']]['language']:
				extracted_metadata = libjoyn.extract_metadata(metadata, 'TVSHOW')
				list_items.append(get_dir_entry(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata, override_fanart=default_fanart))

	list_items.append(get_favorite_entry({'channel_id' : channel_id}, 'MEDIA_LIBRARY'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def seasons(tv_show_id, title):


	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_TITLE)
	addSortMethod(pluginhandle, SORT_METHOD_DATEADDED)

	has_date_added = False
	seasons = libjoyn.get_json_by_type('SEASON', {'tvShowId' : tv_show_id})
	list_items = []

	for season in seasons['data']:
		season_id = season['id']
		for metadata_lang, metadata in season['metadata'].items():
			if metadata_lang == CONST['COUNTRIES'][libjoyn.config['country']]['language']:
				extracted_metadata = libjoyn.extract_metadata(metadata,'SEASON', season.get('visibilities', None));
				if 'dateadded' in extracted_metadata['infoLabels'].keys():
					has_date_added = True
				break
		extracted_metadata.update({'art' : libjoyn.merge_subtype_art('SEASON', extracted_metadata['art'], season)})
		list_items.append(get_dir_entry(mode='video', season_id=season_id, tv_show_id=tv_show_id,metadata=extracted_metadata, title_prefix=(title + ' - ')))

	list_items.append(get_favorite_entry({'tv_show_id' : tv_show_id, 'season_id': None}, 'TV_SHOW'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'SEASONS', title)



def videos(tv_show_id, season_id, title):

	xbmc_helper.log_debug('video : tv_show_id: ' + tv_show_id + 'season_id: ' + season_id)

	videos = libjoyn.get_json_by_type('VIDEO', {'tvShowId' : tv_show_id, 'seasonId' : season_id})
	list_items = []

	sort_methods = set([SORT_METHOD_UNSORTED, SORT_METHOD_LABEL])

	for video in videos['data']:
		availability_end = None
		video_id = video['id']
		cast = []

		for metadata_lang, metadata_values in video['metadata'].items():
			if metadata_lang == CONST['COUNTRIES'][libjoyn.config['country']]['language']:
				extracted_metadata = libjoyn.extract_metadata(metadata=metadata_values,selection_type='VIDEO');
				if 'broadcastDate' in metadata_values.keys():
					broadcastDate = datetime.fromtimestamp(metadata_values['broadcastDate'])
					extracted_metadata['infoLabels'].update({
						'premiered' : broadcastDate.strftime('%Y-%m-%d'),
						'date': broadcastDate.strftime('%Y-%m-%d'),
						'aired' : broadcastDate.strftime('%Y-%m-%d')
					})
					sort_methods.add(SORT_METHOD_DATE)
				if 'video' in metadata_values.keys() and 'ageRatings' in metadata_values['video'].keys():
					for age_rating in metadata_values['video']['ageRatings']:
						if 'minAge' in age_rating:
							fsk = str(age_rating['minAge'])
							if fsk is not '0':
								extracted_metadata['infoLabels'].update({'mpaa' : xbmc_helper.translation('MIN_AGE').format(fsk)})
								break

				if 'licenses' in metadata_values.keys():
					for license in  metadata_values['licenses']:
						if 'timeslots' in license.keys():
							for timeslot in license['timeslots']:
								if 'end' in timeslot.keys() and timeslot['end'] is not None and str(timeslot['end']).startswith('2286') is False:
									end_date = dateutil.parser.parse(timeslot['end'])
									if availability_end is None or end_date > availability_end:
										availability_end = end_date

				if 'cast' in metadata_values.keys():
					for actor in metadata_values['cast']:
						if 'name' in actor.keys():
							cast.append(actor['name'])
				if 'copyrights' in metadata_values.keys():
					extracted_metadata['infoLabels'].update({'studio' : ', '.join(metadata_values['copyrights'])})

				extracted_metadata['infoLabels'].update({'cast' : cast})

				break
		if availability_end is not None:
			extracted_metadata['infoLabels'].update({
							'plot' : compat._unicode(xbmc_helper.translation('VIDEO_AVAILABLE')).format(availability_end) + extracted_metadata['infoLabels'].get('plot', '')
				})

		extracted_metadata['infoLabels'].update({'genre' : []})
		if 'tvShow' in video.keys():
			if 'genres' in video['tvShow'].keys():
				for genre in video['tvShow']['genres']:
					extracted_metadata['infoLabels']['genre'].append(genre['title'])
			if 'titles' in video['tvShow'].keys():
				for title_key, title_value in video['tvShow']['titles'].items():
					if title_key == 'default':
						extracted_metadata['infoLabels'].update({'tvshowtitle' : HTMLParser().unescape(title_value)})
						break

		if 'season' in video.keys() and 'number' in video['season'].keys():
			extracted_metadata['infoLabels'].update({'season' : video['season']['number']})

		if 'episode' in video.keys():
			if 'number' in video['episode'].keys():
				extracted_metadata['infoLabels'].update({'episode' : video['episode']['number']})
				extracted_metadata['infoLabels'].update({'sortepisode' : video['episode']['number']})
				sort_methods.add(SORT_METHOD_EPISODE)
			if 'productionYear' in video['episode'].keys():
				extracted_metadata['infoLabels'].update({'year' : video['episode']['productionYear']})

		if 'duration' in video.keys():
			extracted_metadata['infoLabels'].update({'duration' : (video['duration']//1000)})
			sort_methods.add(SORT_METHOD_DURATION)

		#'mediatype' : 'episode',
		extracted_metadata['art'] = libjoyn.merge_subtype_art('VIDEO', extracted_metadata['art'], video)
		list_items.append(get_dir_entry(is_folder=False, mode='play_video', metadata=extracted_metadata, video_id=video_id))


	for sort_method in sort_methods:
		addSortMethod(pluginhandle, sort_method)

	list_items.append(get_favorite_entry({'tv_show_id' : tv_show_id , 'season_id' : season_id}, 'SEASON'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'EPISODES', title)


def play_video(video_id, stream_type):

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
					xbmc_helper.log_debug('SET DRM CERT: ' + video_data['certificateUrl'])
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


def search(stream_type, title):
	search_term = Dialog().input('Suche', type=INPUT_ALPHANUM)

	if len(search_term) > 0:
		request_params = {'search': search_term.lower(), 'hasVodContent': 'true'}
		tvshows = libjoyn.get_json_by_type(path_type='TVSHOW',additional_params=request_params)
		list_items = []
		if len(tvshows['data']) > 0:
			for tvshow in tvshows['data']:
				tv_show_id = str(tvshow['id'])
				if 'metadata' in tvshow.keys() and CONST['COUNTRIES'][libjoyn.config['country']]['language'] in tvshow['metadata'].keys():
					extracted_metadata = libjoyn.extract_metadata(metadata=tvshow['metadata'][CONST['COUNTRIES'][libjoyn.config['country']]['language']], selection_type='TVSHOW')
					list_items.append(get_dir_entry(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata))

			xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)

		else:
			return xbmc_helper.notification(
						xbmc_helper.translation('SEARCH'),
						 xbmc_helper.translation('MSG_NO_SEARCH_RESULTS').format(search_term),
						 default_icon
				)


def categories(stream_type, title):

	categories = libjoyn.get_categories()
	list_items = []

	for category_name, category_ids in categories.items():
		list_items.append(get_dir_entry(metadata={'infoLabels': {'title' : category_name, 'plot' : ''}, 'art': {}}, mode='fetch_categories', fetch_ids=','.join(category_ids),
			category_name=compat._encode(category_name)))

	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEORIES', title)




def fetch_categories(categories, category_name, stream_type, title):

	xbmc_helper.log_debug('fetch_categories - multithreading : ' + str(multi_threading))
	fetch_results = []
	list_items = []

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
				list_items.append(get_dir_entry(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata, override_fanart=default_fanart))

	list_items.append(get_favorite_entry({'category_name' : category_name }, 'CATEGORY'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEGORY', title)

def get_favorite_entry(favorite_item, favorite_type):

	fav_del_art = {'thumb' : xbmc_helper.get_media_filepath('fav_del_thumb.png'), 'icon' : xbmc_helper.get_media_filepath('fav_del_icon.png')}
	fav_add_art = {'thumb' : xbmc_helper.get_media_filepath('fav_add_thumb.png'), 'icon' : xbmc_helper.get_media_filepath('fav_add_icon.png')}

	if check_favorites(favorite_item) is False:
		return get_dir_entry(is_folder=False, metadata={'infoLabels': {
						'title' :  xbmc_helper.translation('ADD_TO_WATCHLIST'),
						'plot' : xbmc_helper.translation('ADD_TO_WATCHLIST_PRX').format(xbmc_helper.translation(favorite_type)),
						}, 'art': fav_add_art }, mode='add_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation(favorite_type))
	else:
		return get_dir_entry(is_folder=False,metadata={'infoLabels': {
						'title' : xbmc_helper.translation('REMOVE_FROM_WATCHLIST'),
						'plot' : xbmc_helper.translation('REMOVE_FROM_WATCHLIST_PRFX').format(xbmc_helper.translation(favorite_type)),
						}, 'art': fav_del_art }, mode='drop_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation(favorite_type))


def get_dir_entry(mode, metadata, is_folder=True, channel_id='', tv_show_id='', season_id='', video_id='', stream_type='VOD', fetch_ids='', override_fanart='',
			category_name='', fav_type='',  favorite_item=None, title_prefix=''):

	params = {
		'mode' : mode,
		'tv_show_id': tv_show_id,
		'season_id' : season_id,
		'video_id': video_id,
		'stream_type': stream_type,
		'channel_id': channel_id,
		'fetch_ids' : fetch_ids,
		'category_name' : category_name,
		'fav_type' : fav_type,
		'title' : compat._encode(title_prefix) + compat._encode(metadata['infoLabels']['title'])
	}

	if favorite_item is not None:
		params.update({'favorite_item' : dumps(favorite_item)})

	list_item = ListItem(metadata['infoLabels']['title'])
	list_item.setInfo(type='video', infoLabels=metadata['infoLabels'])

	if 'poster' not in metadata['art'] and 'thumb' in metadata['art']:
		metadata['art'].update({'poster' : metadata['art']['thumb']})
	elif 'thumb' not in metadata['art']:
		metadata['art'].update({ 'thumb' : default_logo})
		metadata['art'].update({ 'poster' : default_logo})

	if 'icon' not in metadata['art']:
		metadata['art'].update({ 'icon' : default_icon})

	if override_fanart != '':
		metadata['art'].update({'fanart': override_fanart})

	if 'fanart' not in metadata['art']:
		metadata['art'].update({'fanart': default_fanart})

	for art_key, art_value in metadata['art'].items():
		metadata['art'].update({art_key : request_helper.add_user_agend_header_string(art_value, libjoyn.config['USER_AGENT'])})

	list_item.setArt(metadata['art'])

	if (mode == 'play_video' and video_id is not ''):
		list_item.setProperty('IsPlayable', 'True')

	url = pluginurl+'?'
	url += urlencode(params)


	xbmc_helper.log_debug('get_dir_entry : ' + url + ' : ' + dumps(metadata))

	return (url,list_item,is_folder)

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
default_logo = xbmc_helper.get_media_filepath('logo.gif')

params = xbmc_helper.get_addon_params(pluginquery)
param_keys = params.keys()

if 'mode' in param_keys:

	mode = params['mode']

	if mode == 'clear_cache':
		clear_cache()

	elif mode == 'open_foreign_settings' and 'forein_addon_id' in param_keys:
		xbmc_helper.open_foreign_addon_settings(params['forein_addon_id'])

	else:
		libjoyn = lib_joyn(default_icon)

		stream_type = params.get('stream_type', 'VOD')
		title =  params.get('title', '')

		if mode == 'season' and 'tv_show_id' in param_keys:
			seasons(params['tv_show_id'], title)

		elif mode == 'video' and 'tv_show_id' in param_keys and 'season_id' in param_keys:
			videos(params['tv_show_id'],params['season_id'], title)

		elif mode == 'play_video' and 'video_id' in param_keys:
			play_video(params['video_id'], stream_type)

		elif mode == 'channels':
			channels(stream_type,title)

		elif mode == 'tvshows' and 'channel_id' in param_keys:
			tvshows(params['channel_id'], title)

		elif mode == 'search':
			search(stream_type, title)

		elif mode == 'categories':
			categories(stream_type,title)

		elif mode == 'fetch_categories' and 'fetch_ids' in param_keys and 'category_name' in param_keys:
			fetch_categories(params['fetch_ids'].split(','), compat._decode(params['category_name']), stream_type, title)

		elif mode == 'show_favs':
			show_favorites(title)

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
