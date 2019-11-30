# -*- coding: utf-8 -*-

from base64 import b64decode
from re import search, findall
from os import environ
from hashlib import sha1, sha256
from math import floor
from sys import exit
from datetime import datetime
from time import time
from copy import copy
from codecs import encode
from io import open as io_open
from uuid import uuid4
from xbmc import getCondVisibility
from random import choice
from .const import CONST
from . import compat as compat
from . import request_helper as request_helper
from . import cache as cache
from . import xbmc_helper as xbmc_helper
from .mpd_parser import mpd_parser as mpd_parser

try:
	from simplejson import loads, dumps
except ImportError:
	from json import loads, dumps

if compat.PY2:
	from urllib import urlencode
	from urlparse import urlparse, urlunparse , parse_qs
	from HTMLParser import HTMLParser
elif compat.PY3:
	from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
	from html.parser import HTMLParser


class lib_joyn(object):


	def __init__(self, default_icon):

		self.config = lib_joyn.get_config(default_icon)
		self.default_icon = default_icon


	def build_signature(self, video_id, encoded_client_data, entitlement_token):

		sha_input = video_id + ','
		sha_input += entitlement_token + ','
		sha_input += encoded_client_data
		sha_input += compat._decode(encode(self.config['SECRET'].encode('utf-8'), 'hex'))
		xbmc_helper.log_debug('Build signature: ' + sha_input)

		return  sha1(sha_input.encode('utf-8')).hexdigest()


	def set_mpd_props(self, list_item, url, stream_type='VOD'):

		xbmc_helper.log_debug('get_mpd_path: ' + url + 'stream_type: ' + stream_type)
		mpdparser = None

		##strip out the filter parameter
		parts = urlparse(url)
		query_dict = parse_qs(parts.query)

		if 'filter' in query_dict.keys():
			query_dict.update({'filter': ''})
			new_parts = list(parts)
			new_parts[4] = urlencode(query_dict)
			new_mpd_url = urlunparse(new_parts)
			xbmc_helper.log_debug('Stripped out filter from mpd url is ' + new_mpd_url)
			try:
				mpdparser = mpd_parser(new_mpd_url,self. config)
			except Exception as e:
				xbmc_helper.log_debug('Invalid MPD - Exception: ' + str(e))
				pass

		if mpdparser is None or mpdparser.mpd_tree is None:
			try:
				mpdparser = mpd_parser(url, self.config)
			except Exception as e:
				xbmc_helper.log_error('Invalid Orginal MPD - Exception: ' + str(e))

		if mpdparser is not None and mpdparser.mpd_tree is not None:

			list_item.setProperty('inputstreamaddon', CONST['INPUTSTREAM_ADDON'])
			list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.manifest_type', 'mpd')

			if stream_type == 'LIVE':
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.manifest_update_parameter', 'full')

			toplevel_base_url = None

			# the mpd has a Base URL at toplevel at a remote location
			# inputstream adaptive currently can't handle this correctly
			# it's known that this Base URL can be used to retrieve a 'better' mpd
			toplevel_base_url_res = mpdparser.get_toplevel_base_url()
			if toplevel_base_url_res is not None and toplevel_base_url_res.startswith('http'):
				xbmc_helper.log_debug('Found MPD with Base URL at toplevel: ' + toplevel_base_url_res)
				toplevel_base_url =  toplevel_base_url_res

			if toplevel_base_url is not None:
				if stream_type == 'VOD':
					new_mpd_url = toplevel_base_url + '.mpd?filter='
					try:
						test_mpdparser = mpd_parser(new_mpd_url, self.config)
						if test_mpdparser.mpd_tree is not None:
							mpdparser = test_mpdparser
							toplevel_base_url = None
							toplevel_base_url_res = mpdparser.get_toplevel_base_url()
							if toplevel_base_url_res is not None and toplevel_base_url_res.startswith('http'):
								xbmc_helper.log_debug('Found MPD with Base URL at toplevel in REPLACED url: ' + toplevel_base_url_res + 'URL: ' + new_mpd_url)
								toplevel_base_url =  toplevel_base_url_res
							else:
								toplevel_base_url = None
					except Exception as e:
						xbmc_helper.log_debug('Invalid MPD - Exception: ' + str(e))
						pass

				elif stream_type == 'LIVE':
					period_base_url_res = mpdparser.query_node_value(['Period','BaseURL'])
					if period_base_url_res is not None and period_base_url_res.startswith('/') and period_base_url_res.endswith('/'):
						new_mpd_url = toplevel_base_url + period_base_url_res + 'cenc-default.mpd'

						try:
							test_mpdparser = mpd_parser(new_mpd_url, self.config)
							if test_mpdparser.mpd_tree is not None:
								mpdparser = test_mpdparser
								toplevel_base_url = None
								toplevel_base_url_res = mpdparser.get_toplevel_base_url()
								if toplevel_base_url_res is not None and toplevel_base_url_res.startswith('http'):
									xbmc_helper.log_debug('Found MPD with Base URL at toplevel in REPLACED url: ' + toplevel_base_url_res + 'URL: ' + new_mpd_url)
									toplevel_base_url =  toplevel_base_url_res
								else:
									toplevel_base_url = None
						except Exception as e:
							xbmc_helper.log_debug('Invalid MPD - Exception: ' + str(e))
							pass

			if toplevel_base_url is not None:
				xbmc_helper.log_debug('Writing MPD file to local disc, since it has a remote top Level Base URL ...')
				sha_1 = sha1()
				sha_1.update(mpdparser.mpd_url)

				mpd_filepath = xbmc_helper.get_file_path(CONST['TEMP_DIR'],  sha_1.hexdigest() + '.mpd')
				with io_open(file=mpd_filepath, mode='w', encoding='utf-8') as mpd_filepath_out:
					mpd_filepath_out.write(compat._unicode(mpdparser.mpd_contents))

				xbmc_helper.log_debug('Local MPD filepath is: ' + mpd_filepath)
				list_item.setPath(mpd_filepath)

			else:
				list_item.setPath(request_helper.add_user_agend_header_string(mpdparser.mpd_url, self.config['USER_AGENT']))

			return True

		return False


	def get_entitlement_data(self, video_id, stream_type):

		entitlement_request_data = {
			'access_id' 	: self.config['PSF_CLIENT_CONFIG']['accessId'],
			'content_id' 	: video_id,
			'content_type'	: stream_type,
		}
		entitlement_request_headers = [('x-api-key', self.config['PSF_CONFIG']['default'][stream_type.lower()]['apiGatewayKey'])]

		return request_helper.post_json(self.config['PSF_CONFIG']['default'][stream_type.lower()]['entitlementBaseUrl'] + CONST['ENTITLEMENT_URL'],
					self.config, entitlement_request_data, entitlement_request_headers)


	def get_video_data(self, video_id, client_data, stream_type, season_id=None, compilation_id=None):

		video_url = self.config['PSF_CONFIG']['default'][stream_type.lower()]['playoutBaseUrl']
		xbmc_helper.log_debug("GOT CLIENT DATA: "  + dumps(client_data))

		if stream_type == 'VOD':
			video_url += 'playout/video/' + client_data['videoId']

		elif stream_type == 'LIVE':
			video_url += 'playout/channel/' + client_data['channelId']

		entitlement_data = self.get_entitlement_data(video_id, stream_type)

		encoded_client_data = request_helper.base64_encode_urlsafe(dumps(client_data))
		signature = self.build_signature(video_id, encoded_client_data, entitlement_data['entitlement_token'])

		video_url_params = {
			'entitlement_token'	: entitlement_data['entitlement_token'],
			'clientData'		: encoded_client_data,
			'sig'			: signature,
		}

		video_url += '?' + urlencode(video_url_params)

		video_data = request_helper.get_json_response(url=video_url, config=self.config, headers=[('Content-Type', 'application/x-www-form-urlencoded charset=utf-8')], \
			post_data='false', no_cache=True)

		if xbmc_helper.get_bool_setting('force_playready') and self.config['IS_ANDROID'] is True \
				and 'drm' in video_data.keys() and 'licenseUrl' in video_data.keys():

			if stream_type == 'VOD' and video_data['licenseUrl'].find('/widevine/v1') is not -1:
				video_data.update({'licenseUrl': video_data['licenseUrl'].replace('/widevine/v1', '/playready/v1')})
				video_data.update({'drm': 'playready'})
			elif stream_type == 'LIVE':
				video_data.update({'drm': 'playready'})

		if season_id is not None:
			video_data.update({'season_id': season_id})
		if  compilation_id is not None:
			video_data.update({'compilation_id': compilation_id})

		return video_data


	def get_epg(self):

		cached_epg =  cache.get_json('EPG')
		dt_now = datetime.now()
		if cached_epg['data'] is not None and cached_epg['is_expired'] is False and 'epg_expires' in cached_epg['data'].keys() \
			and datetime.fromtimestamp(cached_epg['data']['epg_expires']) > dt_now:

			xbmc_helper.log_debug('EPG FROM CACHE')
			epg_data = cached_epg['data']['epg_data']
		else:
			xbmc_helper.log_debug('EPG FROM API')
			epg_data = self.get_graphql_response('EPG')
			epg = {
				'epg_data': epg_data,
				'epg_expires': None,
			}
			for brand_epg in epg_data['brands']:
				if brand_epg.get('livestream', None) is not None and \
				'epg' in brand_epg['livestream'].keys () and len(brand_epg['livestream']['epg']) > 0:

					brand_live_stream_epg_count = len(brand_epg['livestream']['epg'])
					if brand_live_stream_epg_count > 0:
						penultimate_brand_live_stream_epg_timestamp = brand_epg['livestream']['epg'][(brand_live_stream_epg_count-2)]['startDate']
						if epg['epg_expires'] is None or epg['epg_expires'] > penultimate_brand_live_stream_epg_timestamp:
							epg.update({'epg_expires': penultimate_brand_live_stream_epg_timestamp})
			cache.set_json('EPG',epg)

		return epg_data


	def get_landingpage(self):

		cached_landingpage = cache.get_json('LANDINGPAGE')
		if cached_landingpage['data'] is not None and cached_landingpage['is_expired'] is False:
			landingpage = cached_landingpage['data']
		else:
			landingpage = {}
			raw_landingpage = self.get_graphql_response('LANDINGPAGE', {'path': '/'}, True)
			if 'page' in raw_landingpage.keys() and 'blocks' in raw_landingpage['page'].keys():
				for block in raw_landingpage['page']['blocks']:
					if block['isPersonalized'] is False:
						if  block['__typename'] not in landingpage.keys():
							landingpage.update({block['__typename']: {}})

						landingpage[block['__typename']].update({block['id']: block.get('headline', None)})

				cache.set_json('LANDINGPAGE', landingpage)

		return landingpage


	def get_uepg_data(self, pluginurl):

		epg = self.get_epg()
		uEPG_data = []
		channel_num = 0

		for brand_epg in epg['brands']:
			if brand_epg['livestream'] is not None and 'epg' in brand_epg['livestream'].keys() \
				and len(brand_epg['livestream']['epg']) > 0:

				if 'logo' in brand_epg.keys() and 'url' in brand_epg['logo'].keys():
					channel_logo=request_helper.add_user_agend_header_string(
							brand_epg['logo']['url']  + '/profile:nextgen-web-artlogo-183x75',
							self.config['USER_AGENT'])
				else:
					channel_logo=self.default_icon

				channel_name = brand_epg['livestream']['title']

				if brand_epg['livestream']['quality'] == 'HD':
					channel_name += ' HD'

				channel_num += 1

				client_data=dumps({'videoId': None,'channelId': brand_epg['livestream']['id']})

				uEPG_channel = {
					'channelnumber': channel_num,
					'isfavorite': False,
					'channellogo': channel_logo,
					'channelname': channel_name,
				}

				guidedata = []

				for epg_entry in brand_epg['livestream']['epg']:
					epg_metadata = lib_joyn.get_metadata(epg_entry, 'EPG')

					for art_item_type, art_item in epg_metadata['art'].items():
						epg_metadata['art'].update({art_item_type: request_helper.add_user_agend_header_string(art_item,self.config['USER_AGENT'])})

					epg_metadata['art'].update({
						'clearlogo': channel_logo,
						'icon': channel_logo
					})

					guidedata.append({
						'label': epg_metadata['infoLabels']['title'],
						'title': epg_metadata['infoLabels']['title'],
						'plot': epg_metadata['infoLabels'].get('plot', None),
						'art': epg_metadata['art'],
						'starttime': epg_entry['startDate'],
						'duration': (epg_entry['endDate']-epg_entry['startDate']),
						'url': pluginurl + '?' + urlencode({
								'mode': 'play_video',
								'stream_type': 'LIVE',
								'video_id': brand_epg['livestream']['id'],
								'client_data': client_data
							})
					})
				uEPG_channel.update({'guidedata': guidedata})
				uEPG_data.append(uEPG_channel)

		return uEPG_data


	def get_graphql_response(self, operation, variables={}, needs_auth=False):

		xbmc_helper.log_debug('GraphQL Operation: ' + str(operation))

		for required_var in CONST['GRAPHQL'][operation]['REQUIRED_VARIABLES']:
			if required_var not in variables.keys():
				if required_var in CONST['GRAPHQL']['STATIC_VARIABLES'].keys():
					variables.update({required_var: CONST['GRAPHQL']['STATIC_VARIABLES'][required_var]})
				else:
					xbmc_helper.log_error('Not all required variables set for operation: ' + operation)
					exit(0)

		params = {
			'query'	: 'query ' + CONST['GRAPHQL'][operation]['OPERATION'] + ' ' + CONST['GRAPHQL'][operation]['QUERY'],
			'extensions': {
					'persistedQuery': {
						'version': 1,
					},
			},
			'operationName'	: CONST['GRAPHQL'][operation]['OPERATION'],

		}

		if len(variables.keys()) != 0:
			params.update({'variables': dumps(variables)})

		params['extensions']['persistedQuery'].update({'sha256Hash': sha256(params['query'].encode('utf-8')).hexdigest()})
		params.update({'extensions': dumps(params['extensions'])})

		headers = copy(self.config['GRAPHQL_HEADERS'])

		if needs_auth is True:

			auth_token = self.get_auth_token()
			joyn_user_id = self.get_joyn_userid()

			if auth_token is not None and joyn_user_id is not None:
				headers.append(('Authorization', 'Bearer ' + auth_token))
				headers.append(('Joyn-User-Id', joyn_user_id))
			else:
				xbmc_helper.log_error("Failed to get auth_token or joyn_user_id")
				return {}

		api_response = {}

		try:
			api_response = request_helper.get_json_response(
				url=CONST['GRAPHQL']['API_URL'],
				config=self.config,
				params=params,
				headers=headers,
			)


		except Exception as e:
			xbmc_helper.log_error('Could not complete graphql request: ' + str(e) + 'params: ' + dumps(params))

		if 'errors' in api_response.keys():
			xbmc_helper.log_error('GraphQL query returned errors: ' + dumps(api_response['errors']) + 'params: ' + dumps(params))

		if 'data' in api_response.keys() and api_response['data'] is not None:
			return api_response['data']
		else:
			xbmc_helper.log_error('GraphQL query returned no data - response: ' + dumps(api_response) + 'params: '  + dumps(params))

		xbmc_helper.notification(
				xbmc_helper.translation('ERROR').format('GraphQL'),
				xbmc_helper.translation('MSG_GAPHQL_ERROR'),
		)
		exit(0)


	def get_joyn_userid(self):

		client_id_data = self.get_client_ids()
		return client_id_data.get('anon_device_id', None)


	def get_client_ids(self):

		client_id_data = xbmc_helper.get_json_data('client_ids')
		if client_id_data is None:
			xbmc_helper.log_debug("Creating new client_data")
			client_id_data = {
				'anon_device_id': str(uuid4()),
				'client_id': str(uuid4()),
				'client_name': self.config['USER_AGENT'],
			}
			xbmc_helper.set_json_data('client_ids', client_id_data)

		return client_id_data


	def get_auth_token(self):

		auth_token_data = xbmc_helper.get_json_data('auth_tokens')

		if auth_token_data is None:
			xbmc_helper.log_debug("Creating new auth_token_data")
			client_id_data = self.get_client_ids()
			auth_token_data = request_helper.post_json(
				CONST['AUTH_URL'] + CONST['AUTH_ANON_URL'],
				self.config,
				client_id_data
			)

			auth_token_data.update({'created': int(time())})
			xbmc_helper.set_json_data('auth_tokens', auth_token_data)

		#refresh the token at least 1h before it actual expires
		auth_token_expires = auth_token_data['created'] + (auth_token_data['expires_in']/1000) - 3600

		if time() >= auth_token_expires:
			xbmc_helper.log_debug("Refreshing auth_token_data")
			client_id_data = self.get_client_ids()
			refresh_auth_token_req_data = {
				'refresh_token': auth_token_data['refresh_token'],
				'client_id': client_id_data['client_id'],
				'client_name': client_id_data['client_name'],
			}
			refresh_auth_token_data = request_helper.post_json(
				CONST['AUTH_URL'] + CONST['AUTH_REFRESH'],
				self.config,
				refresh_auth_token_req_data
			)
			refresh_auth_token_data.update({'created': int(time())})
			xbmc_helper.set_json_data('auth_tokens', refresh_auth_token_data)

			return refresh_auth_token_data['access_token']

		return auth_token_data.get('access_token', None)

	@staticmethod
	def get_metadata(data, query_type, title_type_id=None):

		metadata = {
			'art': {},
			'infoLabels': {},
		}

		if 'TEXTS' in CONST['GRAPHQL']['METADATA'][query_type].keys():
			for text_key, text_mapping_key in CONST['GRAPHQL']['METADATA'][query_type]['TEXTS'].items():
				if text_key in data.keys() and data[text_key] is not None:
					metadata['infoLabels'].update({text_mapping_key: HTMLParser().unescape(data[text_key])})
				else:
					metadata['infoLabels'].update({text_mapping_key: ''})

		if title_type_id is not None and 'title' in metadata['infoLabels'].keys():
			metadata['infoLabels'].update({'title' :  compat._unicode((xbmc_helper.translation('TITLE_LABEL'))).format(metadata['infoLabels']['title'], \
				xbmc_helper.translation(title_type_id))})

		if 'ART' in CONST['GRAPHQL']['METADATA'][query_type].keys():
			for art_key, art_def in CONST['GRAPHQL']['METADATA'][query_type]['ART'].items():
				if art_key in data.keys():
					if type(data[art_key]) != type(list()):
						images = [data[art_key]]
					else:
						images = data[art_key]
					for image in images:
						for art_def_img_type, art_def_img in art_def.items():
							if image['__typename'] == 'Image' and art_def_img_type == image['type']:
								for art_def_img_map_key, art_def_img_map_profile in art_def_img.items():
									metadata['art'].update({
										art_def_img_map_key: image['url'] + '/' + art_def_img_map_profile
									})
		if 'ageRating' in data.keys() and  data['ageRating'] is not None and 'minAge' in data['ageRating'].keys():
			metadata['infoLabels'].update({'mpaa': xbmc_helper.translation('MIN_AGE').format(str(data['ageRating']['minAge']))})

		if 'genres' in data.keys() and type(data['genres']) == type(list()):
			metadata['infoLabels'].update({'genre': []})

			for genre in data['genres']:
				if 'name' in genre.keys():
					metadata['infoLabels']['genre'].append(genre['name'])

		if query_type == 'EPISODE':

			if 'endsAt' in data.keys() and data['endsAt'] is not None and data['endsAt'] < 9999999999:
				endsAt = xbmc_helper.timestamp_to_datetime(data['endsAt'], True)
				if endsAt is not False:
					metadata['infoLabels'].update({
						'plot': compat._unicode(xbmc_helper.translation('VIDEO_AVAILABLE'))
								.format(endsAt) + metadata['infoLabels'].get('plot', '')
					})

			if 'number' in data.keys() and data['number'] is not None:
				metadata['infoLabels'].update({
						'episode': data['number'],
						'sortepisode': data['number'],
					})
			if 'series' in data.keys():
				if 'title' in data['series'].keys():
					metadata['infoLabels'].update({'tvshowtitle': HTMLParser().unescape(data['series']['title'])})
				series_meta = lib_joyn.get_metadata(data['series'],'TVSHOW')
				if 'clearlogo' in series_meta['art'].keys():
					metadata['art'].update({'clearlogo': series_meta['art']['clearlogo']})

			elif 'compilation' in data.keys():
				compilation_meta = lib_joyn.get_metadata(data['compilation'],'TVSHOW')
				if 'title' in data['compilation'].keys():
					metadata['infoLabels'].update({'tvshowtitle': HTMLParser().unescape(data['compilation']['title'])})
				if 'clearlogo' in compilation_meta['art'].keys():
					metadata['art'].update({'clearlogo': compilation_meta['art']['clearlogo']})


		if 'airdate' in data.keys() and data['airdate'] is not None:
			broadcast_datetime = xbmc_helper.timestamp_to_datetime(data['airdate'], True)
			if broadcast_datetime is not False:
				broadcast_date =broadcast_datetime.strftime('%Y-%m-%d')
				metadata['infoLabels'].update({
					'premiered': broadcast_date,
					'date': broadcast_date,
					'aired': broadcast_date,
				})

		if 'video' in data.keys() and data['video'] is not None \
			and 'duration' in data['video'].keys() and data['video']['duration'] is not None:
				metadata['infoLabels'].update({'duration': (data['video']['duration'])})

		if 'season' in data.keys() and data['season'] is not None \
			and 'number' in data['season'].keys() and data['season']['number'] is not None:

			metadata['infoLabels'].update({
				'season': data['season']['number'],
				'sortseason': data['season']['number'],
			})

		return metadata


	@staticmethod
	def get_epg_metadata(brand_livestream_epg):

		epg_metadata = {
			'art': {},
			'infoLabels': {},
		}

		brand_title = brand_livestream_epg['title']
		if brand_livestream_epg['quality'] == 'HD':
			brand_title += ' HD'
		dt_now = datetime.now()
		epg_metadata['infoLabels'].update({'title': compat._unicode(xbmc_helper.translation('LIVETV_TITLE')).format(brand_title, '')})

		for idx, epg_entry in enumerate(brand_livestream_epg['epg']):
			end_time = xbmc_helper.timestamp_to_datetime(epg_entry['endDate'])

			if end_time is not False and end_time > dt_now:
				epg_metadata = lib_joyn.get_metadata(epg_entry, 'EPG')
				epg_metadata['infoLabels'].update({
						'title': compat._unicode(xbmc_helper.translation('LIVETV_TITLE')).format(brand_title, epg_entry['title'])
					})
				if len(brand_livestream_epg['epg']) > (idx+1):
					epg_metadata['infoLabels'].update({
						'plot': compat._unicode(xbmc_helper.translation('LIVETV_UNTIL_AND_NEXT')).format(
								end_time,
								brand_livestream_epg['epg'][idx+1]['title']
							)
					})
				else:
					epg_metadata['infoLabels'].update({
						'plot': compat._unicode(xbmc_helper.translation('LIVETV_UNTIL')).format(end_time)
					})

				if epg_entry.get('secondaryTitle', None) is not None:
					epg_metadata['infoLabels']['plot'] += epg_entry['secondaryTitle']

				break

		return epg_metadata


	@staticmethod
	def get_config(default_icon):

		recreate_config = True
		config = {}
		cached_config = None
		addon_version = xbmc_helper.get_addon_version()

		expire_config_mins = xbmc_helper.get_int_setting('configcachemins')
		if expire_config_mins is not None:
			confg_cache_res = cache.get_json('CONFIG', (expire_config_mins * 60))
		else:
			confg_cache_res = cache.get_json('CONFIG')

		if confg_cache_res['data'] is not None:
			cached_config =  confg_cache_res['data']

		if (confg_cache_res['is_expired'] is False or expire_config_mins == 0) and cached_config is not None and  'ADDON_VERSION' in cached_config.keys() \
			and cached_config['ADDON_VERSION'] == addon_version:
			recreate_config = False
			config = cached_config

		if cached_config is None or 'ADDON_VERSION' not in cached_config.keys() or ('ADDON_VERSION' in cached_config.keys() and cached_config['ADDON_VERSION'] != addon_version):
			xbmc_helper.remove_dir(CONST['CACHE_DIR'])
			xbmc_helper.log_debug('cleared cache')

		if recreate_config == True:

			xbmc_helper.log_debug('get_config(): create config')

			config = {
				'CONFIG'		: {'PLAYERCONFIG_URL': None, 'API_GW_API_KEY': None},
				'PSF_CONFIG' 		: {},
				'PLAYER_CONFIG'		: {},
				'PSF_VARS'		: {},
				'PSF_CLIENT_CONFIG'	: None,
				'IS_ANDROID'		: False,
				'IS_ARM'		: False,
				'ADDON_VERSION'		: addon_version,
				'country'		: None,
				'http_headers'		: [],
			}

			os_uname = compat._uname_list()

			#android
			if getCondVisibility('System.Platform.Android'):
				from subprocess import check_output
				try:
					os_version = check_output(
						['/system/bin/getprop', 'ro.build.version.release']).strip(' \t\n\r')
					model = model = check_output(
						['/system/bin/getprop', 'ro.product.model']).strip(' \t\n\r')
					build_id = check_output(
						['/system/bin/getprop', 'ro.build.id']).strip(' \t\n\r')

					config['USER_AGENT'] ='Mozilla/5.0 (Linux; Android {}; {} Build/{})'.format(os_version, model, build_id)

				except OSError:
					config['USER_AGENT'] = 'Mozilla/5.0 (Linux; Android 8.1.0; Nexus 6P Build/OPM6.171019.030.B1)'
					pass
				config['USER_AGENT'] += ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.73 Mobile Safari/537.36'
				config['IS_ANDROID'] = True

			# linux on arm uses widevine from chromeos
			elif os_uname[0] == 'Linux' and os_uname[4].lower().find('arm') is not -1:
				config['USER_AGENT'] = 'Mozilla/5.0 (X11 CrOS '+  os_uname[4] + ' 4537.56.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.38 Safari/537.36'
				config['IS_ARM'] = True
			elif os_uname[0] == 'Linux':
				config['USER_AGENT'] = 'Mozilla/5.0 (X11 Linux ' + os_uname[4] + ') AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
			elif os_uname[0] == 'Darwin':
				config['USER_AGENT'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/600.7.12 (KHTML, like Gecko) Version/8.0.7 Safari/600.7.12'
			else:
				config['USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0 Win64 x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'

			html_content = request_helper.get_url(CONST['BASE_URL'], config)
			if html_content is None or html_content is '':
				xbmc_helper.notification(
						xbmc_helper.translation('ERROR').format('Url access'),
						xbmc_helper.translation('MSG_NO_ACCESS_TO_URL').format(CONST['BASE_URL'])
					)
				exit(0)

			county_setting = xbmc_helper.get_setting('country')
			xbmc_helper.log_debug("COUNTRY SETTING: " + county_setting)
			ip_api_response = request_helper.get_json_response(url=CONST['IP_API_URL'].format(xbmc_helper.translation('LANG_CODE')), config=config, silent=True)

			if type(ip_api_response) != type(dict()) or 'countryCode' not in ip_api_response.keys():

				ip_api_response = {
							'status'	: 'success',
							'country'	: 'Deutschland',
							'countryCode'	: 'DE',
					}
			config.update({'actual_country': ip_api_response.get('countryCode', 'Unknown')})

			if county_setting is '' or county_setting is '0':
				xbmc_helper.log_debug('IP API Response is: ' + dumps(ip_api_response))
				if ip_api_response is not None and ip_api_response != '' and 'countryCode' in ip_api_response.keys():
					if ip_api_response['countryCode'] in CONST['COUNTRIES'].keys():
						config.update({'country': ip_api_response['countryCode']})
					else:
						xbmc_helper.dialog_settings(
								xbmc_helper.translation('MSG_COUNTRY_INVALID').format(compat._encode(ip_api_response.get('country', 'Unknown')))
						)
						exit(0)

			else:
				for supported_country_key, supported_country in CONST['COUNTRIES'].items():
					if supported_country['setting_id'] == county_setting:
						config.update({'country': supported_country_key})
						break

			if config['country'] is None:
				xbmc_helper.dialog_settings(xbmc_helper.translation('MSG_COUNTRY_NOT_DETECTED'))
				exit(0)

			if config['country'] != config['actual_country']:

				try:
					from ipaddress import IPv4Network
				except ImportError:
					from external.ipaddress import IPv4Network

				config['http_headers'].append(('x-forwarded-for',
					str(choice(list(IPv4Network(compat._unicode(choice(CONST['NETBLOCKS'][config.get('country', 'DE')]))).hosts())))))

			main_js_src = None
			graphql_headers = []
			for match in findall('<script type="text/javascript" src="(.*?)"></script>', html_content):
				if match.find('/main') is not -1:
					main_js_src = CONST['BASE_URL'] + match
					main_js =  request_helper.get_url(main_js_src, config)
					break

			if main_js_src is None:
				xbmc_helper.log_debug('Using local main.js')
				main_js = xbmc_helper.get_file_contents(xbmc_helper.get_resource_filepath('main.js', 'external'))

			uri_start_match = CONST['GRAPHQL']['API_URL']
			uri_start = main_js.find(uri_start_match)

			for key in config['CONFIG']:
				find_str = key + ':"'
				start = main_js.find(find_str)
				length = main_js[start:].find('",')
				config['CONFIG'][key] = main_js[(start+len(find_str)):(start+length)]

			for essential_config_item_key, essential_config_item in config['CONFIG'].items():
				if essential_config_item is None or essential_config_item is '':
					xbmc_helper.notification(
						xbmc_helper.translation('ERROR').format('Config'),
						xbmc_helper.translation('MSG_CONFIG_VALUES_INCOMPLETE').format(essential_config_item_key)
					)
					xbmc_helper.log_error('Could not extract configuration value from js: KEY: ' + essential_config_item_key + ' JS source: ' + str(main_js_src))
					exit(0)

			config['GRAPHQL_HEADERS'] = [
				('x-api-key', config['CONFIG']['API_GW_API_KEY']),
				('joyn-platform', xbmc_helper.get_text_setting('joyn_platform'))
			]

			config['PLAYER_CONFIG'] = request_helper.get_json_response(url=config['CONFIG']['PLAYERCONFIG_URL'], config=config)
			if config['PLAYER_CONFIG'] is None:
				xbmc_helper.notification(
						xbmc_helper.translation('ERROR').format('Player Config'),
						xbmc_helper.translation('MSG_CONFIG_VALUES_INCOMPLETE').format('Player Config')
					)
				xbmc_helper.log_error('Could not load player config from url  ' +  config['CONFIG']['SevenTV_player_config_url'])
				exit(0)


			config['PSF_CONFIG'] =  request_helper.get_json_response(url=CONST['PSF_CONFIG_URL'], config=config)
			if config['PSF_CONFIG'] is None:
				xbmc_helper.notification(
						xbmc_helper.translation('ERROR').format('PSF Config'),
						xbmc_helper.translation('MSG_CONFIG_VALUES_INCOMPLETE').format('PSF Config')
					)
				xbmc_helper.log_error('Could not load psf config from url  ' + CONST['PSF_CONFIG_URL'])
				exit(0)

			psf_vars = request_helper.get_url(CONST['PSF_URL'], config)
			find_str = 'call(this,['
			start = psf_vars.find(find_str + '"exports')
			length = psf_vars[start:].rfind('])')
			psf_vars = psf_vars[(start+len(find_str)):(start+length)].split(',')
			for i in range(len(psf_vars)):
				psf_vars[i] = psf_vars[i][1:-1]
			config['PSF_VARS'] = psf_vars

			if cached_config is not None and cached_config.get('SECRET_INDEX', None) is not None and len(config['PSF_VARS']) >= cached_config['SECRET_INDEX']:
				xbmc_helper.log_debug("Trying to reuse psf secret index from cached config: " + str(cached_config['SECRET_INDEX']))
				decrypted_psf_client_config = lib_joyn.decrypt_psf_client_config(config['PSF_VARS'][cached_config['SECRET_INDEX']],
					config['PLAYER_CONFIG']['toolkit']['psf'])
				if decrypted_psf_client_config is not None:
					config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
					config['SECRET'] = config['PSF_VARS'][cached_config['SECRET_INDEX']]
					config['SECRET_INDEX'] = cached_config['SECRET_INDEX']
					xbmc_helper.log_debug('Reusing psf secret index from cached config succeeded')
				else:
					xbmc_helper.log_debug('Reusing psf secret index from cached config failed')

			if config.get('PSF_CLIENT_CONFIG', None) is None and len(config['PSF_VARS']) >= CONST['PSF_VAR_DEFS']['SECRET']['INDEX']:
				decrypted_psf_client_config = lib_joyn.decrypt_psf_client_config(config['PSF_VARS'][CONST['PSF_VAR_DEFS']['SECRET']['INDEX']],
					config['PLAYER_CONFIG']['toolkit']['psf'])
				if decrypted_psf_client_config is not None:
					config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
					config['SECRET'] = config['PSF_VARS'][CONST['PSF_VAR_DEFS']['SECRET']['INDEX']]
				else:
					xbmc_helper.log_debug('Could not decrypt psf client config with psf var index from CONST')

			if config.get('PSF_CLIENT_CONFIG', None) is None:

				index_before = index_after = index_secret = None

				for index,value in enumerate(config['PSF_VARS']):
					if value == CONST['PSF_VAR_DEFS']['SECRET']['VAL_BEFORE']:
						index_before = index
					if value == CONST['PSF_VAR_DEFS']['SECRET']['VAL_AFTER']:
						index_after = index
					if index_before is not None and index_after is not None and index_after == (index_before + 2):
						index_secret = index_before + 1
						decrypted_psf_client_config = lib_joyn.decrypt_psf_client_config(config['PSF_VARS'][index_secret],
							config['PLAYER_CONFIG']['toolkit']['psf'])
						if decrypted_psf_client_config is not None:
							config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
							config['SECRET'] = config['PSF_VARS'][index_secret]
							config['SECRET_INDEX'] = index_secret
							xbmc_helper.log_debug('PSF client config decryption succeded with new index: ' + str(index_secret))
							break

			if config.get('PSF_CLIENT_CONFIG', None) is None:

				xbmc_helper.log_debug('Could not find a new valid secret from psf vars ... using fallback value')
				decrypted_psf_client_config = lib_joyn.decrypt_psf_client_config(CONST['PSF_VAR_DEFS']['SECRET']['FALLBACK'],
					config['PLAYER_CONFIG']['toolkit']['psf'])
				if decrypted_psf_client_config is not None:
					xbmc_helper.log_debug('PSF client config decryption succeded with fallback value')
					config['SECRET'] = CONST['PSF_VAR_DEFS']['SECRET']['FALLBACK']
					config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
				else:
					xbmc_helper.log_debug('PSF client config decryption failed with fallback value ... giving up.')
					xbmc_helper.notification(
						xbmc_helper.translation('ERROR').format('Decrypt'),
						xbmc_helper.translation('MSG_ERROR_CONFIG_DECRYPTION'),
					)

					xbmc_helper.log_error('Could not decrypt config - PSF VARS: '  \
						+ dumps(config['PSF_VARS']) + 'PLAYER CONFIG: ' + dumps(config['PLAYER_CONFIG']))
					exit(0)

			cache.set_json('CONFIG', config)

		return config

	@staticmethod
	def get_client_data(asset_id, stream_type, asset_data={}):

		client_data = {
			'genre': [],
			'startTime': 0,
			'videoId': None,
		}

		if stream_type == 'VOD':
			client_data.update({'videoId': asset_id})
		elif stream_type == 'LIVE':
			client_data.update({'channelId': asset_id})

		if 'video' in asset_data.keys() and 'duration' in asset_data['video'].keys():
			client_data.update({'duration': (asset_data['video']['duration'] * 1000)})

		if 'genres' in asset_data.keys():
			for genre in asset_data['genres']:
				if 'name' in genre.keys():
					client_data['genre'].append(genre['name'])

		if 'series' in asset_data.keys() and 'id' in asset_data['series'].keys():
			client_data.update({'tvShowId': asset_data['series']['id']})

		if 'compilation' in asset_data.keys() and 'id' in asset_data['compilation'].keys():
			client_data.update({'tvShowId': asset_data['compilation']['id']})

		if 'tracking' in asset_data.keys():
			if 'agofCode' in asset_data['tracking'].keys():
				client_data.update({'agofCode': asset_data['tracking']['agofCode']})
			if 'brand' in asset_data['tracking'].keys():
				client_data.update({'brand': asset_data['tracking']['brand']})

		return client_data


	@staticmethod
	def decrypt_psf_client_config(secret, encrypted_psf_config):

		try:
			decrypted_psf_config = loads(
							compat._decode(
								b64decode(
									lib_joyn.decrypt(
										lib_joyn.uc_string_to_long_array(secret),
										lib_joyn.uc_string_to_long_array(
											lib_joyn.uc_slices_to_string(
												lib_joyn.uc_slice(encrypted_psf_config)
											)
										)
									)
								)
							)
						)
		except Exception as e:
			xbmc_helper.log_debug('Could not decrypt psf config - Exception: ' + str(e))
			pass
			return None

		return decrypted_psf_config


	@staticmethod
	def decrypt(key, value):
		n = len(value) - 1
		z = value[n - 1]
		y = value[0]

		mx = e = p = None
		q = int(floor(6 + 52 / (n + 1)))
		sum = q * 2654435769 & 4294967295

		while sum != 0:
			e = sum >> 2 & 3
			p = n
			while p > 0:
				z = value[p - 1]
				mx = (z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (key[p & 3 ^ e] ^ z)
				y = value[p] = value[p] - mx & 4294967295
				p = p-1

			z = value[n]
			mx = (z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (key[p & 3 ^ e] ^ z)
			y = value[0] = value[0] - mx & 4294967295
			sum = sum - 2654435769 & 4294967295

		length = len(value)
		n = length - 1 << 2
		m = value[length -1]
		if m < n - 3 or m > n:
			return None

		n = m
		ret = compat._encode('')
		for i in range(length):
			ret+= compat._unichr(value[i] & 255)
			ret+= compat._unichr(value[i] >> 8 & 255)
			ret+= compat._unichr(value[i] >> 16 & 255)
			ret+= compat._unichr(value[i] >> 24 & 255)

		return ret[0:n]


	@staticmethod
	def uc_slice(hex_string, start_pos=None, end_pos=None):
		unit8s = []
		res = []

		for hex_val in findall('..',hex_string):
			unit8s.append(int(hex_val,16) & 0xff)

		start = 0 if start_pos is None else start_pos
		end = len(unit8s) if end_pos is None else end_pos

		bytes_per_sequence = 0
		i = 0

		while i < end:
			first_byte = unit8s[i]
			code_point = None

			if first_byte > 239:
				bytes_per_sequence  = 4
			elif first_byte > 223:
				bytes_per_sequence = 3
			elif first_byte > 191:
				bytes_per_sequence = 2
			else:
				bytes_per_sequence = 1

			if (i + bytes_per_sequence) <= end:
				second_byte = None
				third_byte = None
				fourth_byte = None
				temp_code_point = None

				if bytes_per_sequence == 1 and first_byte < 128:
					code_point = first_byte
				elif bytes_per_sequence == 2:
					second_byte = unit8s[i + 1]
					if (second_byte & 192) == 128:
						temp_code_point = (first_byte & 31) << 6 | second_byte & 63
						if temp_code_point > 127:
							code_point = temp_code_point
				elif bytes_per_sequence == 3:
					second_byte = unit8s[i + 1]
					third_byte = unit8s[i + 2]
					if (second_byte & 192) == 128 and (third_byte & 192) == 128:
						temp_code_point = (first_byte & 15) << 12 | (second_byte & 63) << 6 | third_byte & 63
						if temp_code_point > 2047 and (temp_code_point < 55296 or temp_code_point > 57343):
							code_point = temp_code_point
				elif bytes_per_sequence == 4:
					second_byte = unit8s[i + 1]
					third_byte = unit8s[i + 2]
					fourth_byte = unit8s[i + 3]
					if (second_byte & 192) == 128 and (third_byte & 192) == 128 and (fourth_byte & 192) == 128:
						temp_code_point = (first_byte & 15) << 18 | (second_byte & 63) << 12 | (third_byte & 63) << 6 | fourth_byte & 63
					if temp_code_point > 65535 and temp_code_point < 1114112:
						code_point = temp_code_point
			if code_point == None:
				code_point = 65533
				bytes_per_sequence = 1
			elif code_point > 65535:
			    code_point -= 65536
			    res.append(code_point > 10 & 1023 | 55296)
			    code_point = 56320 | code_point & 1023

			res.append(code_point)
			i += bytes_per_sequence

		return res


	@staticmethod
	def uc_slices_to_string(uc_slices):
		uc_string = compat._encode('')

		for codepoint in uc_slices:
			uc_string += compat._unichr(codepoint)

		return uc_string


	@staticmethod
	def uc_string_to_long_array(uc_string, length=None):
		length = len(uc_string) if length is None else length

		if length % 4 > 0:
			result = [None] * ((length >> 2) + 1)
		else:
			result = [None] * (length >> 2)

		i = 0

		while i < length and ((i >> 2) < len(result)):
			result[i >> 2] = ord(uc_string[i:(i+1)])
			result[i >> 2] |= ord(uc_string[(i+1):(i+2)]) << 8
			if len(uc_string[(i+2):(i+3)]) > 0:
				result[i >> 2] |= ord(uc_string[(i+2):(i+3)]) << 16
			if len(uc_string[(i+3):(i+4)]) > 0:
				result[i >> 2] |= ord(uc_string[(i+3):(i+4)]) << 24
			i+=4

		return result
