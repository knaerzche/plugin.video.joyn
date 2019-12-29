# -*- coding: utf-8 -*-

# A singleton instancing metaclass compatible with both Python 2 & 3.
# The __init__ of each class is only called once per addon handle

from sys import argv


class _Singleton(type):
	""" A metaclass that creates a Singleton base class when called. """
	_instances = {}

	def __call__(cls, *args, **kwargs):
		_handle = -1 if len(argv) < 2 else int(argv[1])

		if _handle not in cls._instances.keys():
			cls._instances.update({_handle: {}})

		if cls not in cls._instances[_handle].keys():
			cls._instances[_handle][cls] = super(_Singleton, cls).__call__(*args, **kwargs)

		return cls._instances[_handle][cls]


class Singleton(_Singleton('SingletonMeta', (object, ), {})):
	pass
