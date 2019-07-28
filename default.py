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
	from urllib2 import build_opener, HTTPCookieProcessor, Request, urlopen  # Python 2.X
	from urlparse import urljoin, urlparse, urlunparse , urlsplit, parse_qs # Python 2.X
elif PY3:
	from urllib.parse import quote, unquote, quote_plus, unquote_plus, urlencode, urljoin, urlparse, urlunparse, urlsplit, parse_qs  # Python 3+
	from urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen  # Python 3+
import json
import xbmcvfs
import shutil
import socket
import time
from datetime import datetime, timedelta
import io
import gzip
import ssl
import base64
import hashlib
from bs4 import BeautifulSoup
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

				  },

	'CACHE_DIR'		: 'cache',
	'TEMP_DIR'		: 'tmp',

	'CONFIG_CACHE_FILE'	: 'config.json',
	'CONFIG_CACHE_EXPIRES'	: 3600,
	'INPUTSTREAM_ADDON'	: 'inputstream.adaptive'

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
	xbmc.log("["+addon.getAddonInfo('id')+"-"+addon.getAddonInfo('version')+"]"+msg, level)


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

	except Exception as e:
		failing('Failed to load url: ' + url + ' headers: ' + json.dumps(additional_headers) + ' qs: ' + json.dumps(additional_query_string) + ' post_data: ' +  json.dumps(post_data) + 'Exception: ' +  str(e))
		pass

	opener.close()

	return response_content

def post_json(url, data=None, additional_headers=None, additional_query_string=None):
	if additional_headers is None:
		additional_headers = [('Content-Type', 'application/json')]
	else:
		additional_headers.append(('Content-Type', 'application/json'))

	return get_json_response(url, additional_headers, additional_query_string, json.dumps(data))

def get_json_response(url, headers=None, params=None, post_data=None):
	return json.loads(get_url(url, headers, params, post_data))


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

def get_config():
	global config, CONST, addon

	cached_config_path = get_xbmc_file_path(CONST['CACHE_DIR'], CONST['CONFIG_CACHE_FILE'])

	recreate_config = True
	config = {}

	if os.path.exists(cached_config_path):
		expire_config_mins = addon.getSetting("configcachemins")
		if expire_config_mins is not '':
			expire_secs = int(expire_config_mins) * 60
		else:
			expire_secs = CONST['CONFIG_CACHE_EXPIRES']

		expire_time = datetime.now() - timedelta(seconds=expire_secs)
		filetime = datetime.fromtimestamp(os.path.getctime(cached_config_path))

		if filetime >= expire_time:
			debug('get_config(): Use Cache: ' + cached_config_path)
			with open(cached_config_path) as cached_config_infile:
				try:
					config = json.load(cached_config_infile)
					recreate_config = False
				except ValueError:
					log('Could not load cached config ' + cached_config_path + ' ... recreating it')
					pass

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


		js_sources=BeautifulSoup(get_url(CONST['BASE_URL']),'html.parser').findAll('script',{'src':True})

		for js_source in js_sources:
			if 'main' in js_source['src']:
				main_js =  get_url(CONST['BASE_URL'] + js_source['src'])
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
		psf_vars = psf_vars[(start+len(find_str)):(start+length)].split(",")
		for i in range(len(psf_vars)):
			psf_vars[i] = psf_vars[i][1:-1]
		config['PSF_VARS'] = psf_vars

		try:
			config['PSF_CLIENT_CONFIG'] = json.loads(py3_dec(base64.b64decode(decrypt(uc_string_to_long_array(config['PSF_VARS'][CONST['PSF_VARS_IDX']['SECRET']]),uc_string_to_long_array(uc_slices_to_string(uc_slice(config['PLAYER_CONFIG']['toolkit']['psf'])))))))

		except Exception as e:
			failing('Could not decrypt config: ' + str(e))
			sys.exit(0)


		with open (cached_config_path, 'w') as cached_config_outfile:
			json.dump(config,cached_config_outfile)

	return config

