# -*- coding: utf-8 -*-

from sys import exit
from xbmc import executebuiltin
from xbmcgui import Dialog, ListItem, INPUT_ALPHANUM
from xbmcplugin import setResolvedUrl, addSortMethod
from xbmcplugin import SORT_METHOD_UNSORTED, SORT_METHOD_LABEL, SORT_METHOD_DATE, \
        SORT_METHOD_EPISODE, SORT_METHOD_DURATION, SORT_METHOD_TITLE
from .const import CONST
from . import compat as compat
from .xbmc_helper import xbmc_helper as xbmc_helper
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

if xbmc_helper().get_bool_setting('dont_verify_ssl_certificates') is True:

	import ssl
	try:
		_create_unverified_https_context = ssl._create_unverified_context
	except AttributeError:
		pass
	else:
		ssl._create_default_https_context = _create_unverified_https_context


def get_uepg_params():

	return compat._format('json={}&refresh_path={}epg&refresh_interval={}&row_count={}',
	                      quote(dumps(lib_joyn().get_uepg_data(pluginurl))), quote(compat._format('{}?mode=epg', pluginurl)),
	                      quote(str(CONST['UEPG_REFRESH_INTERVAL'])), quote(str(CONST['UEPG_ROWCOUNT'])))


def get_list_items(response_items,
                   prefix_label=None,
                   subtype_merges=[],
                   override_fanart='',
                   additional_metadata={},
                   force_resume_pos=False):

	from .submodules.libjoyn_video import get_video_client_data

	list_items = []

	for response_item in response_items:

		if isinstance(response_item.get('licenseTypes', None), list) and lib_joyn().check_license(response_item) is False:
			continue

		if force_resume_pos is True and (not isinstance(response_item.get('resumePosition', {}).get('position'), int)
		                                 or response_item.get('resumePosition').get('position') == 0):
			continue

		if response_item['__typename'] == 'Movie' and 'video' in response_item.keys() and 'id' in response_item['video']:

			movie_metadata = lib_joyn().get_metadata(response_item, 'EPISODE', 'MOVIE')
			movie_metadata.update(additional_metadata)

			movie_metadata['infoLabels'].update({'mediatype': 'movie'})

			if prefix_label is not None:
				movie_metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper().translation(prefix_label), movie_metadata['infoLabels'].get('title', ''))})

			list_items.append(
			        get_dir_entry(is_folder=False,
			                      mode='play_video',
			                      metadata=movie_metadata,
			                      video_id=response_item['video']['id'],
			                      client_data=dumps(get_video_client_data(response_item['video']['id'], 'VOD', response_item)),
			                      movie_id=response_item['id'],
			                      override_fanart=override_fanart))

		elif response_item['__typename'] == 'Brand':

			channel_metadata = lib_joyn().get_metadata(response_item, 'TVCHANNEL')
			if prefix_label is not None:
				channel_metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper().translation(prefix_label), channel_metadata['infoLabels'].get('title', ''))})
				channel_metadata.update(additional_metadata)

			list_items.append(
			        get_dir_entry(mode='tvshows',
			                      metadata=channel_metadata,
			                      channel_id=str(response_item['id']),
			                      channel_path=response_item['path'],
			                      override_fanart=override_fanart))

		elif response_item['__typename'] == 'Episode':

			if 'EPSIODE_AS_SERIES_SEASON' in subtype_merges and 'series' in response_item.keys() and 'season' in response_item.keys():

				season_metadata = lib_joyn().get_metadata(response_item['series'], 'TVSHOW')
				season_metadata['infoLabels'].update({
				        'title':
				        compat._format('{} - {}', season_metadata['infoLabels'].get('title', ''),
				                       compat._format(xbmc_helper().translation('SEASON_NO'), str(response_item['season']['number'])))
				})
				season_metadata.update(additional_metadata)

				if prefix_label is not None:
					season_metadata['infoLabels'].update(
					        {'title': compat._format(xbmc_helper().translation(prefix_label), season_metadata['infoLabels'].get('title', ''))})

				list_items.append(
				        get_dir_entry(
				                mode='season_episodes',
				                season_id=response_item['season']['id'],
				                metadata=season_metadata,
				                override_fanart=override_fanart,
				        ))
			else:

				episode_metadata = lib_joyn().get_metadata(response_item, 'EPISODE')
				episode_metadata['infoLabels'].update({'mediatype': 'episode'})
				video_id = response_item.get('video', {}).get('id', response_item.get('id'))

				list_items.append(
				        get_dir_entry(is_folder=False,
				                      mode='play_video',
				                      metadata=episode_metadata,
				                      video_id=video_id,
				                      client_data=dumps(get_video_client_data(video_id, 'VOD', response_item)),
				                      override_fanart=override_fanart,
				                      season_id=response_item.get('season', {}).get('id', '')))

		elif response_item['__typename'] == 'CompilationItem':

			compilation_item_metadata = lib_joyn().get_metadata(response_item, 'EPISODE')
			compilation_item_metadata['infoLabels'].update({'mediatype': 'episode'})

			video_id = response_item.get('video', {}).get('id', response_item.get('id'))
			list_items.append(
			        get_dir_entry(is_folder=False,
			                      mode='play_video',
			                      metadata=compilation_item_metadata,
			                      video_id=video_id,
			                      client_data=dumps(get_video_client_data(video_id, 'VOD', response_item)),
			                      override_fanart=override_fanart,
			                      compilation_id=response_item.get('compilation', {}).get('id', '')))

		elif response_item['__typename'] in ['Series', 'Compilation']:

			tvshow_metadata = lib_joyn().get_metadata(response_item, 'TVSHOW')
			tvshow_metadata.update(additional_metadata)

			if prefix_label is not None:
				tvshow_metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper().translation(prefix_label), tvshow_metadata['infoLabels'].get('title', ''))})

			if response_item['__typename'] == 'Series':
				list_items.append(
				        get_dir_entry(mode='season',
				                      tv_show_id=response_item['id'],
				                      metadata=tvshow_metadata,
				                      override_fanart=override_fanart))
			elif response_item['__typename'] == 'Compilation':
				list_items.append(
				        get_dir_entry(mode='compilation_items',
				                      compilation_id=response_item['id'],
				                      metadata=tvshow_metadata,
				                      override_fanart=override_fanart))

	return list_items


