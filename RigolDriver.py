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
	_IdentifyResult = collections.namedtuple("IdentifyResult", [ "vendor", "device", "serial", "fw_version" ])

	def __init__(self, connection):
		self._conn = connection

	def identify(self):
		response = self._conn.command("*IDN?")
		return self._IdentifyResult(*response.split(","))

	def data(self):
		print(self._conn.command(":MEAS:RIS? CHAN1"))

	def run(self):
		response = self._conn.command(":RUN")

	def stop(self):
		response = self._conn.command(":STOP")

	def get_display_data(self, img_format = "png"):
		assert(img_format in [ "bmp24", "bmp8", "png", "jpeg", "tiff" ])
		# color, invert, format
		self._conn.command(":DISPLAY:DATA? ON,OFF,%s" % (img_format.upper()), wait_response = False)
		return self._conn.get_tmc_data(timeout = 5.0)
