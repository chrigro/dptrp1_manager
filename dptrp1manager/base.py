#!/usr/bin/env python
# coding=utf-8

# dptrp1manager, high level tools to interact with the Sony DPT-RP1
# Copyright © 2018 Christian Gross (christian-gross@gmx.de)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import os.path as osp

import anytree
from dptrp1.dptrp1 import DigitalPaper

CONFIGDIR = osp.join(osp.expanduser('~'), '.dptrp1')

class DPManager(object):
    """Main class to manage the DPT-RP1.

    Parameters
    ----------
    addr : string
        The IP adress of the digital paper device
    register : bool (False)
        If True, force registration of the client even if key and id files are
        found.

    """
    def __init__(self, addr, register=False):
        super(DPManager, self).__init__()
        self._dp = DigitalPaper(addr = addr)
        self._key_file = osp.join(CONFIGDIR, 'dptrp1_key')
        self._clientid_file = osp.join(CONFIGDIR, 'dptrp1_id')
        self._check_registered(register)
        self._authenticate()


    def _authenticate(self):
        with open(self._clientid_file, 'r') as f:
            client_id = f.readline().strip()
        with open(self._key_file, 'rb') as f:
            key = f.read()
        self._dp.authenticate(client_id, key)

    def _check_configpath(self):
        if not osp.exists(CONFIGDIR):
            os.mkdir(CONFIGDIR)

    def _check_registered(self, register):
        self._check_configpath()
        if not register:
            if (not osp.exists(self._clientid_file) or not
                    osp.exists(self._key_file)):
                self._register()
        else:
            self._register()

    def _register(self):
        _, key, device_id = self._dp.register()
        with open(self._key_file, 'w') as f:
            f.write(key)
        with open(self._clientid_file, 'w') as f:
            f.write(device_id)

    def _get_all_docs(self):
        data = self._dp.list_documents()
        print(data)
        # for d in data:
        #     print(d['entry_path'])


class DPNode(anytree.NodeMixin):
    """Representation of a node in the file system of the DPT-RP1.

    Attributes
    ----------
    name : string
        The name of the node.
    isfile : bool
        Is the node representing a file? Otherwise it is a dir.

    """
    def __init__(self, name, isfile):
        super(TreeNode, self).__init__()
        self.name = name
        self.isfile = isfile


class DPConfig(object):
    """Represent the configuration of the DPT-RP1.

    """
    def __init__(self):
        super(DPConfig, self).__init__()


class Downloader(object):
    """Manage downloading of files.

    """
    def __init__(self):
        super(Downloader, self).__init__()


class Uploader(object):
    """Manage uploading of files.

    """
    def __init__(self):
        super(Uploader, self).__init__()


def main():
    dp_mgr = DPManager('192.168.178.78')
    dp_mgr._get_all_docs()

if __name__ == '__main__':
    main()
