# -*- coding: utf-8 -*-

from sys import argv, exit
import os.path
from xbmc import translatePath, executebuiltin, sleep as xbmc_sleep
from  xbmcgui import Dialog, ListItem, INPUT_ALPHANUM
from xbmcplugin import setResolvedUrl, addSortMethod
from xbmcplugin import SORT_METHOD_UNSORTED, SORT_METHOD_LABEL, SORT_METHOD_DATE, \
	SORT_METHOD_DATEADDED, SORT_METHOD_EPISODE, SORT_METHOD_DURATION, SORT_METHOD_TITLE
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
elif compat.PY3:
	from urllib.parse import urlencode, quote


def get_lastseen():

	lastseen = xbmc_helper.get_json_data('lastseen')

	if lastseen is not None and len(lastseen) > 0:
		return sorted(lastseen, key=lambda k: k['lastseen'], reverse=True)

	return []


def add_lastseen(max_lastseen, season_id=None, compilation_id=None):

	if max_lastseen > 0:
		found_in_lastseen = False
		lastseen = get_lastseen()

		if lastseen is None:
			lastseen = []

		for idx, lastseen_item in enumerate(lastseen):
			if season_id is not None and 'season_id' in lastseen_item.keys() and lastseen_item['season_id'] == season_id or \
				compilation_id is not None and 'compilation_id' in lastseen_item.keys() and lastseen_item['compilation_id'] == compilation_id:

				lastseen[idx]['lastseen'] = time()
				found_in_lastseen = True
				break

		if found_in_lastseen is False:
			if season_id is not None:
				lastseen.append({'season_id': season_id, 'lastseen': time()})
			elif compilation_id is not None:
				lastseen.append({'compilation_id': compilation_id, 'lastseen': time()})

		lastseen = sorted(lastseen, key=lambda k: k['lastseen'], reverse=True)

		if len(lastseen) > max_lastseen:
			lastseen = lastseen[:(max_lastseen-1)]

		xbmc_helper.set_json_data('lastseen', lastseen)