def index():

	if not xbmc_helper().addon_enabled(CONST['INPUTSTREAM_ADDON']):
		xbmc_helper().dialog_id('MSG_INPUSTREAM_NOT_ENABLED')
		exit(0)

	from inputstreamhelper import Helper
	is_helper = Helper('mpd', drm='com.widevine.alpha')
	if not is_helper.check_inputstream():
		xbmc_helper().dialog_id('MSG_WIDEVINE_NOT_FOUND')
		exit(0)

	from xbmc import getCondVisibility

	request_helper.purge_etags_cache(ttl=CONST['ETAGS_TTL'])
	from .submodules.plugin_lastseen import show_lastseen
	list_items = show_lastseen(xbmc_helper().get_int_setting('max_lastseen'), default_fanart)
	max_recommendations = xbmc_helper().get_int_setting('max_recommendations')

	if max_recommendations > 0:
		landingpage = lib_joyn().get_landingpage()
		if 'HeroLane' in landingpage.keys():
			for block_id, headline in landingpage['HeroLane'].items():
				hero_lane = lib_joyn().get_graphql_response('SINGLEBLOCK', {'blockId': block_id, 'first': max_recommendations})
				if hero_lane.get('block', None) is not None and hero_lane.get('block').get('assets', None) is not None:
					list_items.extend(
					        get_list_items(hero_lane['block']['assets'], prefix_label='RECOMMENDATION', override_fanart=default_fanart))

	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper().translation('MEDIA_LIBRARIES'),
	                        'plot': xbmc_helper().translation('MEDIA_LIBRARIES_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='channels',
	                      stream_type='VOD'))

	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper().translation('LIVE_TV'),
	                        'plot': xbmc_helper().translation('LIVE_TV_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='channels',
	                      stream_type='LIVE'))

	if xbmc_helper().get_bool_setting('show_categories_in_main_menu'):
		list_items.extend(categories('', '', True))
	else:
		list_items.append(
		        get_dir_entry(metadata={
		                'infoLabels': {
		                        'title': xbmc_helper().translation('CATEGORIES'),
		                        'plot': xbmc_helper().translation('CATEGORIES_PLOT'),
		                },
		                'art': {}
		        },
		                      mode='categories',
		                      stream_type='VOD'))
	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper().translation('WATCHLIST'),
	                        'plot': xbmc_helper().translation('WATCHLIST_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='show_favs'))

	if lib_joyn().get_auth_token().get('has_account', False) is True:
		list_items.append(
		        get_dir_entry(metadata={
		                'infoLabels': {
		                        'title': xbmc_helper().translation('JOYN_BOOKMARKS'),
		                        'plot': '',
		                },
		                'art': {}
		        },
		                      mode='show_joyn_bookmarks'))

	list_items.append(
	        get_dir_entry(metadata={
	                'infoLabels': {
	                        'title': xbmc_helper().translation('SEARCH'),
	                        'plot': xbmc_helper().translation('SEARCH_PLOT'),
	                },
	                'art': {}
	        },
	                      mode='search',
	                      is_folder=False))

	if compat.PY2 is True and getCondVisibility('System.HasAddon(script.module.uepg)'):
		list_items.append(
		        get_dir_entry(metadata={
		                'infoLabels': {
		                        'title': xbmc_helper().translation('TV_GUIDE'),
		                        'plot': xbmc_helper().translation('TV_GUIDE_PLOT'),
		                },
		                'art': {}
		        },
		                      mode='epg',
		                      stream_type='LIVE',
		                      is_folder=False))

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'INDEX')
	if str(xbmc_helper().get_data('asked_for_login')) != 'True':
		xbmc_helper().set_data('asked_for_login', 'True')

		if lib_joyn().get_auth_token().get('has_account', False) is False:
			xbmc_helper().dialog_action(msg=compat._unicode(xbmc_helper().translation('LOGIN_NOW_LABEL')),
			                            yes_label_translation='LOGIN_LABEL',
			                            cancel_label_translation='CONTINUE_ANONYMOUS',
			                            ok_addon_parameters='mode=login')


