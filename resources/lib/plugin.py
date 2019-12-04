# -*- coding: utf-8 -*-

from sys import argv, exit
from xbmc import executebuiltin, sleep as xbmc_sleep
from xbmcgui import Dialog, ListItem, INPUT_ALPHANUM, ALPHANUM_HIDE_INPUT
from xbmcplugin import setResolvedUrl, addSortMethod
from xbmcplugin import SORT_METHOD_UNSORTED, SORT_METHOD_LABEL, SORT_METHOD_DATE, SORT_METHOD_DATEADDED, \
        SORT_METHOD_EPISODE, SORT_METHOD_DURATION, SORT_METHOD_TITLE
from xbmcaddon import Addon
from datetime import datetime
from time import time
from .const import CONST
from . import compat as compat
from . import xbmc_helper as xbmc_helper
from . import request_helper as request_helper
from .lib_joyn import lib_joyn as lib_joyn

if compat.PY2:
	from urllib import urlencode, quote
	try:
		from simplejson import loads, dumps
	except ImportError:
		from json import loads, dumps

elif compat.PY3:
	from urllib.parse import urlencode, quote
	from json import loads, dumps

if xbmc_helper.get_bool_setting('dont_verify_ssl_certificates') is True:

	import ssl
	try:
		_create_unverified_https_context = ssl._create_unverified_context
	except AttributeError:
		pass
	else:
		ssl._create_default_https_context = _create_unverified_https_context


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
			if season_id is not None and 'season_id' in lastseen_item.keys(
			) and lastseen_item['season_id'] == season_id or compilation_id is not None and 'compilation_id' in lastseen_item.keys(
			) and lastseen_item['compilation_id'] == compilation_id:

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
			lastseen = lastseen[:(max_lastseen - 1)]

		xbmc_helper.set_json_data('lastseen', lastseen)


def drop_lastseen(compilation_id=None, season_id=None):

	found_in_lastseen = False
	lastseen = get_lastseen()

	for lastseen_item in lastseen:
		if season_id is not None and 'season_id' in lastseen_item.keys() and lastseen_item['season_id'] == season_id:

			lastseen.remove(lastseen_item)

		elif compilation_id is not None and 'compilation_id' in lastseen_item.keys(
		) and lastseen_item['compilation_id'] == compilation_id:

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
		favorite_item.update({'added': time()})
		favorites.append(favorite_item)
		xbmc_helper.set_json_data('favorites', favorites)

		executebuiltin("Container.Refresh")
		xbmc_sleep(100)
		xbmc_helper.notification(xbmc_helper.translation('WATCHLIST'),
		                         compat._format(xbmc_helper.translation('WL_TYPE_ADDED'), fav_type), default_icon)


def drop_favorites(favorite_item, silent=False, fav_type=''):

	xbmc_helper.log_debug(compat._format('drop_favorites  - item {}: ', favorite_item))
	favorites = get_favorites()
	found = False

	for favorite in favorites:

		if 'season_id' in favorite_item.keys() and 'season_id' in favorite.keys(
		) and favorite_item['season_id'] == favorite['season_id']:
			favorites.remove(favorite)
			found = True

		elif 'tv_show_id' in favorite_item.keys() and 'tv_show_id' in favorite.keys(
		) and favorite_item['tv_show_id'] == favorite['tv_show_id']:
			favorites.remove(favorite)
			found = True

		elif 'channel_id' in favorite_item.keys() and 'channel_id' in favorite.keys(
		) and favorite_item['channel_id'] == favorite['channel_id']:
			favorites.remove(favorite)
			found = True

		elif 'compilation_id' in favorite_item.keys() and 'compilation_id' in favorite.keys(
		) and favorite_item['compilation_id'] == favorite['compilation_id']:
			favorites.remove(favorite)
			found = True

		elif 'block_id' in favorite_item.keys() and 'block_id' in favorite.keys(
		) and favorite_item['block_id'] == favorite['block_id']:
			favorites.remove(favorite)
			found = True

		elif 'category_name' in favorite_item.keys() and 'category_name' in favorite.keys(
		) and favorite_item['category_name'] == favorite['category_name']:
			favorites.remove(favorite)
			found = True

	favorites = xbmc_helper.set_json_data('favorites', favorites)

	if silent is False and found is True:
		xbmc_helper.notification(xbmc_helper.translation('WATCHLIST'),
		                         compat._format(xbmc_helper.translation('WL_TYPE_REMOVED'), fav_type), default_icon)
		executebuiltin("Container.Refresh")
		xbmc_sleep(100)


