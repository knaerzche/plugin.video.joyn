#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import platform
import re
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY2:
	from urllib import quote, unquote, quote_plus, unquote_plus, urlencode  # Python 2.X
	from urllib2 import build_opener, Request, urlopen  # Python 2.X
	from urlparse import urljoin, urlparse, urlunparse , urlsplit, parse_qs # Python 2.X
elif PY3:
	from urllib.parse import quote, unquote, quote_plus, unquote_plus, urlencode, urljoin, urlparse, urlunparse, urlsplit, parse_qs  # Python 3+
	from urllib.request import build_opener, Request, urlopen  # Python 3+
import json
import xbmcvfs
import time
from datetime import datetime, timedelta
import io
import gzip
import ssl
import base64
import hashlib
import xml.etree.ElementTree as ET
from math import floor
from inputstreamhelper import Helper

try:
	_create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
	pass
else:
	ssl._create_default_https_context = _create_unverified_https_context

CONST = {
	'BASE_URL' 		: 'https://www.joyn.de',
	'PSF_CONFIG_URL'	: 'https://psf.player.v0.maxdome.cloud/config/psf.json',
	'PSF_URL'		: 'https://psf.player.v0.maxdome.cloud/dist/playback-source-fetcher.min.js',
	'MIDDLEWARE_URL'	: 'https://middleware.p7s1.io/joyn/v1/',
	'ENTITLEMENT_URL'	: 'entitlement-token/anonymous',
	'PSF_VARS_IDX'		: {
					'SECRET' : 1184
				  },

	'PATH'			: {

					'SEASON'	: {
								'PATH'	      	: 	'seasons',
								'QUERY_PARAMS' 	: 	{	'tvShowId' 		: '##tvShowId##',
												'sortBy'   		: 'seasonsOrder',
												'sortAscending'		: 'true',

											},
								'SELECTION'	:	'{data{id,channelId,visibilities,duration,metadata{de}}}',
								'IMG_PROFILE'	:	'profile:original',
							  },

					'VIDEO'		: {
								'PATH'	      	: 	'videos',
								'QUERY_PARAMS' 	: 	{	'tvShowId' 		: '##tvShowId##',
												'seasonId'   		: '##seasonId##',
												'sortBy'		: 'seasonsOrder',
												'sortAscending'		: 'true',
												'skip'			: '0',
											},
								'SELECTION'	:	'{totalCount,data{id,type,startTime,endTime,agofCode,path(context:"web", region:"de", type:"cmsPath"){path},tvShow,season,episode,duration,metadata{de},visibilities{endsAt}}}',
								'IMG_PROFILE'	:	'profile:original',
							  } ,

					'BRAND'		: {
								'PATH'		:	'brands',
								'QUERY_PARAMS' 	: 	{},
								'SELECTION'	:	'{data{id,channelId,agofCodes,metadata{de}}}',
								'IMG_PROFILE'	:	'profile:original',
							  },

					'TVSHOW'	: {
								'PATH'		:	'tvshows',
								'QUERY_PARAMS' 	: 	{
												'channelId'		: '##channelId##',
												'limit'			: '250',
												'skip'			: '0',
											},
								'SELECTION'	:	'{totalCount,data{id,type,startTime,endTime,metadata{de{ageRatings,copyrights ,numberOfSeasons,seasons,id,genres,images{type,url,accentColors},seo,channelObject{classIdentifier,bundleId},type,bundleId,classIdentifier,titles,descriptions}},baseUrl,path(context:"web", region:"de", type:"cmsPath"),brand,channelId,tvShow,season,episode,status}}',
								'IMG_PROFILE'	:	'profile:original',

							  },
					'EPG'		: {
								'PATH'		: 'epg',
								'QUERY_PARAMS'	: {
											'skip'	 	: '0',
											'from'	 	: '##from##',
											'to'	 	: '##to##',
											'sortBy' 	: 'startTime',
											'sortAscending'	: 'true',
											'limit'		: '5000',
										  },
								'SELECTION'	: '{totalCount,data{id,title,description,tvShow,type,tvChannelName,channelId,startTime,endTime,video,images(subType:"cover"){url,subType}}}',
								'IMG_PROFILE'	: 'profile:original',
							  },
					'FETCH'		: {	'PATH'		: 'fetch/',
								'QUERY_PARAMS'	: {},
								'SELECTION'	: '{data{id,visibilities, channelId ,agofCodes,duration,metadata{de}}}',
								'IMG_PROFILE'	: 'profile:original',
							  },

				  },
	'EPG'			: {
					'REQUEST_HOURS'		: 12,
					'REQUEST_OFFSET_HOURS'	: 2,
				  },
	'TEXT_TEMPLATES'	: {
					'LIVETV_TITLE'		: '[B]{:s}[/B] - {:s}',
					'LIVETV_UNTIL'		: '[CR]bis {:%H:%M} Uhr[CR][CR]',
					'LIVETV_UNTIL_AND_NEXT'	: '[CR]bis {:%H:%M} Uhr, danach {:s}[CR][CR]',
				 },

	'CACHE_DIR'		: 'cache',
	'TEMP_DIR'		: 'tmp',
	'CACHE'			: {
					'CONFIG'	: { 'key' : 'config', 'expires' : 3600 },
					'EPG'		: { 'key' : 'epg', 'expires': 28800 },
					'BRANDS'	: { 'key' : 'brands', 'expires' : 36000 },
				  },

	'INPUTSTREAM_ADDON'	: 'inputstream.adaptive',

}

