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
import json
import base64
import gzip
import hashlib
import sys

class UnableToLoadStorageException(Exception): pass

class InputFile(object):
	def __init__(self, args, filename):
		self._args = args
		with open(filename) as f:
			self._meta = json.loads(f.read())
		self._storage = self._load_storage()

	def _load_storage(self):
		storage = { }
		for (blob_name, blob_data) in self._meta["data"].items():
			try:
				data = self._load_blob(blob_data)
				storage[blob_name] = data
			except UnableToLoadStorageException as e:
				print("Cannot load storage %s: %s -- ignoring this data chunk." % (blob_name, str(e)))
		return storage

	def _load_blob(self, blob_data):
		if blob_data["storage"] == "inline":
			data = self._load_inline_blob(blob_data)
		elif blob_data["storage"] == "external":
			data = self._load_external_blob(blob_data)
		else:
			raise UnableToLoadStorageException("Unknown storage format '%s'." % (blob_data["storage"]))
		hashval = hashlib.sha256(data).hexdigest()
		if hashval != blob_data["sha256"]:
			raise UnableToLoadStorageException("SHA256 of blob does not match recorded data. Tampered/corrupt data or wrong file reference.")
		return data

	def _load_inline_blob(self, blob_data):
		return gzip.decompress(base64.b64decode(blob_data["gzip_compressed_data"]))

	def _load_external_blob(self, blob_data):
		if self._args.search_path is not None:
			search_path = self._args.search_path
		else:
			search_path = os.path.dirname(self._args.inputfile)
		if not search_path.endswith("/"):
			search_path += "/"

		full_filename = search_path + blob_data["filename"]
		if os.path.isfile(full_filename):
			with open(full_filename, "rb") as f:
				return f.read()

		if os.path.isfile(full_filename + ".gz"):
			with gzip.open(full_filename + ".gz") as f:
				return f.read()

		raise UnableToLoadStorageException("File not found: %s" % (full_filename))

	def write_hardcopy(self, outputfile):
		for (blob_name, blob_meta, data) in self.iter_hardcopy():
			with open(outputfile, "wb") as f:
				f.write(data)
			print("Wrote hardcopy \"%s\" to %s." % (blob_name, outputfile), file = sys.stderr)
			break

	def _interpret_waveform(self, waveform):
		(name, meta, data) = waveform

		for (i, value) in enumerate(data):
			x = (i + meta["x_origin"]["flt"]) * meta["x_increment"]["flt"]
			y = (value + meta["y_origin"]["flt"]) * meta["y_increment"]["flt"]
			yield (x, y)

	def _write_waveforms_gpl(self, f, waveforms):
		print("# %d waveform(s)" % (len(waveforms)), file = f)
		print("set terminal pngcairo size 1280,960", file = f)
		#set output "usin.png"
		print("set xlabel \"x\"", file = f)
		print("set ylabel \"y\"", file = f)
#		print("set y2label \"y/x\"", file = f)
		print("set ytics nomirror", file = f)
#		print("set y2tics nomirror", file = f)
		print("set grid", file = f)
		plotcmd = [ "'-' using 1:2 with lines title \"Waveform %d\" lc \"#2980b9\"" % (wid) for wid in range(len(waveforms)) ]
		plotcmd = "plot %s" % (", ".join(plotcmd))
		print(plotcmd, file = f)
		print(file = f)
		for waveform in waveforms:
			for (x, y) in self._interpret_waveform(waveform):
				print("%.4e %.4e" % (x, y), file = f)
			print("end", file = f)
			print(file = f)

	def write_waveform(self, outputfile, out_format = "gnuplot"):
		assert(out_format in [ "gnuplot", "png" ])
		waveforms = list(self.iter_waveform())
		with open(outputfile, "w") as gplfile:
			self._write_waveforms_gpl(gplfile, waveforms)

	def iter_type(self, typename):
		for (blob_name, blob_meta, storage) in self:
			if blob_meta["type"] == typename:
				yield (blob_name, blob_meta, storage)

	def iter_hardcopy(self):
		return self.iter_type("hardcopy")

	def iter_waveform(self):
		return self.iter_type("waveform")

	def __iter__(self):
		for (blob_name, blob_data) in self._meta["data"].items():
			if blob_name in self._storage:
				yield (blob_name, blob_data["meta"], self._storage[blob_name])