def check_favorites(favorite_item):

	favorites = get_favorites()
	for favorite in favorites:
		if 'season_id' in favorite_item.keys() and 'season_id' in favorite.keys(
		) and favorite_item['season_id'] == favorite['season_id']:
			return True

		elif 'tv_show_id' in favorite_item.keys() and 'tv_show_id' in favorite.keys(
		) and favorite_item['tv_show_id'] == favorite['tv_show_id']:
			return True

		elif 'block_id' in favorite_item.keys() and 'block_id' in favorite.keys(
		) and favorite_item['block_id'] == favorite['block_id']:
			return True

		elif 'compilation_id' in favorite_item.keys() and 'compilation_id' in favorite.keys(
		) and favorite_item['compilation_id'] == favorite['compilation_id']:
			return True

		elif 'channel_id' in favorite_item.keys() and 'channel_id' in favorite.keys(
		) and favorite_item['channel_id'] == favorite['channel_id']:
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
			if lastseen_item.get('season_id', None) is not None:
				if xbmc_helper.get_bool_setting('dont_show_watchlist_in_lastseen') is True and check_favorites(
				        {'seasonId': lastseen_item['season_id']}) is True:
					continue

				season_data = libjoyn.get_graphql_response('EPISODES', {'seasonId': lastseen_item['season_id'], 'first': 1})
				if season_data.get('season', None) is not None and season_data.get('season').get('episodes', None) is not None and len(
				        season_data['season']['episodes']) > 0:
					season_metadata = libjoyn.get_metadata(season_data['season']['episodes'][0]['series'], 'TVSHOW')

					season_metadata['infoLabels'].update({
					        'title':
					        compat._format(
					                xbmc_helper.translation('CONTINUE_WATCHING'),
					                compat._format('{} - {}', season_metadata['infoLabels'].get('title', ''),
					                               compat._format(xbmc_helper.translation('SEASON_NO'), str(season_data['season']['number']))))
					})
					list_items.append(
					        get_dir_entry(
					                mode='season_episodes',
					                season_id=lastseen_item['season_id'],
					                metadata=season_metadata,
					                override_fanart=default_fanart,
					        ))

			elif lastseen_item.get('compilation_id', None) is not None:
				if xbmc_helper.get_bool_setting('dont_show_watchlist_in_lastseen') is True and check_favorites(
				        {'compilation_id': lastseen_item['compilation_id']}) is True:
					continue

				compilation_data = libjoyn.get_graphql_response('COMPILATION_ITEMS', {'id': lastseen_item['compilation_id'], 'first': 1})
				if compilation_data.get('compilation', None) is not None and compilation_data.get('compilation').get(
				        'compilationItems', None) is not None and len(compilation_data['compilation']['compilationItems']) > 0:
					compilation_metadata = libjoyn.get_metadata(compilation_data['compilation']['compilationItems'][0]['compilation'],
					                                            'TVSHOW')
					compilation_metadata['infoLabels'].update({
					        'title':
					        compat._format(xbmc_helper.translation('CONTINUE_WATCHING'), compilation_metadata['infoLabels'].get('title', ''))
					})
					list_items.append(
					        get_dir_entry(mode='compilation_items',
					                      compilation_id=lastseen_item['compilation_id'],
					                      metadata=compilation_metadata,
					                      override_fanart=default_fanart))

	return list_items


def show_favorites(title):

	favorites = get_favorites()
	list_items = []

	if len(favorites) == 0:
		return xbmc_helper.notification(xbmc_helper.translation('WATCHLIST'), xbmc_helper.translation('MSG_NO_FAVS_YET'),
		                                default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DATEADDED)

	for favorite_item in favorites:

		if favorite_item.get('season_id', None) is not None:
			season_data = libjoyn.get_graphql_response('EPISODES', {'seasonId': favorite_item['season_id'], 'first': 1})
			if season_data.get('season', None) is not None and season_data.get('season').get('episodes', None) is not None and len(
			        season_data['season']['episodes']) > 0:
				season_metadata = libjoyn.get_metadata(season_data['season']['episodes'][0]['series'], 'TVSHOW')
				season_metadata['infoLabels'].update({
				        'title':
				        compat._format('{} - {}', season_metadata['infoLabels'].get('title', ''),
				                       compat._format(xbmc_helper.translation('SEASON_NO'), str(season_data['season']['number'])))
				})

				if 'added' in favorite_item.keys():
					season_metadata.update({'dateadded': datetime.fromtimestamp(favorite_item['added']).strftime('%Y-%m-%d %H:%M:%S')})

				list_items.append(
				        get_dir_entry(
				                mode='season_episodes',
				                season_id=favorite_item['season_id'],
				                metadata=season_metadata,
				                override_fanart=default_fanart,
				        ))

		elif favorite_item.get('tv_show_id', None) is not None:
			seasons = libjoyn.get_graphql_response('SEASONS', {'seriesId': favorite_item['tv_show_id']})
			if seasons.get('series', None) is not None:
				tvshow_metadata = libjoyn.get_metadata(seasons['series'], 'TVSHOW')

				if 'added' in favorite_item.keys():
					tvshow_metadata.update({'dateadded': datetime.fromtimestamp(favorite_item['added']).strftime('%Y-%m-%d %H:%M:%S')})

				list_items.append(
				        get_dir_entry(mode='season',
				                      tv_show_id=favorite_item['tv_show_id'],
				                      metadata=tvshow_metadata,
				                      override_fanart=default_fanart))

		elif favorite_item.get('compilation_id', None) is not None:
			compilation_data = libjoyn.get_graphql_response('COMPILATION_ITEMS', {'id': favorite_item['compilation_id'], 'first': 1})
			if compilation_data.get('compilation', None) is not None and compilation_data.get('compilation').get(
			        'compilationItems', None) is not None and len(compilation_data['compilation']['compilationItems']) > 0:
				compilation_metadata = libjoyn.get_metadata(compilation_data['compilation']['compilationItems'][0]['compilation'], 'TVSHOW')

				if 'added' in favorite_item.keys():
					compilation_metadata.update({'dateadded': datetime.fromtimestamp(favorite_item['added']).strftime('%Y-%m-%d %H:%M:%S')})

				list_items.append(
				        get_dir_entry(mode='compilation_items',
				                      compilation_id=favorite_item['compilation_id'],
				                      metadata=compilation_metadata,
				                      override_fanart=default_fanart))

		elif favorite_item.get('block_id', None) is not None:
			landingpage = libjoyn.get_landingpage()
			break_loop = False
			for lane_type, categories in landingpage.items():
				for category_block_id, category_name in categories.items():
					if category_block_id == favorite_item['block_id'] and lane_type in CONST['CATEGORY_LANES']:
						list_items.append(
						        get_dir_entry(metadata={
						                'infoLabels': {
						                        'title': compat._format('{}: {}', xbmc_helper.translation('CATEGORY'), category_name),
						                        'plot': ''
						                },
						                'art': {}
						        },
						                      mode='category',
						                      block_id=category_block_id))
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
							tv_channel_metadata = libjoyn.get_metadata(channel, 'TVCHANNEL')
							tv_channel_metadata['infoLabels'].update({
							        'title':
							        compat._format('{}: {}', xbmc_helper.translation('MEDIA_LIBRARY'),
							                       tv_channel_metadata['infoLabels'].get('title', ''))
							})
							list_items.append(
							        get_dir_entry(mode='tvshows',
							                      stream_type=stream_type,
							                      metadata=tv_channel_metadata,
							                      channel_id=str(channel['id']),
							                      channel_path=channel['path']))
							break_loop = True
							break
					if break_loop:
						break

	if len(list_items) == 0:
		return xbmc_helper.notification(xbmc_helper.translation('WATCHLIST'), xbmc_helper.translation('MSG_NO_FAVS_YET'),
		                                default_icon)

	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'WATCHLIST', title)


