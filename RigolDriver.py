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

import collections

class RigolDriver(object):
	_InstrumentParameters = collections.namedtuple("InstrumentParameters", [ "number_channels" ])
	_KnownInstruments = {
		("RIGOL TECHNOLOGIES", "DS1104Z"):	_InstrumentParameters(number_channels = 4),
	}
	_IdentifyResult = collections.namedtuple("IdentifyResult", [ "vendor", "device", "serial", "fw_version", "instrument_parameters" ])

	def __init__(self, connection):
		self._conn = connection
		self._identification = self._identify()

	@property
	def identification(self):
		return self._identification

	def _identify(self):
		response = self._conn.command("*IDN?")
		(vendor, device, serial, fw_version) = response.split(",")
		instrument_id = (vendor, device)
		if instrument_id not in self._KnownInstruments:
			raise Exception("Instrument '%s' not known currently, add to 'KnownInstruments' dictionary." % (str(instrument_id)))
		instrument_parameters = self._KnownInstruments[instrument_id]
		return self._IdentifyResult(vendor = vendor, device = device, serial = serial, fw_version = fw_version, instrument_parameters = instrument_parameters)

	def data(self):
		print(self._conn.command(":MEAS:RIS? CHAN1"))

	def run(self):
		response = self._conn.command(":RUN")

	def stop(self):
		response = self._conn.command(":STOP")

	@staticmethod
	def _datatype_bool(data):
		if data.isnumeric():
			data = int(data)
			assert(data in [ 0, 1 ])
			return data == 1
		else:
			data = data.lower()
			assert(data in [ "on", "off" ])
			return data == "on"

	@staticmethod
	def _datatype_float(data):
		return {
			"orig":		data,
			"flt":		float(data),
		}

	def get_acquisition_info(self):
		result = {
			"acquisition": {
				"type":			self._conn.command(":ACQ:TYPE?"),
				"sample_rate":	self._datatype_float(self._conn.command(":ACQ:SRAT?")),
				"mem_depth":	self._conn.command(":ACQ:MDEP?"),
				"averages":		self._conn.command(":ACQ:AVER?"),
			},
			"timebase": {
				"offset":		self._datatype_float(self._conn.command(":TIM:OFFS?")),
				"scale":		self._datatype_float(self._conn.command(":TIM:SCAL?")),
				"mode":			self._conn.command(":TIM:MODE?"),
			},
			"trigger": {
				"mode":			self._conn.command(":TRIG:MODE?"),
				"coupling":		self._conn.command(":TRIG:COUP?"),
				"status":		self._conn.command(":TRIG:STAT?"),
				"sweep":		self._conn.command(":TRIG:SWE?"),
				"holdoff":		self._datatype_float(self._conn.command(":TRIG:HOLD?")),
				"nreject":		self._datatype_bool(self._conn.command(":TRIG:NREJ?")),
				"position":		int(self._conn.command(":TRIG:POS?")),
				"specific":		None,
			},
		}
		if result["trigger"]["mode"].lower() == "edge":
			result["trigger"]["specific"] = {
				"source":	self._conn.command(":TRIG:EDG:SOUR?"),
				"slope":	self._conn.command(":TRIG:EDG:SLOP?"),
				"level":	self._datatype_float(self._conn.command(":TRIG:EDG:LEV?")),
			}
		return result

	def get_channel_info(self, channel_id):
		return {
			"bw_limit":	self._conn.command(":CHAN%d:BWL?" % (channel_id)),
			"coupling":	self._conn.command(":CHAN%d:COUP?" % (channel_id)),
			"inverted":	self._datatype_bool(self._conn.command(":CHAN%d:INV?" % (channel_id))),
			"offset":	self._datatype_float(self._conn.command(":CHAN%d:OFFS?" % (channel_id))),
			"range":	self._datatype_float(self._conn.command(":CHAN%d:RANG?" % (channel_id))),
			"time_cal":	self._datatype_float(self._conn.command(":CHAN%d:TCAL?" % (channel_id))),
			"scale":	self._datatype_float(self._conn.command(":CHAN%d:SCAL?" % (channel_id))),
			"probe":	self._datatype_float(self._conn.command(":CHAN%d:PROB?" % (channel_id))),
			"unit":		self._conn.command(":CHAN%d:UNIT?" % (channel_id)),
			"vernier":	self._datatype_bool(self._conn.command(":CHAN%d:VERN?" % (channel_id))),
		}

	def get_waveform(self, channel_id):
		self._conn.command(":WAV:SOUR CHAN%d" % (channel_id))
		self._conn.command(":WAV:MODE RAW")
		self._conn.command(":WAV:FORM BYTE")
		preamble = self._conn.command(":WAV:PRE?")
		preamble = preamble.split(",")
		assert(len(preamble) == 10)

		waveform = {
			"format":	{
				0:	"BYTE",
				1:	"WORD",
				2:	"ASC",
			}[int(preamble[0])],
			"type":	{
				0:	"NORM",
				1:	"MAX",
				2:	"RAW",
			}[int(preamble[1])],
			"points":		int(preamble[2]),
			"count":		int(preamble[3]),
			"x_increment":	self._datatype_float(preamble[4]),
			"x_origin":		self._datatype_float(preamble[5]),
			"x_reference":	self._datatype_float(preamble[6]),
			"y_increment":	self._datatype_float(preamble[7]),
			"y_origin":		self._datatype_float(preamble[8]),
			"y_reference":	self._datatype_float(preamble[9]),
		}
		print(preamble)

		total_data = bytearray()
		total_bytes = waveform["points"]
		bytes_per_batch = 250000
		batches = (total_bytes + bytes_per_batch - 1) // bytes_per_batch
		for i in range(batches):
			start = 1 + (i * bytes_per_batch)
			stop = start + bytes_per_batch - 1
			stop = min(stop, total_bytes)
			self._conn.command(":WAV:STAR %d" % (start))
			self._conn.command(":WAV:STOP %d" % (stop))
			self._conn.command(":WAV:DATA?", wait_response = False)
			data = self._conn.get_tmc_data(timeout = 5.0)
			total_data += data
		waveform["data"] = total_data
		return waveform

	def is_channel_enabled(self, channel_id):
		return self._datatype_bool(self._conn.command(":CHAN%d:DISP?" % (channel_id)))

	def get_enabled_channel_info(self):
		channel_info = { }
		for channel_id in range(1, self.identification.instrument_parameters.number_channels + 1):
			if self.is_channel_enabled(channel_id):
				channel_info[channel_id] = self.get_channel_info(channel_id)
		return channel_info

	def get_display_data(self, img_format = "png"):
		assert(img_format in [ "bmp24", "bmp8", "png", "jpeg", "tiff" ])
		# color, invert, format
		self._conn.command(":DISPLAY:DATA? ON,OFF,%s" % (img_format.upper()), wait_response = False)
		return self._conn.get_tmc_data(timeout = 5.0)
