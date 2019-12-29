# -*- coding: utf-8 -*-

from ..xbmc_helper import xbmc_helper


def get_lastseen():

	lastseen = xbmc_helper().get_json_data('lastseen')

	if lastseen is not None and len(lastseen) > 0:
		return sorted(lastseen, key=lambda k: k['lastseen'], reverse=True)

	return []


def add_lastseen(max_lastseen, season_id=None, compilation_id=None):

	from time import time

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

		xbmc_helper().set_json_data('lastseen', lastseen)


def show_lastseen(max_lastseen_count, default_fanart):

	from ..lib_joyn import lib_joyn
	from .plugin_favorites import check_favorites
	from ..plugin import get_list_items

	list_items = []
	season_ids = []
	compilation_ids = []

	landingpage = lib_joyn().get_landingpage()

	if 'ResumeLane' in landingpage.keys():
		for block_id, headline in landingpage['ResumeLane'].items():
			resume_lane = lib_joyn().get_graphql_response('SINGLEBLOCK', {'blockId': block_id, 'first': max_lastseen_count})
			if resume_lane.get('block', None) is not None and isinstance(resume_lane.get('block').get('assets', None), list):
				for asset in resume_lane.get('block').get('assets'):
					if len(list_items) < max_lastseen_count:
						if asset['__typename'] == 'Movie':
							list_items.extend(get_list_items([asset], prefix_label='CONTINUE_WATCHING', override_fanart=default_fanart))
						if asset['__typename'] == 'Episode' and 'series' in asset.keys() and 'season' in asset.keys(
						) and asset['season']['id'] not in season_ids:
							if xbmc_helper().get_bool_setting('dont_show_watchlist_in_lastseen') is True and check_favorites(
							        {'seasonId': asset['season']['id']}) is True:
								continue
							list_items.extend(
							        get_list_items([asset],
							                       prefix_label='CONTINUE_WATCHING',
							                       subtype_merges=['EPSIODE_AS_SERIES_SEASON'],
							                       override_fanart=default_fanart))
							season_ids.append(asset['season']['id'])
					else:
						break

	lastseen = get_lastseen()
	if len(lastseen) > 0:
		for lastseen_item in lastseen:
			if len(list_items) < max_lastseen_count:
				if lastseen_item.get('season_id', None) is not None and lastseen_item.get('season_id') not in season_ids:
					if xbmc_helper().get_bool_setting('dont_show_watchlist_in_lastseen') is True and check_favorites(
					        {'seasonId': lastseen_item['season_id']}) is True:
						continue

					season_data = lib_joyn().get_graphql_response('EPISODES', {'seasonId': lastseen_item['season_id'], 'first': 1})
					if season_data.get('season', None) is not None and season_data.get('season').get('episodes', None) is not None and len(
					        season_data['season']['episodes']) > 0 and lastseen_item['season_id'] not in season_ids:

						list_items.extend(
						        get_list_items(season_data['season']['episodes'],
						                       prefix_label='CONTINUE_WATCHING',
						                       subtype_merges=['EPSIODE_AS_SERIES_SEASON'],
						                       override_fanart=default_fanart))
						season_ids.append(lastseen_item['season_id'])

				elif lastseen_item.get('compilation_id', None) is not None:
					if xbmc_helper().get_bool_setting('dont_show_watchlist_in_lastseen') is True and check_favorites(
					        {'compilation_id': lastseen_item['compilation_id']}) is True:
						continue

					compilation_data = lib_joyn().get_graphql_response('COMPILATION', {
					        'id': lastseen_item['compilation_id'],
					})
					if lastseen_item['compilation_id'] not in compilation_ids and compilation_data.get('compilation', None) is not None:
						list_items.extend(
						        get_list_items([compilation_data['compilation']],
						                       prefix_label='CONTINUE_WATCHING',
						                       override_fanart=default_fanart))

						compilation_ids.append(lastseen_item['compilation_id'])

			else:
				break

	return list_items
