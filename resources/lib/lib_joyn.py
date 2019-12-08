# -*- coding: utf-8 -*-
from base64 import b64decode
from re import findall
from hashlib import sha1, sha256
from sys import exit
from datetime import datetime
from time import time
from copy import copy, deepcopy
from codecs import encode
from io import open as io_open
from xbmc import getCondVisibility, sleep as xbmc_sleep
from .const import CONST
from . import compat as compat
from . import request_helper as request_helper
from . import cache as cache
from . import xbmc_helper as xbmc_helper
from .mpd_parser import mpd_parser as mpd_parser

if compat.PY2:
	from urllib import urlencode
	from urlparse import urlparse, urlunparse, parse_qs
	from HTMLParser import HTMLParser
	try:
		from simplejson import loads, dumps
	except ImportError:
		from json import loads, dumps
elif compat.PY3:
	from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
	from html.parser import HTMLParser
	from json import loads, dumps


class lib_joyn(object):
	def __init__(self, default_icon):

		self.config = lib_joyn.get_config(default_icon)
		self.default_icon = default_icon
		self.auth_token_data = None
		self.account_info = None
		self.landingpage = None
		self.user_agent_http_header = None

	def build_signature(self, video_id, encoded_client_data, entitlement_token):

		sha_input = compat._format('{},{},{}{}', video_id, entitlement_token, encoded_client_data,
		                           compat._decode(encode(self.config['SECRET'].encode('utf-8'), 'hex')))
		xbmc_helper.log_debug(compat._format('Build signature: {}', sha_input))

		return sha1(sha_input.encode('utf-8')).hexdigest()

	def set_mpd_props(self, list_item, url, stream_type='VOD'):

		xbmc_helper.log_debug(compat._format('set_mpd_props {} stream_type {}', url, stream_type))
		mpdparser = None

		# strip out the filter parameter
		parts = urlparse(url)
		query_dict = parse_qs(parts.query)

		if 'filter' in query_dict.keys():
			query_dict.update({'filter': ''})
			new_parts = list(parts)
			new_parts[4] = urlencode(query_dict)
			new_mpd_url = urlunparse(new_parts)
			xbmc_helper.log_debug(compat._format('Stripped out filter from mpd url is {}', new_mpd_url))
			try:
				mpdparser = mpd_parser(new_mpd_url, self.config)
			except Exception as e:
				xbmc_helper.log_debug(compat._format('Invalid MPD - Exception: {}', e))
				pass

		if mpdparser is None or mpdparser.mpd_tree is None:
			try:
				mpdparser = mpd_parser(url, self.config)
			except Exception as e:
				xbmc_helper.log_error(compat._format('Invalid Orginal MPD - Exception: {}', e))

		if mpdparser is not None and mpdparser.mpd_tree is not None:

			list_item.setProperty('inputstreamaddon', CONST['INPUTSTREAM_ADDON'])
			list_item.setProperty(compat._format('{}.manifest_type', CONST['INPUTSTREAM_ADDON']), 'mpd')

			if stream_type == 'LIVE':
				list_item.setProperty(compat._format('{}.manifest_update_parameter', CONST['INPUTSTREAM_ADDON']), 'full')

			toplevel_base_url = None

			# the mpd has a Base URL at toplevel at a remote location
			# inputstream adaptive currently can't handle this correctly
			# it's known that this Base URL can be used to retrieve a 'better' mpd
			toplevel_base_url_res = mpdparser.get_toplevel_base_url()
			if toplevel_base_url_res is not None and toplevel_base_url_res.startswith('http'):
				xbmc_helper.log_debug(compat._format('Found MPD with Base URL at toplevel: {}', toplevel_base_url_res))
				toplevel_base_url = toplevel_base_url_res

			if toplevel_base_url is not None:
				if stream_type == 'VOD':
					new_mpd_url = compat._format('{}.mpd?filter=', toplevel_base_url)
					try:
						test_mpdparser = mpd_parser(new_mpd_url, self.config)
						if test_mpdparser.mpd_tree is not None:
							mpdparser = test_mpdparser
							toplevel_base_url = None
							toplevel_base_url_res = mpdparser.get_toplevel_base_url()
							if toplevel_base_url_res is not None and toplevel_base_url_res.startswith('http'):
								xbmc_helper.log_debug(
								        compat._format('Found MPD with Base URL at toplevel in REPLACED url {} new url {}', toplevel_base_url_res,
								                       new_mpd_url))
								toplevel_base_url = toplevel_base_url_res
							else:
								toplevel_base_url = None
					except Exception as e:
						xbmc_helper.log_debug(compat._format('Invalid MPD - Exception {}', e))
						pass

				elif stream_type == 'LIVE':
					period_base_url_res = mpdparser.query_node_value(['Period', 'BaseURL'])
					if period_base_url_res is not None and period_base_url_res.startswith('/') and period_base_url_res.endswith('/'):
						new_mpd_url = compat._format('{}{}cenc-default.mpd', toplevel_base_url, period_base_url_res)

						try:
							test_mpdparser = mpd_parser(new_mpd_url, self.config)
							if test_mpdparser.mpd_tree is not None:
								mpdparser = test_mpdparser
								toplevel_base_url = None
								toplevel_base_url_res = mpdparser.get_toplevel_base_url()
								if toplevel_base_url_res is not None and toplevel_base_url_res.startswith('http'):
									xbmc_helper.log_debug(
									        compat._format('Found MPD with Base URL at toplevel in REPLACED url {} new url {}', toplevel_base_url_res,
									                       new_mpd_url))
									toplevel_base_url = toplevel_base_url_res
								else:
									toplevel_base_url = None
						except Exception as e:
							xbmc_helper.log_debug(compat._format('Invalid MPD - Exception: {}', e))
							pass

			if toplevel_base_url is not None:
				xbmc_helper.log_debug('Writing MPD file to local disc, since it has a remote top Level Base URL ...')
				sha_1 = sha1()
				sha_1.update(mpdparser.mpd_url)

				mpd_filepath = xbmc_helper.get_file_path(CONST['TEMP_DIR'], compat._format('{}.mpd', sha_1.hexdigest()))
				with io_open(file=mpd_filepath, mode='w', encoding='utf-8') as mpd_filepath_out:
					mpd_filepath_out.write(compat._unicode(mpdparser.mpd_contents))

				xbmc_helper.log_notice(compat._format('Local MPD filepath is: {}', mpd_filepath))
				list_item.setPath(mpd_filepath)

			else:
				list_item.setPath(self.add_user_agent_http_header(mpdparser.mpd_url))

			return True

		return False

	def get_entitlement_data(self, video_id, stream_type, pin_required=False, invalid_pin=False):

		entitlement_request_data = {
		        'access_id': self.config['PSF_CLIENT_CONFIG']['accessId'],
		        'content_id': video_id,
		        'content_type': stream_type,
		}

		if pin_required is True:
			if invalid_pin is True:
				xbmc_helper.notification(xbmc_helper.translation('MPAA_PIN'), xbmc_helper.translation('MSG_INVALID_MPAA_PIN'))
			mpaa_pin_settings = xbmc_helper.get_text_setting('mpaa_pin')
			if len(mpaa_pin_settings) == 4 and invalid_pin is False:
				entitlement_request_data.update({'pin': mpaa_pin_settings})
			else:
				from xbmcgui import Dialog, INPUT_NUMERIC
				_fsk_pin = Dialog().input(xbmc_helper.translation('MPAA_PIN'), type=INPUT_NUMERIC)
				if len(_fsk_pin) == 4:
					entitlement_request_data.update({'pin': _fsk_pin})
				elif len(_fsk_pin) == 0:
					return {}
				else:
					return self.get_entitlement_data(video_id=video_id, stream_type=stream_type, pin_required=pin_required, invalid_pin=True)

		entitlement_request_headers = [('x-api-key', self.config['PSF_CONFIG']['default'][stream_type.lower()]['apiGatewayKey'])]
		auth_token_data = self.get_auth_token()

		if auth_token_data.get('has_account', False) is not False and auth_token_data.get('access_token', None) is not None:
			entitlement_request_headers.append(('Authorization', compat._format('Bearer {}', auth_token_data.get('access_token'))))
			entitlement_response = request_helper.post_json(url=compat._format(
			        '{}{}', self.config['PSF_CONFIG']['default'][stream_type.lower()]['entitlementBaseUrl'], CONST['ENTITLEMENT_URL']),
			                                                config=self.config,
			                                                data=entitlement_request_data,
			                                                additional_headers=entitlement_request_headers,
			                                                no_cache=True,
			                                                return_json_errors=['ENT_PINRequired', 'ENT_PINInvalid'])

			if isinstance(entitlement_response, dict) and 'json_errors' in entitlement_response:
				if 'ENT_PINInvalid' in entitlement_response['json_errors']:
					return self.get_entitlement_data(video_id=video_id, stream_type=stream_type, pin_required=True, invalid_pin=True)
				elif 'ENT_PINRequired' in entitlement_response['json_errors']:
					return self.get_entitlement_data(video_id=video_id, stream_type=stream_type, pin_required=True)

			return entitlement_response
		else:
			return request_helper.post_json(url=compat._format(
			        '{}{}', self.config['PSF_CONFIG']['default'][stream_type.lower()]['entitlementBaseUrl'],
			        CONST['ANON_ENTITLEMENT_URL']),
			                                config=self.config,
			                                data=entitlement_request_data,
			                                additional_headers=entitlement_request_headers,
			                                no_cache=True)

	def get_video_data(self, video_id, client_data, stream_type, season_id=None, compilation_id=None):

		video_url = compat._format('{}playout/{}/{}', self.config['PSF_CONFIG']['default'][stream_type.lower()]['playoutBaseUrl'],
		                           'channel' if stream_type == 'LIVE' else 'video', video_id)
		xbmc_helper.log_debug(compat._format('get_video_data: video url: {} - client data {}', video_url, client_data))

		video_data = {}
		entitlement_data = self.get_entitlement_data(video_id, stream_type)
		encoded_client_data = request_helper.base64_encode_urlsafe(dumps(client_data))

		if entitlement_data.get('entitlement_token', None) is not None:

			video_url_params = {
			        'entitlement_token': entitlement_data['entitlement_token'],
			        'clientData': encoded_client_data,
			        'sig': self.build_signature(video_id, encoded_client_data, entitlement_data['entitlement_token']),
			}

			video_data = request_helper.get_json_response(url=video_url,
			                                              config=self.config,
			                                              params=video_url_params,
			                                              headers=[('Content-Type', 'application/x-www-form-urlencoded charset=utf-8')],
			                                              post_data='false',
			                                              no_cache=True)

			if xbmc_helper.get_bool_setting('force_playready') and self.config['IS_ANDROID'] is True and 'drm' in video_data.keys(
			) and 'licenseUrl' in video_data.keys():

				if stream_type == 'VOD' and video_data['licenseUrl'].find('/widevine/v1') is not -1:
					video_data.update({'licenseUrl': video_data['licenseUrl'].replace('/widevine/v1', '/playready/v1')})
					video_data.update({'drm': 'playready'})
				elif stream_type == 'LIVE':
					video_data.update({'drm': 'playready'})

			if season_id is not None:
				video_data.update({'season_id': season_id})
			if compilation_id is not None:
				video_data.update({'compilation_id': compilation_id})

		return video_data

	def get_epg(self):

		cached_epg = cache.get_json('EPG')
		dt_now = datetime.now()
		if cached_epg['data'] is not None and cached_epg['is_expired'] is False and 'epg_expires' in cached_epg['data'].keys(
		) and datetime.fromtimestamp(cached_epg['data']['epg_expires']) > dt_now:

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
				if brand_epg.get('livestream', None) is not None and 'epg' in brand_epg['livestream'].keys() and len(
				        brand_epg['livestream']['epg']) > 0:

					brand_live_stream_epg_count = len(brand_epg['livestream']['epg'])
					if brand_live_stream_epg_count > 0:
						penultimate_brand_live_stream_epg_timestamp = brand_epg['livestream']['epg'][(brand_live_stream_epg_count -
						                                                                              2)]['startDate']
						if epg['epg_expires'] is None or epg['epg_expires'] > penultimate_brand_live_stream_epg_timestamp:
							epg.update({'epg_expires': penultimate_brand_live_stream_epg_timestamp})
			cache.set_json('EPG', epg)

		return epg_data

	def get_landingpage(self):

		if self.landingpage is None:
			self.landingpage = {}
			raw_landingpage = self.get_graphql_response('LANDINGPAGE', {'path': '/'})
			if 'page' in raw_landingpage.keys() and 'blocks' in raw_landingpage['page'].keys():
				for block in raw_landingpage['page']['blocks']:
					if self.get_auth_token().get('has_account', False) is True or block.get('isPersonalized', False) is False:
						if block['__typename'] not in self.landingpage.keys():
							self.landingpage.update({block['__typename']: {}})

						self.landingpage[block['__typename']].update({block['id']: block.get('headline', None)})

		return self.landingpage

	def get_account_info(self, force_refresh=False):

		cached_account_info = cache.get_json('ACCOUNT_INFO')
		if force_refresh is False and cached_account_info['data'] is not None and cached_account_info['is_expired'] is False:
			if self.account_info is None:
				self.account_info = cached_account_info['data']
			return self.account_info
		else:
			account_info = self.get_graphql_response('ACCOUNT')
			_account_info = deepcopy(account_info)
			# unset any personal data before saving
			if _account_info.get('me', None) is not None and _account_info.get('me').get('profile', None) is not None:
				del _account_info['me']['profile']
			cache.set_json('ACCOUNT_INFO', _account_info)
			self.account_info = _account_info

			return account_info

	def get_account_state(self):
		if self.get_auth_token().get('has_account', False) is not False:
			return self.get_account_info().get('me', {}).get('state', 'R_A')
		return False

	def get_account_subscription_config(self, subscription_type):
		if self.get_auth_token().get('has_account', False) is not False:
			return self.get_account_info().get('me', {}).get('subscriptionConfig', {}).get(subscription_type, False)
		return False

	def get_uepg_data(self, pluginurl):

		epg = self.get_epg()
		uEPG_data = []
		channel_num = 0

		for brand_epg in epg['brands']:
			if brand_epg['livestream'] is not None and 'epg' in brand_epg['livestream'].keys() and len(
			        brand_epg['livestream']['epg']) > 0:

				if 'logo' in brand_epg.keys() and 'url' in brand_epg['logo'].keys():
					channel_logo = self.add_user_agent_http_header(
					        compat._format('{}/profile:nextgen-web-artlogo-183x75', brand_epg['logo']['url']))
				else:
					channel_logo = self.default_icon

				channel_name = brand_epg['livestream']['title']

				if brand_epg['livestream']['quality'] == 'HD' and channel_name[-2:] != 'HD':
					channel_name = compat._format('{} HD', channel_name)

				channel_num += 1
				client_data = dumps({'videoId': None, 'channelId': brand_epg['livestream']['id']})

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
						epg_metadata['art'].update({art_item_type: self.add_user_agent_http_header(art_item)})

					epg_metadata['art'].update({'clearlogo': channel_logo, 'icon': channel_logo})

					guidedata.append({
					        'label':
					        epg_metadata['infoLabels']['title'],
					        'title':
					        epg_metadata['infoLabels']['title'],
					        'plot':
					        epg_metadata['infoLabels'].get('plot', None),
					        'art':
					        epg_metadata['art'],
					        'starttime':
					        epg_entry['startDate'],
					        'duration': (epg_entry['endDate'] - epg_entry['startDate']),
					        'url':
					        compat._format(
					                '{}?{}', pluginurl,
					                urlencode({
					                        'mode': 'play_video',
					                        'stream_type': 'LIVE',
					                        'video_id': brand_epg['livestream']['id'],
					                        'client_data': client_data
					                }))
					})
				uEPG_channel.update({'guidedata': guidedata})
				uEPG_data.append(uEPG_channel)

		return uEPG_data

	def get_graphql_response(self, operation, variables={}, retry_count=0, force_refresh_auth=False):

		xbmc_helper.log_debug(compat._format('get_graphql_response: Operation: {}', operation))
		for required_var in CONST['GRAPHQL'][operation]['REQUIRED_VARIABLES']:
			if required_var not in variables.keys():
				if required_var in CONST['GRAPHQL']['STATIC_VARIABLES'].keys():
					variables.update({required_var: CONST['GRAPHQL']['STATIC_VARIABLES'][required_var]})
				else:
					xbmc_helper.log_error(
					        compat._format('Not all required variables set for operation {} required var {} set vars{}', operation,
					                       required_var, variables))
					exit(0)

		if force_refresh_auth is True:
			self.get_auth_token(force_refresh=True)

		if CONST['GRAPHQL'][operation].get('BOOKMARKS', False) is True  and self.get_auth_token().get('has_account', False) is False:
			query = CONST['GRAPHQL'][operation]['QUERY'].replace('isBookmarked ', '')
		else:
			query = CONST['GRAPHQL'][operation]['QUERY']

		params = {
		        'query':
		        compat._format('{} {} {}', 'query' if CONST['GRAPHQL'][operation].get('IS_MUTATION', False) is False else 'mutation',
		                       CONST['GRAPHQL'][operation]['OPERATION'], query),
		        'extensions': {
		                'persistedQuery': {
		                        'version': 1,
		                },
		        },
		        'operationName':
		        CONST['GRAPHQL'][operation]['OPERATION'],
		}

		if len(variables.keys()) != 0:
			if CONST['GRAPHQL'][operation].get('IS_MUTATION', False) is False:
				params.update({'variables': dumps(variables)})
			else:
				params.update({'variables': variables})

		params['extensions']['persistedQuery'].update({'sha256Hash': sha256(params['query'].encode('utf-8')).hexdigest()})

		if CONST['GRAPHQL'][operation].get('IS_MUTATION', False) is False:
			params.update({'extensions': dumps(params['extensions'])})

		headers = copy(self.config['GRAPHQL_HEADERS'])

		account_state = False
		if operation != 'ACCOUNT' and self.get_auth_token().get('has_account', False) is not False:
			account_state = self.get_account_state()
			if account_state is not False:
				headers.append(('Joyn-User-State', account_state))
			if self.get_account_subscription_config('hasActivePlus') is True:
				params.update({'enable_plus': 'true'})
			else:
				params.update({'enable_plus': 'false'})

		if CONST['GRAPHQL'][operation].get('AUTH', False) is True:
			auth_token_data = self.get_auth_token()
			if auth_token_data.get('access_token', None) is not None:
				headers.append(('Authorization', compat._format('Bearer {}', auth_token_data.get('access_token'))))
			else:
				xbmc_helper.log_error("Failed to get auth_token; continue unauthorized")

			if operation != 'ACCOUNT' and account_state is False:
				joyn_user_id = self.get_client_ids().get('anon_device_id', None)
				if joyn_user_id is not None:
					headers.append(('Joyn-User-Id', joyn_user_id))
				else:
					xbmc_helper.log_notice("Failed to get joyn_user_id; continue without")

		api_response = {}

		try:
			if CONST['GRAPHQL'][operation].get('IS_MUTATION', False) is False:

				api_response = request_helper.get_json_response(url=CONST['GRAPHQL']['API_URL'],
				                                                config=self.config,
				                                                params=params,
				                                                headers=headers,
				                                                no_cache=CONST['GRAPHQL'][operation].get('NO_CACHE', False),
				                                                return_json_errors=['INVALID_JWT'])
			else:
				api_response = request_helper.post_json(url=CONST['GRAPHQL']['API_URL'],
				                                        config=self.config,
				                                        data=params,
				                                        additional_headers=headers,
				                                        no_cache=CONST['GRAPHQL'][operation].get('NO_CACHE', False),
				                                        return_json_errors=['INVALID_JWT'])

			if isinstance(api_response, dict) and 'json_errors' in api_response.keys():
				if 'INVALID_JWT' in api_response['json_errors']:
					self.get_graphql_response(operation=operation, variables=variables, retry_count=retry_count, force_refresh_auth=True)

		except Exception as e:
			xbmc_helper.log_error(compat._format('Could not complete graphql request: {} params {}', e, params))

		if 'errors' in api_response.keys():
			xbmc_helper.log_error(compat._format('GraphQL query returned errors: {} params {}', api_response['errors'], params))

		if 'data' in api_response.keys() and api_response['data'] is not None:
			return api_response['data']
		else:
			xbmc_helper.log_error(compat._format('GraphQL query returned no data - response: {} params {}', api_response, params))

			if retry_count < 3:
				xbmc_helper.log_error(compat._format('Retrying to complete graphql request ... retry count: {}', retry_count))
				xbmc_sleep(500)
				return self.get_graphql_response(operation=operation, variables=variables, retry_count=(retry_count + 1))
			else:
				xbmc_helper.notification(
				        compat._format(xbmc_helper.translation('ERROR'), 'GraphQL'),
				        xbmc_helper.translation('MSG_GAPHQL_ERROR'),
				)
				exit(0)

	def get_client_ids(self, username=None, password=None):

		client_id_data = xbmc_helper.get_json_data('client_ids')
		if client_id_data is None or client_id_data.get('client_name', 'android') not in CONST['CLIENT_NAMES']:
			from uuid import uuid4
			xbmc_helper.log_debug("Creating new client_data")
			client_id_data = {
			        'anon_device_id': str(uuid4()),
			        'client_id': str(uuid4()),
			        'client_name': self.config.get('CLIENT_NAME', 'android'),
			}
			xbmc_helper.set_json_data('client_ids', client_id_data)

		if username is not None and password is not None:
			del client_id_data['anon_device_id']
			client_id_data.update({
			        'email': username,
			        'password': password,
			})

		return client_id_data

	def get_auth_token(self, username=None, password=None, reset_anon=False, is_retry=False, logout=False, force_refresh=False):

		if username is not None and password is not None:
			try:
				auth_token_data = request_helper.post_json(url=CONST['AUTH_URL'] + CONST['AUTH_LOGIN'],
				                                           config=self.config,
				                                           data=self.get_client_ids(username, password),
				                                           no_cache=True,
				                                           return_json_errors='UNAUTHORIZED')

				if isinstance(auth_token_data, dict) and 'json_errors' in auth_token_data.keys():
					if 'UNAUTHORIZED' in auth_token_data['json_errors']:
						xbmc_helper.log_debug(compat._format('Failed to log in'))
						return False

				xbmc_helper.log_debug('Successfully logged in an retrieved auth token')
				auth_token_data.update({
				        'created': int(time()),
				        'has_account': True,
				})

				xbmc_helper.set_json_data('auth_tokens', auth_token_data)
				self.auth_token_data = auth_token_data
				cache.remove_json('EPG')

			except Exception as e:
				xbmc_helper.log_debug(compat._format('Failed to log in - exception: {}', e))
				pass
				return False

		elif reset_anon is False:
			if self.auth_token_data is None:
				self.auth_token_data = xbmc_helper.get_json_data('auth_tokens')

		if reset_anon is True or self.auth_token_data is None:
			xbmc_helper.log_debug("Creating new auth_token_data")

			auth_token_data = request_helper.post_json(url=CONST['AUTH_URL'] + CONST['AUTH_ANON'],
			                                           config=self.config,
			                                           data=self.get_client_ids(),
			                                           no_cache=True)

			auth_token_data.update({'created': int(time())})
			xbmc_helper.set_json_data('auth_tokens', auth_token_data)
			self.auth_token_data = auth_token_data
			if reset_anon is True:
				cache.remove_json('ACCOUNT_INFO')
				cache.remove_json('EPG')

		# refresh the token at least 30min before it actual expires
		if force_refresh is True or time() >= self.auth_token_data['created'] + ((self.auth_token_data['expires_in'] / 1000) - 1800):
			xbmc_helper.log_debug("Refreshing auth_token_data")
			client_id_data = self.get_client_ids()

			refresh_auth_token_req_data = {
			        'refresh_token': self.auth_token_data['refresh_token'],
			        'client_id': client_id_data['client_id'],
			        'client_name': client_id_data['client_name'],
			}

			try:
				refresh_auth_token_data = request_helper.post_json(url=CONST['AUTH_URL'] + CONST['AUTH_REFRESH'],
				                                                   config=self.config,
				                                                   data=refresh_auth_token_req_data,
				                                                   no_cache=True,
				                                                   return_json_errors=['VALIDATION_ERROR'])

				if isinstance(refresh_auth_token_data, dict) and 'json_errors' in refresh_auth_token_data.keys():
					if 'VALIDATION_ERROR' in refresh_auth_token_data['json_errors']:
						# ask to re-login
						if self.auth_token_data.get('has_account', False) is True:
							pass
							xbmc_helper.log_debug("ssk to re-login")
							from xbmcaddon import Addon
							from xbmc import executebuiltin
							executebuiltin(
							        compat._format('RunPlugin(plugin://{}{})',
							                       Addon().getAddonInfo('id'), '?mode=login&dont_check_account=true'))
							xbmc_helper.notification(compat._format(xbmc_helper.translation('ERROR'), xbmc_helper.translation('ACCOUNT')),
							                         xbmc_helper.translation('MSG_RERESH_AUTH_FAILED_RELOG'))
							exit(0)
						else:
							if is_retry is False:
								pass
								return self.get_auth_token(reset_anon=True, is_retry=True)
							else:
								pass
								return xbmc_helper.notification(compat._format(xbmc_helper.translation('ERROR'), xbmc_helper.translation('ACCOUNT')),
								                                xbmc_helper.translation('MSG_RERESH_AUTH_FAILED'))

				self.auth_token_data.update({
				        'created': int(time()),
				        'access_token': refresh_auth_token_data.get('access_token'),
				        'refresh_token': refresh_auth_token_data.get('refresh_token')
				})

			except Exception as e:
				xbmc_helper.log_debug(compat._format('Could not refresh auth token! - {}', e))

			# refresh account_info too
			if self.auth_token_data.get('has_account', False) is not False:
				self.account_info = self.get_account_info(True)

			xbmc_helper.set_json_data('auth_tokens', self.auth_token_data)

		if logout is True and self.auth_token_data.get('has_account', False) is True and self.auth_token_data.get(
		        'access_token', None) is not None:

			request_helper.get_url(url=CONST['AUTH_URL'] + CONST['AUTH_LOGOUT'],
			                       config=self.config,
			                       post_data='',
			                       no_cache=True,
			                       additional_headers=[('Authorization',
			                                            compat._format('Bearer {}', self.auth_token_data.get('access_token')))])

			return self.get_auth_token(reset_anon=True)

		return self.auth_token_data

	def add_user_agent_http_header(self, uri):

		if uri.startswith('http') and uri.find('|User-Agent') == -1:
			if self.user_agent_http_header is None:
				self.user_agent_http_header = request_helper.get_header_string({'User-Agent': self.config.get('USER_AGENT')})
			uri = compat._format('{}|{}', uri, self.user_agent_http_header)

		return uri

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
			metadata['infoLabels'].update(
			        {'title': compat._format(xbmc_helper.translation('TITLE_LABEL'), metadata['infoLabels'].get('title', ''))})

		if data.get('isBookmarked', None) is not None:
			if data.get('isBookmarked', False) is True:
				metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper.translation('JOYN_BOOKMARK_LABEL'), metadata['infoLabels']['title'])})
				metadata['is_bookmarked'] = True
			else:
				metadata['is_bookmarked'] = False

		if 'ART' in CONST['GRAPHQL']['METADATA'][query_type].keys():
			for art_key, art_def in CONST['GRAPHQL']['METADATA'][query_type]['ART'].items():
				if art_key in data.keys():
					if not isinstance(data[art_key], list):
						images = [data[art_key]]
					else:
						images = data[art_key]

					for image in images:
						for art_def_img_type, art_def_img in art_def.items():
							if image.get('__typename', '') == 'Image' and art_def_img_type == image.get('type', ''):
								for art_def_img_map_key, art_def_img_map_profile in art_def_img.items():
									metadata['art'].update({art_def_img_map_key: compat._format('{}/{}', image['url'], art_def_img_map_profile)})

		if 'ageRating' in data.keys() and data['ageRating'] is not None and 'minAge' in data['ageRating'].keys():
			metadata['infoLabels'].update({'mpaa': compat._format(xbmc_helper.translation('MIN_AGE'), str(data['ageRating']['minAge']))})

		if 'genres' in data.keys() and isinstance(data['genres'], list):
			metadata['infoLabels'].update({'genre': []})

			for genre in data['genres']:
				if 'name' in genre.keys():
					metadata['infoLabels']['genre'].append(genre['name'])

		if 'copyrights' in data.keys() and data.get('copyrights', None) is not None:
			metadata['infoLabels'].update({'Studio': data.get('copyrights')})

		if query_type == 'EPISODE':
			if 'endsAt' in data.keys() and data['endsAt'] is not None and data['endsAt'] < 9999999999:
				endsAt = xbmc_helper.timestamp_to_datetime(data['endsAt'], True)
				if endsAt is not False:
					metadata['infoLabels'].update({
					        'plot':
					        compat._format(xbmc_helper.translation('VIDEO_AVAILABLE'), endsAt) + metadata['infoLabels'].get('plot', '')
					})

			if 'number' in data.keys() and data['number'] is not None:
				metadata['infoLabels'].update({
				        'episode': data['number'],
				        'sortepisode': data['number'],
				})
			if 'series' in data.keys():
				if 'title' in data['series'].keys():
					metadata['infoLabels'].update({'tvshowtitle': HTMLParser().unescape(data['series']['title'])})
				series_meta = lib_joyn.get_metadata(data['series'], 'TVSHOW')
				if 'clearlogo' in series_meta['art'].keys():
					metadata['art'].update({'clearlogo': series_meta['art']['clearlogo']})

			elif 'compilation' in data.keys():
				compilation_meta = lib_joyn.get_metadata(data['compilation'], 'TVSHOW')
				if 'title' in data['compilation'].keys():
					metadata['infoLabels'].update({'tvshowtitle': HTMLParser().unescape(data['compilation']['title'])})
				if 'clearlogo' in compilation_meta['art'].keys():
					metadata['art'].update({'clearlogo': compilation_meta['art']['clearlogo']})

		if 'airdate' in data.keys() and data['airdate'] is not None:
			broadcast_datetime = xbmc_helper.timestamp_to_datetime(data['airdate'], True)
			if broadcast_datetime is not False:
				broadcast_date = broadcast_datetime.strftime('%Y-%m-%d')
				metadata['infoLabels'].update({
				        'premiered': broadcast_date,
				        'date': broadcast_date,
				        'aired': broadcast_date,
				})

		if 'video' in data.keys() and data['video'] is not None and 'duration' in data['video'].keys(
		) and data['video']['duration'] is not None:
			metadata['infoLabels'].update({'duration': (data['video']['duration'])})

		if 'season' in data.keys() and data['season'] is not None and 'number' in data['season'].keys(
		) and data['season']['number'] is not None:

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
		if brand_livestream_epg['quality'] == 'HD' and brand_title[-2:] != 'HD':
			brand_title = compat._format('{} HD', brand_title)
		dt_now = datetime.now()
		epg_metadata['infoLabels'].update({'title': compat._format(xbmc_helper.translation('LIVETV_TITLE'), brand_title, '')})

		for idx, epg_entry in enumerate(brand_livestream_epg['epg']):
			end_time = xbmc_helper.timestamp_to_datetime(epg_entry['endDate'])

			if end_time is not False and end_time > dt_now:
				epg_metadata = lib_joyn.get_metadata(epg_entry, 'EPG')
				epg_metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper.translation('LIVETV_TITLE'), brand_title, epg_entry['title'])})
				if len(brand_livestream_epg['epg']) > (idx + 1):
					epg_metadata['infoLabels'].update({
					        'plot':
					        compat._format(xbmc_helper.translation('LIVETV_UNTIL_AND_NEXT'), end_time,
					                       brand_livestream_epg['epg'][idx + 1]['title'])
					})
				else:
					epg_metadata['infoLabels'].update({'plot': compat._format(xbmc_helper.translation('LIVETV_UNTIL'), end_time)})

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

		expire_config_days = xbmc_helper.get_int_setting('configcachedays')
		if expire_config_days is not None:
			confg_cache_res = cache.get_json('CONFIG', (expire_config_days * 86400))
		else:
			confg_cache_res = cache.get_json('CONFIG')

		if confg_cache_res['data'] is not None:
			cached_config = confg_cache_res['data']

		if (confg_cache_res['is_expired'] is False
		    or expire_config_days == 0) and cached_config is not None and 'ADDON_VERSION' in cached_config.keys(
		    ) and cached_config['ADDON_VERSION'] == addon_version:
			recreate_config = False
			config = cached_config

		if cached_config is None or 'ADDON_VERSION' not in cached_config.keys() or ('ADDON_VERSION' in cached_config.keys() and
		                                                                            cached_config['ADDON_VERSION'] != addon_version):
			xbmc_helper.remove_dir(CONST['CACHE_DIR'])
			xbmc_helper.log_debug('cleared cache')

		if recreate_config == True:

			xbmc_helper.log_debug('get_config(): create config')
			use_outdated_cached_config = False

			config = {
			        'CONFIG': {
			                'PLAYERCONFIG_URL': None,
			                'API_GW_API_KEY': None,
			        },
			        'PSF_CONFIG': {},
			        'PLAYER_CONFIG': {},
			        'PSF_VARS': {},
			        'PSF_CLIENT_CONFIG': None,
			        'IS_ANDROID': False,
			        'IS_ARM': False,
			        'ADDON_VERSION': addon_version,
			        'country': None,
			        'http_headers': [],
			}

			# Fails on some systems
			try:
				os_uname = compat._uname_list()
			except Exception:
				os_uname = ['Linux', 'hostname', 'kernel-ver', 'kernel-sub-ver', 'x86_64']

			# android
			if getCondVisibility('System.Platform.Android'):
				from subprocess import check_output
				try:
					os_version = compat._decode(check_output(['/system/bin/getprop', 'ro.build.version.release'])).strip(' \t\n\r')
					model = compat._decode(check_output(['/system/bin/getprop', 'ro.product.model'])).strip(' \t\n\r')
					build_id = compat._decode(check_output(['/system/bin/getprop', 'ro.build.id'])).strip(' \t\n\r')

					config['USER_AGENT'] = compat._format('Mozilla/5.0 (Linux; Android {}; {} Build/{})', os_version, model, build_id)

				except Exception as e:
					xbmc_helper.log_debug(compat._format('getprop failed on android with exception: {}', e))
					config['USER_AGENT'] = 'Mozilla/5.0 (Linux; Android 8.1.0; Nexus 6P Build/OPM6.171019.030.B1)'
					pass
				config['USER_AGENT'] += ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.73 Mobile Safari/537.36'
				config['IS_ANDROID'] = True

			# linux on arm uses widevine from chromeos
			elif os_uname[0] == 'Linux' and os_uname[4].lower().find('arm') is not -1:
				config['USER_AGENT'] = 'Mozilla/5.0 (X11 CrOS ' + os_uname[
				        4] + ' 4537.56.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.38 Safari/537.36'
				config['IS_ARM'] = True
			elif os_uname[0] == 'Linux':
				config['USER_AGENT'] = 'Mozilla/5.0 (X11 Linux ' + os_uname[
				        4] + ') AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
			elif os_uname[0] == 'Darwin':
				config['USER_AGENT'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/600.7.12 (KHTML, like Gecko) Version/8.0.7 Safari/600.7.12'
			else:
				config['USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0 Win64 x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'

			html_content = request_helper.get_url(CONST['BASE_URL'], config)
			if html_content is None or html_content is '':
				xbmc_helper.notification(compat._format(xbmc_helper.translation('ERROR'), 'Url access'),
				                         compat._format(xbmc_helper.translation('MSG_NO_ACCESS_TO_URL'), CONST['BASE_URL']))
				exit(0)

			county_setting = xbmc_helper.get_setting('country')
			xbmc_helper.log_debug(compat._format('COUNTRY SETTING: {}', county_setting))
			try:
				ip_api_response = request_helper.get_json_response(url=compat._format(CONST['IP_API_URL'],
				                                                                      xbmc_helper.translation('LANG_CODE')),
				                                                   config=config, silent=True)

			except Exception as e:
				xbmc_helper.log_debug(compat._format('ip-api request failed - {}', e))
				ip_api_response = {
				        'status': 'success',
				        'country': 'Deutschland',
				        'countryCode': 'DE',
				}
			config.update({'actual_country': ip_api_response.get('countryCode', 'DE')})

			if county_setting is '' or county_setting is '0':
				xbmc_helper.log_debug(compat._format('IP API Response is: {}', ip_api_response))
				if config.get('actual_country', 'DE') in CONST['COUNTRIES'].keys():
					config.update({'country': config.get('actual_country', 'DE')})
				else:
					xbmc_helper.dialog_action(
					        compat._format(xbmc_helper.translation('MSG_COUNTRY_INVALID'), ip_api_response.get('country', 'DE')))
					exit(0)

			else:
				for supported_country_key, supported_country in CONST['COUNTRIES'].items():
					if supported_country['setting_id'] == county_setting:
						config.update({'country': supported_country_key})
						break

			if config['country'] is None:
				xbmc_helper.dialog_action(xbmc_helper.translation('MSG_COUNTRY_NOT_DETECTED'))
				exit(0)

			if config['country'] != config['actual_country']:

				from random import choice
				try:
					from ipaddress import IPv4Network
				except ImportError:
					from external.ipaddress import IPv4Network

				config['http_headers'].append(
				        ('x-forwarded-for',
				         str(choice(list(IPv4Network(compat._unicode(choice(CONST['NETBLOCKS'][config.get('country', 'DE')]))).hosts())))))

			main_js_src = None
			for match in findall('<script type="text/javascript" src="(.*?)"></script>', html_content):
				if match.find('/main') is not -1:
					main_js_src = CONST['BASE_URL'] + match
					main_js = request_helper.get_url(main_js_src, config)
					break

			if main_js_src is None:
				xbmc_helper.log_debug('Using local main.js')
				main_js = xbmc_helper.get_file_contents(xbmc_helper.get_resource_filepath('main.js', 'external'))

			for key in config['CONFIG']:
				find_str = key + ':"'
				start = main_js.find(find_str)
				length = main_js[start:].find('",')
				config['CONFIG'][key] = main_js[(start + len(find_str)):(start + length)]

			for essential_config_item_key, essential_config_item in config['CONFIG'].items():
				if essential_config_item is None or essential_config_item is '':
					use_outdated_cached_config = True
					xbmc_helper.log_error(
					        compat._format('Could not extract configuration value from js: KEY{} JS source {} ', essential_config_item_key,
					                       main_js_src))
					break

			if use_outdated_cached_config is False:
				config['GRAPHQL_HEADERS'] = [('x-api-key', config['CONFIG']['API_GW_API_KEY']),
				                             ('joyn-platform', xbmc_helper.get_text_setting('joyn_platform'))]

				config['CLIENT_NAME'] = xbmc_helper.get_text_setting('joyn_platform')

			if use_outdated_cached_config is False:
				config['PLAYER_CONFIG'] = request_helper.get_json_response(url=config['CONFIG']['PLAYERCONFIG_URL'], config=config)
				if config['PLAYER_CONFIG'] is None:
					use_outdated_cached_config = True
					xbmc_helper.log_error(
					        compat._format('Could not load player config from url {}', config['CONFIG']['SevenTV_player_config_url']))

			if use_outdated_cached_config is False:
				config['PSF_CONFIG'] = request_helper.get_json_response(url=CONST['PSF_CONFIG_URL'], config=config)
				if config['PSF_CONFIG'] is None:
					use_outdated_cached_config = True
					xbmc_helper.log_error(compat._format('Could not load psf config from url  {}', CONST['PSF_CONFIG_URL']))

			if use_outdated_cached_config is False:
				psf_vars = request_helper.get_url(CONST['PSF_URL'], config)
				find_str = 'call(this,['
				start = psf_vars.find(find_str + '"exports')
				length = psf_vars[start:].rfind('])')
				psf_vars = psf_vars[(start + len(find_str)):(start + length)].split(',')
				for i in range(len(psf_vars)):
					psf_vars[i] = psf_vars[i][1:-1]
				config['PSF_VARS'] = psf_vars

				if cached_config is not None and cached_config.get('SECRET_INDEX', None) is not None and len(
				        config['PSF_VARS']) >= cached_config['SECRET_INDEX']:
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
					decrypted_psf_client_config = lib_joyn.decrypt_psf_client_config(
					        config['PSF_VARS'][CONST['PSF_VAR_DEFS']['SECRET']['INDEX']], config['PLAYER_CONFIG']['toolkit']['psf'])
					if decrypted_psf_client_config is not None:
						config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
						config['SECRET'] = config['PSF_VARS'][CONST['PSF_VAR_DEFS']['SECRET']['INDEX']]
					else:
						xbmc_helper.log_debug('Could not decrypt psf client config with psf var index from CONST')

				if config.get('PSF_CLIENT_CONFIG', None) is None:
					index_before = index_after = index_secret = None
					for index, value in enumerate(config['PSF_VARS']):
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
								xbmc_helper.log_debug(compat._format('PSF client config decryption succeded with new index: {}', index_secret))
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
						use_outdated_cached_config = True
						xbmc_helper.log_error(
						        compat._format('Could not decrypt config - PSF VARS: {} PLAYER CONFIG {}', config['PSF_VARS'],
						                       config['PLAYER_CONFIG']))

			if use_outdated_cached_config is True:
				if cached_config is not None and isinstance(cached_config, dict) and 'PSF_CLIENT_CONFIG' in cached_config.keys():
					xbmc_helper.log_notice(
					        compat._format('!!!Using outdated cached config - from addon version {} !!!',
					                       cached_config.get('ADDON_VERSION', '[UNKNOWN]')))
					_config = deepcopy(cached_config)
					_config.update({
					        'IS_ANDROID': config.get('IS_ANDROID', cached_config.get('IS_ANDROID', False)),
					        'IS_ARM': config.get('IS_ARM', cached_config.get('IS_ARM', False)),
					        'actual_country': config.get('actual_country', cached_config.get('actual_country', '')),
					        'country': config.get('country', cached_config.get('country', 'DE')),
					        'USER_AGENT': config.get('USER_AGENT', cached_config.get('USER_AGENT', '')),
					})
					config = _config
				else:
					xbmc_helper.log_error('Configuration could not be extracted and no valid cached config exists. Giving Up!')
					xbmc_helper.notification(compat._format(xbmc_helper.translation('ERROR'), ''),
					                         compat._format(xbmc_helper.translation('MSG_CONFIG_VALUES_INCOMPLETE'), ''))
					exit(0)
			else:
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

		if client_data.get('brand', None) is None:
			client_data.update({'brand': ''})

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
			                                        lib_joyn.uc_slices_to_string(lib_joyn.uc_slice(encrypted_psf_config)))))))
		except Exception as e:
			xbmc_helper.log_debug(compat._format('Could not decrypt psf config - Exception: {}', e))
			pass
			return None

		return decrypted_psf_config

	@staticmethod
	def decrypt(key, value):

		from math import floor

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
				p = p - 1

			z = value[n]
			mx = (z >> 5 ^ y << 2) + (y >> 3 ^ z << 4) ^ (sum ^ y) + (key[p & 3 ^ e] ^ z)
			y = value[0] = value[0] - mx & 4294967295
			sum = sum - 2654435769 & 4294967295

		length = len(value)
		n = length - 1 << 2
		m = value[length - 1]
		if m < n - 3 or m > n:
			return None

		n = m
		ret = compat._encode('')
		for i in range(length):
			ret += compat._unichr(value[i] & 255)
			ret += compat._unichr(value[i] >> 8 & 255)
			ret += compat._unichr(value[i] >> 16 & 255)
			ret += compat._unichr(value[i] >> 24 & 255)

		return ret[0:n]

	@staticmethod
	def uc_slice(hex_string, start_pos=None, end_pos=None):
		unit8s = []
		res = []

		for hex_val in findall('..', hex_string):
			unit8s.append(int(hex_val, 16) & 0xff)

		start = 0 if start_pos is None else start_pos
		end = len(unit8s) if end_pos is None else end_pos

		bytes_per_sequence = 0
		i = 0

		while i < end:
			first_byte = unit8s[i]
			code_point = None

			if first_byte > 239:
				bytes_per_sequence = 4
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
					if 65535 < temp_code_point < 1114112:
						code_point = temp_code_point
			if code_point is None:
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
			result[i >> 2] = ord(uc_string[i:(i + 1)])
			result[i >> 2] |= ord(uc_string[(i + 1):(i + 2)]) << 8
			if len(uc_string[(i + 2):(i + 3)]) > 0:
				result[i >> 2] |= ord(uc_string[(i + 2):(i + 3)]) << 16
			if len(uc_string[(i + 3):(i + 4)]) > 0:
				result[i >> 2] |= ord(uc_string[(i + 3):(i + 4)]) << 24
			i += 4

		return result
