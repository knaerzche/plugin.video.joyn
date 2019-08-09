#!/usr/bin/python
# -*- coding: utf-8 -*-

from sys import version_info
from platform import uname

PY2 = version_info[0] == 2
PY3 = version_info[0] == 3

def _encode(s, encoding='utf-8'):
	if PY2 and isinstance(s, unicode):
		s = s.encode(encoding)
	return s


def _unicode(s, encoding='utf-8'):
	if PY2 and isinstance(s, str):
		s = unicode(s, encoding)
	return s


def _decode(d, encoding='utf-8'):
	if PY3 and isinstance(d, bytes):
		d = d.decode(encoding)
	return d


def _unichr(char):
	if PY2:
		return unichr(char)
	else:
		return chr(char)


def _uname_list():
	if PY3:
		return list(uname())
	else:
		return uname()
