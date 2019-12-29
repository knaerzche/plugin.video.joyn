# -*- coding: utf-8 -*-

from xbmc import getCondVisibility
from sys import exit
from copy import deepcopy
from base64 import b64decode
from re import findall
from ..const import CONST
from ..xbmc_helper import xbmc_helper
from .. import compat
from .. import cache
from .. import request_helper

if compat.PY2:
	try:
		from simplejson import loads
	except ImportError:
		from json import loads
elif compat.PY3:
	from json import loads


def create_config(cached_config, addon_version):
	xbmc_helper().log_debug('get_config(): create config')
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
		config['USER_AGENT'] = compat._format(
		        'Mozilla/5.0 (Linux; Android {}; {} Build/{} AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.73 Mobile Safari/537.36)',
		        xbmc_helper().get_android_prop('ro.build.version.release', True) or '8.1.0',
		        xbmc_helper().get_android_prop('ro.product.model', True) or 'Nexus 6P Build',
		        xbmc_helper().get_android_prop('ro.build.id', True) or 'OPM6.171019.030.B1')
		config['IS_ANDROID'] = True

	# linux on arm uses widevine from chromeos
	elif os_uname[0] == 'Linux' and os_uname[4].lower().find('arm') is not -1:
		config['USER_AGENT'] = compat._format(
		        'Mozilla/5.0 (X11; CrOS {}) 12105.100.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.144 Safari/537.36',
		        os_uname[4])
		config['IS_ARM'] = True
	elif os_uname[0] == 'Linux':
		config['USER_AGENT'] = compat._format(
		        'Mozilla/5.0 (X11; Linux {}) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/78.0.3904.70 Safari/537.36',
		        os_uname[4])
	elif os_uname[0] == 'Darwin':
		config['USER_AGENT'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36'
	else:
		config['USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36'

	html_content = request_helper.get_url(CONST['BASE_URL'], config)
	if html_content is None or html_content is '':
		xbmc_helper().notification(compat._format(xbmc_helper().translation('ERROR'), 'Url access'),
		                           compat._format(xbmc_helper().translation('MSG_NO_ACCESS_TO_URL'), CONST['BASE_URL']))
		exit(0)

	county_setting = xbmc_helper().get_setting('country')
	xbmc_helper().log_debug('COUNTRY SETTING: {}', county_setting)
	try:
		ip_api_response = request_helper.get_json_response(url=compat._format(CONST['IP_API_URL'],
		                                                                      xbmc_helper().translation('LANG_CODE')),
		                                                   config=config,
		                                                   silent=True)

	except Exception as e:
		xbmc_helper().log_debug('ip-api request failed - {}', e)
		ip_api_response = {
		        'status': 'success',
		        'country': 'Deutschland',
		        'countryCode': 'DE',
		}
	config.update({'actual_country': ip_api_response.get('countryCode', 'DE')})

	if county_setting is '' or county_setting is '0':
		xbmc_helper().log_debug('IP API Response is: {}', ip_api_response)
		if config.get('actual_country', 'DE') in CONST['COUNTRIES'].keys():
			config.update({'country': config.get('actual_country', 'DE')})
		else:
			xbmc_helper().dialog_action(
			        compat._format(xbmc_helper().translation('MSG_COUNTRY_INVALID'), ip_api_response.get('country', 'DE')))
			exit(0)

	else:
		for supported_country_key, supported_country in CONST['COUNTRIES'].items():
			if supported_country['setting_id'] == county_setting:
				config.update({'country': supported_country_key})
				break

	if config['country'] is None:
		xbmc_helper().dialog_action(xbmc_helper().translation('MSG_COUNTRY_NOT_DETECTED'))
		exit(0)

	if config['country'] != config['actual_country']:

		from random import choice

		try:
			from ipaddress import IPv4Network
		except ImportError:
			from ..external.ipaddress import IPv4Network

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
		xbmc_helper().log_debug('Using local main.js')
		main_js = xbmc_helper().get_file_contents(xbmc_helper().get_resource_filepath('main.js', 'external'))

	for key in config['CONFIG']:
		find_str = key + ':"'
		start = main_js.find(find_str)
		length = main_js[start:].find('",')
		config['CONFIG'][key] = main_js[(start + len(find_str)):(start + length)]

	for essential_config_item_key, essential_config_item in config['CONFIG'].items():
		if essential_config_item is None or essential_config_item is '':
			use_outdated_cached_config = True
			xbmc_helper().log_error('Could not extract configuration value from js: KEY{} JS source {} ', essential_config_item_key,
			                        main_js_src)
			break

	if use_outdated_cached_config is False:
		config['GRAPHQL_HEADERS'] = [('x-api-key', config['CONFIG']['API_GW_API_KEY']),
		                             ('joyn-platform', xbmc_helper().get_text_setting('joyn_platform'))]

		config['CLIENT_NAME'] = xbmc_helper().get_text_setting('joyn_platform')

	if use_outdated_cached_config is False:
		config['PLAYER_CONFIG'] = request_helper.get_json_response(url=config['CONFIG']['PLAYERCONFIG_URL'], config=config)
		if config['PLAYER_CONFIG'] is None:
			use_outdated_cached_config = True
			xbmc_helper().log_error('Could not load player config from url {}', config['CONFIG']['SevenTV_player_config_url'])

	if use_outdated_cached_config is False:
		config['PSF_CONFIG'] = request_helper.get_json_response(url=CONST['PSF_CONFIG_URL'], config=config)
		if config['PSF_CONFIG'] is None:
			use_outdated_cached_config = True
			xbmc_helper().log_error('Could not load psf config from url  {}', CONST['PSF_CONFIG_URL'])

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
			xbmc_helper().log_debug('Trying to reuse psf secret index from cached config: {}', cached_config['SECRET_INDEX'])
			decrypted_psf_client_config = decrypt_psf_client_config(config['PSF_VARS'][cached_config['SECRET_INDEX']],
			                                                        config['PLAYER_CONFIG']['toolkit']['psf'])
			if decrypted_psf_client_config is not None:
				config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
				config['SECRET'] = config['PSF_VARS'][cached_config['SECRET_INDEX']]
				config['SECRET_INDEX'] = cached_config['SECRET_INDEX']
				xbmc_helper().log_debug('Reusing psf secret index from cached config succeeded')
			else:
				xbmc_helper().log_debug('Reusing psf secret index from cached config failed')

		if config.get('PSF_CLIENT_CONFIG', None) is None and len(config['PSF_VARS']) >= CONST['PSF_VAR_DEFS']['SECRET']['INDEX']:
			decrypted_psf_client_config = decrypt_psf_client_config(config['PSF_VARS'][CONST['PSF_VAR_DEFS']['SECRET']['INDEX']],
			                                                        config['PLAYER_CONFIG']['toolkit']['psf'])
			if decrypted_psf_client_config is not None:
				config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
				config['SECRET'] = config['PSF_VARS'][CONST['PSF_VAR_DEFS']['SECRET']['INDEX']]
			else:
				xbmc_helper().log_debug('Could not decrypt psf client config with psf var index from CONST')

		if config.get('PSF_CLIENT_CONFIG', None) is None:
			index_before = index_after = index_secret = None
			for index, value in enumerate(config['PSF_VARS']):
				if value == CONST['PSF_VAR_DEFS']['SECRET']['VAL_BEFORE']:
					index_before = index
				if value == CONST['PSF_VAR_DEFS']['SECRET']['VAL_AFTER']:
					index_after = index
				if index_before is not None and index_after is not None and index_after == (index_before + 2):
					index_secret = index_before + 1
					decrypted_psf_client_config = decrypt_psf_client_config(config['PSF_VARS'][index_secret],
					                                                        config['PLAYER_CONFIG']['toolkit']['psf'])
					if decrypted_psf_client_config is not None:
						config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
						config['SECRET'] = config['PSF_VARS'][index_secret]
						config['SECRET_INDEX'] = index_secret
						xbmc_helper().log_debug('PSF client config decryption succeded with new index: {}', index_secret)
						break

		if config.get('PSF_CLIENT_CONFIG', None) is None:
			xbmc_helper().log_debug('Could not find a new valid secret from psf vars ... using fallback value')
			decrypted_psf_client_config = decrypt_psf_client_config(CONST['PSF_VAR_DEFS']['SECRET']['FALLBACK'],
			                                                        config['PLAYER_CONFIG']['toolkit']['psf'])
			if decrypted_psf_client_config is not None:
				xbmc_helper().log_debug('PSF client config decryption succeded with fallback value')
				config['SECRET'] = CONST['PSF_VAR_DEFS']['SECRET']['FALLBACK']
				config['PSF_CLIENT_CONFIG'] = decrypted_psf_client_config
			else:
				use_outdated_cached_config = True
				xbmc_helper().log_error('Could not decrypt config - PSF VARS: {} PLAYER CONFIG {}', config['PSF_VARS'],
				                        config['PLAYER_CONFIG'])

	if use_outdated_cached_config is True:
		if cached_config is not None and isinstance(cached_config, dict) and 'PSF_CLIENT_CONFIG' in cached_config.keys():
			xbmc_helper().log_notice('!!!Using outdated cached config - from addon version {} !!!',
			                         cached_config.get('ADDON_VERSION', '[UNKNOWN]'))
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
			xbmc_helper().log_error('Configuration could not be extracted and no valid cached config exists. Giving Up!')
			xbmc_helper().notification(compat._format(xbmc_helper().translation('ERROR'), ''),
			                           compat._format(xbmc_helper().translation('MSG_CONFIG_VALUES_INCOMPLETE'), ''))
			exit(0)
	else:
		cache.set_json('CONFIG', config)

	return config


def decrypt_psf_client_config(secret, encrypted_psf_config):

	try:
		decrypted_psf_config = loads(
		        compat._decode(
		                b64decode(
		                        decrypt(uc_string_to_long_array(secret),
		                                uc_string_to_long_array(uc_slices_to_string(uc_slice(encrypted_psf_config)))))))
	except Exception as e:
		xbmc_helper().log_debug('Could not decrypt psf config - Exception: {}', e)
		pass
		return None

	return decrypted_psf_config


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


def uc_slices_to_string(uc_slices):
	uc_string = compat._encode('')

	for codepoint in uc_slices:
		uc_string += compat._unichr(codepoint)

	return uc_string


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
