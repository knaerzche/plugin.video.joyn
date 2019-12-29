# -*- coding: utf-8 -*-

from os import path, remove
from datetime import datetime, timedelta
from io import open as io_open
from pickle import dump as pickle_dump, load as pickle_load
from .const import CONST
from .xbmc_helper import xbmc_helper as xbmc_helper
from . import compat as compat

if compat.PY2:
	try:
		from simplejson import loads, dumps
	except ImportError:
		from json import loads, dumps
elif compat.PY3:
	from json import loads, dumps


def _get(cache_key, file_name, override_expire_secs=None, pickle=False):

	expire_datetime = None
	cache_path = xbmc_helper().get_file_path(CONST['CACHE_DIR'], file_name)

	if (override_expire_secs is not None):
		expire_datetime = datetime.now() - timedelta(seconds=override_expire_secs)
	elif 'expires' in CONST['CACHE'][cache_key].keys() and CONST['CACHE'][cache_key]['expires'] is not None:
		expire_datetime = datetime.now() - timedelta(seconds=CONST['CACHE'][cache_key]['expires'])

	cache_data = {
	        'data': None,
	        'is_expired': True,
	}

	if path.exists(cache_path):

		filectime = datetime.fromtimestamp(path.getctime(cache_path))
		filemtime = datetime.fromtimestamp(path.getmtime(cache_path))

		if filemtime is None or filectime > filemtime:
			filemtime = filectime
		if pickle is False:
			with io_open(file=cache_path, mode='r', encoding='utf-8') as cache_infile:
				cache_data.update({'data': cache_infile.read()})
		else:
			with io_open(file=cache_path, mode='rb') as cache_infile:
				cache_data.update({'data': pickle_load(cache_infile)})

		if expire_datetime is None or filemtime >= expire_datetime:
			cache_data.update({'is_expired': False})

	return cache_data


def _set(cache_key, file_name, data, pickle=False):

	cache_path = xbmc_helper().get_file_path(CONST['CACHE_DIR'], file_name)
	if pickle is False:
		with io_open(file=cache_path, mode='w', encoding='utf-8') as cache_outfile:
			cache_outfile.write(compat._unicode(data))
	else:
		with io_open(file=cache_path, mode='wb') as cache_outfile:
			pickle_dump(data, cache_outfile, protocol=0)


def _remove(cache_key, file_name):

	cache_path = xbmc_helper().get_file_path(CONST['CACHE_DIR'], file_name)
	if path.exists(cache_path) and path.isfile(cache_path):
		remove(cache_path)
		return True
	return False


def remove_json(cache_key):
	_remove(cache_key, CONST['CACHE'][cache_key]['key'] + '.json')


def get_json(cache_key, override_expire_secs=None):

	cache_data = _get(cache_key, CONST['CACHE'][cache_key]['key'] + '.json')

	if cache_data['data'] is not None:
		try:
			cache_data.update({'data': loads(cache_data['data'])})
		except ValueError:
			xbmc_helper().log_error('Could decode as json from cache: {}', cache_key)
			pass

	return cache_data


def set_json(cache_key, data):

	try:
		_set(cache_key, CONST['CACHE'][cache_key]['key'] + '.json', dumps(data))
	except ValueError:
		xbmc_helper().log_error('Could not encode json from cache: {}', cache_key)
		pass


def get_pickle(cache_key):
	return _get(cache_key, CONST['CACHE'][cache_key]['key'] + '.pickle', pickle=True)


def set_pickle(cache_key, data):
	return _set(cache_key, CONST['CACHE'][cache_key]['key'] + '.pickle', data, pickle=True)