def get_json_by_type(type, replacements={}):
	global CONST

	valued_query_params = {}

	for key, value in CONST['PATH'][type]['QUERY_PARAMS'].items():
		if re.search('^##(.)+##$', value) is not None:
			key = value[2:-2]
			if (key in replacements.keys()):
				value = replacements[key]
		valued_query_params.update({key : value})

	valued_query_params.update({'selection' : CONST['PATH'][type]['SELECTION']})

	return get_joyn_json_response(url=CONST['MIDDLEWARE_URL'] + CONST['PATH'][type]['PATH'] , params=valued_query_params)


def get_video_listitem(video_data,stream_type='VOD'):
	global xbmcgui, CONST, config, addon

	list_item = xbmcgui.ListItem()
	if (video_data['streamingFormat'] == 'dash'):
		if set_mpd_props(list_item, video_data['videoUrl'], stream_type) is not False:
			if 'drm' in video_data.keys() and video_data['drm'] == 'widevine' and 'licenseUrl' in video_data.keys():
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.license_type', 'com.widevine.alpha')
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.license_key', video_data['licenseUrl'] + '|' + get_header_string({'User-Agent' : config['USER_AGENT'], 'Content-Type': 'application/octet-stream'}) + '|R{SSM}|')
				list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.stream_headers',  get_header_string({'User-Agent' : config['USER_AGENT']}))
				if addon.getSetting("checkdrmcert") == 'true' and 'certificateUrl' in video_data.keys():
					list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.server_certificate', video_data['certificateUrl'] + '|' +  get_header_string({'User-Agent' : config['USER_AGENT']}))
		else:
			failing('Could not get valid MPD')

	else:
		return list_item.setPath(path=video_data['videoUrl'] + '|' + get_header_string({'User-Agent' : config['USER_AGENT']}) )

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
		mpd_contents = get_url(new_mpd_url)

		if len(mpd_contents) > 0:
			try:
				test_mpd_tree = ET.fromstring(mpd_contents)
				test_mpd_tree_ns = '{' + test_mpd_tree.tag.split('}')[0].strip('{') + '}'

				if test_mpd_tree is not None and test_mpd_tree.tag is not None and test_mpd_tree.tag == test_mpd_tree_ns + 'MPD':

					mpd_tree = test_mpd_tree
					mpd_tree_ns = test_mpd_tree_ns
					url = new_mpd_url

			except Exception as e:
				log('Could not parse filter stripped mpd with url: ' + new_mpd_url + ' Exception: ' + str(e))
				pass
	if mpd_tree is None:
		mpd_contents = get_url(url)
		if len(mpd_contents) > 0:
			try:
				test_mpd_tree = ET.fromstring(mpd_contents)
				test_mpd_tree_ns = ns = '{' + test_mpd_tree.tag.split('}')[0].strip('{') + '}'

				if test_mpd_tree is not None and test_mpd_tree.tag is not None and test_mpd_tree.tag == test_mpd_tree_ns + 'MPD':
					mpd_tree = test_mpd_tree
					mpd_tree_ns = test_mpd_tree_ns

			except Exception as e:
				failing('Could not parse orginal mpd with url: ' + url + ' Exception: ' + str(e))

	if mpd_tree is not None and mpd_tree_ns is not None:

		list_item.setProperty('inputstreamaddon', CONST['INPUTSTREAM_ADDON'])
		list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.manifest_type', 'mpd')

		if stream_type == 'LIVE':
			list_item.setProperty(CONST['INPUTSTREAM_ADDON'] + '.manifest_update_parameter', 'full')

		toplevel_base_url = ''
		top_level_base_url_element = mpd_tree.find('./' + mpd_tree_ns + 'BaseURL')

		# the mpd has a Base URL at toplevel at a remote location
		# inputstream adaptive currently can't handle this correctly
		# it's known that this Base URL can be used to retrieve a 'better' mpd
		if top_level_base_url_element is not None and top_level_base_url_element.text.find('http') == 0:
				debug("Found MPD with Base URL at toplevel : " + top_level_base_url_element.tag + " ==> " + top_level_base_url_element.text)
				if top_level_base_url_element.text.find('http') == 0:
					toplevel_base_url =  top_level_base_url_element.text

		if len(toplevel_base_url) :
			if stream_type == 'VOD':
				new_mpd_url = toplevel_base_url + '.mpd?filter='
				new_mpd_contents = get_url(new_mpd_url)
				if len(new_mpd_contents) > 0:
					try:
						new_mpd_tree = ET.fromstring(new_mpd_contents)
						new_mpd_tree_ns = '{' + new_mpd_tree.tag.split('}')[0].strip('{') + '}'
						if new_mpd_tree.tag is not None and new_mpd_tree.tag == new_mpd_tree_ns + 'MPD':
							log('Replacing MPD url ' + url + ' with ' + new_mpd_url)
							mpd_tree = new_mpd_tree
							mpd_tree_ns = new_mpd_tree_ns
							url = new_mpd_url
							toplevel_base_url = ''
							mpd_contents = new_mpd_contents
							top_level_base_url_element = mpd_tree.find('./' + mpd_tree_ns + 'BaseURL')
							if top_level_base_url_element is not None and top_level_base_url_element.text.find('http') == 0:
								debug("Found MPD with Base URL at toplevel in REPLACED url: " + top_level_base_url_element.tag + " ==> " + top_level_base_url_element.text + 'URL: ' + new_mpd_url)
								toplevel_base_url =  top_level_base_url_element.text
					except Exception as e:
						log('Could not parse BaseURL extracted mpd with url: ' + new_mpd_url + 'Exception: ' + str(e))
						pass

			elif stream_type == 'LIVE':
				period_base_url =  mpd_tree.find('./' + mpd_tree_ns + 'Period/' + mpd_tree_ns + 'BaseURL')
				if period_base_url is not None and period_base_url.text[0] == '/' and period_base_url.text[-1] == '/':
					new_mpd_url = toplevel_base_url + period_base_url.text + 'cenc-default.mpd'

					new_mpd_contents = get_url(new_mpd_url)
					if len(new_mpd_contents) > 0:
						try:
							new_mpd_tree = ET.fromstring(new_mpd_contents)
							new_mpd_tree_ns = '{' + new_mpd_tree.tag.split('}')[0].strip('{') + '}'
							if new_mpd_tree.tag is not None and new_mpd_tree.tag == new_mpd_tree_ns + 'MPD':
								log('Replacing MPD url ' + url + ' with ' + new_mpd_url)
								mpd_tree = new_mpd_tree
								mpd_tree_ns = new_mpd_tree_ns
								url = new_mpd_url
								toplevel_base_url = ''
								mpd_contents = new_mpd_contents
								top_level_base_url_element = mpd_tree.find('./' + mpd_tree_ns + 'BaseURL')
								if top_level_base_url_element is not None and top_level_base_url_element.text.find('http') == 0:
									debug("Found MPD with Base URL at toplevel in REPLACED url: " + top_level_base_url_element.tag + " ==> " + top_level_base_url_element.text + 'URL: ' + new_mpd_url)
									toplevel_base_url =  top_level_base_url_element.text

						except Exception as e:
							log('Could not parse BaseURL extracted mpd with url: ' + new_mpd_url + 'Exception: ' + str(e))
							pass

		if toplevel_base_url is not '' :
			debug("Writing MPD file to local disc, since it has a remote top Level Base URL ...")
			sha_1 = hashlib.sha1()
			sha_1.update(url)
		        sha_output = sha_1.hexdigest()
			mpd_filepath = get_xbmc_file_path(CONST['TEMP_DIR'],  get_sha_output + '.mpd')

			with open (mpd_filepath, 'w') as mpd_filepath_out:
				mpd_filepath_out.write(mpd_contents)

			log('Local MPD filepath is: ' + mpd_filepath)
			list_item.setPath(mpd_filepath)

		else:
			list_item.setPath( url + '|' + get_header_string({'User-Agent' : config['USER_AGENT']}))

		return True

	return False

