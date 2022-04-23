## Installation instructions for Linux

hstk requires python 3 to run and can only operate against a Hammerspace SMB
endpoint.

1. Ensure that an up2date version of python3 is installed
```
# python3 -V
Python 3.8.10
```
2. Verify that pip is installed along with python. From a command prompt, run:
```
# pip -V
pip 20.0.2 from /usr/lib/python3/dist-packages/pip (python 3.8)
```
3. Install hstk
```
# pip install hstk
Collecting hstk
  Downloading hstk-4.6.3.5-py3-none-any.whl (25 kB)
Requirement already satisfied: Click in /usr/lib/python3/dist-packages (from hstk) (7.0)
Requirement already satisfied: six in /usr/lib/python3/dist-packages (from hstk) (1.14.0)
Installing collected packages: hstk
Successfully installed hstk-4.6.3.5
```
4. Verify that it was installed by running it to print the help.
```
# hs
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
