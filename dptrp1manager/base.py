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


import sys
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

    Attributes
    ----------
    dp : DigitalPaper
        DigitalPaper instance

    """
    def __init__(self, addr, register=False):
        super(DPManager, self).__init__()
        self.dp = DigitalPaper(addr = addr)
        self._key_file = osp.join(CONFIGDIR, 'dptrp1_key')
        self._clientid_file = osp.join(CONFIGDIR, 'dptrp1_id')
        self._dataparser = DPDataParser()
        self._resolver = anytree.resolver.Resolver('name')
        self._content_tree = None

        self._check_registered(register)
        self._authenticate()
        self._build_tree()

    def _authenticate(self):
        with open(self._clientid_file, 'r') as f:
            client_id = f.readline().strip()
        with open(self._key_file, 'rb') as f:
            key = f.read()
        self.dp.authenticate(client_id, key)

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
        _, key, device_id = self.dp.register()
        with open(self._key_file, 'w') as f:
            f.write(key)
        with open(self._clientid_file, 'w') as f:
            f.write(device_id)

    def _get_all_contents(self):
        data = self.dp.list_documents()
        return data

    def _build_tree(self):
        data = self._get_all_contents()
        added_dirnodes = []
        for entry in data:
            md = self._dataparser.parse(entry)
            pathlist = md['entry_path']
            for depth, subpath in enumerate(pathlist[:-1]):
                fullname = '/' + '/'.join(pathlist[:depth + 1])
                parent_fullname = '/' + '/'.join(pathlist[:depth])
                if self._content_tree is None and parent_fullname == '/':
                    n = DPNode(name=subpath, isfile=False, metadata={'entry_path': pathlist[:depth + 1],
                        'entry_name': subpath})
                    self._content_tree = n
                elif not parent_fullname == '/':
                    if not fullname in added_dirnodes:
                        parent = self._resolver.get(self._content_tree, parent_fullname)
                        n = DPNode(name=subpath, isfile=False, metadata={'entry_path': pathlist[:depth + 1],
                            'entry_name': subpath})
                        n.parent = parent
                        added_dirnodes.append(fullname)
            # now the file node
            filenode = DPNode(name=md['entry_name'], isfile=True, metadata=md)
            parent_fullname = '/' + '/'.join(pathlist[:-1])
            parent = self._resolver.get(self._content_tree, parent_fullname)
            filenode.parent = parent

    def print_full_tree(self):
        for pre, _, node in anytree.render.RenderTree(self._content_tree):
            print("%s%s" % (pre, node.name))

    def print_dir_tree(self):
        for pre, _, node in anytree.render.RenderTree(self._content_tree):
            if not node.isfile:
                print("%s%s" % (pre, node.name))

    def get_folder_contents(self, folder):
        folder = self._resolver.get(self._content_tree, folder)
        return folder.children

    def get_standalone_notes(self):
        folder = self._resolver.get(self._content_tree, '/Document/Note')
        return folder.children

    def get_file(self, fn):
        res = self._resolver.get(self._content_tree, fn)
        return res


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
        Parsed file metadata as provided by DPT-RP1. For files see
        DPDataParser, directories have only entry_path and entry_name as keys.

    """
    def __init__(self, name, isfile, metadata):
        super(DPNode, self).__init__()
        self.name = name
        self.isfile = isfile
        self.metadata = metadata


class DPConfig(object):
    """Represent the configuration of the DPT-RP1.

    """
    def __init__(self):
        super(DPConfig, self).__init__()


class Downloader(object):
    """Manage downloading of files.

    Parameters
    ----------
    dp_mgr : DPManager

    """
    def __init__(self, dp_mgr):
        super(Downloader, self).__init__()
        self._dp_mgr = dp_mgr

    def _is_equal(self, source, dest):
        """Check if two files are equal.

        For now we just check for the size

        """
        source_size = self._dp_mgr.get_file(source).metadata['file_size']
        dest_size = osp.getsize(dest)
        if source_size == dest_size:
            return True
        else:
            return False

    def _check_datetime(self, source, dest):
        """Check if the dest or source is newer.

        """
        source_time = self._dp_mgr.get_file(source).metadata['modified_date']
        dest_time = datetime.datetime.fromtimestamp(osp.getmtime(dest))
        if source_size > dest_size:
            return 'source_newer'
        else:
            return 'dest_newer'

    def download_file(self, source, dest, policy='dp_wins'):
        """Download a file from the DPT-RP1.

        Parameter
        ---------
        source : string
            Full path to the file on the DPT-RP1
        dest : string
            Full path to the destination including the file name
        policy : 'dp_wins', 'loc_wins', 'newer'
            Decide what to do if the file is already present.

        """
        do_download = True
        if not source.startswith('/Document/'):
            print('ERROR: Source must start with "/Document/"')
        else:
            if osp.exists(dest):
                if self._is_equal(source, dest):
                    do_download = False
                    print('Skipping download of {}. Already present and equal.'.format(source))
                else:
                    if policy == 'loc_wins':
                        do_download = False
                        print('Skipping download of {}. Already present and loc_wins.'.format(source))
                    elif policy == 'dp_wins':
                        do_download = True
                    elif policy == 'newer':
                        if self._check_datetime(source, dest) == 'source_newer':
                            do_download = True
                        else:
                            do_download = False
                            print('Skipping download of {}. Already present and local file newer.'.format(source))
        if do_download:
            data = self._dp_mgr.dp.download(source[1:])
            with open(dest, 'wb') as f:
                f.write(data)

    def download_folder_contents(self, source, dest, policy='dp_wins'):
        """Download a full folder from the DPT-RP1.

        """
        if not source.startswith('/Document/'):
            print('ERROR: Source must start with "/Document/"')
        else:
            src_files = self._dp_mgr.get_folder_contents(source)
            if osp.exists(dest):
                for f in src_files:
                    src_fp = osp.join(source, f.name)
                    print('Downloading {}'.format(src_fp))
                    self.download_file(src_fp, osp.join(dest, f.name), policy)
            else:
                print('ERROR: Destination folder does not exist.')
                sys.exit(0)

    def download_notes(self, dest, policy='dp_wins'):
        """Download all notes.

        """
        src_files = self._dp_mgr.get_standalone_notes()
        if osp.exists(dest):
            for f in src_files:
                src_fp = osp.join('/Document/Note', f.name)
                print('Downloading {}'.format(src_fp))
                self.download_file(src_fp, osp.join(dest, f.name), policy)
        else:
            print('ERROR: Destination folder does not exist.')
            sys.exit(0)


class Uploader(object):
    """Manage uploading of files.

    Parameters
    ----------
    dp_mgr : DPManager

    """
    def __init__(self, dp_mgr):
        super(Uploader, self).__init__()
        self._dp_mgr = dp_mgr

    def upload_file(self, source, dest):
        with open(source, 'rb') as f:
            self._dp_mgr.dp.upload(f, dest)


def main():
    dp_mgr = DPManager('192.168.178.78')
    dp_mgr.print_full_tree()
    dp_mgr.print_dir_tree()
    nodes = dp_mgr.get_folder_contents('/Document/Reader/topics/quantum_simulation')
    for n in nodes:
        print(n.name)
    nodes = dp_mgr.get_standalone_notes()
    for n in nodes:
        print(n.name)

    downloader = Downloader(dp_mgr)
    # downloader.download_folder_contents('/Document/Reader/topics/quantum_simulation', '/home/cgross/Downloads')
    downloader.download_notes('/home/cgross/Downloads')

if __name__ == '__main__':
    main()
