# -*- coding: utf-8 -*-

from hashlib import sha512
import xml.etree.ElementTree as ET
from io import BytesIO
from time import time
from . import request_helper as request_helper
from .xbmc_helper import xbmc_helper as xbmc_helper
from . import compat

if compat.PY2:
	from urlparse import urlparse
elif compat.PY3:
	from urllib.parse import urlparse


class mpd_parser(object):
	def __init__(self, url, config):

		self.mpd_url = None
		self.mpd_contents = None
		self.mpd_tree = None
		self.mpd_tree_ns = None
		self.mpd_tree_cenc_ns = None
		self.elementtree = ET
		self.mpd_filepath = None
		self.cp_urn_playready = '9A04F079-9840-4286-AB92-E65BE0885F95'
		self.cp_urn_widevine = 'EDEF8BA9-79D6-4ACE-A3C8-27DCD51D21E'
		self.supports_widevine = False
		self.supports_playready = False

		final_url, _mpd_contents = request_helper.get_url(url=url, config=config, no_cache=True, return_final_url=True)
		if final_url != url:
			xbmc_helper().log_debug('MPD: acutal URL does not match original URL - setting new url {}', final_url)
			self.mpd_url = final_url
		else:
			self.mpd_url = url

		mpd_in_mem_file = BytesIO(compat._bytes(_mpd_contents))

		if mpd_in_mem_file:
			namespaces = dict([node for _, node in self.elementtree.iterparse(mpd_in_mem_file, events=['start-ns'])])
			for ns in namespaces:
				if ns.startswith('ns') is False:
					self.elementtree.register_namespace(ns, namespaces[ns])
					if namespaces[ns].find('mpeg:dash:schema:mpd') != -1:
						self.mpd_tree_ns = compat._format('{{{}}}', namespaces[ns])
					elif namespaces[ns].find('mpeg:cenc') != -1:
						self.mpd_tree_cenc_ns = compat._format('{{{}}}', namespaces[ns])

			if self.elementtree is not None:
				self.mpd_tree = self.elementtree.fromstring(_mpd_contents)
				if self.mpd_tree.tag == compat._format('{}{}', self.mpd_tree_ns, 'MPD'):
					self.set_content_protection_props()

					return

		raise ValueError(compat._format('{} could not by parsed as an valid MPD', url))

	def set_content_protection_props(self):

		res_widevine = self.query(
		        'ContentProtection[@schemeIdUri="urn:uuid:' + self.cp_urn_playready + '"]', anywhere=True,
		        find_all=True) or self.query('ContentProtection[@schemeIdUri="urn:uuid:' + self.cp_urn_playready.lower() + '"]',
		                                     anywhere=True,
		                                     find_all=True)
		res_playready = self.query(
		        'ContentProtection[@schemeIdUri="urn:uuid:' + self.cp_urn_playready + '"]', anywhere=True,
		        find_all=True) or self.query('ContentProtection[@schemeIdUri="urn:uuid:' + self.cp_urn_playready.lower() + '"]',
		                                     anywhere=True,
		                                     find_all=True)
		if isinstance(res_widevine, list) and len(res_widevine) > 0:
			self.supports_widevine = True
		if isinstance(res_playready, list) and len(res_playready) > 0:
			self.supports_playready = True

	def query(self, query_path, find_all=False, anywhere=False):

		if isinstance(query_path, str):
			query_path = [query_path]

		query = '.'
		if anywhere is True and len(query_path) > 0:
			query += '/'

		for query_param in query_path:
			query += '/' + self.mpd_tree_ns + query_param

		try:
			if find_all is True:
				return self.mpd_tree.findall(query)
			else:
				return self.mpd_tree.find(query)
		except Exception as e:
			xbmc_helper().log('Could not query mpd - query: {} - Ex: {}', query, e)
			pass

		return None

	def query_node_value(self, query_path):

		query_element = self.query(query_path)
		if query_element is not None and query_element.text is not None:
			return query_element.text
		return None

	def get_toplevel_base_url(self):

		return self.query_node_value(['BaseURL'])

	@staticmethod
	def get_attrib(element, attribute_name):

		if isinstance(element, ET.Element):
			return element.attrib.get(attribute_name, None)
		return None

	def get_timeshift_buffer_secs(self):
		timeshift_buffer = mpd_parser.get_attrib(self.mpd_tree, 'timeShiftBufferDepth')
		if timeshift_buffer is not None:
			from re import match as re_match
			matches = re_match(r'PT(\d+)S', timeshift_buffer)
			if matches is not None and len(matches.groups()) == 1:
				return int(matches.group(1))
		return None

	def set_local_path(self, video_id):

		#check mpdtype
		mpd_type = mpd_parser.get_attrib(self.mpd_tree, 'type')

		if mpd_type is not None and mpd_type == 'dynamic':
			xbmc_helper().log_debug('MPD-Type is dynamic and therefore cannot be saved locally')
			return

		#check if mpd has an location tag
		location = self.query('Location')
		if location is not None:
			xbmc_helper().log_debug('MPD has a location-tag and therefore cannot be saved locally: {}', location.text)
			return

		cur_toplevel_baseurl = self.get_toplevel_base_url()
		xbmc_helper().log_debug('add_toplevel_base_url: {}', cur_toplevel_baseurl)
		if self.mpd_url.startswith('http'):
			parsed_mpd_url = urlparse(self.mpd_url)
			xbmc_helper().log_debug('add_toplevel_base_url -parsed  {}', parsed_mpd_url)
			new_base_url = compat._format('{}://{}{}/', parsed_mpd_url.scheme, parsed_mpd_url.netloc,
			                              '/'.join(parsed_mpd_url.path.split('/')[:-1]))

			#no toplevel BaseURL exists - add a new one
			if cur_toplevel_baseurl is None:
				base_url_node = self.elementtree.Element(compat._format('{}{}', self.mpd_tree_ns, 'BaseURL'))
				base_url_node.text = new_base_url

			if cur_toplevel_baseurl is None or not cur_toplevel_baseurl.startswith('http'):
				all_base_urls = self.query(['BaseURL'], find_all=True, anywhere=True)
				for _base_url_node in all_base_urls:
					_base_url_node_text = _base_url_node.text
					xbmc_helper().log_debug('found baseurl: {}', _base_url_node_text)
					# absoulute BaseURL
					if _base_url_node_text.startswith('/'):
						_base_url_node_text = compat._format('{}://{}{}', parsed_mpd_url.scheme, parsed_mpd_url.netloc, _base_url_node_text)
						xbmc_helper().log_debug('Replace it with: {}', _base_url_node_text)
						_base_url_node.text = _base_url_node_text
					# relative BaseURL
					elif not _base_url_node_text.startswith('http'):
						_base_url_node_text = compat._format('{}{}', new_base_url, _base_url_node_text)
						xbmc_helper().log_debug('Replace it with: {}', _base_url_node_text)
						_base_url_node.text = _base_url_node_text

			self.mpd_filepath = xbmc_helper().set_data(filename=compat._format('{}_{}.mpd.tmp',
			                                                                   sha512(str(time()).encode('utf-8')).hexdigest(),
			                                                                   str(video_id)),
			                                           data=self.elementtree.tostring(self.mpd_tree),
			                                           dir_type='TEMP_DIR')
			xbmc_helper().log_debug('Wrote local mpd file: {}', self.mpd_filepath)

		return
