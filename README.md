# rigolrdout
rigolrdout is a tool that can connect to your Rigol oscilloscope (at least to a
1000Z series) via LAN and read out screen grabs or data and write them to local
files.

## Help!
Just type `./rigolrdout --help`:

```
$ ./rigolrdout --help
usage: rigolrdout [-h] -c conn_str [-f {json,files}] [--include-screengrab] -o
                  file [-v]

optional arguments:
  -h, --help            show this help message and exit
  -c conn_str, --connect conn_str
                        Specify where to connect to. Can be something like
                        "tcpip:192.168.1.4". Currently the only supported
                        driver is "tcpip". Mandatory argument.
  -f {json,files}, --output-format {json,files}
                        Specify output filetype. Can be one of json, files,
                        defaults to files.
  --include-screengrab  Include a hardcopy of the oscilloscope screen in the
                        result.
  -o file, --output file
                        Specify output filename. Mandatory argument.
  -v, --verbose         Increase level of debugging verbosity.
```

## Why not sigrok?
Short answer: It didn't work for me. First, I found it really troublesome to
find working documentation and the command line tool is insanely unhelpful (for
example, sigrok-cli has a "--driver" option -- but which drivers are available?
Same goes for file formats, etc.).  Then, the version included in my disto
(Ubuntu Artful) were too old to properly recognize my Rigol. Then, I built
everything from git and tried to fetch data and save it as CSV. Sigrok dumped
something that looked like CSV, but also had some "CH1: 1.23V" lines before it,
meaning that I would have needed to manually change the CSV.

Super annoying stuff. In effect, when sigrok would be more user-friendly, it
should comlpetely replace this little tool. Until it does, this project will
stay here.

## Dependencies
rigolrdout only needs Python3.

## License
GNU GPL-3.
