Hammerspace CLI tool and python toolkit (hstk)

Supports Hammerspace release 4.5.x and later, and python 3

Install
=======

Installing with pip
-------------------

The easiest way to install the hs command + hstk library is with pip.  You may
need to use your package manager (yum/apt/etc) to install the python-pip
package.  Once you have the 'pip' command, decide if you want to install for
all users in the system libraries or for just your account.

As your user (installs in your account only) or using sudo/root (installs in system directories):

$ pip3 install hstk

This will pull down the needed dependencies as well.  This does not install the
bash completions, see [shell completions](shell-completions)


python click dependency
-----------------------

There is a dependency on the click python package.  It is known to work with
click version 6.7 that comes from the EPEL repo for centos 7.  The easiest
thing to do is to grab that RPM.  If you have EPEL repos enabled:
$ yum install python2-click

If not, you can build your own RPM of click... This example grabs an older version
of click, if you try a newer version and it doesn't work, plese file a bug at
https://github.com/hammer-space/hstk

$ yum install rpm-build
$ wget https://github.com/pallets/click/archive/6.7.tar.gz
$ tar xzvf 6.7.tar.gz
$ cd click-6.7/
$ python2 setup.py bdist_rpm
$ ls -l dist/click-6.7-1.noarch.rpm
-rw-r----- 1 user group 120312 Dec 18 19:59 dist/click-6.7-1.noarch.rpm

building hstk rpm
-----------------

$ git clone https://github.com/hammer-space/hstk.git
$ cd hstk
$ python3 setup.py bdist_rpm
$ ls -l dist/hstk-4.1.0.1-1.noarch.rpm
-rw-r----- 1 root root 20652 Dec 18 20:01 dist/hstk-4.1.0.1-1.noarch.rpm


shell completion
----------------

The above pip and rpm install methods don't configure shell completion.  The
short version, for bash, to enable system wide completions, add this file
    $ cat /etc/bash_completion.d/hs_bash_completion
    eval "$(LANG=en_US.utf8 _HS_COMPLETE=source hs)"

More details on how to enable shell completion are available from the
[Click Project](https://click.palletsprojects.com/en/6.x/bashcomplete/)


Installing on a system that is not connected to the internet
============================================================

Centos8
-------

Install base python3 RPMs on target system
    python3 python3-pip python3-setuptools

move on to 'Collect and install wheel files for any Distro'


Collect and install wheel files for any Distro
----------------------------------------------

On an internet connected system, generate the pip requirements and download all
needd packages.
    python3 -m hstk_for_req
    source hstk_for_req/bin/activate
    pip3 install hstk
    mkdir /tmp/hstk_pkgs
    cd /tmp/hstk_pkgs
    pip3 freeze > requirements.txt

Note that you may need to remove some old packages installed by RPM for
download to work, I removed the 'gpg==' and 'rpm==' lines from the generated
requirements.txt

    pip3 download -r requirements.txt

Copy that directory over to your offline system and (assuming you are going to
install into a venv)

    python3 -m venv hstk
    source hstk/bin/activate
    cd /path/to/hstk_pkgs       # copied over to this node
    pip3 install *.whl


Changelog
=========

4.6.6.0
-------

* No longer works with Hammerspace 4.6.4 and earlier
* Removed support for python2
* Moved to shadow gateway file for issuing commands, benefits include
  * no limitation on length of hammerscript command
  * doesn’t lock out the directory on the client it was run from on long running commands
  * better support for windows
* For windows, is write a bunch of null padding.  For some reason if the write to the shadow gateway file isn't big enough it will not be pushed all the way through the stack on a windows client.