def index():
	global pluginhandle

	add_dir(name='VOD', desc='Video on demand', mode='channels', stream_type='VOD')
	add_dir(name='Live', desc='Live TV', mode='channels',stream_type='LIVE')
	xbmcplugin.endOfDirectory(pluginhandle)

def channels(stream_type):
	global config

	if stream_type == 'VOD':
		brands = get_json_by_type('BRAND')
		for brand in brands['data']:
			channel_id = str(brand['channelId'])
			desc = ''
			name = ''
			img = ''
			for metadata_lang, metadata in brand['metadata'].items():
				if metadata_lang == 'de':
					if metadata['hasVodContent'] == True:
						for description in metadata['descriptions']:
							if description['type'] == 'seo':
								desc = description['text']
								break
						for title in metadata['titles']:
							if title['type'] == 'main':
								name = title['text']
								break
						for image in metadata['images']:
							if image['type'] == 'BRAND_LOGO':
								img = image['url'] + '/' + CONST['PATH']['BRAND']['IMG_PROFILE']
								break
						debug('ADD CHANNEL: name=' + name + ', mode=\'tvhshow\', stream_type=' + stream_type + ', channel_id=' + channel_id + ', img=' + img + ', desc=' + desc)
						add_dir(name=name, mode='tvshows', stream_type=stream_type, channel_id=channel_id, img=img, desc=desc)
		xbmcplugin.endOfDirectory(pluginhandle)
	elif stream_type == 'LIVE':
		brands = get_json_by_type('BRAND')

		for brand in brands['data']:
			for metadata_lang, metadata in brand['metadata'].items():
				if metadata_lang == 'de':
					if 'livestreams' in metadata.keys():
						for livestream in metadata['livestreams']:
							stream_id = livestream['streamId']
							img = ''
							name = ''
							for title in metadata['titles']:
								if title['type'] == 'main':
									name = title['text']
									break
							for image in metadata['images']:
								if image['type'] == 'BRAND_LOGO':
									img = image['url'] + '/' + CONST['PATH']['BRAND']['IMG_PROFILE']
							debug('ADD LIVETV: name=' + name + ', mode=\'play_video\' img=' + img + ', video_id=' + stream_id)
							add_link(name=name, mode='play_video', video_id=stream_id, iconimage=img, stream_type='LIVE')

		xbmcplugin.endOfDirectory(pluginhandle)

	else:
		index()

