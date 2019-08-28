#!/usr/bin/python
# -*- coding: utf-8 -*-

from base64 import b64decode
from json import loads, dumps
from re import search, findall
from os import environ
from hashlib import sha1
from math import floor
from sys import exit
from datetime import datetime, timedelta
from time import time
from copy import deepcopy
from .const import CONST
from . import compat as compat
from . import request_helper as request_helper
from . import cache as cache
from . import xbmc_helper as xbmc_helper
from .mpd_parser import mpd_parser as mpd_parser

if compat.PY2:
	from urllib import urlencode
	from urlparse import urlparse, urlunparse , parse_qs
elif compat.PY3:
	from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

class lib_joyn:


	def __init__(self, default_icon):

		self.config = lib_joyn.get_config(default_icon)
		self.default_icon = default_icon


	def get_joyn_json_response(self, url, headers=None, params=None):

		if headers is not None:
				headers.append(('key', self.config['CONFIG']['header_7TV_key']))
		else:
			headers = [('key', self.config['CONFIG']['header_7TV_key'])]

		decoded_json = request_helper.get_json_response(url, self.config, headers, params)

		if decoded_json[compat._unicode('status')] == 200:
			return decoded_json[compat._unicode('response')]
		else:
			return None


	def build_signature(self, video_id, encoded_client_data, entitlement_token):

		sha_input = video_id + ','
		sha_input += entitlement_token + ','
		sha_input += encoded_client_data

		for char in findall('.',self.config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']]):
			sha_input += hex(ord(char))[2:]

		sha_1 = sha1()
		sha_1.update(sha_input.encode('utf-8'))
		sha_output = sha_1.hexdigest()

		return sha_output


	def get_json_by_type(self, path_type, replacements={}, additional_params={}, url_annex=''):

		valued_query_params = {}

		if 'search' not in additional_params.keys():
			for key, value in CONST['PATH'][path_type]['QUERY_PARAMS'].items():
				if search('^##(.)+##$', value) is not None:
					key = value[2:-2]
					if (key in replacements.keys()):
						value = replacements[key]
				valued_query_params.update({key : value})

		if  CONST['PATH'][path_type]['SELECTION'].find('%s') is not -1:
			valued_query_params.update({'selection' : (CONST['PATH'][path_type]['SELECTION'] % CONST['COUNTRIES'][self.config['country']]['language'])})
		else:
			valued_query_params.update({'selection' : CONST['PATH'][path_type]['SELECTION']})

		valued_query_params.update(additional_params)

		return self.get_joyn_json_response(url=CONST['MIDDLEWARE_URL'] + CONST['PATH'][path_type]['PATH'] + url_annex , params=valued_query_params)


	def set_mpd_props(self, list_item, url, stream_type='VOD'):

		xbmc_helper.log_debug('get_mpd_path : ' + url + 'stream_type: ' + stream_type)
		mpdparser = None

		##strip out the filter parameter
		parts = urlparse(url)
		query_dict = parse_qs(parts.query)

		if 'filter' in query_dict.keys():
			query_dict.update({'filter' : ''})
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
				xbmc_helper.log_debug('Found MPD with Base URL at toplevel : ' + toplevel_base_url_res)
				toplevel_base_url =  toplevel_base_url_res

			if toplevel_base_url is not None :
				if stream_type == 'VOD':
					new_mpd_url = toplevel_base_url + '.mpd?filter='
					try :
						test_mpdparser = mpd_parser(new_mpd_url, self.config);
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
					period_base_url_res = mpdparser.query_node_value(['Period','BaseURL']);
					if period_base_url_res is not None and period_base_url_res.startswith('/') and period_base_url_res.endswith('/'):
						new_mpd_url = toplevel_base_url + period_base_url_res + 'cenc-default.mpd'

						try :
							test_mpdparser = mpd_parser(new_mpd_url, self.config);
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

			if toplevel_base_url is not None :
				xbmc_helper.log_debug('Writing MPD file to local disc, since it has a remote top Level Base URL ...')
				sha_1 = sha1()
				sha_1.update(mpdparser.mpd_url)

				mpd_filepath = xbmc_helper.get_file_path(CONST['TEMP_DIR'],  sha_1.hexdigest() + '.mpd')
				with open (mpd_filepath, 'w') as mpd_filepath_out:
					mpd_filepath_out.write(mpdparser.mpd_contents)

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


	def get_video_data(self, video_id, stream_type):

		video_url = self.config['PSF_CONFIG']['default'][stream_type.lower()]['playoutBaseUrl']

		client_data = {}
		if stream_type == 'VOD':
			video_metadata = self.get_joyn_json_response(CONST['MIDDLEWARE_URL'] + 'metadata/video/' + video_id)

			client_data.update({
					'startTime' 	: '0',
					'videoId' 	: video_metadata['tracking']['id'],
					'duration'	: video_metadata['tracking']['duration'],
					'brand'		: video_metadata['tracking']['channel'],
					'genre'		: video_metadata['tracking']['genres'],
					'tvshowid'	: video_metadata['tracking']['tvShow']['id'],
			})

			if 'agofCode' in video_metadata['tracking'].keys():
				client_data.update({'agofCode' : video_metadata['tracking']['agofCode']})

		elif stream_type == 'LIVE':
			client_data.update({
					'videoId' 	: None,
					'channelId'	: video_id,

			})

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

		video_data = request_helper.get_json_response(url=video_url, config=self.config, headers=[('Content-Type', 'application/x-www-form-urlencoded charset=utf-8')], post_data='false')

		if 'video_metadata' in locals() and 'video' in video_metadata.keys():
			video_data.update({'tv_show_id' : video_metadata['tracking']['tvShow']['id'],
				'season_id' : video_metadata['video']['metadata'][CONST['COUNTRIES'][self.config['country']]['language']]['seasonObject']['id']})

		return video_data


	def get_epg(self):

		cached_epg =  cache.get_json('EPG')
		if cached_epg['data'] is not None and cached_epg['is_expired'] is False:
			epg = cached_epg['data']
		else:
			epg = {}
			raw_epg = self.get_json_by_type('EPG',{
					'from' : (datetime.now() - timedelta(hours=CONST['EPG']['REQUEST_OFFSET_HOURS'])).strftime('%Y-%m-%d %H:%M:00'),
					'to': (datetime.now() + timedelta(hours=CONST['EPG']['REQUEST_HOURS'])).strftime('%Y-%m-%d %H:%M:00')}
				);

			for raw_epg_data in raw_epg['data']:
				raw_epg_data['channelId'] = str(raw_epg_data['channelId'])
				if raw_epg_data['channelId'] not in epg.keys():
					epg.update({raw_epg_data['channelId'] : []})
				epg[raw_epg_data['channelId']].append(raw_epg_data);

			cache.set_json('EPG',epg)

		return epg


	def get_brands(self):

		cached_brands = cache.get_json('BRANDS')
		if cached_brands['data'] is not None and cached_brands['is_expired'] is False:
			brands = cached_brands['data']
		else:
			brands = self.get_json_by_type('BRAND')
			cache.set_json('BRANDS', brands)

		return brands


	def get_categories(self):

		raw_cats = self.get_joyn_json_response(CONST['MIDDLEWARE_URL']  + 'ui?path=/')
		categories = {}

		if 'blocks' in raw_cats.keys():
			for block in raw_cats['blocks']:
				if 'type' in block.keys() and 'configuration' in block.keys() and block['type'] == 'StandardLane':
					categories.update({block['configuration']['Headline'] : []})
					for block_item in block['items']:
						categories[block['configuration']['Headline']].append(block_item['fetch']['id'])

		return categories;


	def get_uepg_data(self, pluginurl):

		brands = self.get_brands()
		epg = self.get_epg()
		uEPG_data = []
		channel_num = 0

		for brand in brands['data']:
			channel_id = str(brand['channelId'])
			if 'metadata' in brand.keys() and CONST['COUNTRIES'][self.config['country']]['language'] in brand['metadata'].keys() and \
					'livestreams' in  brand['metadata'][CONST['COUNTRIES'][self.config['country']]['language']].keys():

				for livestream in brand['metadata'][CONST['COUNTRIES'][self.config['country']]['language']]['livestreams']:
					stream_id = livestream['streamId']
					brand_metadata = extracted_metadata = self.extract_metadata(
						metadata= brand['metadata'][CONST['COUNTRIES'][self.config['country']]['language']],
							selection_type='BRAND')

					for art_key, art_value in brand_metadata['art'].items():
						brand_metadata['art'].update({art_key : request_helper.add_user_agend_header_string(art_value, self.config['USER_AGENT'])})

					if channel_id in epg.keys():
						channel_num += 1
						uEPG_channel = {
							'channelnumber'  :channel_num,
							'isfavorite' : False,
							'channellogo' : brand_metadata['art']['icon']
						}

						guidedata = []
						first = True
						for channel_epg_data in epg[channel_id]:
							if first is True:
								uEPG_channel.update({
									'channelname' : channel_epg_data['tvChannelName']
								})
							first = False
							art = deepcopy(brand_metadata['art'])
							if 'images' in 	channel_epg_data:
								for image in channel_epg_data['images']:
									if image['subType'] == 'cover':
										art.update({'thumb' :  request_helper.add_user_agend_header_string(
											image['url'] + '/' +  CONST['PATH']['EPG']['IMG_PROFILE'], self.config['USER_AGENT'])})

							guidedata.append({
								'label'	: channel_epg_data['tvShow']['title'],
								'plot' : channel_epg_data['description'],
								'title' : channel_epg_data['tvShow']['title'],
								'starttime' : channel_epg_data['startTime'],
								'duration' : (channel_epg_data['endTime'] - channel_epg_data['startTime']),
								'art' : art,
								'url' : pluginurl + '?' + urlencode({'mode' : 'play_video', 'stream_type': 'LIVE', 'video_id' : stream_id})
							})

						uEPG_channel.update({'guidedata' : guidedata})
						uEPG_data.append(uEPG_channel)
		return uEPG_data


	@staticmethod
	def combine_tvshow_season_data(tvshow_data, season_data):

		combined_title =  tvshow_data['infoLabels']['title'] + ' - ' + season_data['infoLabels']['title']
		season_data['infoLabels'].update({'title' : combined_title})
		season_data.update({'art' : tvshow_data['art']})
		return season_data


	@staticmethod
	def merge_subtype_art(selection_type, metadata_art, data):

		if 'SUBTYPE_ART' in CONST['PATH'][selection_type].keys():
			for subtype_art_key, subtype_art in CONST['PATH'][selection_type]['SUBTYPE_ART'].items():
				if subtype_art_key in data.keys() and 'images' in data[subtype_art_key].keys():

					for subtype_art_item in data[subtype_art_key]['images']:
						if 'subType' in subtype_art_item.keys() and subtype_art_item['subType'] in subtype_art.keys():
							for art_type, art_profile in subtype_art[subtype_art_item['subType']].items():
								xbmc_helper.log_debug('merge_subtype_art : ' + art_type + '--->' + subtype_art_item['url'] + '/' + art_profile)
								metadata_art.update({art_type : subtype_art_item['url'] + '/' + art_profile})

		return metadata_art

	@staticmethod
	def extract_metadata(metadata, selection_type, visibilities=None):
		extracted_metadata = {
			'art': {},
			'infoLabels' : {},
		};

		path = CONST['PATH'][selection_type]

		if 'descriptions' in metadata.keys() and 'description' in path['TEXTS'].keys():
			for description in metadata['descriptions']:
				if description['type'] == path['TEXTS']['description']:
					extracted_metadata['infoLabels'].update({'plot' : description['text']})
					break

		if selection_type == 'SEASON':
			cast = []
			if 'seasonNumber' in metadata.keys() and metadata['seasonNumber'] is not None:
				extracted_metadata['infoLabels'].update({'title' : xbmc_helper.translation('SEASON_NO').format(str(metadata['seasonNumber']))})
				extracted_metadata['infoLabels'].update({'season' : metadata['seasonNumber']})
				extracted_metadata['infoLabels'].update({'sortseason' : metadata['seasonNumber']})


			if 'cast' in metadata.keys():
				for actor in metadata['cast']:
					if 'name' in actor.keys():
						cast.append(actor['name'])

			extracted_metadata['infoLabels'].update({'cast' : cast})

		elif 'titles' in metadata.keys() and 'title' in path['TEXTS'].keys():
			for title in metadata['titles']:
				if title['type'] ==  path['TEXTS']['title']:
					extracted_metadata['infoLabels'].update({'title' : title['text']})
					break
		if 'images' in metadata.keys() and 'ART' in path.keys():
			for image in metadata['images']:
				if image['type'] in path['ART'].keys():
					for art_type, img_profile in path['ART'][image['type']].items():
						extracted_metadata['art'].update({art_type : image['url'] + '/' + img_profile})

		avaibility_end = None
		avaibility_start = None

		if visibilities is not None:
			for visibility in visibilities:
				if 'endsAt' in visibility.keys() and visibility['endsAt'] < 9999999999:
					avaibility_end = datetime.fromtimestamp(visibility['endsAt'])
				if 'startsAt' in visibility.keys():
					avaibility_start = datetime.fromtimestamp(visibility['startsAt'])
				if avaibility_start is not None and avaibility_end is not None:
					break

		if avaibility_end is not None:
			extracted_metadata['infoLabels'].update({
				'plot' : compat._unicode(xbmc_helper.translation('VIDEO_AVAILABLE')).format(avaibility_end) + extracted_metadata['infoLabels'].get('plot', '')
			})

		if avaibility_start is not None:
			extracted_metadata['infoLabels'].update({'dateadded' : avaibility_start.strftime('%Y-%m-%d %H:%M:%S')})

		if 'INFOLABELS' in path.keys():
			extracted_metadata['infoLabels'].update(path['INFOLABELS'])

		return extracted_metadata


	@staticmethod
	def extract_metadata_from_epg(epg_channel_data):
		extracted_metadata = {
			'art': {},
			'infoLabels' : {},
		};


		for idx, program_data in enumerate(epg_channel_data):
			endTime = datetime.fromtimestamp(program_data['endTime'])
			if  endTime > datetime.now():
				extracted_metadata['infoLabels']['title'] = compat._unicode(xbmc_helper.translation('LIVETV_TITLE')).format(
											program_data['tvChannelName'], program_data['tvShow']['title'])

				if len(epg_channel_data) > (idx+1):
					extracted_metadata['infoLabels']['plot'] = compat._unicode(xbmc_helper.translation('LIVETV_UNTIL_AND_NEXT')).format(
											endTime,epg_channel_data[idx+1]['tvShow']['title'])
				else:
					extracted_metadata['infoLabels']['plot'] =  compat._unicode(xbmc_helper.translation('LIVETV_UNTIL')).format(endTime)

				if program_data['description'] is not None:
					extracted_metadata['infoLabels']['plot'] += program_data['description']

				for image in program_data['images']:
					if image['subType'] == 'cover':
						extracted_metadata['art']['poster'] = image['url'] + '/' + CONST['PATH']['EPG']['IMG_PROFILE']
				break

		return extracted_metadata;


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

		if confg_cache_res['is_expired'] is False and  'ADDON_VERSION' in cached_config.keys() and cached_config['ADDON_VERSION'] == addon_version:
			recreate_config = False;
			config = cached_config;

		if recreate_config == True:

			xbmc_helper.log_debug('get_config(): create config')
			config = {
				'CONFIG'		: {
								'header_7TV_key_web': None,
								'header_7TV_key': None,
								'SevenTV_player_config_url': None
							  },
				'PLAYER_CONFIG'		: {},
				'PSF_CONFIG' 		: {},
				'PSF_VARS'		: {},
				'PSF_CLIENT_CONFIG'	: {},
				'IS_ANDROID'		: False,
				'IS_ARM'		: False,
				'ADDON_VERSION'		: addon_version,
				'country'		: None,

			}

			os_uname = compat._uname_list()
			#android
			if os_uname[0] == 'Linux' and 'KODI_ANDROID_LIBS' in environ:
				config['USER_AGENT'] = 'Mozilla/5.0 (Linux Android 8.1.0 Nexus 6P Build/OPM6.171019.030.B1) AppleWebKit/537.36 (KHTML, like Gecko) '\
								'Chrome/68.0.3440.91 Mobile Safari/537.36'
				config['IS_ANDROID'] = True
			# linux on arm uses widevine from chromeos
			elif os_uname[0] == 'Linux' and os_uname[4].lower().find('arm') is not -1:
				config['USER_AGENT'] = 'Mozilla/5.0 (X11 CrOS '+  os_uname[4] + ' 4537.56.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.38 Safari/537.36'
				config['IS_ARM'] = True
			elif os_uname[0] == 'Linux':
				config['USER_AGENT'] = 'Mozilla/5.0 (X11 Linux ' + os_uname[4] + ') AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
			else:
				config['USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0 Win64 x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'

			html_content = request_helper.get_url(CONST['BASE_URL'], config);
			if html_content is None or html_content is '':
				xbmc_helper.notification(
						xbmc_helper.translation('ERROR').format('Url access'),
						xbmc_helper.translation('MSG_NO_ACCESS_TO_URL').format(CONST['BASE_URL'])
					)
				exit(0)

			county_setting = xbmc_helper.get_setting('country')
			xbmc_helper.log_debug("COUNTRY SETTING : " + county_setting)
			if county_setting is '' or county_setting is '0':
				ip_api_response = request_helper.get_json_response(url=CONST['IP_API_URL'].format(xbmc_helper.translation('LANG_CODE')), config=config, silent=True)
				xbmc_helper.log_debug('IP API Response is : ' + dumps(ip_api_response))
				if ip_api_response is not None and ip_api_response != '' and 'countryCode' in ip_api_response.keys():
					if ip_api_response['countryCode'] in CONST['COUNTRIES'].keys():
						config.update({'country' : ip_api_response['countryCode']})
					else:
						xbmc_helper.dialog_settings(
								xbmc_helper.translation('MSG_COUNTRY_INVALID').format(compat._encode(ip_api_response.get('country', 'Unknown')))
						)
						exit(0)

			else:
				for supported_country_key, supported_country in CONST['COUNTRIES'].items():
					if supported_country['setting_id'] == county_setting:
						config.update({'country' : supported_country_key})
						break

			if config['country'] is None:
				xbmc_helper.dialog_settings(xbmc_helper.translation('MSG_COUNTRY_NOT_DETECTED'))
				exit(0)
			main_js_src = None
			for match in findall('<script type="text/javascript" src="(.*?)"></script>', html_content):
				if match.find('/main') is not -1:
					main_js_src = CONST['BASE_URL'] + match
					main_js =  request_helper.get_url(main_js_src, config)
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

			config['PLAYER_CONFIG'] = request_helper.get_json_response(url=config['CONFIG']['SevenTV_player_config_url'], config=config)
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

			for psf_vars_index_name, psf_vars_index in CONST['PSF_VARS_IDX'].items():
				if len(config['PSF_VARS']) < psf_vars_index or config['PSF_VARS'][psf_vars_index] is '' :
					xbmc_helper.notification(
							xbmc_helper.translation('ERROR').format('PSF VAR'),
							xbmc_helper.translation('MSG_CONFIG_VALUES_INCOMPLETE').format('PSF VAR: ' + psf_vars_index_name)
						)
					xbmc_helper.log_error('Could not extract psf var ' + psf_vars_index_name + ' from js url  ' + CONST['PSF_URL'] + ' compete list : ' + dumps(config['PSF_VARS']))
					exit(0)

			if (cached_config is not None and
			    cached_config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']] == config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']] and
			    cached_config['PLAYER_CONFIG']['toolkit']['psf'] == config['PLAYER_CONFIG']['toolkit']['psf']):
				config['PSF_CLIENT_CONFIG'] = cached_config['PSF_CLIENT_CONFIG']
			else:
				try:
					config['PSF_CLIENT_CONFIG'] = loads(
									compat._decode(
										b64decode(
											lib_joyn.decrypt(
												lib_joyn.uc_string_to_long_array(config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']]),
												lib_joyn.uc_string_to_long_array(
													lib_joyn.uc_slices_to_string(
														lib_joyn.uc_slice(config['PLAYER_CONFIG']['toolkit']['psf'])
													)
												)
											)
										)
									)
								)

				except Exception as e:
					xbmc_helper.notification(
							xbmc_helper.translation('ERROR').format('Decrypt'),
							xbmc_helper.translation('MSG_ERROR_CONFIG_DECRYPTION'),
					)
					xbmc_helper.log_error('Could not decrypt config - Exception: ' + str(e) + ' PSF VARS: '  \
						+ dumps(config['PSF_VARS']) + 'PLAYER CONFIG: ' + dumps(config['PLAYER_CONFIG']))
					exit(0)

			cache.set_json('CONFIG', config)

		return config


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
