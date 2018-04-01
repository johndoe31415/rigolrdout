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

import threading
import time

class DataBufferTimeout(Exception): pass

class DataBuffer(object):
	def __init__(self):
		self._cond = threading.Condition()
		self._buf = bytearray()

	def put(self, data):
		with self._cond:
			self._buf += data
			self._cond.notify_all()

	def get(self, length, timeout = 1.0):
		end = time.time() + timeout
		with self._cond:
			while True:
				if len(self._buf) >= length:
					head = self._buf[:length]
					tail = self._buf[length:]
					self._buf = tail
					return head
				else:
					# Wait for data
					remaining = end - time.time()
					if remaining > 0:
						self._cond.wait(timeout = remaining)
					else:
						raise DataBufferTimeout("Timeout waiting for %d bytes of data line (%.1f sec)" % (timeout))

	def getline(self, codec = None, timeout = 1.0):
		end = time.time() + timeout
		with self._cond:
			while True:
				splitbuf = self._buf.split(b"\n", maxsplit = 1)
				if len(splitbuf) == 2:
					line = splitbuf[0]
					self._buf = splitbuf[1]
					if codec is not None:
						line = line.decode(codec)
					return line
				else:
					# Wait for data
					remaining = end - time.time()
					if remaining > 0:
						self._cond.wait(timeout = remaining)
					else:
						raise DataBufferTimeout("Timeout waiting for line (%.1f sec)" % (timeout))