def channels(stream_type, title):

	list_items = []
	landingpage = lib_joyn().get_landingpage()
	if stream_type == 'VOD':
		if 'ChannelLane' in landingpage.keys():
			for block_id, headline in landingpage['ChannelLane'].items():
				channels = lib_joyn().get_graphql_response('SINGLEBLOCK', {'blockId': block_id})
				if channels.get('block', {}).get('assets', None) is not None:
					list_items.extend(get_list_items(channels['block']['assets'], override_fanart=default_fanart))

			xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEORIES', title)

	elif stream_type == 'LIVE':

		from .submodules.libjoyn_video import get_video_client_data
		epg = lib_joyn().get_epg(first=2, use_cache=False)
		for brand_epg in epg['brands']:
			if brand_epg['livestream'] is not None:
				if 'epg' in brand_epg['livestream'].keys() and len(brand_epg['livestream']['epg']) > 0:
					metadata = lib_joyn().get_epg_metadata(brand_epg['livestream'])

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
					                      client_data=dumps(get_video_client_data(brand_epg['livestream']['id'], 'LIVE')),
					                      video_id=brand_epg['livestream']['id'],
					                      stream_type='LIVE'))

		xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'LIVE_TV', title)


def tvshows(channel_id, channel_path, title):

	from .submodules.plugin_favorites import get_favorite_entry
	list_items = []

	tvshows = lib_joyn().get_graphql_response('CHANNEL', {'path': channel_path})
	if tvshows is not None and tvshows.get('page', None) is not None and tvshows.get('page').get('assets', None) is not None:
		list_items = get_list_items(tvshows['page']['assets'], override_fanart=default_fanart)

	if len(list_items) == 0:
		from xbmcplugin import endOfDirectory
		endOfDirectory(handle=pluginhandle, succeeded=False)

		return xbmc_helper().notification(xbmc_helper().translation('MEDIA_LIBRARY'),
		                                  xbmc_helper().translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	list_items.append(get_favorite_entry({'channel_id': channel_id}, 'MEDIA_LIBRARY'))
	xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)


