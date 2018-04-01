#	rigolrdout - Read data and screenshots from Rigol oscilloscopes
#	Copyright (C) 2012-2018 Johannes Bauer
#
#	This file is part of rigolrdout.
#
#	rigolrdout is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	rigolrdout is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with rigolrdout; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import json
import base64
import hashlib
import gzip

class TMCBool(object):
	_FALSE_VALUES = set([ "0", "off" ])
	_TRUE_VALUES = set([ "1", "on" ])
	_VALID_VALUES = _FALSE_VALUES | _TRUE_VALUES

	def __init__(self, value):
		assert(isinstance(value, str))
		self._orig_value = value

		value = value.lower()
		if value not in self._VALID_VALUES:
			raise TypeError("'%s' is not a valid TMC boolean." % (value))
		self._bool_value = value in self._TRUE_VALUES

	def to_repr(self):
		return bool(self)

	def __bool__(self):
		return self._bool_value

class TMCFloat(object):
	def __init__(self, value):
		assert(isinstance(value, str))
		self._orig_value = value
		self._flt_value = float(value)

	def to_repr(self):
		return {
			"orig":		self._orig_value,
			"flt":		float(self),
		}

	def __float__(self):
		return self._flt_value

class TMCRawData(object):
	def __init__(self, data, file_format, metadata = None):
		self._data = bytes(data)
		self._file_format = file_format
		self._metadata = metadata

	@property
	def data(self):
		return self._data

	@property
	def file_format(self):
		return self._file_format

	@property
	def metadata(self):
		return self._metadata

	def to_repr(self, external_filename = None):
		result = {
			"length":	len(self._data),
			"format":	self._file_format,
			"sha256":	hashlib.sha256(self._data).hexdigest(),
		}
		if external_filename is None:
			result["gzip_compressed_data"] = base64.b64encode(gzip.compress(self._data)).decode("ascii")
			result["storage"] = "inline"
		else:
			result["filename"] = external_filename
			result["storage"] = "external"
		if self._metadata is not None:
			result["meta"] = self._metadata
		return result

class TMCJSONEncoder(json.JSONEncoder):
	def default(self, obj):
		return obj.to_repr()
