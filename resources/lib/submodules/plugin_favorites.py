# -*- coding: utf-8 -*-

from xbmc import executebuiltin
from ..xbmc_helper import xbmc_helper
from ..const import CONST
from .. import compat
from ..lib_joyn import lib_joyn


def get_favorites():
	favorites = xbmc_helper().get_json_data('favorites')

	if favorites is not None:
		return favorites

	return []


def get_favorite_entry(favorite_item, favorite_type):

	from ..plugin import get_dir_entry

	fav_del_art = {
	        'thumb': xbmc_helper().get_media_filepath('fav_del_thumb.png'),
	        'icon': xbmc_helper().get_media_filepath('fav_del_icon.png')
	}
	fav_add_art = {
	        'thumb': xbmc_helper().get_media_filepath('fav_add_thumb.png'),
	        'icon': xbmc_helper().get_media_filepath('fav_add_icon.png')
	}

	if check_favorites(favorite_item) is False:
		return get_dir_entry(is_folder=False,
		                     metadata={
		                             'infoLabels': {
		                                     'title':
		                                     xbmc_helper().translation('ADD_TO_WATCHLIST'),
		                                     'plot':
		                                     compat._format(xbmc_helper().translation('ADD_TO_WATCHLIST_PRX'),
		                                                    xbmc_helper().translation(favorite_type)),
		                             },
		                             'art': fav_add_art
		                     },
		                     mode='add_fav',
		                     favorite_item=favorite_item,
		                     fav_type=xbmc_helper().translation(favorite_type))
	else:
		return get_dir_entry(is_folder=False,
		                     metadata={
		                             'infoLabels': {
		                                     'title':
		                                     xbmc_helper().translation('REMOVE_FROM_WATCHLIST'),
		                                     'plot':
		                                     compat._format(xbmc_helper().translation('REMOVE_FROM_WATCHLIST_PRFX'),
		                                                    xbmc_helper().translation(favorite_type)),
		                             },
		                             'art': fav_del_art
		                     },
		                     mode='drop_fav',
		                     favorite_item=favorite_item,
		                     fav_type=xbmc_helper().translation(favorite_type))


def add_favorites(favorite_item, default_icon, fav_type=''):

	from time import time

	if check_favorites(favorite_item) is False:
		favorites = get_favorites()
		favorite_item.update({'added': time()})
		favorites.append(favorite_item)
		xbmc_helper().set_json_data('favorites', favorites)

		executebuiltin("Container.Refresh")
		xbmc_helper().notification(xbmc_helper().translation('WATCHLIST'),
		                           compat._format(xbmc_helper().translation('WL_TYPE_ADDED'), fav_type), default_icon)


def drop_favorites(favorite_item, default_icon, silent=False, fav_type=''):

	xbmc_helper().log_debug('drop_favorites  - item {}: ', favorite_item)
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

	xbmc_helper().set_json_data('favorites', favorites)

	if silent is False and found is True:
		xbmc_helper().notification(xbmc_helper().translation('WATCHLIST'),
		                           compat._format(xbmc_helper().translation('WL_TYPE_REMOVED'), fav_type), default_icon)
		executebuiltin("Container.Refresh")


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