def tvshows(channel_id, stream_type):
	global config, CONST

	if stream_type == 'VOD':
		tvshows = get_json_by_type('TVSHOW', {'channelId': channel_id})
		for tvshow in tvshows['data']:

			tv_show_id = str(tvshow['id'])
			desc = ''
			name = ''
			img = ''

			for metadata_lang, metadata in tvshow['metadata'].items():
				if metadata_lang == 'de':
					for description in metadata['descriptions']:
						if description['type'] == 'main':
							desc = description['text']
							break
					for title in metadata['titles']:
						if title['type'] == 'main':
							name = title['text']
							break
					for image in metadata['images']:

						if image['type'] == 'PRIMARY':
							img = image['url'] + '/' + CONST['PATH']['TVSHOW']['IMG_PROFILE']
							break
				debug('ADD TVSHOW: name=' + name + ', mode=\'tvhshow\', stream_type=' + stream_type + ', tv_show_id=' + tv_show_id + ', img=' + img + ', desc=' + desc)
				add_dir(name=name, mode='season', tv_show_id=tv_show_id, img=img, desc=desc)
		xbmcplugin.endOfDirectory(pluginhandle)
	else:
		index()

def season(tv_show_id):
	global config, CONST
	seasons = get_json_by_type('SEASON', {'tvShowId' : tv_show_id})
	for season in seasons['data']:
		season_id = season['id']
		title = ''
		img = ''
		desc = ''
		for season_metadata_lang, season_metadata_values in season['metadata'].items():
			if season_metadata_lang == 'de':
				for season_metadata_image in season_metadata_values['images']:
					if season_metadata_image['type'] == 'PRIMARY':
						img = season_metadata_image['url'] + '/' + CONST['PATH']['SEASON']['IMG_PROFILE']
						break
				for season_metadata_title in season_metadata_values['titles']:
					if season_metadata_title['type'] == 'main':
						title = season_metadata_title['text']
						break
				for season_metadata_description in season_metadata_values['descriptions']:
					if season_metadata_description['type'] == 'main':
						desc = season_metadata_description['text']
						break
		debug ('id: ' + season_id + '\n' + 'img: ' + img + '\n' + 'title: ' + title + '\n' + 'desc: ' + desc)

		add_dir(name=title, mode='video', season_id=season_id, tv_show_id=tv_show_id, img=img, desc=desc)

	xbmcplugin.endOfDirectory(pluginhandle)