def drop_lastseen(compilation_id=None, season_id=None):

	found_in_lastseen = False
	lastseen = get_lastseen()

	for lastseen_item in lastseen:
		if season_id is not None and 'season_id' in lastseen_item.keys() \
			and lastseen_item['season_id'] == season_id:

			lastseen.remove(lastseen_item)

		elif compilation_id is not None and  'compilation_id' in lastseen_item.keys() \
			and lastseen_item['compilation_id'] == compilation_id:

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
		favorite_item.update({'added':  time()})
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

		if 'season_id' in favorite_item.keys() and 'season_id' in favorite.keys() \
			and favorite_item['season_id'] == favorite['season_id']:

				favorites.remove(favorite)
				found = True

		elif 'tv_show_id' in favorite_item.keys() and 'tv_show_id' in favorite.keys() \
			and favorite_item['tv_show_id'] == favorite['tv_show_id']:

				favorites.remove(favorite)
				found = True

		elif 'channel_id' in favorite_item.keys() and 'channel_id' in favorite.keys() \
			and favorite_item['channel_id'] == favorite['channel_id']:

				favorites.remove(favorite)
				found = True

		elif 'compilation_id' in favorite_item.keys() and 'compilation_id' in favorite.keys() \
			and favorite_item['compilation_id'] == favorite['compilation_id']:

				favorites.remove(favorite)
				found = True

		elif 'block_id' in favorite_item.keys() and 'block_id' in favorite.keys() \
			and favorite_item['block_id'] == favorite['block_id']:

				favorites.remove(favorite)
				found = True

		elif 'category_name' in favorite_item.keys() and 'category_name' in favorite.keys() \
			and favorite_item['category_name'] == favorite['category_name']:

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
		if 'season_id' in favorite_item.keys() and 'season_id' in favorite.keys() \
			and favorite_item['season_id'] == favorite['season_id']:

			return True

		elif 'tv_show_id' in favorite_item.keys() and 'tv_show_id' in favorite.keys() \
			and favorite_item['tv_show_id'] == favorite['tv_show_id']:

			return True

		elif 'block_id' in favorite_item.keys() and 'block_id' in favorite.keys() \
			and favorite_item['block_id'] == favorite['block_id']:

			return True

		elif 'compilation_id' in favorite_item.keys() and 'compilation_id' in favorite.keys() \
			and favorite_item['compilation_id'] == favorite['compilation_id']:

			return True

		elif 'channel_id' in favorite_item.keys() and 'channel_id' in favorite.keys() \
			and favorite_item['channel_id'] == favorite['channel_id']:

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
		for lastseen_item in lastseen:

			found = False

			if lastseen_item.get('season_id', None) is not None:
				if xbmc_helper.get_bool_setting('dont_show_watchlist_in_lastseen') is True and \
					check_favorites({'seasonId': lastseen_item['season_id']}) is True:

					continue

				season_data = libjoyn.get_graphql_response('EPISODES', {'seasonId': lastseen_item['season_id'], 'first': 1})
				if season_data.get('season', None) is not None and season_data.get('season').get('episodes', None) is not None and len(season_data['season']['episodes']) > 0:
					season_metadata = libjoyn.get_metadata(season_data['season']['episodes'][0]['series'], 'TVSHOW')

					season_metadata['infoLabels'].update({'title':
						xbmc_helper.translation('CONTINUE_WATCHING').format(
							compat._encode(season_metadata['infoLabels'].get('title','')
								+ ' - ' + xbmc_helper.translation('SEASON_NO').format(str(season_data['season']['number']))))
							})
					list_items.append(get_dir_entry(
						mode='season_episodes',
						season_id=lastseen_item['season_id'],
						metadata=season_metadata,
						override_fanart=default_fanart,
					))

					found = True

			elif lastseen_item.get('compilation_id', None) is not None:

				if xbmc_helper.get_bool_setting('dont_show_watchlist_in_lastseen') is True and \
					check_favorites({'compilation_id': lastseen_item['compilation_id']}) is True:

					continue

				compilation_data = libjoyn.get_graphql_response('COMPILATION_ITEMS', {'id': lastseen_item['compilation_id'], 'first': 1})
				if compilation_data.get('compilation', None) is not None and compilation_data.get('compilation').get('compilationItems', None) is not None \
					and len(compilation_data['compilation']['compilationItems']) > 0:

					found = True
					compilation_metadata = libjoyn.get_metadata(compilation_data['compilation']['compilationItems'][0]['compilation'], 'TVSHOW')
					compilation_metadata['infoLabels'].update({'title': xbmc_helper.translation('CONTINUE_WATCHING').format(
							compat._encode(compilation_metadata['infoLabels'].get('title',''))
						)})
					list_items.append(get_dir_entry(
						mode='compilation_items',
						compilation_id=lastseen_item['compilation_id'],
						metadata=compilation_metadata,
						override_fanart=default_fanart
					))


			if found is False:
				if 'season_id' in lastseen_item.keys():
					drop_lastseen(season_id=lastseen_item['season_id'])
				elif 'compilation_id' in lastseen_item.keys():
					drop_lastseen(compilation_id=lastseen_item['compilation_id'])

	return list_items