def show_favorites(title, pluginurl, pluginhandle, pluginquery, default_fanart, default_icon):

	from xbmcplugin import addSortMethod, SORT_METHOD_UNSORTED, SORT_METHOD_LABEL, SORT_METHOD_DATEADDED
	from datetime import datetime
	from ..plugin import get_list_items, get_dir_entry

	favorites = get_favorites()
	list_items = []

	if len(favorites) == 0:
		from xbmcplugin import endOfDirectory
		endOfDirectory(handle=pluginhandle, succeeded=False)
		return xbmc_helper().notification(xbmc_helper().translation('WATCHLIST'),
		                                  xbmc_helper().translation('MSG_NO_FAVS_YET'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DATEADDED)

	for favorite_item in favorites:
		if 'added' in favorite_item.keys():
			add_meta = {'dateadded': datetime.fromtimestamp(favorite_item['added']).strftime('%Y-%m-%d %H:%M:%S')}
		else:
			add_meta = {}

		if favorite_item.get('season_id', None) is not None:
			season_data = lib_joyn().get_graphql_response('EPISODES', {'seasonId': favorite_item['season_id'], 'first': 1})
			if season_data.get('season', None) is not None and season_data.get('season').get('episodes', None) is not None and len(
			        season_data['season']['episodes']) > 0:
				season_metadata = lib_joyn().get_metadata(season_data['season']['episodes'][0]['series'], 'TVSHOW')
				season_metadata['infoLabels'].update({
				        'title':
				        compat._format('{} - {}', season_metadata['infoLabels'].get('title', ''),
				                       compat._format(xbmc_helper().translation('SEASON_NO'), str(season_data['season']['number'])))
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
			tvshow_data = lib_joyn().get_graphql_response('SERIES', {'id': favorite_item['tv_show_id']})
			if tvshow_data.get('series', None) is not None:
				list_items.extend(get_list_items([tvshow_data.get('series')], additional_metadata=add_meta, override_fanart=default_fanart))

		elif favorite_item.get('compilation_id', None) is not None:
			compilation_data = lib_joyn().get_graphql_response('COMPILATION', {'id': favorite_item['compilation_id']})
			if compilation_data.get('compilation', None) is not None:
				list_items.extend(
				        get_list_items([compilation_data['compilation']], additional_metadata=add_meta, override_fanart=default_fanart))

		elif favorite_item.get('block_id', None) is not None:
			landingpage = lib_joyn().get_landingpage()
			break_loop = False
			for lane_type, categories in landingpage.items():
				for category_block_id, category_name in categories.items():
					if category_block_id == favorite_item['block_id'] and lane_type in CONST['CATEGORY_LANES']:
						list_items.append(
						        get_dir_entry(metadata={
						                'infoLabels': {
						                        'title': compat._format('{}: {}',
						                                                xbmc_helper().translation('CATEGORY'), category_name),
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
			brand_data = lib_joyn().get_graphql_response('BRAND', {'id': int(favorite_item.get('channel_id'))})
			xbmc_helper().log_debug('brand: {}', brand_data)
			if brand_data.get('brand') is not None:
				list_items.extend(get_list_items([brand_data['brand']], additional_metadata=add_meta, override_fanart=default_fanart))
	if len(list_items) == 0:
		return xbmc_helper().notification(xbmc_helper().translation('WATCHLIST'),
		                                  xbmc_helper().translation('MSG_NO_FAVS_YET'), default_icon)

	xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'WATCHLIST', title)


def add_joyn_bookmark(asset_id, default_icon):

	add_joyn_bookmark_res = lib_joyn().get_graphql_response('ADD_BOOKMARK', {'assetId': asset_id})
	executebuiltin("Container.Refresh")
	return xbmc_helper().notification(
	        xbmc_helper().translation('JOYN_BOOKMARKS'),
	        xbmc_helper().translation('MSG_JOYN_BOOKMARK_ADD_SUCC' if add_joyn_bookmark_res.get('setBookmark', '') is not '' else
	                                  'MSG_JOYN_BOOKMARK_ADD_FAIL'), default_icon)


def remove_joyn_bookmark(asset_id, default_icon):

	del_bookmark_res = lib_joyn().get_graphql_response('DEL_BOOKMARK', {'assetId': asset_id})
	executebuiltin("Container.Refresh")
	return xbmc_helper().notification(
	        xbmc_helper().translation('JOYN_BOOKMARKS'),
	        xbmc_helper().translation('MSG_JOYN_BOOKMARK_DEL_SUCC' if del_bookmark_res.get('removeBookmark', False) is True else
	                                  'MSG_JOYN_BOOKMARK_DEL_FAIL'), default_icon)


def show_joyn_bookmarks(title, pluginurl, pluginhandle, pluginquery, default_icon, default_fanart):

	from ..plugin import get_list_items
	from xbmcplugin import addSortMethod, SORT_METHOD_UNSORTED, SORT_METHOD_LABEL

	list_items = []
	landingpage = lib_joyn().get_landingpage()

	if 'BookmarkLane' in landingpage.keys():
		for block_id, headline in landingpage['BookmarkLane'].items():
			bookmark_lane = lib_joyn().get_graphql_response('SINGLEBLOCK', {'blockId': block_id})
			if bookmark_lane.get('block', None) is not None and bookmark_lane.get('block').get('assets', None) is not None:
				list_items.extend(get_list_items(bookmark_lane['block']['assets'], override_fanart=default_fanart))

	if len(list_items) == 0:
		from xbmcplugin import endOfDirectory
		endOfDirectory(handle=pluginhandle, succeeded=False)

		return xbmc_helper().notification(xbmc_helper().translation('JOYN_BOOKMARKS'),
		                                  xbmc_helper().translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)
