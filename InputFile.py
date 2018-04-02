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
import tempfile
import subprocess

class UnableToLoadStorageException(Exception): pass

class RigolWaveformInterpreter(object):
	_COLORS = {
		0:	"f1c40f",	# yellow
		1:	"3498db",	# blue
		2:	"e82dc6",	# pink
		3:	"8e44ad",	# purple
	}
	def __init__(self, args, inputfile):
		self._args = args
		self._input = inputfile
		self._waveforms  = list(self._input.iter_waveform())

	def _interpret_waveform(self, waveform):
		(name, meta, data) = waveform

		for (i, value) in enumerate(data, -self._input["acquisition_info"]["trigger"]["position"] + 1):
			x = (i - meta["x_origin"]["flt"] - meta["x_reference"]) * meta["x_increment"]["flt"]
			y = (value - meta["y_origin"]["flt"] - meta["y_reference"]) * meta["y_increment"]["flt"]
			yield (x, y)

	def _waveform_color(self, channel_id):
		return self._COLORS[(channel_id - 1) % len(self._COLORS)]

	@staticmethod
	def _get_unit(unit):
		if unit is None:
			return ("", 1)
		return {
			"m":	("m", 1e-3),
			"u":	("µ", 1e-6),
			"n":	("n", 1e-9),
		}[unit]

	def write_gpl(self, f):
		(xunit, xunit_value) = self._get_unit(self._args.x_unit)
		(yunit, yunit_value) = self._get_unit(self._args.y_unit)

		print("# %d waveform(s)" % (len(self._waveforms)), file = f)
		print("set terminal pngcairo size %s,%s" % (self._args.width, self._args.height), file = f)
		if self._input.get("comment"):
			print("set title \"%s\"" % (self._input["comment"]), file = f)
		else:
			print("set title \"%s %s\"" % (self._input["instrument"]["vendor"], self._input["instrument"]["device"]), file = f)
		print("set xlabel \"x / %ss\"" % (xunit), file = f)
		print("set ylabel \"y / %sV\"" % (yunit), file = f)
		print("set ytics nomirror", file = f)
		print("set grid", file = f)
		print("set samples 2000", file = f)
		plotcmds = [ ]
		for (name, meta, data) in self._waveforms:
			single_cmd = [ "'-' using" ]

			if not self._args.honor_offsets:
				(xplot, yplot) = ("$1", "$2")
			else:
				channel_id = str(meta["channel"])
				xplot = "$1-%f" % (self._input["acquisition_info"]["timebase"]["offset"]["flt"])
				yplot = "$2+%f" % (self._input["channel_info"][channel_id]["offset"]["flt"])
			if xunit_value != 1:
				xplot = "(%s)/%e" % (xplot, xunit_value)
			if yunit_value != 1:
				yplot = "(%s)/%e" % (yplot, yunit_value)
			single_cmd.append("(%s):(%s)" % (xplot, yplot))

			single_cmd.append("with lines")
			if self._args.smooth_waveform:
				single_cmd.append("smooth cspline")
			single_cmd.append("title \"Channel %d\"" % (meta["channel"]))
			single_cmd.append("lc \"#%s\"" % (self._waveform_color(meta["channel"])))
			single_cmd.append("lw 2")
			plotcmds.append(" ".join(single_cmd))
		plotcmd = "plot %s" % (", ".join(plotcmds))
		print(plotcmd, file = f)
		print(file = f)
		for waveform in self._waveforms:
			for (x, y) in self._interpret_waveform(waveform):
				print("%.4e %.4e" % (x, y), file = f)
			print("end", file = f)
			print(file = f)

	def write(self, filename, out_format):
		assert(out_format in [ "gnuplot", "png" ])
		if out_format == "gnuplot":
			with open(filename, "w") as f:
				self.write_gpl(f)
		elif out_format == "png":
			with tempfile.NamedTemporaryFile(prefix = "plot_", suffix = ".gpl", mode = "w") as f:
				self.write_gpl(f)
				f.flush()
				png = subprocess.check_output([ "gnuplot", f.name ])
			with open(filename, "wb") as f:
				f.write(png)

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

	def write_waveform(self, outputfile, out_format = "gnuplot"):
		assert(out_format in [ "gnuplot", "png" ])
		waveform_interpreter = RigolWaveformInterpreter(self._args, self)
		waveform_interpreter.write(outputfile, out_format)

	def write_hardcopy(self, outputfile):
		for (blob_name, blob_meta, data) in self.iter_hardcopy():
			with open(outputfile, "wb") as f:
				f.write(data)
			print("Wrote hardcopy \"%s\" to %s." % (blob_name, outputfile), file = sys.stderr)
			break

	def iter_type(self, typename):
		for (blob_name, blob_meta, storage) in self:
			if blob_meta["type"] == typename:
				yield (blob_name, blob_meta, storage)

	def iter_hardcopy(self):
		return self.iter_type("hardcopy")

	def iter_waveform(self):
		return self.iter_type("waveform")

	def get(self, key):
		return self._meta.get(key)

	def __getitem__(self, key):
		return self._meta[key]

	def __iter__(self):
		for (blob_name, blob_data) in sorted(self._meta["data"].items(), key = lambda v: (v[1].get("channel", 0), v[0])):
			if blob_name in self._storage:
				yield (blob_name, blob_data["meta"], self._storage[blob_name])
