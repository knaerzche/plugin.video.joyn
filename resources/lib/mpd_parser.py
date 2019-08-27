#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import request_helper as request_helper
from . import xbmc_helper as xbmc_helper
import xml.etree.ElementTree as ET

class mpd_parser:


	def __init__(self, url, config):

		self.mpd_url = None
		self.mpd_contents = None
		self.mpd_tree = None
		self.mpd_tree_ns = None

		_mpd_contents = request_helper.get_url(url, config);
		if len(_mpd_contents) > 0:
			_mpd_tree = ET.fromstring(_mpd_contents)
			if  _mpd_tree.tag is not None:
				_mpd_tree_ns = '{' + _mpd_tree.tag.split('}')[0].strip('{') + '}'
				if _mpd_tree.tag == _mpd_tree_ns + 'MPD':
					self.mpd_url = url
					self.mpd_contents = _mpd_contents
					self.mpd_tree = _mpd_tree
					self.mpd_tree_ns = _mpd_tree_ns
					return

		raise ValueError( url + 'could not by parsed as an valid MPD')


	def query(self,query_path):

		query = '.'
		for query_param in query_path:
			query += '/' + self.mpd_tree_ns + query_param

		try:
			mpd_element = self.mpd_tree.find(query);
			return mpd_element
		except Exception as e:
			xbmc_helper.log_debug('Could not query mpd - Exception: ' + str(e))
			pass

		return None


	def query_node_value(self, query_path):

		query_element = self.query(query_path)
		if query_element is not None and query_element.text is not None:
			return query_element.text
		return None


	def get_toplevel_base_url(self):

		return self.query_node_value(['BaseURL'])
