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

import datetime
import json
import base64

class HardCopy(object):
	def __init__(self, data, file_format):
		self._data = bytes(data)
		self._file_format = file_format

	@property
	def data(self):
		return self._data

	@property
	def file_format(self):
		return self._file_format

	def to_dict(self):
		return {
			"length":	len(self._data),
			"format":	self._file_format,
			"data":		base64.b64encode(self._data).decode("ascii"),
		}

class OutputFile(object):
	def __init__(self):
		self._creation = datetime.datetime.utcnow()
		self._connection = None
		self._instrument = None
		self._hardcopies = [ ]

	@property
	def connection(self):
		return self._connection

	@connection.setter
	def connection(self, value):
		self._connection = value

	@property
	def instrument(self):
		return self._instrument

	@instrument.setter
	def instrument(self, value):
		self._instrument = value

	def add_hardcopy(self, hardcopy):
		self._hardcopies.append(hardcopy)

	def _metadata(self):
		content = {
			"created":		self._creation.strftime("%Y-%m-%dT%H:%M:%SZ"),
			"connection":	self.connection,
		}
		if self.instrument is not None:
			content["instrument"] = {
				"vendor":					self.instrument.vendor,
				"device":					self.instrument.device,
				"serial":					self.instrument.serial,
				"fw_version":				self.instrument.fw_version,
				"instrument_parameters": {
					"number_channels":		self.instrument.instrument_parameters.number_channels,
				},
			}
		return content

	def _write_json(self, filename):
		content = self._metadata()
		content["hardcopies"] = [ hardcopy.to_dict() for hardcopy in self._hardcopies ]
		with open(filename, "w") as f:
			print(json.dumps(content, sort_keys = True, indent = 4), file = f)

	def _write_files(self, filename):
		content = self._metadata()
		with open(filename + "_meta.json", "w") as f:
			print(json.dumps(content, sort_keys = True, indent = 4), file = f)
		for (hcid, hardcopy) in enumerate(self._hardcopies, 1):
			with open(filename + "_hardcopy%d.%s" % (hcid, hardcopy.file_format), "wb") as f:
				f.write(hardcopy.data)

	def write(self, file_format, filename):
		if file_format == "json":
			return self._write_json(filename)
		elif file_format == "files":
			return self._write_files(filename)
		else:
			raise Exception("Unsupported file format: %s" % (file_format))