def show_joyn_bookmarks(title):

	list_items = []
	landingpage = libjoyn.get_landingpage()

	if 'BookmarkLane' in landingpage.keys():
		for block_id, headline in landingpage['BookmarkLane'].items():
			bookmark_lane = libjoyn.get_graphql_response('SINGLEBLOCK', {'blockId': block_id})
			if bookmark_lane.get('block', None) is not None and bookmark_lane.get('block').get('assets', None) is not None:
				list_items.extend(get_list_items(bookmark_lane['block']['assets']))

	if len(list_items) == 0:
		return xbmc_helper.notification(xbmc_helper.translation('JOYN_BOOKMARKS'), xbmc_helper.translation('MSG_NO_CONTENT'),
		                                default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def add_joyn_bookmark(asset_id):

	add_joyn_bookmark_res = libjoyn.get_graphql_response('ADD_BOOKMARK', {'assetId': asset_id})
	executebuiltin("Container.Refresh")
	xbmc_sleep(100)
	return xbmc_helper.notification(
	        xbmc_helper.translation('JOYN_BOOKMARKS'),
	        xbmc_helper.translation('MSG_JOYN_BOOKMARK_ADD_SUCC' if add_joyn_bookmark_res.get('setBookmark', '') is not '' else
	                                'MSG_JOYN_BOOKMARK_ADD_FAIL'), default_icon)


def remove_joyn_bookmark(asset_id):

	del_bookmark_res = libjoyn.get_graphql_response('DEL_BOOKMARK', {'assetId': asset_id})
	executebuiltin("Container.Refresh")
	xbmc_sleep(100)
	return xbmc_helper.notification(
	        xbmc_helper.translation('JOYN_BOOKMARKS'),
	        xbmc_helper.translation('MSG_JOYN_BOOKMARK_DEL_SUCC' if del_bookmark_res.get('removeBookmark', False) is True else
	                                'MSG_JOYN_BOOKMARK_DEL_FAIL'), default_icon)


def get_uepg_params():

	return compat._format('json={}&refresh_path={}epg&refresh_interval={}&row_count={}',
	                      quote(dumps(libjoyn.get_uepg_data(pluginurl))), quote(compat._format('{}?mode=epg', pluginurl)),
	                      quote(str(CONST['UEPG_REFRESH_INTERVAL'])), quote(str(CONST['UEPG_ROWCOUNT'])))


def get_list_items(response_items, prefix_label=None):

	list_items = []

	for response_item in response_items:
		if response_item['__typename'] == 'Movie' and 'video' in response_item.keys() and 'id' in response_item['video']:

			movie_metadata = libjoyn.get_metadata(response_item, 'EPISODE', 'MOVIE')
			movie_metadata['infoLabels'].update({'mediatype': 'movie'})

			if prefix_label is not None:
				movie_metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper.translation(prefix_label), movie_metadata['infoLabels'].get('title', ''))})

			list_items.append(
			        get_dir_entry(is_folder=False,
			                      mode='play_video',
			                      metadata=movie_metadata,
			                      video_id=response_item['video']['id'],
			                      client_data=dumps(libjoyn.get_client_data(response_item['video']['id'], 'VOD', response_item)),
			                      override_fanart=default_fanart,
			                      movie_id=response_item['id']))

		elif response_item['__typename'] == 'Brand':

			channel_metadata = libjoyn.get_metadata(response_item, 'TVCHANNEL')
			if prefix_label is not None:
				channel_metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper.translation(prefix_label), channel_metadata['infoLabels'].get('title', ''))})

			list_items.append(
			        get_dir_entry(mode='tvshows',
			                      metadata=channel_metadata,
			                      channel_id=str(response_item['id']),
			                      channel_path=response_item['path']))

		else:
			tvshow_metadata = libjoyn.get_metadata(response_item, 'TVSHOW')
			tvshow_metadata['infoLabels'].update({'mediatype': 'tvshow'})

			if prefix_label is not None:
				tvshow_metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper.translation(prefix_label), tvshow_metadata['infoLabels'].get('title', ''))})

			if response_item['__typename'] == 'Series':
				list_items.append(
				        get_dir_entry(mode='season',
				                      tv_show_id=response_item['id'],
				                      metadata=tvshow_metadata,
				                      override_fanart=default_fanart))
			elif response_item['__typename'] == 'Compilation':
				list_items.append(
				        get_dir_entry(mode='compilation_items',
				                      compilation_id=response_item['id'],
				                      metadata=tvshow_metadata,
				                      override_fanart=default_fanart))

	return list_items