def seasons(tv_show_id, title):

	from .submodules.plugin_favorites import get_favorite_entry
	list_items = []
	seasons = lib_joyn().get_graphql_response('SEASONS', {'seriesId': tv_show_id})

	if seasons is not None and seasons.get('series', None) is not None:
		tvshow_metadata = lib_joyn().get_metadata(seasons['series'], 'TVSHOW')
		counter = 1
		seasons_count = len(seasons['series']['seasons'])

		for season in seasons['series']['seasons']:

			if 'number' in season.keys():
				season_number = season['number']
			else:
				season_number = counter

			if xbmc_helper().get_bool_setting('show_episodes_immediately') and len(seasons['series']['seasons']) == 1:
				return season_episodes(
				        season['id'],
				        compat._format('{} - {}', title, compat._format(xbmc_helper().translation('SEASON_NO'), str(season_number))))

			tvshow_metadata['infoLabels'].update({
			        'title': compat._format(xbmc_helper().translation('SEASON_NO'), str(season_number)),
			        'season': seasons_count,
			        'sortseason': season_number,
			})

			list_items.append(
			        get_dir_entry(mode='season_episodes',
			                      season_id=season['id'],
			                      metadata=tvshow_metadata,
			                      title_prefix=compat._format('{} - ', title)))
			counter += 1

	if len(list_items) == 0:
		from xbmcplugin import endOfDirectory
		endOfDirectory(handle=pluginhandle, succeeded=False)

		return xbmc_helper().notification(xbmc_helper().translation('TV_SHOW'),
		                                  xbmc_helper().translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_TITLE)

	list_items.append(get_favorite_entry({'tv_show_id': tv_show_id}, 'TV_SHOW'))
	xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'SEASONS', title)


def season_episodes(season_id, title):

	from .submodules.plugin_favorites import get_favorite_entry
	list_items = []
	episodes = lib_joyn().get_graphql_response('EPISODES', {'seasonId': season_id})
	override_fanart = default_fanart
	if episodes is not None and episodes.get('season', None) is not None and isinstance(
	        episodes.get('season').get('episodes', None), list) and len(episodes.get('season').get('episodes')) > 0:

		first_episode = episodes.get('season').get('episodes')[0]
		if 'series' in first_episode.keys():
			tvshow_meta = lib_joyn().get_metadata(first_episode['series'], 'TVSHOW')
			if 'fanart' in tvshow_meta['art']:
				override_fanart = tvshow_meta['art']['fanart']

		list_items = get_list_items(episodes.get('season').get('episodes'), override_fanart=override_fanart)

	if len(list_items) == 0:
		from xbmcplugin import endOfDirectory
		endOfDirectory(handle=pluginhandle, succeeded=False)

		return xbmc_helper().notification(xbmc_helper().translation('SEASON'),
		                                  xbmc_helper().translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DURATION)
	addSortMethod(pluginhandle, SORT_METHOD_DATE)
	addSortMethod(pluginhandle, SORT_METHOD_EPISODE)

	list_items.append(get_favorite_entry({'season_id': season_id}, 'SEASON'))
	xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'EPISODES', title)


def get_compilation_items(compilation_id, title):

	from .submodules.plugin_favorites import get_favorite_entry
	list_items = []
	compilation_items = lib_joyn().get_graphql_response('COMPILATION_ITEMS', {'id': compilation_id})
	override_fanart = default_fanart

	if compilation_items is not None and compilation_items.get('compilation', None) is not None and isinstance(
	        compilation_items.get('compilation').get('compilationItems', None),
	        list) and len(compilation_items.get('compilation').get('compilationItems')) > 0:

		first_item = compilation_items.get('compilation').get('compilationItems')[0]
		if 'compilation' in first_item.keys():
			compilation_metadata = lib_joyn().get_metadata(first_item['compilation'], 'TVSHOW')
			if 'fanart' in compilation_metadata['art']:
				override_fanart = compilation_metadata['art']['fanart']

		list_items = get_list_items(compilation_items.get('compilation').get('compilationItems'), override_fanart=override_fanart)

	if len(list_items) == 0:
		from xbmcplugin import endOfDirectory
		endOfDirectory(handle=pluginhandle, succeeded=False)

		return xbmc_helper().notification(xbmc_helper().translation('TV_SHOW'),
		                                  xbmc_helper().translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)
	addSortMethod(pluginhandle, SORT_METHOD_DURATION)

	list_items.append(get_favorite_entry({'compilation_id': compilation_id}, 'TV_SHOW'))
	xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'EPISODES', title)


