# dptrp1manager

A python package to provide high level tools to work with the Sony DPT-RP1.
This relies heavily on the [https://github.com/janten/dpt-rp1-py](dpt-rp1-py)
package and all credit goes to its author.


## Install

To install the library run `python3 setup.py install` or `pip3 install .` from
the root directory. To install as a developer use `python3 setup.py develop`
(see [the setuptools
docs](http://setuptools.readthedocs.io/en/latest/setuptools.html#development-mode))
and work on the source as usual. Not that the package has so far only be tested
on linux.


## Usage

The package provides the command line tool dpmgr to interact with the Sony
DPT-RP1. If it is invoked without arguments, all possible commands are listed.
The key and id file necessary to interact with the digital paper are stored in
`~/.dpmgr`. This directory also contains two configuration files:

- `~/.dpmgr/dpmgr.conf`: Configure the ip of the digital paper. It is possible
  to configure the ip dependent on the wireless network the computer is
  connected to. To use this feature, add an option in the format `ssid = ip` to
  the `[IP]` section in the file.

- `~/.dpmgr/sync.conf`: This file provides a possibility to define
  synchronization pairs, which are all synchronized when running `dpmgr
  syncpairs`. A synchronization pair is defined by A local and a remote path
  and the policy to decide which file to keep in case it is present locally and
  remotely.


## Note:

Not all commands have been tested yet, but the majority of them works for me.