def index():

	if not xbmc_helper.addon_enabled(CONST['INPUTSTREAM_ADDON']):
		xbmc_helper.dialog_id('MSG_INPUSTREAM_NOT_ENABLED')
		exit(0)

	from inputstreamhelper import Helper
	is_helper = Helper('mpd', drm='com.widevine.alpha')
	if not is_helper.check_inputstream():
		xbmc_helper.dialog_id('MSG_WIDEVINE_NOT_FOUND')
		exit(0)

	request_helper.purge_etags_cache(ttl=CONST['ETAGS_TTL'])

	list_items = show_lastseen(xbmc_helper.get_int_setting('max_lastseen'))
	max_recommendations = xbmc_helper.get_int_setting('max_recommendations')

	if max_recommendations > 0:
		landingpage = libjoyn.get_landingpage()
		if 'HeroLane' in landingpage.keys():
			for block_id, headline in landingpage['HeroLane'].items():
				hero_lane = libjoyn.get_graphql_response('SINGLEBLOCK', {'blockId': block_id, 'first': max_recommendations})
				if hero_lane.get('block', None) is not None and hero_lane.get('block').get('assets', None) is not None:
					list_items.extend(get_list_items(hero_lane['block']['assets'], 'RECOMMENDATION'))

	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper.translation('MEDIA_LIBRARIES'),
	                        'plot': xbmc_helper.translation('MEDIA_LIBRARIES_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='channels',
	                      stream_type='VOD'))
	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper.translation('CATEGORIES'),
	                        'plot': xbmc_helper.translation('CATEGORIES_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='categories',
	                      stream_type='VOD'))
	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper.translation('WATCHLIST'),
	                        'plot': xbmc_helper.translation('WATCHLIST_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='show_favs'))

	if libjoyn.get_auth_token().get('has_account', False) is True:
		list_items.append(
		        get_dir_entry(metadata={
		                'infoLabels': {
		                        'title': xbmc_helper.translation('JOYN_BOOKMARKS'),
		                        'plot': '',
		                },
		                'art': {}
		        },
		                      mode='show_joyn_bookmarks'))

	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper.translation('SEARCH'),
	                        'plot': xbmc_helper.translation('SEARCH_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='search'))
	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper.translation('LIVE_TV'),
	                        'plot': xbmc_helper.translation('LIVE_TV_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='channels',
	                      stream_type='LIVE'))

	if compat.PY2 is True:
		list_items.append(
		        get_dir_entry(metadata={
		                'infoLabels': {
		                        'title': xbmc_helper.translation('TV_GUIDE'),
		                        'plot': xbmc_helper.translation('TV_GUIDE_PLOT'),
		                },
		                'art': {}
		        },
		                      mode='epg',
		                      stream_type='LIVE',
		                      is_folder=False))

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'INDEX')


def channels(stream_type, title):

	list_items = []
	landingpage = libjoyn.get_landingpage()
	if stream_type == 'VOD':
		if 'ChannelLane' in landingpage.keys():
			for block_id, headline in landingpage['ChannelLane'].items():
				channels = libjoyn.get_graphql_response('SINGLEBLOCK', {'blockId': block_id})
				if channels.get('block', {}).get('assets', None) is not None:
					list_items.extend(get_list_items(channels['block']['assets']))

			xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEORIES', title)

	elif stream_type == 'LIVE':
		epg = libjoyn.get_epg()
		for brand_epg in epg['brands']:
			if brand_epg['livestream'] is not None:
				if 'epg' in brand_epg['livestream'].keys() and len(brand_epg['livestream']['epg']) > 0:
					metadata = libjoyn.get_epg_metadata(brand_epg['livestream'])

					if 'logo' in brand_epg.keys():
						metadata['art'].update({
						        'icon': compat._format('{}/profile:nextgen-web-artlogo-183x75', brand_epg['logo']['url']),
						        'clearlogo': compat._format('{}/profile:nextgen-web-artlogo-183x75', brand_epg['logo']['url']),
						        'thumb': compat._format('{}/profile:original', brand_epg['logo']['url']),
						})

					list_items.append(
					        get_dir_entry(is_folder=False,
					                      metadata=metadata,
					                      mode='play_video',
					                      client_data=dumps(libjoyn.get_client_data(brand_epg['livestream']['id'], 'LIVE')),
					                      video_id=brand_epg['livestream']['id'],
					                      stream_type='LIVE'))

		xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'LIVE_TV', title)