def search(stream_type, title, search_term=''):

	if len(search_term) != 0:
		xbmc_helper().log_debug('Search term: {}', search_term)
		search_response = lib_joyn().get_graphql_response('SEARCH', {'text': search_term})
		if 'search' in search_response.keys() and 'results' in search_response['search'] and len(
		        search_response['search']['results']) > 0:

			return xbmc_helper().set_folder(get_list_items(search_response['search']['results'], override_fanart=default_fanart),
			                                pluginurl, pluginhandle, pluginquery, 'TV_SHOWS', title)
	else:
		_search_term = Dialog().input(xbmc_helper().translation('SEARCH'), type=INPUT_ALPHANUM)
		search_response = lib_joyn().get_graphql_response('SEARCH', {'text': _search_term})
		if 'search' in search_response.keys() and 'results' in search_response['search'] and len(
		        search_response['search']['results']) > 0:
			_url = compat._format('Container.Update({}?{},replace)', pluginurl,
			                      urlencode({
			                              'mode': 'search',
			                              'search_term': _search_term,
			                      }))
			return executebuiltin(_url)
		else:
			xbmc_helper().notification(xbmc_helper().translation('SEARCH'),
			                           compat._format(xbmc_helper().translation('MSG_NO_SEARCH_RESULTS'), _search_term), default_icon)


def categories(stream_type, title, return_list_items=False):

	list_items = []
	landingpage = lib_joyn().get_landingpage()

	for lane_type in CONST['CATEGORY_LANES']:
		if lane_type in landingpage.keys():
			block_ids = list(landingpage[lane_type].keys())
			block_ids.reverse()
			for block_id in block_ids:
				list_items.append(
				        get_dir_entry(metadata={
				                'infoLabels': {
				                        'title': landingpage[lane_type][block_id],
				                        'plot': ''
				                },
				                'art': {}
				        },
				                      mode='category',
				                      viewtype='TV_SHOWS' if lane_type != 'ResumeLane' else 'EPISODES',
				                      block_id=block_id))
	if return_list_items is True:
		return list_items
	else:
		xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, 'CATEORIES', title)


def category(block_id, title, viewtype='TV_SHOWS'):

	from .submodules.plugin_favorites import get_favorite_entry
	list_items = []
	category = lib_joyn().get_graphql_response('SINGLEBLOCK', {'blockId': block_id})

	if category is not None and category.get('block', None) is not None and category.get('block').get('assets', None) is not None:
		list_items = get_list_items(category['block']['assets'],
		                            override_fanart=default_fanart,
		                            force_resume_pos=False if viewtype != 'EPISODES' else True)

	if len(list_items) == 0:
		from xbmcplugin import endOfDirectory
		endOfDirectory(handle=pluginhandle, succeeded=False)

		return xbmc_helper().notification(xbmc_helper().translation('CATEGORY'),
		                                  xbmc_helper().translation('MSG_NO_CONTENT'), default_icon)

	addSortMethod(pluginhandle, SORT_METHOD_UNSORTED)
	addSortMethod(pluginhandle, SORT_METHOD_LABEL)

	list_items.append(get_favorite_entry({'block_id': block_id}, 'CATEGORY'))
	xbmc_helper().set_folder(list_items, pluginurl, pluginhandle, pluginquery, viewtype, title)


