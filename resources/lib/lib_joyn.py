# -*- coding: utf-8 -*-

from hashlib import sha256, sha512
from sys import exit
from datetime import datetime
from time import time
from copy import copy, deepcopy
from xbmc import sleep as xbmc_sleep
from .external.singleton import Singleton
from .const import CONST
from . import compat as compat
from . import request_helper as request_helper
from . import cache as cache
from .xbmc_helper import xbmc_helper

if compat.PY2:
	from urllib import urlencode
	from HTMLParser import HTMLParser
	html = HTMLParser()
	from urlparse import urlparse, parse_qs
	try:
		from simplejson import dumps
	except ImportError:
		from json import dumps
elif compat.PY3:
	from urllib.parse import urlencode, urlparse, parse_qs
	import html
	from json import dumps


class lib_joyn(Singleton):
	def __init__(self):
		xbmc_helper().log_debug('libjoyn init')
		self.default_icon = xbmc_helper().get_addon().getAddonInfo('icon')
		self.config = lib_joyn.get_config()
		self.auth_token_data = None
		self.account_info = None
		self.landingpage = None
		self.user_agent_http_header = None
		self.addon = None
		self.epg_cache = None
		self.node = None

	def get_node(self):

		if self.node is None:
			from .submodules.libjoyn_auth import get_node_value
			self.node = get_node_value()
		return self.node

	def get_epg(self, first=30, use_cache=True):

		dt_now = datetime.now()
		if use_cache is True:
			cached_epg = cache.get_pickle('EPG')

			if cached_epg['data'] is not None and cached_epg['is_expired'] is False and 'epg_expires' in cached_epg['data'].keys(
			) and datetime.fromtimestamp(cached_epg['data']['epg_expires']) > dt_now:

				xbmc_helper().log_debug('EPG FROM CACHE')
				return cached_epg['data']['epg_data']

		elif self.epg_cache is not None and 'epg_cache_expires' in self.epg_cache.keys() and datetime.fromtimestamp(
		        self.epg_cache['epg_cache_expires']) > dt_now:
			xbmc_helper().log_debug('EPG FROM CLASS CACHE')
			return self.epg_cache['epg_data']

		xbmc_helper().log_debug('EPG FROM API')
		epg_data = self.get_graphql_response(operation='EPG',
		                                     variables={'first': first},
		                                     force_cache=False if use_cache is True else True)
		epg = {'epg_data': epg_data, 'epg_expires': None, 'epg_cache_expires': None}

		for brand_epg in epg_data['brands']:
			if brand_epg.get('livestream', None) is not None:
				if not isinstance(brand_epg['livestream'].get('epg', None), list):
					brand_epg['livestream']['epg'] = []
				brand_live_stream_epg_count = len(brand_epg['livestream']['epg'])
				if brand_live_stream_epg_count > 0:
					penultimate_brand_live_stream_epg_timestamp = brand_epg['livestream']['epg'][(brand_live_stream_epg_count -
					                                                                              2)]['startDate']
					if epg['epg_expires'] is None or epg['epg_expires'] > penultimate_brand_live_stream_epg_timestamp:
						epg.update({'epg_expires': penultimate_brand_live_stream_epg_timestamp})
					if epg['epg_cache_expires'] is None or brand_epg['livestream']['epg'][0]['endDate'] < epg['epg_cache_expires']:
						epg['epg_cache_expires'] = brand_epg['livestream']['epg'][0]['endDate']
				else:
					brand_epg['livestream']['epg'].append({
					        '__typename':
					        'EpgEntry',
					        'startDate':
					        int(time()),
					        'endDate':
					        int(time()) + 36000,
					        'title':
					        compat._format(xbmc_helper().translation('NO_INFORMATION_AVAILABLE')),
					        'secondaryTitle':
					        compat._format(xbmc_helper().translation('NO_INFORMATION_AVAILABLE'))
					})
		if use_cache is True:
			cache.set_pickle('EPG', epg)
		else:
			self.epg_cache = epg

		return epg_data

	def get_landingpage(self):

		if self.landingpage is None:
			landingpage = {}
			raw_landingpage = self.get_graphql_response('LANDINGPAGE', {'path': '/'})
			if 'page' in raw_landingpage.keys() and 'blocks' in raw_landingpage['page'].keys():
				for block in raw_landingpage['page']['blocks']:
					if self.get_auth_token().get('has_account', False) is True or block.get('isPersonalized', False) is False:
						if block['__typename'] not in landingpage.keys():
							landingpage.update({block['__typename']: {}})

						landingpage[block['__typename']].update({block['id']: block.get('headline', None)})

				self.landingpage = landingpage

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

	def get_license_filter(self, default='ALL'):

		if xbmc_helper().get_bool_setting('always_show_premium') is not True:
			for license_filter_cond, license_filter_value in CONST['LICENSE_FILTER'].items():
				if self.get_account_subscription_config(license_filter_cond) is False:
					return license_filter_value
		return default

	def check_license(self, asset_data, respect_setting=True):

		license_types = asset_data.get('licenseTypes', [])
		markings = asset_data.get('markings', [])
		xbmc_helper().log_debug('check_license: {} types {} markings {}', asset_data.get('title', ''), license_types, markings)

		if respect_setting is True and xbmc_helper().get_bool_setting('always_show_premium') is True:
			return True

		if len(license_types) > 0:
			for license_type in license_types:
				if license_type in CONST['LICENSE_TYPES']['FREE'].keys():
					if len(markings) > 0:
						found_all_markings = True
						for marking in markings:
							if not marking in CONST['LICENSE_TYPES']['FREE'][license_type]['MARKING_TYPES']:
								found_all_markings = False
								break

						if found_all_markings is True:
							return True
					else:
						return True
				elif license_type in CONST['LICENSE_TYPES']['PAID'].keys():
					if self.get_account_subscription_config(CONST['LICENSE_TYPES']['PAID'][license_type]['SUBSCRIPTION_TYPE']) is True:
						if len(markings) > 0:
							found_all_markings = True
							for marking in markings:
								if not marking in CONST['LICENSE_TYPES']['PAID'][license_type]['MARKING_TYPES']:
									found_all_markings = False

							if found_all_markings is True:
								return True
						else:
							return True
			return False
		else:
			return True

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

	def get_graphql_response(self, operation, variables={}, retry_count=0, force_refresh_auth=False, force_cache=False):

		xbmc_helper().log_debug('get_graphql_response: Operation: {}', operation)

		if isinstance(CONST['GRAPHQL'][operation].get('REQUIRED_VARIABLES', None), list):
			for required_var in CONST['GRAPHQL'][operation]['REQUIRED_VARIABLES']:
				if required_var not in variables.keys():
					if required_var in CONST['GRAPHQL']['STATIC_VARIABLES'].keys():
						variables.update({required_var: CONST['GRAPHQL']['STATIC_VARIABLES'][required_var]})
					else:
						xbmc_helper().log_error('Not all required variables set for operation {} required var {} set vars{}', operation,
						                        required_var, variables)
						exit(0)

		if force_refresh_auth is True:
			self.get_auth_token(force_refresh=True)

		request_url = CONST['GRAPHQL']['API_URL']

		if CONST['GRAPHQL'][operation].get('BOOKMARKS', False) is True and self.get_auth_token().get('has_account', False) is False:
			query = CONST['GRAPHQL'][operation]['QUERY'].replace('isBookmarked ', '')
		else:
			query = CONST['GRAPHQL'][operation]['QUERY']

		params = {
		        'query':
		        compat._format(
		                '{} {} {}', 'query' if CONST['GRAPHQL'][operation].get('IS_MUTATION', False) is False else 'mutation', ''
		                if CONST['GRAPHQL'][operation].get('OPERATION', None) is None else CONST['GRAPHQL'][operation]['OPERATION'],
		                query)
		}

		if len(variables.keys()) != 0:
			if CONST['GRAPHQL'][operation].get('IS_MUTATION', False) is False:
				params.update({'variables': dumps(variables)})
			else:
				params.update({'variables': variables})

		if CONST['GRAPHQL'][operation].get('OPERATION', None) is not None:
			params.update({
			        'operationName': CONST['GRAPHQL'][operation].get('OPERATION'),
			        'extensions': {
			                'persistedQuery': {
			                        'version': 1,
			                        'sha256Hash': sha256(params['query'].encode('utf-8')).hexdigest(),
			                },
			        }
			})

			if CONST['GRAPHQL'][operation].get('IS_MUTATION', False) is False:
				params.update({'extensions': dumps(params['extensions'])})

		headers = copy(self.config['GRAPHQL_HEADERS'])

		account_state = False
		if operation != 'ACCOUNT' and operation != 'USER_PROFILE' and self.get_auth_token().get('has_account', False) is not False:
			account_state = self.get_account_state()
			if account_state is not False:
				headers.append(('Joyn-User-State', account_state))

		headers.append(('Authorization', self.get_access_token()))

		api_response = {}
		no_cache = False if force_cache is True else CONST['GRAPHQL'][operation].get('NO_CACHE', False)

		try:
			if CONST['GRAPHQL'][operation].get('IS_MUTATION', False) is False:

				api_response = request_helper.get_json_response(url=request_url,
				                                                config=self.config,
				                                                params=params,
				                                                headers=headers,
				                                                no_cache=no_cache,
				                                                return_json_errors=['INVALID_JWT'])
			else:
				api_response = request_helper.post_json(url=request_url,
				                                        config=self.config,
				                                        data=params,
				                                        additional_headers=headers,
				                                        no_cache=no_cache,
				                                        return_json_errors=['INVALID_JWT'])

			if isinstance(api_response, dict) and 'json_errors' in api_response.keys():
				if 'INVALID_JWT' in api_response['json_errors']:
					self.get_graphql_response(operation=operation, variables=variables, retry_count=retry_count, force_refresh_auth=True)

		except Exception as e:
			xbmc_helper().log_error('Could not complete graphql request: {} params {}', e, params)

		if isinstance(api_response, dict) and 'errors' in api_response.keys():
			xbmc_helper().log_error('GraphQL query returned errors: {} params {}', api_response['errors'], params)

		if isinstance(api_response, dict) and 'data' in api_response.keys() and api_response['data'] is not None:
			return api_response['data']
		else:
			xbmc_helper().log_error('GraphQL query returned no data - response: {} params {}', api_response, params)

			if retry_count < 3:
				xbmc_helper().log_error('Retrying to complete graphql request ... retry count: {}', retry_count)
				xbmc_sleep(500)
				return self.get_graphql_response(operation=operation, variables=variables, retry_count=(retry_count + 1))
			else:
				xbmc_helper().notification(
				        compat._format(xbmc_helper().translation('ERROR'), 'GraphQL'),
				        xbmc_helper().translation('MSG_GAPHQL_ERROR'),
				)
				exit(0)

	def get_client_ids(self, username=None, password=None):

		from .submodules.libjoyn_auth import get_device_uuid

		client_id_data = xbmc_helper().get_json_data('client_ids')
		if client_id_data is None or client_id_data.get('client_name', 'android') not in CONST['CLIENT_NAMES']:
			client_id_data = {
			        'anon_device_id': get_device_uuid(),
			        'client_id': get_device_uuid(prefix='JOYNCLIENTID'),
			        'client_name': self.config.get('CLIENT_NAME', 'web'),
			}
			xbmc_helper().log_debug('Created new client_id_data: {}', client_id_data)
			xbmc_helper().set_json_data('client_ids', client_id_data)

		if username is not None and password is not None:
			del client_id_data['anon_device_id']
			client_id_data.update({
			        'email': username,
			        'password': password,
			})

		return client_id_data

	def get_auth_token(self,
	                   username=None,
	                   password=None,
	                   reset_anon=False,
	                   is_retry=False,
	                   logout=False,
	                   force_refresh=False,
	                   force_reload_cache=False,
	                   do_legacy_login=False):

		if username is not None and password is not None:
			try:
				client_ids = self.get_client_ids(username, password)

				if do_legacy_login is False and xbmc_helper().get_bool_setting('force_legacy_login') is False:
					sso_resp = request_helper.get_json_response(url=CONST.get('SSO_AUTH_URL'),
					                                            config=self.config,
					                                            params={
					                                                    'client_id': client_ids.get('client_id'),
					                                                    'client_name': client_ids.get('client_name'),
					                                            },
					                                            no_cache=True)
					if isinstance(sso_resp, dict) and 'web-login' in sso_resp.keys() and sso_resp.get('web-login').startswith(
					        'http') and 'redeem-token' in sso_resp.keys() and sso_resp.get('redeem-token').startswith('http'):
						web_login_query_dict = parse_qs(urlparse(sso_resp.get('web-login')).query)

						if 'client_id' not in web_login_query_dict.keys():
							return self.get_auth_token(username=username,
							                           password=password,
							                           reset_anon=reset_anon,
							                           is_retry=is_retry,
							                           logout=logout,
							                           force_refresh=force_refresh,
							                           force_reload_cache=force_reload_cache,
							                           do_legacy_login=True)

						cookie_file = xbmc_helper().set_data(filename=compat._format('{}.cookie.tmp',
						                                                             sha512(str(time()).encode('utf-8')).hexdigest()),
						                                     data='',
						                                     dir_type='TEMP_DIR')
						xbmc_helper().log_debug("Created empty cookie file: {}", cookie_file)
						login_url, login_response = request_helper.get_url(url=sso_resp.get('web-login'),
						                                                   config=self.config,
						                                                   additional_query_string={
						                                                           'redirect_uri': CONST.get('OAUTH_URL'),
						                                                           'state': '%2F',
						                                                   },
						                                                   cookie_file=cookie_file,
						                                                   return_final_url=True)
						csrf_param = None
						csrf_token = None
						from re import findall

						for match in findall('<meta name="csrf-(param|token)" content="(.*)" />', login_response):
							if match[0] == 'param':
								csrf_param = match[1]
							elif match[0] == 'token':
								csrf_token = match[1]

						if csrf_param is None or csrf_token is None:
							xbmc_helper().log_debug('Failed to find csrf meta tags - trying with hidden field as fallback')
							for match in findall(' <input type="hidden" name="_csrf_(.*)" value=(.*) />', login_response):
								csrf_param = compat._format('_csrf_{}', match[0])
								csrf_token = match[1]

						if csrf_param is not None and csrf_token is not None:

							login_params = {csrf_param: csrf_token, 'account[email]': username, 'password': password}

							login_res_url, login_res_response = request_helper.get_url(url=login_url,
							                                                           config=self.config,
							                                                           post_data=login_params,
							                                                           cookie_file=cookie_file,
							                                                           return_final_url=True,
							                                                           no_cache=True)

							xbmc_helper().del_data(cookie_file, 'TEMP_DIR')

							# login failed
							if login_res_url == login_url:
								xbmc_helper().log_notice('Login failed - url: {}', login_res_url)
								return False

							login_res_parsed = urlparse(login_res_url)
							login_res_query_dict = parse_qs(login_res_parsed.query)
							xbmc_helper().log_debug("LOGIN RESULT: {} {}", login_res_parsed, login_res_query_dict)
							token_req_params = {
							        'code': login_res_query_dict.get('code')[0],
							        'client_id': web_login_query_dict.get('client_id')[0],
							        'redirect_uri': compat._format('{}://{}{}', login_res_parsed.scheme, login_res_parsed.netloc,
							                                       login_res_parsed.path),
							        'tracking_id': client_ids.get('client_id'),
							        'tracking_name': client_ids.get('client_name')
							}

							auth_token_data = request_helper.post_json(url=sso_resp.get('redeem-token'),
							                                           config=self.config,
							                                           data=token_req_params,
							                                           no_cache=True,
							                                           return_json_errors='UNAUTHORIZED')

						else:
							xbmc_helper().log_error("Could not find required csrf login parameters - response was: {} - retrying with legacy login",
							                        login_response)
							xbmc_helper().del_data(cookie_file, 'TEMP_DIR')
							return self.get_auth_token(username=username,
							                           password=password,
							                           reset_anon=reset_anon,
							                           is_retry=is_retry,
							                           logout=logout,
							                           force_refresh=force_refresh,
							                           force_reload_cache=force_reload_cache,
							                           do_legacy_login=True)
					else:
						xbmc_helper().log_error('Failed to retrieve required sso auth parameters - response was: {} - retrying with legacy login',
						                        sso_resp)
						return self.get_auth_token(username=username,
						                           password=password,
						                           reset_anon=reset_anon,
						                           is_retry=is_retry,
						                           logout=logout,
						                           force_refresh=force_refresh,
						                           force_reload_cache=force_reload_cache,
						                           do_legacy_login=True)

				else:
					xbmc_helper().log_notice('Using legacy login')

					auth_token_data = request_helper.post_json(url=compat._format('{}{}', CONST.get('AUTH_URL'), CONST.get('AUTH_LOGIN')),
					                                           config=self.config,
					                                           data=client_ids,
					                                           no_cache=True,
					                                           return_json_errors='UNAUTHORIZED')

				if isinstance(auth_token_data, dict) and 'json_errors' in auth_token_data.keys():
					if 'UNAUTHORIZED' in auth_token_data['json_errors']:
						xbmc_helper().log_debug('Failed to log in')
						return False

				xbmc_helper().log_debug('Successfully logged in an retrieved auth token')
				auth_token_data.update({
				        'created': int(time()),
				        'has_account': True,
				})

				xbmc_helper().set_json_data('auth_tokens', auth_token_data)

				self.auth_token_data = auth_token_data
				cache.remove_json('EPG')
				self.landingpage = None
				self.epg_cache = None

			except Exception as e:
				xbmc_helper().log_debug('Failed to log in - exception: {}', e)
				pass
				return False

		elif reset_anon is False:
			if self.auth_token_data is None or force_reload_cache is True:
				self.auth_token_data = xbmc_helper().get_json_data('auth_tokens')

		if reset_anon is True or self.auth_token_data is None:
			xbmc_helper().log_debug("Creating new auth_token_data")

			auth_token_data = request_helper.post_json(url=compat._format('{}{}', CONST.get('AUTH_URL'), CONST.get('AUTH_ANON')),
			                                           config=self.config,
			                                           data=self.get_client_ids(),
			                                           no_cache=True)

			auth_token_data.update({'created': int(time())})
			xbmc_helper().set_json_data('auth_tokens', auth_token_data)
			self.auth_token_data = auth_token_data
			if reset_anon is True:
				cache.remove_json('ACCOUNT_INFO')
				cache.remove_json('EPG')
				self.landingpage = None
				self.epg_cache = None

		# refresh the token at least 30min before it actual expires
		if force_refresh is True or time() >= self.auth_token_data['created'] + ((self.auth_token_data['expires_in'] / 1000) - 1800):
			xbmc_helper().log_debug("Refreshing auth_token_data")
			client_id_data = self.get_client_ids()

			refresh_auth_token_req_data = {
			        'refresh_token': self.auth_token_data['refresh_token'],
			        'client_id': client_id_data['client_id'],
			        'client_name': client_id_data['client_name'],
			}

			try:
				refresh_auth_token_data = request_helper.post_json(url=compat._format('{}{}', CONST.get('AUTH_URL'),
				                                                                      CONST.get('AUTH_REFRESH')),
				                                                   config=self.config,
				                                                   data=refresh_auth_token_req_data,
				                                                   no_cache=True,
				                                                   return_json_errors=['VALIDATION_ERROR'])

				if isinstance(refresh_auth_token_data, dict) and 'json_errors' in refresh_auth_token_data.keys():
					if 'VALIDATION_ERROR' in refresh_auth_token_data['json_errors']:
						# ask to re-login
						if self.auth_token_data.get('has_account', False) is True:
							xbmc_helper().log_debug("ask to re-login")

							from .submodules.libjoyn_auth import login, get_auth_data
							if not get_auth_data():
								xbmc_helper().notification(compat._format(xbmc_helper().translation('ERROR'),
								                                          xbmc_helper().translation('ACCOUNT')),
								                           xbmc_helper().translation('MSG_RERESH_AUTH_FAILED_RELOG'))

							login(dont_check_account=True)
							return self.get_auth_token(force_reload_cache=True, is_retry=True)
						else:
							if is_retry is False:
								pass
								return self.get_auth_token(reset_anon=True, is_retry=True)
							else:
								pass
								return xbmc_helper().notification(
								        compat._format(xbmc_helper().translation('ERROR'),
								                       xbmc_helper().translation('ACCOUNT')),
								        xbmc_helper().translation('MSG_RERESH_AUTH_FAILED'))

				self.auth_token_data.update({
				        'created': int(time()),
				        'access_token': refresh_auth_token_data.get('access_token'),
				        'refresh_token': refresh_auth_token_data.get('refresh_token')
				})

			except Exception as e:
				xbmc_helper().log_debug('Could not refresh auth token! - {}', e)

			# refresh account_info too
			if self.auth_token_data.get('has_account', False) is not False:
				self.account_info = self.get_account_info(True)

			xbmc_helper().set_json_data('auth_tokens', self.auth_token_data)

		if logout is True and self.auth_token_data.get('has_account', False) is True and self.auth_token_data.get(
		        'access_token', None) is not None:

			request_helper.get_url(url=compat._format('{}{}', CONST.get('AUTH_URL'), CONST.get('AUTH_LOGOUT')),
			                       config=self.config,
			                       post_data='',
			                       no_cache=True,
			                       additional_headers=[('Authorization', self.get_access_token())])
			xbmc_helper().del_data('auth_data')

			return self.get_auth_token(reset_anon=True)

		return self.auth_token_data

	def get_access_token(self, force_refresh=False):
		_auth_token = self.get_auth_token(force_refresh=force_refresh)
		if _auth_token is not None:
			return compat._format('{} {}', _auth_token.get('token_type'), _auth_token.get('access_token'))
		else:
			xbmc_helper().log_notice("Failed to get auth token")
			return None

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
					metadata['infoLabels'].update({text_mapping_key: html.unescape(data[text_key])})
				else:
					metadata['infoLabels'].update({text_mapping_key: ''})

		if title_type_id is not None and 'title' in metadata['infoLabels'].keys():
			metadata['infoLabels'].update(
			        {'title': compat._format(xbmc_helper().translation('TITLE_LABEL'), metadata['infoLabels'].get('title', ''))})

		if xbmc_helper().get_bool_setting('highlight_premium') is True and isinstance(data.get('markings', None),
		                                                                              list) and 'PREMIUM' in data['markings']:
			metadata['infoLabels'].update({
			        'title':
			        compat._format(xbmc_helper().translation('PLUS_HIGHLIGHT_LABEL'), metadata['infoLabels'].get('title', ''))
			})

		if data.get('isBookmarked', None) is not None:
			if data.get('isBookmarked', False) is True:
				metadata['infoLabels'].update(
				        {'title': compat._format(xbmc_helper().translation('JOYN_BOOKMARK_LABEL'), metadata['infoLabels']['title'])})
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

		age_rating = None
		if 'ageRating' in data.keys() and data['ageRating'] is not None and 'minAge' in data['ageRating'].keys():
			age_rating = data['ageRating']['minAge']
		elif isinstance(data.get('series', None), dict) and isinstance(data.get('series').get(
		        'ageRating', None), dict) and data.get('series').get('ageRating').get('minAge', None) is not None:
			age_rating = data.get('series').get('ageRating').get('minAge')
		elif isinstance(data.get('season', None), dict) and isinstance(data.get('season').get(
		        'ageRating', None), dict) and data.get('season').get('ageRating').get('minAge', None) is not None:
			age_rating = data.get('season').get('ageRating').get('minAge')
		elif isinstance(data.get('compilation', None), dict) and isinstance(data.get('compilation').get(
		        'ageRating', None), dict) and data.get('compilation').get('ageRating').get('minAge', None) is not None:
			age_rating = data.get('compilation').get('ageRating').get('minAge')

		if age_rating is not None:
			metadata['infoLabels'].update({'mpaa': compat._format(xbmc_helper().translation('MIN_AGE'), str(age_rating))})

		if 'genres' in data.keys() and isinstance(data['genres'], list):
			metadata['infoLabels'].update({'genre': []})

			for genre in data['genres']:
				if 'name' in genre.keys():
					metadata['infoLabels']['genre'].append(genre['name'])

		copyrights = None
		if 'copyrights' in data.keys() and data.get('copyrights', None) is not None:
			copyrights = data.get('copyrights', None)
		elif isinstance(data.get('series', None), dict) and data.get('series').get('copyrights', None) is not None:
			copyrights = data.get('series').get('copyrights')
		elif isinstance(data.get('season', None), dict) and data.get('season').get('copyrights', None) is not None:
			copyrights = data.get('season').get('copyrights')
		elif isinstance(data.get('compilation', None), dict) and data.get('compilation').get('copyrights', None) is not None:
			copyrights = data.get('compilation').get('copyrights')

		if copyrights is not None:
			metadata['infoLabels'].update({'Studio': copyrights})

		if query_type == 'EPISODE':
			if 'endsAt' in data.keys() and data['endsAt'] is not None and data['endsAt'] < 9999999999:
				endsAt = xbmc_helper().timestamp_to_datetime(data['endsAt'])
				if endsAt is not False:
					metadata['infoLabels'].update({
					        'plot':
					        compat._format('{}{}', compat._format(xbmc_helper().translation('VIDEO_AVAILABLE'), endsAt),
					                       metadata['infoLabels'].get('plot', ''))
					})

			if 'number' in data.keys() and data['number'] is not None:
				metadata['infoLabels'].update({
				        'episode': data['number'],
				        'sortepisode': data['number'],
				})
			if 'series' in data.keys():
				if 'title' in data['series'].keys():
					metadata['infoLabels'].update({'tvshowtitle': html.unescape(data['series']['title'])})
				series_meta = lib_joyn.get_metadata(data['series'], 'TVSHOW')
				if 'clearlogo' in series_meta['art'].keys():
					metadata['art'].update({'clearlogo': series_meta['art']['clearlogo']})

			elif 'compilation' in data.keys():
				compilation_meta = lib_joyn.get_metadata(data['compilation'], 'TVSHOW')
				if 'title' in data['compilation'].keys():
					metadata['infoLabels'].update({'tvshowtitle': html.unescape(data['compilation']['title'])})
				if 'clearlogo' in compilation_meta['art'].keys():
					metadata['art'].update({'clearlogo': compilation_meta['art']['clearlogo']})

		if 'airdate' in data.keys() and data['airdate'] is not None:
			broadcast_datetime = xbmc_helper().timestamp_to_datetime(data['airdate'])
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

		if data.get('tagline', None) is not None:
			metadata['infoLabels'].update({'tagline': data.get('tagline')})

		if data.get('resumePosition', None) is not None and data.get('resumePosition').get('position', 0) > 0:
			metadata.update({'resume_pos': str(float(data.get('resumePosition').get('position')))})

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
		epg_metadata['infoLabels'].update({'title': compat._format(xbmc_helper().translation('LIVETV_TITLE'), brand_title, '')})

		for idx, epg_entry in enumerate(brand_livestream_epg['epg']):
			end_time = xbmc_helper().timestamp_to_datetime(epg_entry['endDate'])

			if end_time is not False and end_time > dt_now:
				epg_metadata = lib_joyn.get_metadata(epg_entry, 'EPG')
				epg_metadata['infoLabels'].update({
				        'title':
				        compat._format(xbmc_helper().translation('LIVETV_TITLE'), brand_title, epg_entry['title']),
				        'tvShowTitle':
				        epg_entry['title'],
				        'mediatype':
				        'tvshow'
				})
				if len(brand_livestream_epg['epg']) > (idx + 1):
					epg_metadata['infoLabels'].update({
					        'plot':
					        compat._format(xbmc_helper().translation('LIVETV_UNTIL_AND_NEXT'), end_time,
					                       brand_livestream_epg['epg'][idx + 1]['title'])
					})
				else:
					epg_metadata['infoLabels'].update({'plot': compat._format(xbmc_helper().translation('LIVETV_UNTIL'), end_time)})

				if epg_entry.get('secondaryTitle', None) is not None:
					epg_metadata['infoLabels']['plot'] += epg_entry['secondaryTitle']

				break

		return epg_metadata

	@staticmethod
	def get_config():

		recreate_config = True
		config = {}
		cached_config = None
		addon_version = xbmc_helper().get_addon_version()

		expire_config_days = xbmc_helper().get_int_setting('configcachedays')
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
			xbmc_helper().remove_dir(CONST['CACHE_DIR'])
			xbmc_helper().log_debug('cleared cache')

		if recreate_config == True:
			from .submodules.libjoyn_create_config import create_config
			config = create_config(cached_config, addon_version)

		return config