def py2_enc(s, encoding='utf-8'):
	if PY2 and isinstance(s, unicode):
		s = s.encode(encoding)
	return s

def py2_uni(s, encoding='utf-8'):
	if PY2 and isinstance(s, str):
		s = unicode(s, encoding)
	return s

def py3_dec(d, encoding='utf-8'):
	if PY3 and isinstance(d, bytes):
		d = d.decode(encoding)
	return d

def _unichr(char):
	if PY2:
		return unichr(char)
	else:
		return chr(char)

def get_os_uname_list():
	if PY3:
		return list(platform.uname())
	else:
		return platform.uname()

def translation(id):
	LANGUAGE = addon.getLocalizedString(id)
	LANGUAGE = py2_enc(LANGUAGE)
	return LANGUAGE

def failing(content):
	log(content, xbmc.LOGERROR)

def debug(content):
	log(content, xbmc.LOGDEBUG)

def log(msg, level=xbmc.LOGNOTICE):
	msg = py2_enc(msg)
	xbmc.log('['+addon.getAddonInfo('id')+'-'+addon.getAddonInfo('version')+']'+msg, level)

def get_url(url, additional_headers=None, additional_query_string=None, post_data=None):

	response_content = ''
	opener = build_opener()
	debug('get_url - url: ' + url + ' headers: ' + json.dumps(additional_headers) + ' qs: ' + json.dumps(additional_query_string) + ' post_data: ' +  json.dumps(post_data))

	try:
		headers = {
			'Accept-Encoding' : 'gzip, deflate',
			'User-Agent' : config['USER_AGENT'],
		}

		if additional_headers is not None:
			headers.update(additional_headers)

		if additional_query_string is not None:

			if url.find('?') is not -1:
				url += '&' + urlencode(additional_query_string)
			else:
				url += '?' + urlencode(additional_query_string)

		if post_data is not None:
			request = Request(url, data=post_data, headers=headers)
		else:
			request = Request(url, headers=headers)

		response = opener.open(request, timeout=40)

		if response.info().get('Content-Encoding') == 'gzip':
			response_content =  py3_dec(gzip.GzipFile(fileobj=io.BytesIO(response.read())).read())
		else:
			response_content = py3_dec(response.read())
		opener.close()

	except Exception as e:

		failing('Failed to load url: ' + url + ' headers: ' + json.dumps(additional_headers) + ' qs: ' + json.dumps(additional_query_string) + ' post_data: '
			+  json.dumps(post_data) + 'Exception: ' +  str(e))
		pass

	return response_content

def post_json(url, data=None, additional_headers=None, additional_query_string=None):
	if additional_headers is None:
		additional_headers = [('Content-Type', 'application/json')]
	else:
		additional_headers.append(('Content-Type', 'application/json'))

	return get_json_response(url, additional_headers, additional_query_string, json.dumps(data))

def get_json_response(url, headers=None, params=None, post_data=None):
	try:
		return json.loads(get_url(url, headers, params, post_data))
	except ValueError:
		failing('Could not decode json from url ' + url)
		raise
	return None

def get_header_string(headers):
	header_string = ''
	for header_key, header_value in headers.items():
		header_string += '&' + quote(header_key) + '=' + quote(header_value)

	return header_string[1:]

def base64_encode_urlsafe(string):
    encoded = base64.urlsafe_b64encode(string)
    return encoded.rstrip(b'=')

def get_joyn_json_response(url, headers=None, params=None):
	if headers is not None:
		headers.append(('key', config['CONFIG']['header_7TV_key']))
	else:
		headers = [('key', config['CONFIG']['header_7TV_key'])]

	decoded_json = get_json_response(url, headers, params)
	if decoded_json[py2_uni('status')] == 200:
		return decoded_json[py2_uni('response')]
	else:
		return None

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
	ret = u''
	for i in range(length):
		ret+= _unichr(value[i] & 255)
		ret+= _unichr(value[i] >> 8 & 255)
		ret+= _unichr(value[i] >> 16 & 255)
		ret+= _unichr(value[i] >> 24 & 255)

	return ret[0:n]

def uc_slice(hex_string, start_pos=None, end_pos=None):
	unit8s = []
	res = []

	for hex_val in re.findall('..',hex_string):
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

def uc_slices_to_string(uc_slices):
	uc_string = u''

	for codepoint in uc_slices:
		uc_string += _unichr(codepoint)

	return uc_string

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