def play_video(video_id, client_data, stream_type, season_id=None, compilation_id=None):

	from .mpd_parser import mpd_parser as mpd_parser
	from xbmc import getCondVisibility
	xbmc_helper().log_debug('play_video: video_id {}', video_id)
	succeeded = False
	list_item = ListItem()

	try:
		from .submodules.libjoyn_video import get_video_data
		video_data = get_video_data(video_id, loads(client_data), stream_type, season_id, compilation_id)

		xbmc_helper().log_debug('Got video data: {}', video_data.get('licenseUrl'))

		parser = video_data.get('parser', None)
		if parser is not None:
			list_item.setProperty('inputstreamaddon', CONST['INPUTSTREAM_ADDON'])
			# DASH
			if isinstance(parser, mpd_parser):
				list_item.setMimeType('application/dash+xml')
				list_item.setProperty(compat._format('{}.manifest_type', CONST['INPUTSTREAM_ADDON']), 'mpd')
				if parser.mpd_filepath is not None:
					list_item.setPath(parser.mpd_filepath if not getCondVisibility('System.Platform.Windows')
					                  and not getCondVisibility('System.Platform.UWP') else parser.mpd_filepath.replace('\\', '/'))
				elif parser.mpd_url is not None:
					list_item.setPath(lib_joyn().add_user_agent_http_header(parser.mpd_url))
				else:
					raise ValueError(compat._format('Could not find a valid DASH Manifest - parser: {}', vars(mpd_parser)))

				drm = video_data.get('drm', '')
				license_key = video_data.get('licenseUrl', None)
				license_cert = video_data.get('certificateUrl', None)
				xbmc_helper().log_debug('drm: {} key: {} cert: {}', drm, license_key, license_cert)

				if license_key is not None:
					if drm.lower() == 'widevine':
						xbmc_helper().log_notice('Using Widevine as DRM')
						list_item.setProperty(compat._format('{}.license_type', CONST['INPUTSTREAM_ADDON']), 'com.widevine.alpha')
						list_item.setProperty(
						        compat._format('{}.license_key', CONST['INPUTSTREAM_ADDON']),
						        compat._format(
						                '{}|{}|R{{SSM}}|', license_key,
						                request_helper.get_header_string({
						                        'User-Agent': lib_joyn().config.get('USER_AGENT'),
						                        'Content-Type': 'application/octet-stream'
						                })))
						list_item.setProperty(compat._format('{}.stream_headers', CONST['INPUTSTREAM_ADDON']),
						                      request_helper.get_header_string({'User-Agent': lib_joyn().config['USER_AGENT']}))

						if license_cert is not None and xbmc_helper().get_bool_setting('checkdrmcert') is True:
							xbmc_helper().log_debug('Set DRM cert: {}', license_cert)
							list_item.setProperty(compat._format('{}.server_certificate', CONST['INPUTSTREAM_ADDON']),
							                      lib_joyn().add_user_agent_http_header(license_cert))

					elif drm.lower() == 'playready':
						xbmc_helper().log_notice('Using PlayReady as DRM')
						list_item.setProperty(compat._format('{}.license_type', CONST['INPUTSTREAM_ADDON']), 'com.microsoft.playready')
						list_item.setProperty(
						        compat._format('{}.license_key', CONST['INPUTSTREAM_ADDON']),
						        compat._format(
						                '{}|{}|R{{SSM}}|', license_key,
						                request_helper.get_header_string({
						                        'User-Agent':
						                        CONST['EDGE_UA'],
						                        'Content-Type':
						                        'text/xml',
						                        'SOAPAction':
						                        'http://schemas.microsoft.com/DRM/2007/03/protocols/AcquireLicense'
						                })))

						list_item.setProperty(compat._format('{}.stream_headers', CONST['INPUTSTREAM_ADDON']),
						                      request_helper.get_header_string({'User-Agent': CONST['EDGE_UA']}))
					else:
						raise ValueError(compat._format('Unsupported DRM {}', drm))

			if stream_type == 'LIVE':
				list_item.setProperty(compat._format('{}.manifest_update_parameter', CONST['INPUTSTREAM_ADDON']), 'full')

				if xbmc_helper().get_bool_setting('fix_livestream_audio_sync') is True:
					mpd_timeshift_buffer = parser.get_timeshift_buffer_secs()
					if mpd_timeshift_buffer is not None:
						xbmc_helper().log_debug('Got timeshiftbuffer from mpd: {}', mpd_timeshift_buffer)
						live_stream_length = mpd_timeshift_buffer
					else:
						live_stream_length = xbmc_helper().get_int_setting('livestream_total_length')

					live_stream_resume_pos = live_stream_length - xbmc_helper().get_int_setting('livestream_offset')

					list_item.setProperty('TotalTime', str(float(live_stream_length)))
					list_item.setProperty('ResumeTime', str(float(live_stream_resume_pos)))
					xbmc_helper().log_debug('Tried fixing livestream audio sync issue - total time: {} - resume pos {}', live_stream_length,
					                        live_stream_resume_pos)

			succeeded = True

			from .submodules.plugin_lastseen import add_lastseen
			if 'season_id' in video_data.keys() and video_data['season_id'] is not None:
				add_lastseen(season_id=video_data['season_id'], max_lastseen=CONST['LASTSEEN_ITEM_COUNT'])
			elif 'compilation_id' in video_data.keys() and video_data['compilation_id'] is not None:
				add_lastseen(compilation_id=video_data['compilation_id'], max_lastseen=CONST['LASTSEEN_ITEM_COUNT'])

		else:
			raise ValueError(compat._format('Could not get parser: {}', parser))

	except Exception as e:
		xbmc_helper().log_error('Getting videostream / manifest failed with Exception: {}', e)
		xbmc_helper().notification(compat._format(xbmc_helper().translation('ERROR'), 'Video-Stream'),
		                           xbmc_helper().translation('MSG_ERROR_NO_VIDEOSTEAM'))
		pass

	if succeeded is True and stream_type == 'VOD':
		from xbmcgui import Window, getCurrentWindowId
		Window(getCurrentWindowId()).setProperty('joyn_video_id', video_id)

	setResolvedUrl(pluginhandle, succeeded, list_item)


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
                  movie_id='',
                  viewtype=''):

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
	        'viewtype': viewtype,
	}

	if favorite_item is not None:
		params.update({'favorite_item': dumps(favorite_item)})

	list_item = ListItem(label=metadata['infoLabels']['title'], offscreen=True)
	list_item.setInfo(type='video', infoLabels=metadata['infoLabels'])

	if is_folder is True:
		list_item.setProperty('isPlayable', 'false')

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
		metadata['art'].update({art_key: lib_joyn().add_user_agent_http_header(art_value)})

	list_item.setArt(metadata['art'])

	if mode == 'play_video' and video_id is not '' and client_data is not '':
		list_item.setProperty('IsPlayable', 'True')

		if 'resume_pos' in metadata.keys() and 'duration' in metadata['infoLabels'].keys():
			xbmc_helper().log_debug('Setting resume position - asset {} - pos {}', metadata['infoLabels']['title'],
			                        metadata.get('resume_pos'))
			list_item.setProperty('ResumeTime', metadata.get('resume_pos'))
			list_item.setProperty('TotalTime', str(float(metadata['infoLabels'].get('duration'))))

	if metadata.get('is_bookmarked', None) is not None and lib_joyn().get_auth_token().get('has_account', False) is True:
		asset_id = None

		if mode == 'season' and tv_show_id is not '':
			asset_id = tv_show_id
		elif mode == 'play_video' and movie_id is not '':
			asset_id = movie_id
		elif mode == 'compilation_items' and compilation_id is not '':
			asset_id = compilation_id

		if asset_id is not None:
			if metadata.get('is_bookmarked', False) is True:
				list_item.addContextMenuItems([(xbmc_helper().translation('DEL_FROM_JOYN_BOOKMARKS_LABEL'),
				                                compat._format('RunPlugin({}?{})', pluginurl,
				                                               urlencode({
				                                                       'mode': 'remove_joyn_bookmark',
				                                                       'asset_id': asset_id
				                                               })))])
			else:
				list_item.addContextMenuItems([(xbmc_helper().translation('ADD_TO_JOYN_BOOKMARKS_LABEL'),
				                                compat._format('RunPlugin({}?{})', pluginurl,
				                                               urlencode({
				                                                       'mode': 'add_joyn_bookmark',
				                                                       'asset_id': asset_id
				                                               })))])

	return (compat._format('{}?{}', pluginurl, urlencode(params)), list_item, is_folder)


