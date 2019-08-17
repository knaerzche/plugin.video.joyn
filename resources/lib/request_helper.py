#!/usr/bin/python
# -*- coding: utf-8 -*-

import resources.lib.compat as compat

if compat.PY2:
	from urllib import quote, urlencode
	from urllib2 import Request, urlopen
elif compat.PY3:
	from urllib.parse import quote, urlencode
	from urllib.request import Request, urlopen

from json import dumps, loads
from base64 import urlsafe_b64encode
from io import BytesIO
from gzip import GzipFile
import resources.lib.xbmc_helper as xbmc_helper


def get_url(url, config, additional_headers=None, additional_query_string=None, post_data=None):

	response_content = ''
	xbmc_helper.log_debug('get_url - url: ' + str(url) + ' headers: ' + dumps(additional_headers) + ' qs: ' + dumps(additional_query_string) + ' post_data: ' +  dumps(post_data))

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
			request = Request(url, data=post_data.encode('utf-8'), headers=headers)
		else:
			request = Request(url, headers=headers)

		response = urlopen(request, timeout=40)

		if response.info().get('Content-Encoding') == 'gzip':
			response_content =  compat._decode(GzipFile(fileobj=BytesIO(response.read())).read())
		else:
			response_content = compat._decode(response.read())

	except Exception as e:

		xbmc_helper.log_error('Failed to load url: ' + url + ' headers: ' + dumps(additional_headers) + ' qs: ' + dumps(additional_query_string) + ' post_data: '
			+  dumps(post_data) + 'Exception: ' +  str(e))
		pass

	return response_content


def post_json(url, config, data=None, additional_headers=None, additional_query_string=None):
	if additional_headers is None:
		additional_headers = [('Content-Type', 'application/json')]
	else:
		additional_headers.append(('Content-Type', 'application/json'))

	return get_json_response(url, config, additional_headers, additional_query_string, dumps(data))


def get_json_response(url, config, headers=None, params=None, post_data=None, silent=False):
	try:
		return loads(get_url(url, config, headers, params, post_data))
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

	if uri.startswith('http'):
		return uri + '|' + get_header_string({'User-Agent' : user_agent})
	return uri