def show_favorites(title):

	favorites = get_favorites()
	list_items = []

	if len(favorites) == 0:
		return xbmc_helper.notification(
				xbmc_helper.translation('WATCHLIST'),
				xbmc_helper.translation('MSG_NO_FAVS_YET'),
				default_icon)
	needs_drop = False

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DATEADDED)

	for favorite_item in favorites:
		found = False
		if favorite_item.get('season_id', None) is not None:
			season_data = libjoyn.get_graphql_response('EPISODES', {'seasonId': favorite_item['season_id'], 'first': 1})
			if season_data.get('season', None) is not None and season_data.get('season').get('episodes', None) is not None and len(season_data['season']['episodes']) > 0:
				found = True
				season_metadata = libjoyn.get_metadata(season_data['season']['episodes'][0]['series'], 'TVSHOW')
				season_metadata['infoLabels'].update({'title':
					season_metadata['infoLabels'].get('title','')
						+ ' - ' + xbmc_helper.translation('SEASON_NO').format(str(season_data['season']['number'])),
				 })

				if 'added' in favorite_item.keys():
					season_metadata.update({'dateadded': datetime.fromtimestamp(favorite_item['added']).strftime('%Y-%m-%d %H:%M:%S')})

				list_items.append(get_dir_entry(
					mode='season_episodes',
					season_id=favorite_item['season_id'],
					metadata=season_metadata,
					override_fanart=default_fanart,
				))

		elif favorite_item.get('tv_show_id', None) is not None:
			seasons = libjoyn.get_graphql_response('SEASONS', {'seriesId': favorite_item['tv_show_id']})
			if seasons.get('series', None) is not None:
				found = True
				tvshow_metadata = libjoyn.get_metadata(seasons['series'],'TVSHOW')

				if 'added' in favorite_item.keys():
					tvshow_metadata.update({'dateadded': datetime.fromtimestamp(favorite_item['added']).strftime('%Y-%m-%d %H:%M:%S')})

				list_items.append(get_dir_entry
					(mode='season',
					tv_show_id=favorite_item['tv_show_id'],
					metadata=tvshow_metadata,
					override_fanart=default_fanart
				))

		elif favorite_item.get('compilation_id', None) is not None:
			compilation_data = libjoyn.get_graphql_response('COMPILATION_ITEMS', {'id': favorite_item['compilation_id'], 'first': 1})
			if compilation_data.get('compilation', None) is not None and compilation_data.get('compilation').get('compilationItems', None) is not None \
				and len(compilation_data['compilation']['compilationItems']) > 0:

				found = True
				compilation_metadata = libjoyn.get_metadata(compilation_data['compilation']['compilationItems'][0]['compilation'], 'TVSHOW')

				if 'added' in favorite_item.keys():
					compilation_metadata.update({'dateadded': datetime.fromtimestamp(favorite_item['added']).strftime('%Y-%m-%d %H:%M:%S')})

				list_items.append(get_dir_entry(
					mode='compilation_items',
					compilation_id=favorite_item['compilation_id'],
					metadata=compilation_metadata,
					override_fanart=default_fanart
				))

		elif favorite_item.get('block_id', None) is not None:
			landingpage = libjoyn.get_landingpage()
			break_loop = False
			for lane_type, categories in landingpage.items():
				for category_block_id, category_name in categories.items():
					if  category_block_id == favorite_item['block_id'] and lane_type in CONST['CATEGORY_LANES']:
						found = True
						list_items.append(get_dir_entry(metadata={
							'infoLabels': {'title': xbmc_helper.translation('CATEGORY') + ': ' + category_name, 'plot': ''},
							'art': {}}, mode='category', block_id=category_block_id))
						break_loop = True
						break
				if break_loop is True:
					break

		elif favorite_item.get('channel_id', None) is not None:
			landingpage = libjoyn.get_landingpage()
			break_loop = False
			if 'ChannelLane' in landingpage.keys():
				for block_id, headline in landingpage['ChannelLane'].items():
					channels = libjoyn.get_graphql_response('SINGLEBLOCK', {'blockId': block_id})
					for channel in channels['block']['assets']:
						if str(channel['id']) == str(favorite_item['channel_id']):
							found = True
							tv_channel_metadata = libjoyn.get_metadata(channel,'TVCHANNEL')
							tv_channel_metadata['infoLabels'].update(
								{'title': xbmc_helper.translation('MEDIA_LIBRARY') + ': ' +tv_channel_metadata['infoLabels'].get('title','')})
							list_items.append(get_dir_entry(mode='tvshows',
								stream_type=stream_type,
								metadata=tv_channel_metadata,
								channel_id=str(channel['id']),
								channel_path=channel['path']))
							break_loop = True
							break
					if break_loop:
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

	is_helper = Helper('mpd', drm='com.widevine.alpha')
	if not is_helper.check_inputstream():
		xbmc_helper.dialog_id('MSG_WIDEVINE_NOT_FOUND')
		exit(0)

	list_items = show_lastseen(xbmc_helper.get_int_setting('max_lastseen'))
	max_recommendations = xbmc_helper.get_int_setting('max_recommendations')

	if max_recommendations > 0:
		landingpage = libjoyn.get_landingpage()
		if 'HeroLane' in landingpage.keys():
				for block_id, headline in landingpage['HeroLane'].items():
					hero_lane = libjoyn.get_graphql_response('SINGLEBLOCK', {'blockId': block_id, 'first': max_recommendations}, True)
					if hero_lane.get('block', None) is not None and hero_lane.get('block').get('assets', None) is not None:
						for asset in hero_lane['block']['assets']:
							if asset['__typename'] == 'Series':
								metadata=libjoyn.get_metadata(asset,'TVSHOW')
								metadata['infoLabels'].update({'title': xbmc_helper.translation('RECOMMENDATION').format(
									compat._encode(metadata['infoLabels'].get('title', '')))})
								metadata['infoLabels'].update({'mediatype': 'tvshow'})
								list_items.append(get_dir_entry
									(mode='season',
									tv_show_id=asset['id'],
									metadata=metadata,
									override_fanart=default_fanart))


	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title': xbmc_helper.translation('MEDIA_LIBRARIES'),
					'plot': xbmc_helper.translation('MEDIA_LIBRARIES_PLOT'),
					},'art': {}}, mode='channels', stream_type='VOD'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title': xbmc_helper.translation('CATEGORIES'),
					'plot': xbmc_helper.translation('CATEGORIES_PLOT'),
					}, 'art': {}}, mode='categories', stream_type='VOD'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title': xbmc_helper.translation('WATCHLIST'),
					'plot': xbmc_helper.translation('WATCHLIST_PLOT'),
					}, 'art': {}}, mode='show_favs'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title': xbmc_helper.translation('SEARCH'),
					'plot': xbmc_helper.translation('SEARCH_PLOT'),
					}, 'art': {}}, mode='search'))
	list_items.append(get_dir_entry(metadata={'infoLabels': {
					'title': xbmc_helper.translation('LIVE_TV'),
					'plot': xbmc_helper.translation('LIVE_TV_PLOT'),
					}, 'art': {}}, mode='channels',stream_type='LIVE'))

	if compat.PY2 is True:
		list_items.append(get_dir_entry(metadata={'infoLabels': {
						'title':  xbmc_helper.translation('TV_GUIDE'),
						'plot': xbmc_helper.translation('TV_GUIDE_PLOT'),
						}, 'art': {}}, mode='epg',stream_type='LIVE'))

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'INDEX')