def video(tv_show_id, season_id):
	global config, CONST

	debug('video : tv_show_id: ' + tv_show_id + 'season_id: ' + season_id)
	videos = get_json_by_type('VIDEO', {'tvShowId' : tv_show_id, 'seasonId' : season_id})

	for video in videos['data']:
		video_id = video['id']
		title = ''
		img = ''
		desc = ''
		genres = []
		season = ''
		series = ''
		episode = ''
		aired = ''
		duration = ''

		for metadata_lang, metadata_values in video['metadata'].items():
			if metadata_lang == 'de':
				for metadata_image in metadata_values['images']:
					if metadata_image['type'] == 'PRIMARY':
						img = metadata_image['url'] + '/' + CONST['PATH']['VIDEO']['IMG_PROFILE']
						break
				for metadata_title in metadata_values['titles']:
					if metadata_title['type'] == 'main':
						title = metadata_title['text']
						break
				for metadata_description in metadata_values['descriptions']:
					if metadata_description['type'] == 'main':
						desc = metadata_description['text']
						break
				if 'broadcastDate' in metadata_values.keys():
					aired = datetime.utcfromtimestamp(metadata_values['broadcastDate']).strftime('%Y-%m-%d')

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

		debug ('ADD VIDEO: video_id: ' + video_id  + ' img: ' + img + ' title: ' + title + ' desc: ' + desc + ' genres: ' + json.dumps(genres) + ' season: ' + season + ' series: ' + series + ' episode: ' + episode + ' aired: ' + aired + ' duration: ' + str(duration))
		add_link(name=title, mode='play_video', video_id=video_id, iconimage=img, duration=duration, desc=desc, genre=genres,  staffel=season, episode=episode, serie=series, aired=aired)

	xbmcplugin.endOfDirectory(pluginhandle)

def play_video(video_id, stream_type='VOD'):
	global config, CONST,pluginhandle
	debug('play_video: video_id: ' + video_id)

	entitlement_request_data = {
		'access_id' 	: config['PSF_CLIENT_CONFIG']['accessId'],
		'content_id' 	: video_id,
		'content_type'	: stream_type,
	}

	headers = [
			('x-api-key', config['PSF_CONFIG']['default'][stream_type.lower()]['apiGatewayKey']),
	]

	entitlement_data = post_json(config['PSF_CONFIG']['default'][stream_type.lower()]['entitlementBaseUrl'] + CONST['ENTITLEMENT_URL'], entitlement_request_data, headers)
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