def build_signature(video_id, encoded_client_data, entitlement_token):
	global config, CONST

	sha_input = video_id + ','
	sha_input += entitlement_token + ','
	sha_input += encoded_client_data

	for char in re.findall('.',config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']]):
		sha_input += hex(ord(char))[2:]

	sha_1 = hashlib.sha1()
	sha_1.update(sha_input)
	sha_output = sha_1.hexdigest()

	return sha_output

def get_mpd_tree(url):
	mpd_contents = get_url(url);
	if len(mpd_contents) > 0:
		try:
			mpd_tree = ET.fromstring(mpd_contents)
			mpd_tree_ns = '{' + mpd_tree.tag.split('}')[0].strip('{') + '}'
			if mpd_tree is not None and mpd_tree.tag is not None and mpd_tree.tag == mpd_tree_ns + 'MPD':
				return {'tree' : mpd_tree, 'ns': mpd_tree_ns}
		except Exception as e:
			debug('Could not parse mpd with url: ' + url + ' Exception: ' + str(e))
			pass
	return None

def query_mpd_tree(mpd_tree, query_path):
	query = '.'
	for query_param in query_path:
		query += '/' + mpd_tree['ns'] +  query_param

	try:
		mpd_element = mpd_tree['tree'].find(query);
		if mpd_element is not None:
			return mpd_element.text
	except Exception as e:
		debug('Could not query mpd - Exception: ' + str(e))
		pass

	return None

def get_cache(cache_name, override_expire_secs=None):

	cache_path = get_xbmc_file_path(CONST['CACHE_DIR'], CONST['CACHE'][cache_name]['key'] + '.json')

	if (override_expire_secs is not None):
		expire_datetime = datetime.now() - timedelta(seconds=override_expire_secs)
	else:
		expire_datetime = datetime.now() - timedelta(seconds=CONST['CACHE'][cache_name]['expires'])

	res = {
		'data': None,
		'is_expired' : True,
	};

	if os.path.exists(cache_path):
		if platform.system() == 'Windows':
			filetime = datetime.fromtimestamp(os.path.getctime(cache_path))
		else:
			filetime = datetime.fromtimestamp(os.path.getmtime(cache_path))

		with open(cache_path) as cache_infile:
				try:
					res['data'] = json.load(cache_infile)
				except ValueError:
					log('Could decode file from cache: ' + cache_path )
					pass

		if filetime >= expire_datetime:
			res['is_expired'] = False

	return res;

def set_cache(cache_name, data):

	cache_path = get_xbmc_file_path(CONST['CACHE_DIR'], CONST['CACHE'][cache_name]['key'] + '.json')

	with open (cache_path, 'w') as cache_outfile:
			json.dump(data,cache_outfile)

def get_config():
	global config, CONST, addon


	recreate_config = True
	config = {}
	cached_config = None

	expire_config_mins = addon.getSetting('configcachemins')
	if expire_config_mins is not '':
		confg_cache_res = get_cache('CONFIG', (int(expire_config_mins) * 60))
	else:
		confg_cache_res = get_cache('CONFIG')

	if confg_cache_res['data'] is not None:
		cached_config =  confg_cache_res['data']

	if confg_cache_res['is_expired'] is False:
		recreate_config = False;
		config = cached_config;

	if recreate_config == True:
		debug('get_config(): create config')
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

		}

		os_uname = get_os_uname_list()
		#android
		if os_uname[0] == 'Linux' and 'KODI_ANDROID_LIBS' in os.environ:
			config['USER_AGENT'] = 'Mozilla/5.0 (Linux Android 8.1.0 Nexus 6P Build/OPM6.171019.030.B1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.91 Mobile Safari/537.36'
			config['IS_ANDROID'] = True
		# linux on arm uses widevine from chromeos
		elif os_uname[0] == 'Linux' and os_uname[4].lower().find('arm') is not -1:
			config['USER_AGENT'] = 'Mozilla/5.0 (X11 CrOS '+  os_uname[4] + ' 4537.56.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.38 Safari/537.36'
		elif os_uname[0] == 'Linux':
			config['USER_AGENT'] = 'Mozilla/5.0 (X11 Linux ' + os_uname[4] + ') AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
		else:
			config['USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0 Win64 x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'

		html_content = get_url(CONST['BASE_URL']);
		for match in re.findall('<script type="text/javascript" src="(.*?)"></script>', html_content):
			if match.find('/main') is not -1:
				main_js =  get_url(CONST['BASE_URL'] + match)
				for key in config['CONFIG']:
					find_str = key + ':"'
					start = main_js.find(find_str)
					length = main_js[start:].find('",')
					config['CONFIG'][key] = main_js[(start+len(find_str)):(start+length)]

		if config['CONFIG']['SevenTV_player_config_url'] is not None:
			config['PLAYER_CONFIG'] = get_json_response(url=config['CONFIG']['SevenTV_player_config_url'])

		config['PSF_CONFIG'] =  get_json_response(url=CONST['PSF_CONFIG_URL'])

		psf_vars = get_url(CONST['PSF_URL'])
		find_str = 'call(this,['
		start = psf_vars.find(find_str + '"exports')
		length = psf_vars[start:].rfind('])')
		psf_vars = psf_vars[(start+len(find_str)):(start+length)].split(',')
		for i in range(len(psf_vars)):
			psf_vars[i] = psf_vars[i][1:-1]
		config['PSF_VARS'] = psf_vars

		if (cached_config is not None and
		    cached_config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']] == config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']] and
	            cached_config['PLAYER_CONFIG']['toolkit']['psf'] == config['PLAYER_CONFIG']['toolkit']['psf']):
			config['PSF_CLIENT_CONFIG'] = cached_config['PSF_CLIENT_CONFIG']
		else:
			try:
				config['PSF_CLIENT_CONFIG'] = json.loads(py3_dec(base64.b64decode(decrypt(uc_string_to_long_array(config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']]),uc_string_to_long_array(uc_slices_to_string(uc_slice(config['PLAYER_CONFIG']['toolkit']['psf'])))))))

			except Exception as e:
				failing('Could not decrypt config: ' + str(e))
				sys.exit(0)

		set_cache('CONFIG', config)

	return config

def get_json_by_type(type, replacements={}, additional_params={}, url_annex=''):
	global CONST

	valued_query_params = {}

	if 'search' not in additional_params.keys():
		for key, value in CONST['PATH'][type]['QUERY_PARAMS'].items():
			if re.search('^##(.)+##$', value) is not None:
				key = value[2:-2]
				if (key in replacements.keys()):
					value = replacements[key]
			valued_query_params.update({key : value})

	valued_query_params.update({'selection' : CONST['PATH'][type]['SELECTION']})
	valued_query_params.update(additional_params)

	return get_joyn_json_response(url=CONST['MIDDLEWARE_URL'] + CONST['PATH'][type]['PATH'] + url_annex , params=valued_query_params)

def get_video_listitem(video_data,stream_type='VOD'):
	global xbmcgui, CONST, config, addon

	list_item = xbmcgui.ListItem()
	if (video_data['streamingFormat'] == 'dash'):
		if set_mpd_props(list_item, video_data['videoUrl'], stream_type) is not False:
			if 'drm' in video_data.keys() and video_data['drm'] == 'widevine' and 'licenseUrl' in video_data.keys():
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.license_type', 'com.widevine.alpha')
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.license_key', video_data['licenseUrl'] + '|' +
					get_header_string({'User-Agent' : config['USER_AGENT'], 'Content-Type': 'application/octet-stream'}) + '|R{SSM}|')
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.stream_headers',  get_header_string({'User-Agent' : config['USER_AGENT']}))
				if addon.getSetting('checkdrmcert') == 'true' and 'certificateUrl' in video_data.keys():
					list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.server_certificate', video_data['certificateUrl'] + '|'
						+  get_header_string({'User-Agent' : config['USER_AGENT']}))
		else:
			failing('Could not get valid MPD')

	else:
		return list_item.setPath(path=video_data['videoUrl'] + '|' + get_header_string({'User-Agent' : config['USER_AGENT']}))

	return list_item

def set_mpd_props(list_item, url, stream_type='VOD'):
	global CONST, config, addon

	debug('get_mpd_path : ' + url + 'stream_type: ' + stream_type)
	mpd_tree = None
	mpd_tree_ns = None

	##strip out the filter parameter
	parts = urlparse(url)
	query_dict = parse_qs(parts.query)

	if 'filter' in query_dict.keys():
		query_dict.update({'filter' : ''})
		new_parts = list(parts)
		new_parts[4] = urlencode(query_dict)
		new_mpd_url = urlunparse(new_parts)
		debug('Stripped out filter from mpd url is ' + new_mpd_url)
		test_mpd_tree = get_mpd_tree(new_mpd_url)
		if test_mpd_tree is not None:
			mpd_tree = test_mpd_tree
			url = new_mpd_url

	if mpd_tree is None:
		test_mpd_tree = get_mpd_tree(url);
		if test_mpd_tree is not None:
			mpd_tree = test_mpd_tree;

	if mpd_tree is not None:

		list_item.setProperty('inputstreamaddon', CONST['INPUTSTREAM_ADDON'])
		list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.manifest_type', 'mpd')

		if stream_type == 'LIVE':
			list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.manifest_update_parameter', 'full')

		toplevel_base_url = None

		# the mpd has a Base URL at toplevel at a remote location
		# inputstream adaptive currently can't handle this correctly
		# it's known that this Base URL can be used to retrieve a 'better' mpd
		toplevel_base_url_res = query_mpd_tree(mpd_tree, ['BaseURL'])
		if toplevel_base_url_res is not None and toplevel_base_url_res.find('http') == 0:
			debug('Found MPD with Base URL at toplevel : ' + toplevel_base_url_res)
			toplevel_base_url =  toplevel_base_url_res

		if toplevel_base_url is not None :
			if stream_type == 'VOD':
				new_mpd_url = toplevel_base_url + '.mpd?filter='
				test_mpd_tree = get_mpd_tree(new_mpd_url);
				if test_mpd_tree is not None:
					mpd_tree = test_mpd_tree
					url = new_mpd_url
					toplevel_base_url = None
					toplevel_base_url_res = query_mpd_tree(mpd_tree, ['BaseURL'])
					if toplevel_base_url_res is not None and toplevel_base_url_res.find('http') == 0:
						debug('Found MPD with Base URL at toplevel in REPLACED url: ' + toplevel_base_url_res + 'URL: ' + new_mpd_url)
						toplevel_base_url =  toplevel_base_url_res
					else:
						toplevel_base_url = None
			elif stream_type == 'LIVE':
				period_base_url_res = query_mpd_tree(mpd_tree, ['Period','BaseURL']);
				if period_base_url_res is not None and period_base_url_res[0] == '/' and period_base_url_res[-1] == '/':
					new_mpd_url = toplevel_base_url + period_base_url_res + 'cenc-default.mpd'
					test_mpd_tree = get_mpd_tree(new_mpd_url);
					if test_mpd_tree is not None:
						mpd_tree = test_mpd_tree
						url = new_mpd_url
						toplevel_base_url = None
						toplevel_base_url_res = query_mpd_tree(mpd_tree, ['BaseURL'])
						if toplevel_base_url_res is not None and toplevel_base_url_res.find('http') == 0:
							debug('Found MPD with Base URL at toplevel in REPLACED url: ' + toplevel_base_url_res + 'URL: ' + new_mpd_url)
							toplevel_base_url =  toplevel_base_url_res
						else:
							toplevel_base_url = None

		if toplevel_base_url is not None :
			mpd_contents = get_url(url)
			debug('Writing MPD file to local disc, since it has a remote top Level Base URL ...')
			sha_1 = hashlib.sha1()
			sha_1.update(url)

			mpd_filepath = get_xbmc_file_path(CONST['TEMP_DIR'],  sha_1.hexdigest() + '.mpd')
			with open (mpd_filepath, 'w') as mpd_filepath_out:
				mpd_filepath_out.write(mpd_contents)

			log('Local MPD filepath is: ' + mpd_filepath)
			list_item.setPath(mpd_filepath)

		else:
			list_item.setPath( url + '|' + get_header_string({'User-Agent' : config['USER_AGENT']}))

		return True

	return False

def extract_metadata(metadata, selection_type, img_type='PRIMARY', description_type='main', title_type='main', fanart_type=''):
	extracted_metadata = {
		'img'   : '',
		'title' : '',
		'description' : '',
		'fanart': '',
	};

	if 'descriptions' in metadata.keys():
		for description in metadata['descriptions']:
			if description['type'] == description_type:
				extracted_metadata.update({'description' : description['text']})
				break
	if 'titles' in metadata.keys():
		for title in metadata['titles']:
			if title['type'] == title_type:
				extracted_metadata.update({'title' : title['text']})
				break
	if 'images' in metadata.keys():
		for image in metadata['images']:
			if image['type'] == img_type:
				extracted_metadata.update({'img' : image['url'] + '/' + CONST['PATH'][selection_type]['IMG_PROFILE']})
			if image['type'] == fanart_type:
				extracted_metadata.update({'fanart' : image['url'] + '/' + CONST['PATH'][selection_type]['IMG_PROFILE']})

	return extracted_metadata


def extract_metadata_from_epg(epg_channel_data):
	extracted_metadata = {};

	for idx, program_data in enumerate(epg_channel_data):
		endTime = datetime.fromtimestamp(program_data['endTime'])
		if  endTime > datetime.now():
			extracted_metadata['title'] = py2_uni(CONST['TEXT_TEMPLATES']['LIVETV_TITLE']).format(program_data['tvChannelName'], program_data['tvShow']['title'])

			if len(epg_channel_data) > (idx+2):
				extracted_metadata['description'] = py2_uni(CONST['TEXT_TEMPLATES']['LIVETV_UNTIL_AND_NEXT']).format(endTime,epg_channel_data[idx+1]['tvShow']['title'])
			else:
				extracted_metadata['description'] = py2_uni(CONST['TEXT_TEMPLATES']['LIVETV_UNTIL']).format(endTime)

			if program_data['description'] is not None:
				extracted_metadata['description'] += program_data['description']

			for image in program_data['images']:
				if image['subType'] == 'cover':
					extracted_metadata['fanart'] = image['url'] + '/' + CONST['PATH']['EPG']['IMG_PROFILE']
			break

	return extracted_metadata;

def index():
	global pluginhandle

	add_dir(metadata={'title' : 'Mediatheken', 'description' : 'Mediatheken von www.joyn.de'}, mode='channels', stream_type='VOD')
	add_dir(metadata={'title' : 'Rubriken', 'description' : 'Mediatheken gruppiert in Rubriken'}, mode='categories', stream_type='VOD')
	add_dir(metadata={'title' : 'Suche', 'description' : 'Suche in den Mediatheken'}, mode='search')
	add_dir(metadata={'title' : 'Live TV', 'description' : 'Live TV'}, mode='channels',stream_type='LIVE')

	xbmcplugin.endOfDirectory(pluginhandle)

def get_epg():

	epg = {}

	raw_epg = get_json_by_type('EPG',{
			'from' : (datetime.now() - timedelta(hours=CONST['EPG']['REQUEST_OFFSET_HOURS'])).strftime('%Y-%m-%d %H:%M:00'),
			'to': (datetime.now() + timedelta(hours=CONST['EPG']['REQUEST_HOURS'])).strftime('%Y-%m-%d %H:%M:00')}
		);

	for raw_epg_data in raw_epg['data']:
		raw_epg_data['channelId'] = str(raw_epg_data['channelId'])
		if raw_epg_data['channelId'] not in epg.keys():
			epg.update({raw_epg_data['channelId'] : []})
		epg[raw_epg_data['channelId']].append(raw_epg_data);

	return epg

def channels(stream_type):
	global config

	cached_brands = get_cache('BRANDS')
	if cached_brands['data'] is not None and cached_brands['is_expired'] is False:
		brands = cached_brands['data']
	else:
		brands = get_json_by_type('BRAND')
		set_cache('BRANDS', brands)

	if stream_type == 'LIVE':
		cached_epg =  get_cache('EPG')

		if cached_epg['data'] is not None and cached_epg['is_expired'] is False:
			epg = cached_epg['data']
		else:
			epg = get_epg()
			set_cache('EPG',epg)

	for brand in brands['data']:
		channel_id = str(brand['channelId'])
		for metadata_lang, metadata in brand['metadata'].items():
			if metadata_lang == 'de':
				extracted_metadata = extract_metadata(metadata=metadata, selection_type='BRAND',img_type='BRAND_LOGO', description_type='seo')
				if stream_type == 'VOD' and metadata['hasVodContent'] == True:
					add_dir(mode='tvshows', stream_type=stream_type, channel_id=channel_id,metadata=extracted_metadata)
				elif stream_type == 'LIVE' and 'livestreams' in metadata.keys():
					for livestream in metadata['livestreams']:
						stream_id = livestream['streamId']
						if channel_id in epg.keys():
							extracted_metadata.update(extract_metadata_from_epg(epg[channel_id]))

						add_link(metadata=extracted_metadata,mode='play_video', video_id=stream_id, stream_type='LIVE')
				break
	xbmcplugin.endOfDirectory(handle=pluginhandle,cacheToDisc=False)

def tvshows(channel_id, fanart_img):
	global config, CONST
	tvshows = get_json_by_type('TVSHOW', {'channelId': channel_id})

	for tvshow in tvshows['data']:
		tv_show_id = str(tvshow['id'])
		for metadata_lang, metadata in tvshow['metadata'].items():
			if metadata_lang == 'de':
				extracted_metadata = extract_metadata(metadata, 'TVSHOW')
				extracted_metadata.update({'fanart' : fanart_img});
				add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata)
	xbmcplugin.endOfDirectory(pluginhandle)

def season(tv_show_id, fanart_img):
	global config, CONST
	seasons = get_json_by_type('SEASON', {'tvShowId' : tv_show_id})
	for season in seasons['data']:
		season_id = season['id']
		for metadata_lang, metadata in season['metadata'].items():
			if metadata_lang == 'de':
				extracted_metadata = extract_metadata(metadata,'SEASON');
				extracted_metadata.update({'fanart' : fanart_img});
				extracted_metadata.update({'img' : fanart_img});
				add_dir(mode='video', season_id=season_id, tv_show_id=tv_show_id,metadata=extracted_metadata)
				break
	xbmcplugin.endOfDirectory(pluginhandle)

def video(tv_show_id, season_id, fanart_img):
	global config, CONST

	debug('video : tv_show_id: ' + tv_show_id + 'season_id: ' + season_id)
	videos = get_json_by_type('VIDEO', {'tvShowId' : tv_show_id, 'seasonId' : season_id})

	for video in videos['data']:
		video_id = video['id']
		genres = []
		season = ''
		series = ''
		episode = ''
		aired = ''
		duration = ''

		for metadata_lang, metadata_values in video['metadata'].items():
			if metadata_lang == 'de':
				extracted_metadata = extract_metadata(metadata=metadata_values,selection_type='VIDEO');
				extracted_metadata.update({'fanart' : fanart_img});
				if 'broadcastDate' in metadata_values.keys():
					aired = datetime.utcfromtimestamp(metadata_values['broadcastDate']).strftime('%Y-%m-%d')
				break

		if 'tvShow' in video.keys():
			if 'genres' in video['tvShow'].keys():
				for genre in video['tvShow']['genres']:
					genres.append(genre['title'])
			if 'titles' in video['tvShow'].keys():
				for title_key, title_value in video['tvShow']['titles'].items():
					if title_key == 'default':
						series = title_value
		if 'season' in video.keys():
			if 'titles' in video['season'].keys():
				for season_title_key, season_title_value in video['season']['titles'].items():
					if season_title_key == 'default':
						season = season_title_value
						break
		if 'episode' in video.keys():
			if 'number' in video['episode'].keys():
				episode = 'Episode ' + str(video['episode']['number'])
		if 'duration' in video.keys():
			duration = video['duration']/1000

		add_link(mode='play_video', metadata=extracted_metadata, video_id=video_id, duration=duration, genres=genres, season=season, episode=episode, series=series, aired=aired)

	xbmcplugin.endOfDirectory(pluginhandle)

def play_video(video_id, stream_type='VOD'):
	global config, CONST,pluginhandle
	debug('play_video: video_id: ' + video_id)

	entitlement_request_data = {
		'access_id' 	: config['PSF_CLIENT_CONFIG']['accessId'],
		'content_id' 	: video_id,
		'content_type'	: stream_type,
	}
	entitlement_request_headers = [('x-api-key', config['PSF_CONFIG']['default'][stream_type.lower()]['apiGatewayKey'])]

	entitlement_data = post_json(config['PSF_CONFIG']['default'][stream_type.lower()]['entitlementBaseUrl'] + CONST['ENTITLEMENT_URL'], entitlement_request_data, entitlement_request_headers)
	video_url = config['PSF_CONFIG']['default'][stream_type.lower()]['playoutBaseUrl']

	if stream_type == 'VOD':
		video_metadata = get_joyn_json_response(CONST['MIDDLEWARE_URL'] + 'metadata/video/' + video_id)

		client_data = {
				'startTime' 	: '0',
				'videoId' 	: video_metadata['tracking']['id'],
				'duration'	: video_metadata['tracking']['duration'],
				'brand'		: video_metadata['tracking']['channel'],
				'genre'		: video_metadata['tracking']['genres'],
				'tvshowid'	: video_metadata['tracking']['tvShow']['id'],
		}

		if 'agofCode' in video_metadata['tracking']:
			client_data.update({'agofCode' : video_metadata['tracking']['agofCode']})
		video_url += 'playout/video/' + video_metadata['tracking']['id']

	elif stream_type == 'LIVE':
		client_data = {
				'videoId' 	: None,
				'channelId'	: video_id,

		}

		video_url += 'playout/channel/' + video_id

	encoded_client_data = base64_encode_urlsafe(json.dumps(client_data))
	signature = build_signature(video_id, encoded_client_data, entitlement_data['entitlement_token'])

	video_url_params = {
		'entitlement_token'	: entitlement_data['entitlement_token'],
		'clientData'		: encoded_client_data,
		'sig'			: signature,
	}

	video_url += '?' + urlencode(video_url_params)
	video_response = get_json_response(url=video_url, headers=[('Content-Type', 'application/x-www-form-urlencoded charset=utf-8')], post_data='false')
	xbmcplugin.setResolvedUrl(pluginhandle, True, get_video_listitem(video_response, stream_type))

def search(stream_type='VOD'):

	dialog = xbmcgui.Dialog()
	search_term = dialog.input('Suche', type=xbmcgui.INPUT_ALPHANUM)

	if len(search_term) > 0:
		request_params = {'search': search_term.lower(), 'hasVodContent': 'true'}
		tvshows = get_json_by_type(type='TVSHOW',additional_params=request_params)
		if len(tvshows['data']) > 0:
			for tvshow in tvshows['data']:
				tv_show_id = str(tvshow['id'])
				if 'metadata' in tvshow.keys() and 'de' in tvshow['metadata'].keys():
					extracted_metadata = extract_metadata(metadata=tvshow['metadata']['de'], selection_type='TVSHOW')
					add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata)
			xbmcplugin.endOfDirectory(handle=pluginhandle)
		else:
			dialog = xbmcgui.Dialog()
			dialog.notification('Keine Ergebnisse', 'für "' + search_term + '" gefunden', icon)

def categories(stream_type='VOD'):

	cats = get_joyn_json_response(CONST['MIDDLEWARE_URL']  + 'ui?path=/')
	if 'blocks' in cats.keys():
		for block in cats['blocks']:
			if 'type' in block.keys() and 'configuration' in block.keys() and block['type'] == 'StandardLane':
				cat_name = block['configuration']['Headline']
				fetch_ids = []
				for block_item in block['items']:
					fetch_ids.append(block_item['fetch']['id'])
				add_dir('fetch_categories', {'title' : cat_name, 'description': ''}, fetch_ids=json.dumps(fetch_ids))

		xbmcplugin.endOfDirectory(handle=pluginhandle)

def fetch_categories(categories, stream_type='VOD'):

	for category in categories:
		category_data = get_json_by_type('FETCH', url_annex=category)
		for tvshow in category_data['data']:
			tv_show_id = str(tvshow['id'])
			if 'metadata' in tvshow.keys() and 'de' in tvshow['metadata'].keys():
				extracted_metadata = extract_metadata(metadata=tvshow['metadata']['de'], selection_type='TVSHOW')
				add_dir(mode='season', tv_show_id=tv_show_id, metadata=extracted_metadata)
	xbmcplugin.endOfDirectory(handle=pluginhandle)

def add_dir(mode, metadata, channel_id='', tv_show_id='', season_id='', video_id='', stream_type='', fetch_ids=''):
	global xbmcgui, xbmcplugin,pluginhandle, default_fanart, icon, pluginurl

	params = {
		'mode' : mode,
		'tv_show_id': tv_show_id,
		'season_id' : season_id,
		'video_id': video_id,
		'stream_type': stream_type,
		'channel_id': channel_id,
		'fetch_ids' : fetch_ids
	}

	list_item = xbmcgui.ListItem(metadata['title'])

	if 'img' in metadata and metadata['img'] is not '':
		list_item.setArt({ 'thumb': metadata['img']})
		params.update({'parent_img': metadata['img']});
	else:
		list_item.setArt({ 'thumb': icon})

	list_item.setInfo(type='Video', infoLabels={'Title': metadata['title'], 'Plot': metadata['description']})

	if 'fanart' in metadata and metadata['fanart'] is not '':
		list_item.setArt({'fanart': metadata['fanart']})
	else:
		list_item.setArt({'fanart': default_fanart})

	url = pluginurl+'?'
	url += urlencode(params)

	return xbmcplugin.addDirectoryItem(handle=pluginhandle, url=url, listitem=list_item, isFolder=True)

def add_link(mode, video_id, metadata, duration='', genres='', season='', episode='', series='', aired='', stream_type='VOD'):
	global xbmcgui, xbmcplugin, pluginhandle, pluginurl

	url = pluginurl+'?'
	url += urlencode({
		'video_id': video_id,
		'mode' : mode,
		'stream_type': stream_type,
	})

	list_item = xbmcgui.ListItem(metadata['title'], iconImage=icon, thumbnailImage= metadata['img'])

	if stream_type == 'LIVE':
		list_item.setInfo(type='Video', infoLabels={'Title': metadata['title'], 'Plot': metadata['description']})
	else:
		list_item.setInfo(type='Video',
			infoLabels={'Title': metadata['title'], 'Duration': duration, 'Plot': metadata['description'], 'Genre': genres, 'Season': season, 'Episode': episode,
				'TVShowTitle': series, 'Aired': aired, 'mediatype': 'episode'})
		list_item.addStreamInfo('Video', {'Duration': duration})
	if metadata['fanart'] != '':
		list_item.setArt({'fanart': metadata['fanart']})
	else:
		list_item.setArt({'fanart': default_fanart})

	list_item.setProperty('IsPlayable', 'True')

	return xbmcplugin.addDirectoryItem(handle=pluginhandle, url=url, listitem=list_item)

def get_xbmc_file_path(directory, filename):
	global addon

	xbmc_profile_path = xbmc.translatePath(addon.getAddonInfo('profile')).encode('utf-8').decode('utf-8')
	xbmc_directory = xbmc.translatePath(os.path.join(xbmc_profile_path, directory, '')).encode('utf-8').decode('utf-8')

	if not xbmcvfs.exists(xbmc_directory):
	  xbmcvfs.mkdirs(xbmc_directory)

	return os.path.join(xbmc_directory, filename)

def addon_enabled(addon_id):
	result = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","id":1,\
		"params":{"addonid":"%s", "properties": ["enabled"]}}' % addon_id)
	return False if '"error":' in result or '"enabled":false' in result else True

pluginurl = sys.argv[0]
pluginhandle = int(sys.argv[1])
pluginquery = sys.argv[2]
addon = xbmcaddon.Addon()
addon_path = xbmc.translatePath(addon.getAddonInfo('path')).encode('utf-8').decode('utf-8')
icon = addon.getAddonInfo('icon')
default_fanart = addon.getAddonInfo('fanart')
xbmcplugin.setContent(pluginhandle, 'tvshows')

if not  addon_enabled(CONST['INPUTSTREAM_ADDON']):
        dialog = xbmcgui.Dialog()
        dialog.notification('Inputstream nicht aktiviert', 'Inputstream nicht aktiviert', icon)
        sys.exit(0)

is_helper = Helper('mpd', drm='widevine')
if not is_helper.check_inputstream():
	dialog = xbmcgui.Dialog()
	dialog.notification('Widevine nicht gefunden', 'Ohne Widevine kann das Addon nicht verwendet werden.', icon)
	sys.exit(0)

config = get_config()
params = dict( (k, v if len(v)>1 else v[0] )
           for k, v in parse_qs(pluginquery[1:]).iteritems() )
param_keys = params.keys()

if 'mode' in param_keys:
	mode = params['mode']

	if 'stream_type' in param_keys:
		stream_type = params['stream_type']
	else:
		stream_type = 'VOD'
	if 'parent_img' in param_keys:
		parent_img = params['parent_img']
	else:
		parent_img = ''

	if mode == 'season' and 'tv_show_id' in param_keys:
		season(params['tv_show_id'],parent_img)
	elif mode == 'video' and 'tv_show_id' in param_keys and 'season_id' in param_keys:
		video(params['tv_show_id'],params['season_id'],parent_img)
	elif mode == 'play_video' and 'video_id' in param_keys:
		play_video(params['video_id'], stream_type)
	elif mode == 'channels':
		channels(stream_type)
	elif mode == 'tvshows' and 'channel_id' in param_keys:
		tvshows(params['channel_id'],parent_img)
	elif mode == 'search':
		search(stream_type)
	elif mode == 'categories':
		categories(stream_type)
	elif mode == 'fetch_categories' and 'fetch_ids' in param_keys:
		fetch_categories(json.loads(params['fetch_ids']), stream_type)
	else:
		index()
else:
	index()
