# dptrp1manager

A python package to provide high level tools to work with the Sony DPT-RP1.
This relies heavily on the [https://github.com/janten/dpt-rp1-py](dpt-rp1-py)
package and all credit goes to its author.

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
  syncpairs`. A synchronization pair is defined by a local and a remote path
  and the policy to decide which file to keep in case it is present locally and
  remotely.

## Install

To install the library run `python3 setup.py install` or `pip3 install .` from
the root directory. To install as a developer use `python3 setup.py develop`
(see [the setuptools
docs](http://setuptools.readthedocs.io/en/latest/setuptools.html#development-mode))
and work on the source as usual. Note that the package has so far only be tested
on linux.


## Usage

Firstly, make sure you can connect DPT-RP1 with the `dptrp1` command.
Creat a configuration file `~/.dpmgr/dpmgr.conf` which contains:

    [IP]
    ssid = ip
    default = xxx.xxx.xxx.xxx  # you can find the ip address with the `dptrp1` command

Then you can use `dpmgr config`  to initial your connection and run `dpmgr` command.
Some examples are given below:

    dpmgr status   # list the condition of your device
    dpmgr tree -a  # generate a file tree 
    dpmgr upload LocalFile RemoteFile
    dpmgr upload -d  LocalDir RemoteDir   # upload a directory
    dpmgr delete/download  RemoteFile  # a part of the filename is acceptable
    dpmgr sync local Document       # synchronize remote Document directory with a local directory

**Shell completion**

There are completion script for bash and zsh in the tools folder. Both are only
partially done, but work well for the everyday tasks.


## Note:

Not all commands have been tested yet, but the majority of them works for me.
Please notice that the sync command overrides files either on the remote or
locally depending on the defined policy.