def clear_cache():
	if xbmc_helper().remove_dir(CONST['CACHE_DIR']) is True:
		xbmc_helper().notification('Cache', xbmc_helper().translation('CACHE_WAS_CLEARED'), default_icon)
	else:
		xbmc_helper().notification('Cache', xbmc_helper().translation('CACHE_COULD_NOT_BE_CLEARED'))


def logout(dont_check_account=False):
	from .submodules.libjoyn_auth import logout as libjoyn_logout
	return libjoyn_logout(dont_check_account=dont_check_account)


def login(dont_check_account=False, failed=False, no_account_dialog=False):
	from .submodules.libjoyn_auth import login as libjoyn_login
	return libjoyn_login(dont_check_account=dont_check_account, failed=failed, no_account_dialog=no_account_dialog)


def run(_pluginurl, _pluginhandle, _pluginquery, addon):

	global pluginurl
	pluginurl = _pluginurl

	global pluginhandle
	pluginhandle = _pluginhandle

	global pluginquery
	pluginquery = _pluginquery

	xbmc_helper().set_addon(addon)

	global default_icon
	default_icon = xbmc_helper().get_addon().getAddonInfo('icon')

	global default_fanart
	default_fanart = xbmc_helper().get_addon().getAddonInfo('fanart')

	params = xbmc_helper().get_addon_params(pluginquery)
	param_keys = params.keys()

	if 'mode' in param_keys:

		mode = params['mode']

		if mode == 'clear_cache':
			clear_cache()

		elif mode == 'open_foreign_settings' and 'foreign_addon_id' in param_keys:
			xbmc_helper().open_foreign_addon_settings(params['foreign_addon_id'])

		else:

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
				elif stream_type == 'LIVE':
					from .submodules.libjoyn_video import get_video_client_data
					play_video(video_id=params['video_id'],
					           client_data=params.get('client_data', dumps(get_video_client_data(params['video_id'], stream_type))),
					           stream_type=stream_type)

			elif mode == 'compilation_items' and 'compilation_id' in param_keys:
				get_compilation_items(params['compilation_id'], title)

			elif mode == 'channels':
				channels(stream_type, title)

			elif mode == 'tvshows' and 'channel_id' in param_keys and 'channel_path' in param_keys:
				tvshows(params['channel_id'], params['channel_path'], title)

			elif mode == 'search':
				search(stream_type, title, search_term=params.get('search_term', ''))

			elif mode == 'categories':
				categories(stream_type, title)

			elif mode == 'category' and 'block_id' in param_keys:
				category(params['block_id'], title, params.get('viewtype', 'TV_SHOWS'))

			elif mode == 'show_favs':
				from .submodules.plugin_favorites import show_favorites
				show_favorites(title, pluginurl, pluginhandle, pluginquery, default_fanart, default_icon)

			elif mode == 'add_fav' and 'favorite_item' in param_keys and 'fav_type' in param_keys:
				from .submodules.plugin_favorites import add_favorites
				add_favorites(loads(params['favorite_item']), default_icon, params['fav_type'])

			elif mode == 'drop_fav' and 'favorite_item' in param_keys and 'fav_type' in param_keys:
				from .submodules.plugin_favorites import drop_favorites
				drop_favorites(favorite_item=loads(params['favorite_item']), default_icon=default_icon, fav_type=params['fav_type'])

			elif mode == 'epg':
				executebuiltin('ActivateWindow(busydialognocancel)')
				executebuiltin(compat._format('RunScript(script.module.uepg,{})', get_uepg_params()))
				executebuiltin('Dialog.Close(busydialognocancel)')

			elif mode == 'show_joyn_bookmarks':
				from .submodules.plugin_favorites import show_joyn_bookmarks
				show_joyn_bookmarks(title, pluginurl, pluginhandle, pluginquery, default_icon, default_fanart)

			elif mode == 'login':
				login_params = {}
				if 'dont_check_account' in param_keys:
					login_params.update({'dont_check_account': True})
				if 'failed' in param_keys:
					login_params.update({'failed': False if params.get('failed') != 'true' else True})
				if 'no_account_dialog' in param_keys:
					login_params.update({'no_account_dialog': False if params.get('no_account_dialog') != 'true' else True})

				login(**login_params)

			elif mode == 'logout':
				if 'dont_check_account' in param_keys:
					logout(dont_check_account=True)
				else:
					logout()

			elif mode == 'remove_joyn_bookmark' and 'asset_id' in param_keys:
				from .submodules.plugin_favorites import remove_joyn_bookmark
				remove_joyn_bookmark(params['asset_id'], default_icon)

			elif mode == 'add_joyn_bookmark' and 'asset_id' in param_keys:
				from .submodules.plugin_favorites import add_joyn_bookmark
				add_joyn_bookmark(params['asset_id'], default_icon)

			else:
				index()
	else:
		index()


pluginurl = None
pluginhandle = None
pluginquery = None
default_icon = None
default_fanart = None
default_logo = xbmc_helper().get_media_filepath('logo.gif')