def tvshows(channel_id, channel_path, title):

	list_items = []

	tvshows = libjoyn.get_graphql_response('CHANNEL', {'path': channel_path})
	if tvshows is not None and tvshows.get('page', None) is not None and tvshows.get('page').get('assets', None) is not None:
		list_items = get_list_items(tvshows['page']['assets'])

	if len(list_items) == 0:
		return xbmc_helper.notification(xbmc_helper.translation('MEDIA_LIBRARY'), xbmc_helper.translation('MSG_NO_CONTENT'),
		                                default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	list_items.append(get_favorite_entry({'channel_id': channel_id}, 'MEDIA_LIBRARY'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def seasons(tv_show_id, title):

	list_items = []
	seasons = libjoyn.get_graphql_response('SEASONS', {'seriesId': tv_show_id})

	if seasons is not None and seasons.get('series', None) is not None:
		tvshow_metadata = libjoyn.get_metadata(seasons['series'], 'TVSHOW')
		counter = 1
		seasons_count = len(seasons['series']['seasons'])

		for season in seasons['series']['seasons']:

			if 'number' in season.keys():
				season_number = season['number']
			else:
				season_number = counter

			if xbmc_helper.get_bool_setting('show_episodes_immediately') and len(seasons['series']['seasons']) == 1:
				return season_episodes(
				        season['id'],
				        compat._format('{} - {}', title, compat._format(xbmc_helper.translation('SEASON_NO'), str(season_number))))

			tvshow_metadata['infoLabels'].update({
			        'title': compat._format(xbmc_helper.translation('SEASON_NO'), str(season_number)),
			        'season': seasons_count,
			        'sortseason': season_number,
			        'mediatype': 'season',
			})

			list_items.append(
			        get_dir_entry(mode='season_episodes',
			                      season_id=season['id'],
			                      metadata=tvshow_metadata,
			                      title_prefix=compat._format('{} - ', title)))
			counter += 1

	if len(list_items) == 0:
		return xbmc_helper.notification(xbmc_helper.translation('TV_SHOW'), xbmc_helper.translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_TITLE)

	list_items.append(get_favorite_entry({'tv_show_id': tv_show_id}, 'TV_SHOW'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'SEASONS', title)


def season_episodes(season_id, title):

	list_items = []
	episodes = libjoyn.get_graphql_response('EPISODES', {'seasonId': season_id})
	override_fanart = default_fanart
	if episodes is not None and episodes.get('season', None) is not None and episodes.get('season').get('episodes',
	                                                                                                    None) is not None:
		for episode in episodes['season']['episodes']:
			episode_metadata = libjoyn.get_metadata(episode, 'EPISODE')

			if 'series' in episode.keys() and 'id' in episode['series'].keys():
				if override_fanart == default_fanart:
					tv_show_meta = libjoyn.get_metadata(episode['series'], 'TVSHOW')
					if 'fanart' in tv_show_meta['art']:
						override_fanart = tv_show_meta['art']['fanart']

			episode_metadata['infoLabels'].update({'mediatype': 'episode'})
			video_id = episode.get('video', {}).get('id', episode.get('id'))
			list_items.append(
			        get_dir_entry(is_folder=False,
			                      mode='play_video',
			                      metadata=episode_metadata,
			                      video_id=video_id,
			                      client_data=dumps(libjoyn.get_client_data(video_id, 'VOD', episode)),
			                      override_fanart=override_fanart,
			                      season_id=season_id))

	if len(list_items) == 0:
		return xbmc_helper.notification(xbmc_helper.translation('SEASON'), xbmc_helper.translation('MSG_NO_CONTENT'), default_icon)

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

	if compilation_items is not None and compilation_items.get(
	        'compilation', None) is not None and compilation_items.get('compilation').get('compilationItems', None) is not None:
		for compilation_item in compilation_items['compilation']['compilationItems']:

			compilation_item_metadata = libjoyn.get_metadata(compilation_item, 'EPISODE')
			if 'compilation' in compilation_item.keys():
				if override_fanart == default_fanart:
					compilation_metadata = libjoyn.get_metadata(compilation_item['compilation'], 'TVSHOW')
					if 'fanart' in compilation_metadata['art']:
						override_fanart = compilation_metadata['art']['fanart']

			compilation_item_metadata['infoLabels'].update({'mediatype': 'episode'})

			video_id = compilation_item.get('video', {}).get('id', compilation_item.get('id'))
			list_items.append(
			        get_dir_entry(is_folder=False,
			                      mode='play_video',
			                      metadata=compilation_item_metadata,
			                      video_id=video_id,
			                      client_data=dumps(libjoyn.get_client_data(video_id, 'VOD', compilation_item)),
			                      override_fanart=override_fanart,
			                      compilation_id=compilation_id))

	if len(list_items) == 0:
		return xbmc_helper.notification(xbmc_helper.translation('TV_SHOW'), xbmc_helper.translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DURATION)

	list_items.append(get_favorite_entry({'compilation_id': compilation_id}, 'TV_SHOW'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'EPISODES', title)


def search(stream_type, title):
	search_term = Dialog().input('Suche', type=INPUT_ALPHANUM)

	if len(search_term) > 0:
		search_response = libjoyn.get_graphql_response('SEARCH', {'text': search_term})
		list_items = []

		if 'search' in search_response.keys() and 'results' in search_response['search'] and len(
		        search_response['search']['results']) > 0:
			list_items = get_list_items(search_response['search']['results'])

		if len(list_items) == 0:
			return xbmc_helper.notification(xbmc_helper.translation('SEARCH'),
			                                compat._format(xbmc_helper.translation('MSG_NO_SEARCH_RESULTS'), search_term), default_icon)
		else:
			xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def categories(stream_type, title):

	list_items = []
	landingpage = libjoyn.get_landingpage()

	for lane_type in CONST['CATEGORY_LANES']:
		if lane_type in landingpage.keys():
			for category_block_id, category_name in landingpage[lane_type].items():
				list_items.append(
				        get_dir_entry(metadata={
				                'infoLabels': {
				                        'title': category_name,
				                        'plot': ''
				                },
				                'art': {}
				        },
				                      mode='category',
				                      block_id=category_block_id))

	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEORIES', title)


def category(block_id, title):

	list_items = []
	category = libjoyn.get_graphql_response('SINGLEBLOCK', {'blockId': block_id})

	if category is not None and category.get('block', None) is not None and category.get('block').get('assets', None) is not None:
		list_items = get_list_items(category['block']['assets'])

	if len(list_items) == 0:
		return xbmc_helper.notification(xbmc_helper.translation('CATEGORY'), xbmc_helper.translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)

	list_items.append(get_favorite_entry({'block_id': block_id}, 'CATEGORY'))
	xbmc_helper.set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def play_video(video_id, client_data, stream_type, season_id=None, compilation_id=None):

	xbmc_helper.log_debug(compat._format('play_video: video_id {}', video_id))
	list_item = ListItem()
	video_data = libjoyn.get_video_data(video_id, loads(client_data), stream_type, season_id, compilation_id)
	succeeded = True

	if 'streamingFormat' in video_data.keys() and video_data['streamingFormat'] == 'dash':
		if libjoyn.set_mpd_props(list_item, video_data['videoUrl'], stream_type) is not False:
			if 'drm' in video_data.keys() and 'licenseUrl' in video_data.keys():
				list_item.setMimeType('application/dash+xml')
				if video_data['drm'] == 'widevine':
					list_item.setProperty(compat._format('{}.license_type', CONST['INPUTSTREAM_ADDON']), 'com.widevine.alpha')
					list_item.setProperty(
					        compat._format('{}.license_key', CONST['INPUTSTREAM_ADDON']),
					        compat._format(
					                '{}|{}|R{{SSM}}|', video_data['licenseUrl'],
					                request_helper.get_header_string({
					                        'User-Agent': libjoyn.config.get('USER_AGENT'),
					                        'Content-Type': 'application/octet-stream'
					                })))
					xbmc_helper.log_notice('Using Widevine as DRM')
				elif video_data['drm'] == 'playready':
					list_item.setProperty(compat._format('{}.license_type', CONST['INPUTSTREAM_ADDON']), 'com.microsoft.playready')
					list_item.setProperty(compat._format('{}.license_key', CONST['INPUTSTREAM_ADDON']), video_data['licenseUrl'])
					xbmc_helper.log_notice('Using PlayReady as DRM')

				else:
					xbmc_helper.notification(compat._format(xbmc_helper.translation('ERROR'), 'Unsupported DRM'),
					                         xbmc_helper.translation('MSG_ERROR_NO_VIDEOSTEAM'))
					succeeded = False

				list_item.setProperty(compat._format('{}.stream_headers', CONST['INPUTSTREAM_ADDON']),
				                      request_helper.get_header_string({'User-Agent': libjoyn.config['USER_AGENT']}))
				if xbmc_helper.get_bool_setting('checkdrmcert') is True and 'certificateUrl' in video_data.keys():
					list_item.setProperty(compat._format('{}.server_certificate', CONST['INPUTSTREAM_ADDON']),
					                      libjoyn.add_user_agent_http_header(video_data['certificateUrl']))
					xbmc_helper.log_debug(compat._format('SET DRM CERT: {}', video_data['certificateUrl']))
		else:
			xbmc_helper.notification(compat._format(xbmc_helper.translation('ERROR'), 'Video-Stream'),
			                         xbmc_helper.translation('MSG_ERROR_NO_VIDEOSTEAM'))
			xbmc_helper.log_error('Could not get valid MPD')
			succeeded = False

	else:
		succeeded = False

	if succeeded is True and 'season_id' in video_data.keys() and video_data['season_id'] is not None:
		add_lastseen(season_id=video_data['season_id'], max_lastseen=CONST['LASTSEEN_ITEM_COUNT'])
	elif succeeded is True and 'compilation_id' in video_data.keys() and video_data['compilation_id'] is not None:
		add_lastseen(compilation_id=video_data['compilation_id'], max_lastseen=CONST['LASTSEEN_ITEM_COUNT'])

	setResolvedUrl(pluginhandle, succeeded, list_item)


def get_favorite_entry(favorite_item, favorite_type):

	fav_del_art = {
	        'thumb': xbmc_helper.get_media_filepath('fav_del_thumb.png'),
	        'icon': xbmc_helper.get_media_filepath('fav_del_icon.png')
	}
	fav_add_art = {
	        'thumb': xbmc_helper.get_media_filepath('fav_add_thumb.png'),
	        'icon': xbmc_helper.get_media_filepath('fav_add_icon.png')
	}

	if check_favorites(favorite_item) is False:
		return get_dir_entry(is_folder=False,
		                     metadata={
		                             'infoLabels': {
		                                     'title':
		                                     xbmc_helper.translation('ADD_TO_WATCHLIST'),
		                                     'plot':
		                                     compat._format(xbmc_helper.translation('ADD_TO_WATCHLIST_PRX'),
		                                                    xbmc_helper.translation(favorite_type)),
		                             },
		                             'art': fav_add_art
		                     },
		                     mode='add_fav',
		                     favorite_item=favorite_item,
		                     fav_type=xbmc_helper.translation(favorite_type))
	else:
		return get_dir_entry(is_folder=False,
		                     metadata={
		                             'infoLabels': {
		                                     'title':
		                                     xbmc_helper.translation('REMOVE_FROM_WATCHLIST'),
		                                     'plot':
		                                     compat._format(xbmc_helper.translation('REMOVE_FROM_WATCHLIST_PRFX'),
		                                                    xbmc_helper.translation(favorite_type)),
		                             },
		                             'art': fav_del_art
		                     },
		                     mode='drop_fav',
		                     favorite_item=favorite_item,
		                     fav_type=xbmc_helper.translation(favorite_type))


def get_dir_entry(mode,
                  metadata,
                  is_folder=True,
                  channel_id='',
                  channel_path='',
                  tv_show_id='',
                  season_id='',
                  video_id='',
                  stream_type='VOD',
                  block_id='',
                  override_fanart='',
                  fav_type='',
                  favorite_item=None,
                  title_prefix='',
                  client_data='',
                  compilation_id='',
                  movie_id=''):

	params = {
	        'mode': mode,
	        'tv_show_id': tv_show_id,
	        'season_id': season_id,
	        'video_id': video_id,
	        'stream_type': stream_type,
	        'channel_id': channel_id,
	        'channel_path': channel_path,
	        'block_id': block_id,
	        'fav_type': fav_type,
	        'title': compat._encode(title_prefix) + compat._encode(metadata['infoLabels'].get('title', '')),
	        'client_data': client_data,
	        'compilation_id': compilation_id,
	        'movie_id': movie_id,
	}

	if favorite_item is not None:
		params.update({'favorite_item': dumps(favorite_item)})

	list_item = ListItem(metadata['infoLabels']['title'])
	list_item.setInfo(type='video', infoLabels=metadata['infoLabels'])

	if 'poster' not in metadata['art'] and 'thumb' in metadata['art']:
		metadata['art'].update({'poster': metadata['art']['thumb']})
	elif 'thumb' not in metadata['art']:
		metadata['art'].update({'thumb': default_logo})
		metadata['art'].update({'poster': default_logo})

	if 'icon' not in metadata['art']:
		metadata['art'].update({'icon': default_icon})

	if override_fanart != '':
		metadata['art'].update({'fanart': override_fanart})

	if 'fanart' not in metadata['art']:
		metadata['art'].update({'fanart': default_fanart})

	for art_key, art_value in metadata['art'].items():
		metadata['art'].update({art_key: libjoyn.add_user_agent_http_header(art_value)})

	list_item.setArt(metadata['art'])

	if mode == 'play_video' and video_id is not '' and client_data is not '':
		list_item.setProperty('IsPlayable', 'True')

	if metadata.get('is_bookmarked', None) is not None and libjoyn.get_auth_token().get('has_account', False) is True:
		asset_id = None

		if mode == 'season' and tv_show_id is not '':
			asset_id = tv_show_id
		elif mode == 'play_video' and movie_id is not '':
			asset_id = movie_id
		elif mode == 'compilation_items' and compilation_id is not '':
			asset_id = compilation_id

		if asset_id is not None:
			if metadata.get('is_bookmarked', False) is True:
				list_item.addContextMenuItems([(xbmc_helper.translation('DEL_FROM_JOYN_BOOKMARKS_LABEL'),
				                                compat._format('RunPlugin({}?{})', pluginurl,
				                                               urlencode({
				                                                       'mode': 'remove_joyn_bookmark',
				                                                       'asset_id': asset_id
				                                               })))])
			else:
				list_item.addContextMenuItems([(xbmc_helper.translation('ADD_TO_JOYN_BOOKMARKS_LABEL'),
				                                compat._format('RunPlugin({}?{})', pluginurl,
				                                               urlencode({
				                                                       'mode': 'add_joyn_bookmark',
				                                                       'asset_id': asset_id
				                                               })))])

	return (compat._format('{}?{}', pluginurl, urlencode(params)), list_item, is_folder)


def clear_cache():
	if xbmc_helper.remove_dir(CONST['CACHE_DIR']) is True:
		xbmc_helper.notification('Cache', xbmc_helper.translation('CACHE_WAS_CLEARED'), default_icon)
	else:
		xbmc_helper.notification('Cache', xbmc_helper.translation('CACHE_COULD_NOT_BE_CLEARED'))


def logout(dont_check_account=False):

	if dont_check_account is True:
		libjoyn.get_auth_token(reset_anon=True)

		if libjoyn.get_auth_token().get('has_account', False) is False:
			xbmc_helper.dialog(compat._unicode(xbmc_helper.translation('LOGOUT_OK_LABEL')))
		else:
			xbmc_helper.dialog(compat._unicode(xbmc_helper.translation('LOGOUT_NOK_LABEL')))

	elif libjoyn.get_auth_token().get('has_account', False) is True:
		xbmc_helper.log_debug('LOGOUT')
		libjoyn.get_auth_token(logout=True)
		if libjoyn.get_auth_token().get('has_account', False) is False:
			xbmc_helper.dialog(compat._unicode(xbmc_helper.translation('LOGOUT_OK_LABEL')))
			executebuiltin("Container.Refresh")
			xbmc_sleep(100)
		else:
			xbmc_helper.dialog(compat._unicode(xbmc_helper.translation('LOGOUT_NOK_LABEL')))
	else:
		xbmc_helper.dialog(compat._unicode(xbmc_helper.translation('NOT_LOGGED_IN_LABEL')))


def login(username=None, password=None, dont_check_account=False):

	if dont_check_account is False and libjoyn.get_auth_token().get('has_account', False) is True:
		executebuiltin('ActivateWindow(busydialognocancel)')
		account_info = libjoyn.get_account_info(True)
		xbmc_helper.dialog(
		        msg=compat._format(xbmc_helper.translation('LOGGED_IN_LABEL'),
		                           account_info.get('me', {}).get('profile', {}).get('email', '')),
		        msg_line2=compat._format(
		                xbmc_helper.translation('ACCOUNT_INFO_LABEL'),
		                xbmc_helper.translation('NO_LABEL') if libjoyn.get_account_subscription_config('hasActivePlus') is False else
		                xbmc_helper.translation('YES_LABEL'),
		                xbmc_helper.translation('NO_LABEL')
		                if libjoyn.get_account_subscription_config('hasActiveHD') is False else xbmc_helper.translation('YES_LABEL')))
		return executebuiltin('Dialog.Close(busydialognocancel)')

	elif username is None:
		executebuiltin('Dialog.Close(all, true)')
		_username = Dialog().input(compat._unicode(xbmc_helper.translation('USERNAME_LABEL')), type=INPUT_ALPHANUM)
		if len(_username) > 0:
			from re import match as re_match
			if re_match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", _username) is None:
				xbmc_helper.notification('Login', xbmc_helper.translation('MSG_INVALID_EMAIL'), default_icon)
				executebuiltin(compat._format('RunPlugin({}{})', pluginurl, pluginquery))
			else:
				executebuiltin(compat._format('RunPlugin({}{}&{})', pluginurl, pluginquery, urlencode({'username': _username})))
	else:
		if password is None:
			executebuiltin('Dialog.Close(all, true)')
			_password = Dialog().input(compat._unicode(xbmc_helper.translation('PASSWORD_LABEL')),
			                           type=INPUT_ALPHANUM,
			                           option=ALPHANUM_HIDE_INPUT)

			if len(_password) > 0:
				executebuiltin(compat._format('RunPlugin({}{}&{})', pluginurl, pluginquery, urlencode({'password': _password})))
		else:
			auth_token = libjoyn.get_auth_token(username=username, password=password)
			if auth_token is False or auth_token.get('has_account', False) is False:
				xbmc_helper.dialog_action(msg=compat._unicode(xbmc_helper.translation('LOGIN_FAILED_LABEL')),
				                          yes_label_translation='RETRY',
				                          cancel_label_translation='CONTINUE_ANONYMOUS',
				                          ok_addon_parameters='mode=login',
				                          cancel_addon_parameters='mode=logout&dont_check_account=true')
			else:
				executebuiltin("Container.Refresh")
				xbmc_sleep(100)
				executebuiltin(compat._format('RunPlugin({}{})', pluginurl, '?mode=login'))


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

	elif mode == 'open_foreign_settings' and 'foreign_addon_id' in param_keys:
		xbmc_helper.open_foreign_addon_settings(params['foreign_addon_id'])

	else:
		libjoyn = lib_joyn(default_icon)
		stream_type = params.get('stream_type', 'VOD')
		title = params.get('title', '')

		if mode == 'season' and 'tv_show_id' in param_keys:
			seasons(params['tv_show_id'], title)

		elif mode == 'season_episodes' and 'season_id' in param_keys:
			season_episodes(params['season_id'], title)

		elif mode == 'play_video' and 'video_id' in param_keys:
			if 'client_data' in param_keys:
				if 'season_id' in param_keys:
					play_video(video_id=params['video_id'],
					           client_data=params['client_data'],
					           stream_type=stream_type,
					           season_id=params['season_id'])
				elif 'compilation_id' in param_keys:
					play_video(video_id=params['video_id'],
					           client_data=params['client_data'],
					           stream_type=stream_type,
					           compilation_id=params['compilation_id'])
				else:
					play_video(video_id=params['video_id'], client_data=params['client_data'], stream_type=stream_type)
			if stream_type == 'LIVE':
				play_video(video_id=params['video_id'],
				           client_data=params.get('client_data', dumps(libjoyn.get_client_data(params['video_id'], stream_type))),
				           stream_type=stream_type)

		elif mode == 'compilation_items' and 'compilation_id' in param_keys:
			get_compilation_items(params['compilation_id'], title)

		elif mode == 'channels':
			channels(stream_type, title)

		elif mode == 'tvshows' and 'channel_id' in param_keys and 'channel_path' in param_keys:
			tvshows(params['channel_id'], params['channel_path'], title)

		elif mode == 'search':
			search(stream_type, title)

		elif mode == 'categories':
			categories(stream_type, title)

		elif mode == 'category' and 'block_id' in param_keys:
			category(params['block_id'], title)

		elif mode == 'show_favs':
			show_favorites(title)

		elif mode == 'add_fav' and 'favorite_item' in param_keys and 'fav_type' in param_keys:
			add_favorites(loads(params['favorite_item']), params['fav_type'])

		elif mode == 'drop_fav' and 'favorite_item' in param_keys and 'fav_type' in param_keys:
			drop_favorites(favorite_item=loads(params['favorite_item']), fav_type=params['fav_type'])

		elif mode == 'epg':
			executebuiltin('ActivateWindow(busydialognocancel)')
			executebuiltin(compat._format('RunScript(script.module.uepg,{})', get_uepg_params()))
			executebuiltin('Dialog.Close(busydialognocancel)')

		elif mode == 'show_joyn_bookmarks':
			show_joyn_bookmarks(title)

		elif mode == 'login':
			login_params = {}
			if 'dont_check_account' in param_keys:
				login_params.update({'dont_check_account': True})
			if 'username' in param_keys:
				login_params.update({'username': params['username']})
			if 'password' in param_keys:
				login_params.update({'password': params['password']})

			login(**login_params)

		elif mode == 'logout':
			if 'dont_check_account' in param_keys:
				logout(dont_check_account=True)
			else:
				logout()

		elif mode == 'remove_joyn_bookmark' and 'asset_id' in param_keys:
			remove_joyn_bookmark(params['asset_id'])

		elif mode == 'add_joyn_bookmark' and 'asset_id' in param_keys:
			add_joyn_bookmark(params['asset_id'])

		else:
			index()
else:
	libjoyn = lib_joyn(default_icon)
	index()
