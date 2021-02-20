Hammerspace CLI tool and python toolkit (hstk)

Supports Hammerspace release 4.6.0 and later.

Install
=======

Installing with pip
-------------------

The easiest way to install the hs command + hstk library is with pip.  You may
need to use your package manager (yum/apt/etc) to install the python-pip
package.  Once you have the 'pip' command, decide if you want to install for
all users in the system libraries or for just your account.

As your user (installs in your account only) or using sudo/root (installs in system directories):

$ pip install hstk

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
$ python2 setup.py bdist_rpm
$ ls -l dist/hstk-4.1.0.1-1.noarch.rpm
-rw-r----- 1 root root 20652 Dec 18 20:01 dist/hstk-4.1.0.1-1.noarch.rpm


shell completion
----------------

The above pip and rpm install methods don't configure shell completion.  The
short version, for bash, to enable system wide completions, add this file
    $ cat /etc/bash_completion.d/hs_bash_completion
    eval "$(_HS_COMPLETE=source hs)"

More details on how to enable shell completion are available from the 
[Click Project](https://click.palletsprojects.com/en/6.x/bashcomplete/)


