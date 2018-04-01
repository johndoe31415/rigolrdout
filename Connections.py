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

import time
import socket
import threading
from DataBuffer import DataBuffer

class BaseConnection(object):
	def __init__(self):
		self.__buffer = DataBuffer()

	def command(self, text, timeout = 1.0, wait_response = True):
		data = (text + "\n").encode("utf-8")
		self._write(data)
		if wait_response and text.endswith("?"):
			return self.readline(timeout = timeout)
		else:
			time.sleep(0.1)

	def readline(self, codec = "utf-8", timeout = 1.0):
		return self.__buffer.getline(codec = codec, timeout = timeout)

	def get_tmc_data(self, timeout = 5.0):
		header = self.__buffer.get(2)
		assert(header[0] == ord("#"))
		digit_count = int(chr(header[1]))
		data_length = self.__buffer.get(digit_count)
		data_length = int(data_length.decode("ascii"))
		data = self.__buffer.get(data_length, timeout = timeout)
		return data

	def _put(self, data):
#		print("<-", data)
		self.__buffer.put(data)

	def _write(self, data):
		print("->", data)
		self._raw_write(data)

	def _raw_write(self, data):
		raise Exception(NotImplemented)

class TCPIPConnection(BaseConnection):
	def __init__(self, hostname):
		BaseConnection.__init__(self)
		self._conn = socket.create_connection((hostname, 5555))
		self._closed = False
		self._reader_thread = threading.Thread(target = self._reading_fnc)
		self._reader_thread.start()

	def _reading_fnc(self):
		while not self._closed:
			data = self._conn.recv(4096)
			if len(data) == 0:
				break
			self._put(data)

	def _raw_write(self, data):
		self._conn.send(data)

	def close(self):
		self._closed = True
		self._conn.shutdown(socket.SHUT_RDWR)
		self._conn.close()

	@classmethod
	def from_str(cls, conn_str):
		conn_str = conn_str.split(":")
		return cls(conn_str[1])

class Connection(object):
	_ConnectionClasses = {
		"tcpip":	TCPIPConnection,
	}

	@classmethod
	def establish(cls, conn_str):
		if len(conn_str) == 0:
			raise Exception("Connection string is a required argument.")
		driver = conn_str.split(":")[0].lower()
		if driver not in cls._ConnectionClasses:
			raise Exception("No such driver type: %s" % (driver))
		return cls._ConnectionClasses[driver].from_str(conn_str)