def channels(stream_type, title):

	list_items = []
	landingpage = libjoyn.get_landingpage()
	if stream_type == 'VOD':
		if 'ChannelLane' in landingpage.keys():
			for block_id, headline in landingpage['ChannelLane'].items():
				channels = libjoyn.get_graphql_response('SINGLEBLOCK', {'blockId': block_id})
				for channel in channels['block']['assets']:
					list_items.append(get_dir_entry(mode='tvshows',
						stream_type=stream_type,
						metadata=libjoyn.get_metadata(channel,'TVCHANNEL'),
						channel_id=str(channel['id']),
						channel_path=channel['path']))

			xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEORIES', title)

	elif stream_type == 'LIVE':
		epg = libjoyn.get_epg()
		for brand_epg in epg['brands']:
			if brand_epg['livestream'] is not None:
				client_data={
					'videoId': None,
					'channelId': brand_epg['livestream']['id']
				}
				if 'epg' in brand_epg['livestream'].keys() and len(brand_epg['livestream']['epg']) > 0:
					metadata = libjoyn.get_epg_metadata(brand_epg['livestream'])

					if 'logo' in brand_epg.keys():
						metadata['art'].update({
							'icon': brand_epg['logo']['url'] + '/profile:nextgen-web-artlogo-183x75',
							'clearlogo': brand_epg['logo']['url'] + '/profile:nextgen-web-artlogo-183x75',
							'thumb': brand_epg['logo']['url'] + '/profile:original',
						})

					list_items.append(get_dir_entry(
						is_folder=False,
						metadata=metadata,
						mode='play_video',
						client_data=libjoyn.get_livetv_clientdata(brand_epg['livestream']['id']),
						video_id=brand_epg['livestream']['id'],
						stream_type='LIVE'))

		xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'LIVE_TV', title)


