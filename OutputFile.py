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

import os
import datetime
import json
from TMCDataTypes import TMCJSONEncoder

class OutputFile(object):
	def __init__(self, include_serial = True):
		self._creation = datetime.datetime.utcnow()
		self._comment = None
		self._connection = None
		self._channel_info = None
		self._acquisition_info = None
		self._instrument = None
		self._raw_data = { }
		self._include_serial = include_serial

	@property
	def comment(self):
		return self._comment

	@comment.setter
	def comment(self, value):
		self._comment = value

	@property
	def connection(self):
		return self._connection

	@connection.setter
	def connection(self, value):
		self._connection = value

	@property
	def channel_info(self):
		return self._channel_info

	@channel_info.setter
	def channel_info(self, value):
		self._channel_info = value

	@property
	def acquisition_info(self):
		return self._acquisition_info

	@acquisition_info.setter
	def acquisition_info(self, value):
		self._acquisition_info = value

	@property
	def instrument(self):
		return self._instrument

	@instrument.setter
	def instrument(self, value):
		self._instrument = value

	def add_raw_data(self, name, raw_data):
		self._raw_data[name] = raw_data

	def _metadata(self):
		content = {
			"created":		self._creation.strftime("%Y-%m-%dT%H:%M:%SZ"),
			"connection":	self.connection,
		}
		if self.comment is not None:
			content["comment"] = self.comment
		if self.instrument is not None:
			content["instrument"] = {
				"vendor":					self.instrument.vendor,
				"device":					self.instrument.device,
				"fw_version":				self.instrument.fw_version,
				"instrument_parameters": {
					"number_channels":		self.instrument.instrument_parameters.number_channels,
				},
			}
			if self._include_serial:
				content["serial"] =	self.instrument.serial
		if self.channel_info is not None:
			content["channel_info"] = self.channel_info
		if self.acquisition_info is not None:
			content["acquisition_info"] = self.acquisition_info
		return content

	def _write_json(self, filename):
		content = self._metadata()
		content["data"] = self._raw_data
		with open(filename, "w") as f:
			print(json.dumps(content, sort_keys = True, indent = 4, cls = TMCJSONEncoder), file = f)

	def _write_files(self, filename):
		content = self._metadata()
		content["data"] = { }
		for (name, raw_data) in self._raw_data.items():
			raw_filename = filename + "_%s.%s" % (name, raw_data.file_format)
			content["data"][name] = raw_data.to_repr(external_filename = os.path.basename(raw_filename))
			with open(raw_filename, "wb") as f:
				f.write(raw_data.data)
		with open(filename + "_meta.json", "w") as f:
			print(json.dumps(content, sort_keys = True, indent = 4, cls = TMCJSONEncoder), file = f)

	def write(self, file_format, filename):
		if file_format == "json":
			return self._write_json(filename)
		elif file_format == "files":
			return self._write_files(filename)
		else:
			raise Exception("Unsupported file format: %s" % (file_format))
