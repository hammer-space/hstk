## Installation instructions for Windows

hstk requires python 3 to run and can only operate against a Hammerspace SMB or
NFS endpoint.

1. Install python3 for Windows. https://www.python.org/downloads/
2. Verify that pip is installed along with python. From a command prompt, run:
```
C:\Users\Administrator> pip -V
pip 22.0.4 from C:\Program Files\Python310\lib\site-packages\pip (python 3.10)
```
3. Install hstk
```
C:\Users\Administrator> pip install hstk
Collecting hstk
  Downloading hstk-4.6.3.5-py3-none-any.whl (25 kB)
Collecting six
  Downloading six-1.16.0-py2.py3-none-any.whl (11 kB)
Collecting Click
  Downloading click-8.1.2-py3-none-any.whl (96 kB)
     ---------------------------------------- 96.6/96.6 KB 5.8 MB/s eta 0:00:00
Collecting colorama
  Downloading colorama-0.4.4-py2.py3-none-any.whl (16 kB)
Installing collected packages: six, colorama, Click, hstk
Successfully installed Click-8.1.2 colorama-0.4.4 hstk-4.6.3.5 six-1.16.0
```
4. Verify that it was installed by running it to print the help.
```
C:\Users\Administrator>hs
Usage: hs [OPTIONS] COMMAND [ARGS]...

  Hammerspace hammerscript cli

Options:
  -v, --verbose  Debug output
  -n, --dry-run  Don't operate on files
  -d, --debug    Show debug output
  -j, --json     Use JSON formatted output
  --cmd-tree     Show help for available commands
  --help         Show this message and exit.

Commands:
  eval             Evaluate hsscript expressions on a file
  sum              Perform fast calculations on a set of files
  attribute        [sub] inode metadata: schema yes, value yes
  keyword          [sub] inode metadata: schema no, value no
  label            [sub] inode metadata: schema hierarchical, value no
  tag              [sub] inode metadata: schema no, value yes
  rekognition-tag  [sub] inode metadata: schema no, value yes
  objective        [sub] control file placement on backend storage
  rm               Fast offloaded rm -rf
  cp               Fast offloaded recursive copy via clone
  rsync            Fast offloaded recursive directory equalizer (Add and...
  collsum          Usage details about one/all collections in whole share...
  status           [sub] System, component, task status
  usage            [sub] Resource utilization such as capacity or inode
  perf             [sub] Performance and operation stats
  dump             [sub] Dump info about various items
  keep-on-site     [sub] sites in the GNS to keep copies of the data on
```