def tvshows(channel_id, channel_path,  title):

	list_items = []

	tvshows = libjoyn.get_graphql_response('CHANNEL', {'path': channel_path})
	if tvshows is not None and tvshows.get('page', None) is not None and tvshows.get('page').get('assets', None) is not None:
		for tvshow in tvshows['page']['assets']:

			tvshow_metadata=libjoyn.get_metadata(tvshow,'TVSHOW')
			tvshow_metadata['infoLabels'].update({'mediatype': 'tvshow'})

			if tvshow['__typename'] == 'Series':
				list_items.append(get_dir_entry
					(mode='season',
					tv_show_id=tvshow['id'],
					metadata=tvshow_metadata,
					override_fanart=default_fanart
				))
			elif tvshow['__typename'] == 'Compilation':
				list_items.append(get_dir_entry(
					mode='compilation_items',
					compilation_id=tvshow['id'],
					metadata=tvshow_metadata,
					override_fanart=default_fanart
				))

	if len(list_items) == 0:
		return xbmc_helper.notification(
				xbmc_helper.translation('MEDIA_LIBRARY'),
				xbmc_helper.translation('MSG_NO_CONTENT'),
				default_icon
			)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	list_items.append(get_favorite_entry({'channel_id': channel_id}, 'MEDIA_LIBRARY'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def seasons(tv_show_id, title):

	list_items = []
	seasons = libjoyn.get_graphql_response('SEASONS', {'seriesId': tv_show_id})

	if seasons is not None and seasons.get('series', None) is not None:
		tvshow_metadata = libjoyn.get_metadata(seasons['series'],'TVSHOW')
		counter = 1
		seasons_count = len(seasons['series']['seasons'])

		for season in seasons['series']['seasons']:

			if 'number' in season.keys():
				season_number = season['number']
			else:
				season_number = counter

			if xbmc_helper.get_bool_setting('show_episodes_immediately') and len(seasons['series']['seasons']) == 1:
				return season_episodes(season['id'], title + ' - ' + xbmc_helper.translation('SEASON_NO').format(str(season_number)))

			tvshow_metadata['infoLabels'].update({
					'title': xbmc_helper.translation('SEASON_NO').format(str(season_number)),
					'season': seasons_count,
					'sortseason': season_number,
					'mediatype': 'season',
				})

			list_items.append(get_dir_entry(
				mode='season_episodes',
				season_id=season['id'],
				metadata=tvshow_metadata,
				title_prefix=(title + ' - ')
			))

			counter+=1

	if len(list_items) == 0:
		return xbmc_helper.notification(
				xbmc_helper.translation('TV_SHOW'),
				xbmc_helper.translation('MSG_NO_CONTENT'),
				default_icon
			)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_TITLE)

	list_items.append(get_favorite_entry({'tv_show_id': tv_show_id}, 'TV_SHOW'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'SEASONS', title)


def season_episodes(season_id, title):

	list_items = []
	episodes = libjoyn.get_graphql_response('EPISODES', {'seasonId': season_id})
	override_fanart = default_fanart
	if episodes is not None and episodes.get('season', None) is not None and episodes.get('season').get('episodes', None) is not None:
		for episode in episodes['season']['episodes']:
			episode_metadata =  libjoyn.get_metadata(episode,'EPISODE')

			client_data = {
					'startTime': 0,
					'videoId': episode['id'],
					'genre': [],
			}

			if 'video' in episode.keys() and 'duration' in episode['video']:
				client_data.update({'duration': (episode['video']['duration']*1000)})

			if 'series' in episode.keys() and 'id' in episode['series']:
				client_data.update({'tvShowId': episode['series']['id']})
				if override_fanart == default_fanart:
					tv_show_meta = libjoyn.get_metadata(episode['series'],'TVSHOW')
					if 'fanart' in tv_show_meta['art']:
						override_fanart = tv_show_meta['art']['fanart']

			episode_metadata['infoLabels'].update({'mediatype': 'episode'})

			list_items.append(get_dir_entry(
				is_folder=False,
				mode='play_video',
				metadata=episode_metadata,
				video_id=episode['id'],
				client_data=dumps(client_data),
				override_fanart=override_fanart,
				season_id=season_id
				)
			)

	if len(list_items) == 0:
		return xbmc_helper.notification(
				xbmc_helper.translation('SEASON'),
				xbmc_helper.translation('MSG_NO_CONTENT'),
				default_icon
			)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DURATION)
	addSortMethod(pluginhandle, SORT_METHOD_DATE)
	addSortMethod(pluginhandle, SORT_METHOD_EPISODE)

	list_items.append(get_favorite_entry({'season_id': season_id}, 'SEASON'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'EPISODES', title)


def get_compilation_items(compilation_id, title):

	list_items = []
	compilation_items = libjoyn.get_graphql_response('COMPILATION_ITEMS', {'id': compilation_id})
	override_fanart = default_fanart

	if compilation_items is not None and compilation_items.get('compilation', None) is not None and compilation_items.get('compilation').get('compilationItems', None) is not None:
		for compilation_item in compilation_items['compilation']['compilationItems']:

			compilation_item_metadata = libjoyn.get_metadata(compilation_item,'EPISODE')
			client_data = {
					'startTime': 0,
					'videoId': compilation_item['id'],
					'genre': [],
			}

			if 'video' in compilation_item.keys() and 'duration' in compilation_item['video']:
				client_data.update({'duration': (compilation_item['video']['duration']*1000)})

			if 'compilation' in compilation_item.keys():
				if 'id' in compilation_item['compilation']:
					client_data.update({'tvShowId': compilation_item['compilation']['id']})
				if override_fanart == default_fanart:
					compilation_metadata = libjoyn.get_metadata(compilation_item['compilation'],'TVSHOW')
					if 'fanart' in compilation_metadata['art']:
						override_fanart = compilation_metadata['art']['fanart']

			compilation_item_metadata['infoLabels'].update({'mediatype': 'episode'})

			list_items.append(get_dir_entry(
				is_folder=False,
				mode='play_video',
				metadata=compilation_item_metadata,
				video_id=compilation_item['id'],
				client_data=dumps(client_data),
				override_fanart=override_fanart,
				compilation_id=compilation_id
				)
			)

	if len(list_items) == 0:
		return xbmc_helper.notification(
				xbmc_helper.translation('TV_SHOW'),
				xbmc_helper.translation('MSG_NO_CONTENT'),
				default_icon
			)


	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DURATION)

	list_items.append(get_favorite_entry({'compilation_id': compilation_id }, 'TV_SHOW'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'EPISODES', title)


def search(stream_type, title):
	search_term = Dialog().input('Suche', type=INPUT_ALPHANUM)

	if len(search_term) > 0:
		search_response = libjoyn.get_graphql_response('SEARCH', {'text': search_term})
		list_items = []
		if 'search' in search_response.keys() and 'results' in search_response['search'] and len(search_response['search']['results']) > 0:
			for search_result in search_response['search']['results']:
				if search_result['__typename'] == 'Compilation' or search_result['__typename'] == 'Series':

					metadata=libjoyn.get_metadata(search_result,'TVSHOW')
					metadata['infoLabels'].update({'mediatype': 'tvshow'})

					if search_result['__typename'] == 'Series':
						list_items.append(get_dir_entry
							(mode='season',
							tv_show_id=search_result['id'],
							metadata=metadata,
							override_fanart=default_fanart
						))
					elif search_result['__typename'] == 'Compilation':
						list_items.append(get_dir_entry(
							mode='compilation_items',
							compilation_id=search_result['id'],
							season_id='',
							metadata=metadata,
							override_fanart=default_fanart
						))


		if len(list_items) == 0:
			return xbmc_helper.notification(
						xbmc_helper.translation('SEARCH'),
						 xbmc_helper.translation('MSG_NO_SEARCH_RESULTS').format(search_term),
						 default_icon
				)
		else:
			xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def categories(stream_type, title):

	list_items = []
	landingpage = libjoyn.get_landingpage()

	for lane_type in CONST['CATEGORY_LANES']:
		if lane_type in landingpage.keys():
			for category_block_id, category_name in landingpage[lane_type].items():
				list_items.append(get_dir_entry(metadata={'infoLabels': {'title': category_name, 'plot': ''}, 'art': {}}, mode='category', block_id=category_block_id))

	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEORIES', title)


def category(block_id, title):

	list_items = []
	category = libjoyn.get_graphql_response('SINGLEBLOCK', {'blockId': block_id})

	if category is not None and category.get('block', None) is not None and category.get('block').get('assets', None) is not None:
		for category_item in category['block']['assets']:
			category_item_metadata=libjoyn.get_metadata(category_item,'TVSHOW')
			category_item_metadata['infoLabels'].update({'mediatype': 'tvshow'})

			if category_item['__typename'] == 'Series':
				list_items.append(get_dir_entry
					(mode='season',
					tv_show_id=category_item['id'],
					metadata=category_item_metadata,
					override_fanart=default_fanart
				))
			elif category_item['__typename'] == 'Compilation':
				list_items.append(get_dir_entry(
					mode='compilation_items',
					compilation_id=category_item['id'],
					metadata=category_item_metadata,
					override_fanart=default_fanart
				))

	if len(list_items) == 0:
		return xbmc_helper.notification(
				xbmc_helper.translation('CATEGORY'),
				xbmc_helper.translation('MSG_NO_CONTENT'),
				default_icon
			)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)

	list_items.append(get_favorite_entry({'block_id': block_id }, 'CATEGORY'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def play_video(video_id, client_data, stream_type, season_id=None, compilation_id=None):

	xbmc_helper.log_debug('play_video: video_id: ' + video_id)
	list_item = ListItem()
	video_data = libjoyn.get_video_data(video_id, loads(client_data), stream_type, season_id, compilation_id)
	succeeded = True

	if (video_data['streamingFormat'] == 'dash'):
		if libjoyn.set_mpd_props(list_item, video_data['videoUrl'], stream_type) is not False:
			if 'drm' in video_data.keys() and video_data['drm'] == 'widevine' and 'licenseUrl' in video_data.keys():
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.license_type', 'com.widevine.alpha')
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.license_key', video_data['licenseUrl'] + '|' +
					request_helper.get_header_string({'User-Agent': libjoyn.config['USER_AGENT'], 'Content-Type': 'application/octet-stream'}) + '|R{SSM}|')
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.stream_headers',  request_helper.get_header_string({'User-Agent': libjoyn.config['USER_AGENT']}))
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

	if succeeded is True and 'season_id' in video_data.keys() and video_data['season_id'] is not None:
		add_lastseen(season_id=video_data['season_id'], max_lastseen=CONST['LASTSEEN_ITEM_COUNT'])
	elif succeeded is True and 'compilation_id' in video_data.keys() and video_data['compilation_id'] is not None:
		add_lastseen(compilation_id=video_data['compilation_id'], max_lastseen=CONST['LASTSEEN_ITEM_COUNT'])

	setResolvedUrl(pluginhandle, succeeded, list_item)


def get_favorite_entry(favorite_item, favorite_type):

	fav_del_art = {'thumb': xbmc_helper.get_media_filepath('fav_del_thumb.png'), 'icon': xbmc_helper.get_media_filepath('fav_del_icon.png')}
	fav_add_art = {'thumb': xbmc_helper.get_media_filepath('fav_add_thumb.png'), 'icon': xbmc_helper.get_media_filepath('fav_add_icon.png')}

	if check_favorites(favorite_item) is False:
		return get_dir_entry(is_folder=False, metadata={'infoLabels': {
						'title':  xbmc_helper.translation('ADD_TO_WATCHLIST'),
						'plot': xbmc_helper.translation('ADD_TO_WATCHLIST_PRX').format(xbmc_helper.translation(favorite_type)),
						}, 'art': fav_add_art }, mode='add_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation(favorite_type))
	else:
		return get_dir_entry(is_folder=False,metadata={'infoLabels': {
						'title': xbmc_helper.translation('REMOVE_FROM_WATCHLIST'),
						'plot': xbmc_helper.translation('REMOVE_FROM_WATCHLIST_PRFX').format(xbmc_helper.translation(favorite_type)),
						}, 'art': fav_del_art }, mode='drop_fav', favorite_item=favorite_item, fav_type=xbmc_helper.translation(favorite_type))


def get_dir_entry(mode, metadata, is_folder=True, channel_id='', channel_path='', tv_show_id='', season_id='', video_id='', stream_type='VOD', block_id='', \
			override_fanart='', fav_type='', favorite_item=None, title_prefix='', client_data='', compilation_id=''):

	params = {
		'mode' 			: mode,
		'tv_show_id'		: tv_show_id,
		'season_id' 		: season_id,
		'video_id'		: video_id,
		'stream_type'		: stream_type,
		'channel_id'		: channel_id,
		'channel_path'		: channel_path,
		'block_id' 		: block_id,
		'fav_type' 		: fav_type,
		'title' 		: compat._encode(title_prefix) + compat._encode(metadata['infoLabels'].get('title','')),
		'client_data'		: client_data,
		'compilation_id'	: compilation_id
	}

	if favorite_item is not None:
		params.update({'favorite_item': dumps(favorite_item)})

	list_item = ListItem(metadata['infoLabels']['title'])
	list_item.setInfo(type='video', infoLabels=metadata['infoLabels'])

	if 'poster' not in metadata['art'] and 'thumb' in metadata['art']:
		metadata['art'].update({'poster': metadata['art']['thumb']})
	elif 'thumb' not in metadata['art']:
		metadata['art'].update({ 'thumb': default_logo})
		metadata['art'].update({ 'poster': default_logo})

	if 'icon' not in metadata['art']:
		metadata['art'].update({ 'icon': default_icon})

	if override_fanart != '':
		metadata['art'].update({'fanart': override_fanart})

	if 'fanart' not in metadata['art']:
		metadata['art'].update({'fanart': default_fanart})

	for art_key, art_value in metadata['art'].items():
		metadata['art'].update({art_key: request_helper.add_user_agend_header_string(art_value, libjoyn.config['USER_AGENT'])})

	list_item.setArt(metadata['art'])

	if (mode == 'play_video' and video_id is not '' and client_data is not ''):
		list_item.setProperty('IsPlayable', 'True')

	url = pluginurl+'?'
	url += urlencode(params)


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

		elif mode == 'season_episodes' and 'season_id' in param_keys:
			season_episodes(params['season_id'], title)

		elif mode == 'video' and 'tv_show_id' in param_keys and 'season_id' in param_keys:
			videos(params['tv_show_id'],params['season_id'], title)

		elif mode == 'play_video' and 'video_id' in param_keys:
			if 'client_data' in param_keys:
				if 'season_id' in param_keys:
					play_video(video_id=params['video_id'], client_data=params['client_data'], stream_type=stream_type, season_id=params['season_id'])
				elif 'compilation_id' in param_keys:
					play_video(video_id=params['video_id'], client_data=params['client_data'], stream_type=stream_type, compilation_id=params['compilation_id'])
			if stream_type == 'LIVE':
				play_video(video_id=params['video_id'],
						client_data=params.get('client_data', libjoyn.get_livetv_clientdata(params['video_id'])),
						stream_type=stream_type)

		elif mode == 'compilation_items' and 'compilation_id' in param_keys:
			get_compilation_items(params['compilation_id'], title)

		elif mode == 'channels':
			channels(stream_type,title)

		elif mode == 'tvshows' and 'channel_id' in param_keys and 'channel_path' in param_keys:
			tvshows(params['channel_id'], params['channel_path'], title)

		elif mode == 'search':
			search(stream_type, title)

		elif mode == 'categories':
			categories(stream_type,title)

		elif mode == 'category' and 'block_id' in param_keys:
			category(params['block_id'], title)

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
