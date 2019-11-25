# -*- coding: utf-8 -*-

from . import compat as compat

if compat.PY2:
	from urllib import quote, urlencode
	from urllib2 import Request, urlopen, HTTPError, ProxyHandler, build_opener, install_opener
elif compat.PY3:
	from urllib.parse import quote, urlencode
	from urllib.request import Request, urlopen, ProxyHandler, build_opener, install_opener
	from urllib.error import HTTPError

from base64 import urlsafe_b64encode
from io import BytesIO
from gzip import GzipFile
from sys import exit
from time import time
from hashlib import sha512
from datetime import datetime, timedelta
from . import xbmc_helper as xbmc_helper
from . import cache as cache
from xbmcaddon import Addon

try:
	from simplejson import loads, dumps
except ImportError:
	from json import loads, dumps

def get_url(url, config, additional_headers=None, additional_query_string=None, post_data=None, fail_silent=False, no_cache=False):

	response_content = ''
	xbmc_helper.log_debug('get_url - url: ' + str(url) + ' headers: ' + dumps(additional_headers) + ' qs: ' + dumps(additional_query_string) + ' post_data: ' +  dumps(post_data))

	request_hash = sha512((url+dumps(additional_headers)+dumps(additional_query_string)+dumps(post_data)).encode('utf-8')).hexdigest()

	if no_cache is True:
		etags_data = None
	else:
		etags_data = get_etags_data(request_hash)

	try:

		headers = {
			'Accept-Encoding': 'gzip, deflate',
			'User-Agent': config['USER_AGENT'],
			'Accept': '*/*',
		}

		if additional_headers is not None:
			headers.update(additional_headers)

		if config.get('http_headers', None) is not None:
			headers.update(config.get('http_headers', []))

		if etags_data is not None:
			headers.update({'If-None-Match': etags_data['etag']})

		if additional_query_string is not None:

			if url.find('?') is not -1:
				url += '&' + urlencode(additional_query_string)
			else:
				url += '?' + urlencode(additional_query_string)

		if xbmc_helper.get_bool_setting('use_https_proxy') is True and xbmc_helper.get_text_setting('https_proxy_host') != '' \
				and xbmc_helper.get_int_setting('https_proxy_port') != 0:

			proxy_uri = '{}:{}'.format(xbmc_helper.get_text_setting('https_proxy_host'), xbmc_helper.get_text_setting('https_proxy_port'))

			xbmc_helper.log_debug('Using proxy uri: ' + proxy_uri)
			prxy_handler=ProxyHandler({
						'http': proxy_uri,
						'https': proxy_uri,
				})
			install_opener(build_opener(prxy_handler))

		if post_data is not None:
			request = Request(url, data=post_data.encode('utf-8'), headers=headers)
		else:
			request = Request(url, headers=headers)

		response = urlopen(request, timeout=40)

		if response.info().get('Content-Encoding') == 'gzip':
			response_content =  compat._decode(GzipFile(fileobj=BytesIO(response.read())).read())
		else:
			response_content = compat._decode(response.read())

		_etag = response.info().get('etag', None)
		if no_cache is False and _etag is not None:
			xbmc_helper.log_debug('ETAG: ' + str(_etag) + ' URL: ' + str(url))
			set_etags_data(request_hash, _etag, response_content)

	except HTTPError as http_error:

		if http_error.code == 422:
			xbmc_helper.notification(
				'',
				xbmc_helper.translation('MSG_VIDEO_UNAVAILABLE'),
				Addon().getAddonInfo('icon')
			)
			pass
			exit(0)
		elif http_error.code == 304 and etags_data is not None:
			response_content = etags_data.get('data')
		else:
			raise
	except Exception as e:

		xbmc_helper.log_error('Failed to load url: ' + url + ' headers: ' + dumps(additional_headers) + ' qs: ' + dumps(additional_query_string) + ' post_data: '
			+  dumps(post_data) + 'Exception: ' +  str(e))

		if fail_silent is True:
			pass
		else:
			xbmc_helper.notification(
						xbmc_helper.translation('ERROR').format('URL Access'),
						xbmc_helper.translation('MSG_NO_ACCESS_TO_URL').format(str(url))
					)
			exit(0)

	return response_content


def post_json(url, config, data=None, additional_headers=[], additional_query_string=None):

	additional_headers.append(('Content-Type', 'application/json'))
	return get_json_response(url, config, additional_headers, additional_query_string, dumps(data))


def get_json_response(url, config, headers=[], params=None, post_data=None, silent=False, no_cache=False):
	try:

		headers.append(('Accept', 'application/json'))
		return loads(get_url(url, config, headers, params, post_data, silent, no_cache))

	except ValueError:
		if silent is False:
			xbmc_helper.notification(
				xbmc_helper.translation('ERROR').format('Decoding'),
				xbmc_helper.translation('MSG_ERR_TRY_AGAIN')
			)
			raise
		else:
			pass
	return None


def get_header_string(headers):

	header_string = ''
	for header_key, header_value in headers.items():
		header_string += '&' + quote(header_key) + '=' + quote(header_value)

	return header_string[1:]


def base64_encode_urlsafe(string):

	if compat.PY2:
		encoded = urlsafe_b64encode(string)
		return encoded.rstrip(b'=').encode('utf-8').decode('utf-8')
	else:
		return urlsafe_b64encode(string.encode('utf-8')).decode('utf-8')


def add_user_agend_header_string(uri, user_agent):

	if uri.startswith('http') and uri.find('|User-Agent') == -1:
		return uri + '|' + get_header_string({'User-Agent': user_agent})
	return uri

def get_etags_data(request_hash):

	etags_data = cache.get_json('ETAGS').get('data')
	if etags_data is None:
		etags_data = {}

	etag_data = etags_data.get(request_hash, None)
	if etag_data is not None:
		etags_data[request_hash].update({'access': int(time())})
		cache.set_json('ETAGS', etags_data)
		data = cache._get('ETAGS', request_hash + '.etag').get('data', None)
		if data is not None:
			etag_data.update({'data': data})
			return etag_data
	return None

def set_etags_data(request_hash, etag, data):

	etags_data = cache.get_json('ETAGS').get('data', {})
	if etags_data is None:
		etags_data = {}

	etags_data.update({
		request_hash: {
				'etag': etag,
				'access': int(time())
			}
		})
	cache._set('ETAGS', request_hash + '.etag', data)
	cache.set_json('ETAGS', etags_data)

def purge_etags_cache(ttl):

	etags_ttl = datetime.now() - timedelta(seconds=ttl)
	xbmc_helper.log_debug('Removing etags older than: ' + str(etags_ttl))

	etags_data = cache.get_json('ETAGS').get('data')
	if etags_data is not None:
		for request_hash, etag_data in etags_data.items():
			if xbmc_helper.timestamp_to_datetime(etag_data.get('access', 0)) <= etags_ttl:
				xbmc_helper.log_debug('Removing etags hash: ' + str(request_hash))
				cache._remove('ETAGS', request_hash  + '.etag')
				del etags_data[request_hash]
