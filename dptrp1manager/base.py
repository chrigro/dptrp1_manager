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
import datetime

import anytree
from dptrp1.dptrp1 import DigitalPaper

from pprint import pprint

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
        self._dataparser = DPDataParser()
        self._resolver = anytree.resolver.Resolver('name')
        self._content_tree = None

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

    def _get_all_contents(self):
        data = self._dp.list_documents()
        return data

    def _build_tree(self, data):
        for entry in data:
            md = self._dataparser.parse(entry)
            pathlist = md['entry_path']
            lastdirnode = None
            for depth, subpath in enumerate(pathlist[:-1]):
                n = DPNode(name=subpath, isfile=False, metadata={})
                parent_fullname = '/' + '/'.join(pathlist[:depth])
                if not parent_fullname == '/':
                    n.parent = lastdirnode
                elif self._content_tree is None:
                    self._content_tree = n
                for pre, _, node in anytree.render.RenderTree(self._content_tree):
                    print("%s%s" % (pre, node.name))
                lastdirnode = n
            # now the file node
            # node = DPNode(name=md['entry_name'], isfile=True, metadata=md)


class DPDataParser(object):
    """Parser for the data returned for each document.

    """
    def __init__(self):
        super(DPDataParser, self).__init__()

    def parse(self, data):
        """Parse the entry data.

        Returns
        -------
        dict
            Parsed metadata dictionary. It has the following structure:
            'current_page': int
            'total_page': int
            'document_type': 'normal' or 'note'
            'entry_id': string
            'entry_name': string (file name)
            'entry_type': 'document'
            'file_revision': string
            'file_size': int (size in bytes)
            'is_new': bool
            'mime_type': 'application/pdf',
            'parent_folder_id': string
            'title': string
            'author': list of strings
            'entry_path': list of strings (full path)
            'created_date': datetime
            'modified_date': datetime

        """
        res = {}
        # some keys are easy to parse
        res['current_page'] = int(data['current_page'])
        res['total_page'] = int(data['total_page'])
        res['document_type'] = data['document_type']
        res['entry_id'] = data['entry_id']
        res['entry_name'] = data['entry_name']
        res['entry_type'] = data['entry_type']
        res['file_revision'] = data['file_revision']
        res['file_size'] = int(data['file_size'])
        res['is_new'] = bool(data['is_new'])
        res['mime_type'] = data['mime_type']
        res['parent_folder_id'] = data['parent_folder_id']
        res['title'] = data['title']
        res['author'] = self._splitauthors(data['author'])
        res['entry_path'] = self._splitpath(data['entry_path'])
        res['created_date'] = self._string_to_datetime(data['created_date'])
        res['modified_date'] = self._string_to_datetime(data['modified_date'])
        return res

    def _string_to_datetime(self, string):
        dt = datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ')
        return dt

    def _splitpath(self, string):
        path = os.path.normpath(string)
        return path.split(os.sep)

    def _splitauthors(self, string):
        authlist = [s.strip() for s in string.split(';')]
        return authlist



class DPNode(anytree.NodeMixin):
    """Representation of a node in the file system of the DPT-RP1.

    Attributes
    ----------
    name : string
        The name of the node.
    isfile : bool
        Is the node representing a file? Otherwise it is a dir.
    metadata : dict
        Parsed file metadata as provided by DPT-RP1.

    """
    def __init__(self, name, isfile, metadata):
        super(DPNode, self).__init__()
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
    d = dp_mgr._get_all_contents()
    dp_mgr._build_tree(d)

if __name__ == '__main__':
    main()