def add_dir(name, mode, desc='', img='', fanart='', channel_id='', tv_show_id='', season_id='', video_id='', stream_type=''):
	global xbmcgui, xbmcplugin,pluginhandle

	url = sys.argv[0]+'?'
	url += urlencode({
		'mode' : mode,
		'tv_show_id': tv_show_id,
		'season_id' : season_id,
		'video_id': video_id,
		'stream_type': stream_type,
		'channel_id': channel_id,
	})

	list_item = xbmcgui.ListItem(name)
	list_item.addAvailableArtwork(url=img,art_type='thumb',cache=img)
	list_item.setArt({ 'thumb': img})

	list_item.setInfo(type="Video", infoLabels={"Title": name, "Plot": desc})
	if fanart is not '':
		list_item.setArt({'fanart': fanart})
	elif img is not '':
		list_item.setArt({'fanart': img})
	else:
		list_item.setArt({'fanart': defaultFanart})

	return xbmcplugin.addDirectoryItem(handle=pluginhandle, url=url, listitem=list_item, isFolder=True)


def add_link(name, mode, video_id, iconimage, duration="", desc="", genre="", staffel=-1, episode=-1, serie="", aired='', stream_type='VOD'):
	global xbmcgui, xbmcplugin, pluginhandle

	url = sys.argv[0]+'?'
	url += urlencode({
		'video_id': video_id,
		'mode' : mode,
		'stream_type': stream_type,
	})

	list_item = xbmcgui.ListItem(name, iconImage=icon, thumbnailImage=iconimage)
	if stream_type == 'LIVE':
		list_item.setInfo(type="Video", infoLabels={"Title": name + ' (LIVE)'})
	else:
		list_item.setInfo(type="Video", infoLabels={"Title": name, "Duration": duration, "Plot": desc, "Genre": genre, "Season": staffel, "Episode": episode, "TVShowTitle": serie, "Aired": aired, "mediatype": "episode"})
		list_item.addStreamInfo('Video', {'Duration': duration})
	if iconimage != icon:
		list_item.setArt({'fanart': iconimage})
	else:
		list_item.setArt({'fanart': defaultFanart})

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


pluginhandle = int(sys.argv[1])
addon = xbmcaddon.Addon()
addonPath = xbmc.translatePath(addon.getAddonInfo('path')).encode('utf-8').decode('utf-8')
icon = os.path.join(addonPath, 'icon.png')
defaultFanart = os.path.join(addonPath, 'fanart.jpg')
xbmcplugin.setContent(pluginhandle, 'tvshows')

if not  addon_enabled(CONST['INPUTSTREAM_ADDON']):
        dialog = xbmcgui.Dialog()
        dialog.notification("Inputstream nicht aktiviert", 'Inputstream nicht aktiviert', xbmcgui.NOTIFICATION_ERROR)
        sys.exit(0)

is_helper = Helper('mpd', drm='widevine')
if not is_helper.check_inputstream():
	dialog = xbmcgui.Dialog()
	dialog.notification("Widevine nicht gefunden", 'Ohne Widevine kann das Addon nicht verwendet werden.', xbmcgui.NOTIFICATION_ERROR)
	sys.exit(0)

config = get_config()
params = dict( (k, v if len(v)>1 else v[0] )
           for k, v in parse_qs(sys.argv[2][1:]).iteritems() )
param_keys = params.keys()

if 'mode' in param_keys:
	mode = params['mode']

	if 'stream_type' in param_keys:
		stream_type = params['stream_type']
	else:
		stream_type = 'VOD'

	if mode == 'channel' and 'path' in param_keys:
		channel(params['path'])
	elif mode == 'season' and 'tv_show_id' in param_keys:
		season(params['tv_show_id'])
	elif mode == 'video' and 'tv_show_id' in param_keys and 'season_id' in param_keys:
		video(params['tv_show_id'],params['season_id'])
	elif mode == 'play_video' and 'video_id' in param_keys:
		play_video(params['video_id'], stream_type)
	elif mode == 'channels':
		channels(stream_type)
	elif mode == 'tvshows' and 'channel_id' in param_keys:
		tvshows(params['channel_id'], stream_type)
	else:
		index()
else:
	index()
