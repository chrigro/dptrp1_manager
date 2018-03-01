#!/usr/bin/env python
# coding=utf-8

# dptrp1manager, high level tools to interact with the Sony DPT-RP1
# Copyright © 2018 Christian Gross

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
import configparser

import anytree
from dptrp1.dptrp1 import DigitalPaper
from dptrp1manager import tools

from pprint import pprint

CONFIGDIR = osp.join(osp.expanduser('~'), '.dpmgr')

class DPManager(object):
    """Main class to manage the DPT-RP1.

    Parameters
    ----------
    ip : string ('')
        The IP adress of the digital paper device. If empty (the default), use
        the config file.
    register : bool (False)
        If True, force registration of the client even if key and id files are
        found.

    Attributes
    ----------
    dp : DigitalPaper
        DigitalPaper instance

    """
    def __init__(self, ip='', register=False):
        super(DPManager, self).__init__()
        self._config = configparser.ConfigParser()
        self._checkconfigfile()
        addr = self._get_ip(ip)
        print('Attempting connection to ip {}'.format(addr))
        self.dp = DigitalPaper(addr)
        if self.dp is None:
            sys.exit(1)
        self._key_file = osp.join(CONFIGDIR, 'dptrp1_key')
        self._clientid_file = osp.join(CONFIGDIR, 'dptrp1_id')
        self._dataparser = DPDataParser()
        self._resolver = anytree.resolver.Resolver('name')
        self._content_tree = None

        self._check_registered(register)
        self._authenticate()
        self._build_tree()

    def _checkconfigfile(self):
        """Check the config file.

        """
        if osp.exists(osp.join(CONFIGDIR, 'dpmgr.conf')):
            self._config.read(osp.join(CONFIGDIR, 'dpmgr.conf'))
        if not self._config.has_section('IP'):
            self._config['IP'] = {}
            self._config['IP']['default'] = 'digitalpaper.local'
        with open(osp.join(CONFIGDIR, 'dpmgr.conf'), 'w') as f:
            self._config.write(f)

    def _get_ip(self, ip):
        if ip == '':
            ip = self._config['IP']['default']
            ssids = tools.get_ssids()
            print('Network info: {}'.format(ssids))
            if ssids is not None:
                # we are on linux, try to find configured ip
                for ssid in ssids.values():
                    if not ssid == '':
                        if self._config.has_option('IP', ssid):
                            ip = self._config['IP'][ssid]
                        else:
                            print('No custom IP defined for network {}'.format(ssid))
        return ip

    def _authenticate(self):
        with open(self._clientid_file, 'r') as f:
            client_id = f.readline().strip()
        with open(self._key_file, 'rb') as f:
            key = f.read()
        res = self.dp.authenticate(client_id, key)
        if res is False:
            sys.exit(1)

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
        res = self.dp.register()
        if res is not None:
            key = res[1]
            device_id = res[2]
            with open(self._key_file, 'w') as f:
                f.write(key)
            with open(self._clientid_file, 'w') as f:
                f.write(device_id)
        else:
            sys.exit(1)

    def _get_all_contents(self):
        data = self.dp.list_all()
        return data

    def _build_tree(self):
        data = self._get_all_contents()
        added_dirnodes = []
        # first folders
        for entry in data:
            if entry['entry_type'] == 'folder':
                md = self._dataparser.parsefolder(entry)
                pathlist = md['entry_path']
                for depth, subpath in enumerate(pathlist):
                    fullname = '/' + '/'.join(pathlist[:depth + 1])
                    parent_fullname = '/' + '/'.join(pathlist[:depth])
                    if self._content_tree is None and parent_fullname == '/':
                        n = DPNode(name=subpath, isfile=False, metadata={'entry_path': pathlist[:depth + 1],
                            'entry_name': subpath})
                        self._content_tree = n
                    elif not parent_fullname == '/':
                        if not fullname in added_dirnodes:
                            parent = self.get_node(parent_fullname)
                            n = DPNode(name=subpath, isfile=False, metadata={'entry_path': pathlist[:depth + 1],
                                'entry_name': subpath})
                            n.parent = parent
                            added_dirnodes.append(fullname)
        # now files
        for entry in data:
            if entry['entry_type'] == 'document':
                md = self._dataparser.parsefile(entry)
                pathlist = md['entry_path']
                filenode = DPNode(name=md['entry_name'], isfile=True, metadata=md)
                parent_fullname = '/' + '/'.join(pathlist[:-1])
                parent = self.get_node(parent_fullname)
                filenode.parent = parent

    def rebuild_tree(self):
        """Rebuild the local tree.

        """
        self._content_tree = None
        self._build_tree()

    def print_full_tree(self):
        for pre, _, node in anytree.render.RenderTree(self._content_tree):
            print("{}{}".format(pre, node.name))

    def print_dir_tree(self, path):
        if self.node_name_ok(path) and self.node_exists(path, print_error=False):
            for pre, _, node in anytree.render.RenderTree(self.get_node(path)):
                if not node.isfile:
                    print("{}{}".format(pre, node.name))

    def _sizeof_fmt(self, num, suffix='B'):
        for unit in ['','k','M','G','T','P','E','Z']:
            if abs(num) < 1024.0:
                return '{:3.1f}{}{}'.format(num, unit, suffix)
            num /= 1024.0
        return '{:.1f}{}{}'.format(num, 'Y', suffix)

    def print_folder_contents(self, path):
        if self.node_name_ok(path) and self.node_exists(path, print_error=False):
            for pre, _, node in anytree.render.RenderTree(self.get_node(path)):
                if node.isfile:
                    size = node.metadata['file_size']
                    print("{}[{}] {}".format(pre, self._sizeof_fmt(size), node.name))
                else:
                    print("{}{}".format(pre, node.name))

    def get_folder_contents(self, folder):
        folder = self.get_node(folder)
        return folder.children

    def get_node(self, path):
        res = self._resolver.get(self._content_tree, path)
        return res

    def node_exists(self, path, print_error=True):
        """Check if a node exists on the DPT-RP1.

        """
        try:
            self.get_node(path)
            return True
        except anytree.resolver.ResolverError:
            if print_error:
                print('ERROR: DPT-RP1 file or folder {} does not exist'.format(path))
            return False

    def node_name_ok(self, name):
        if not name.startswith('/Document'):
            print('ERROR: DPT-RP1 file or folder name must start with "/Document"')
            return False
        else:
            return True

    def file_name_ok(self, name):
        splitname = name.rsplit('.', maxsplit=1)
        if len(splitname) == 2 and splitname[1] == 'pdf':
            return True
        else:
            print('ERROR: DPT-RP1 file name must end with ".pdf"')
            return False

    def mkdir(self, path):
        """Create a new directory on the DPT-RP1.

        """
        if path.endswith('/'):
            path = path[:-1]
        if (self.node_name_ok(path) and
                self.node_exists(path.rsplit('/', maxsplit=1)[0])):
            if not self.node_exists(path, print_error=False):
                print('Creating folder {}'.format(path))
                self.dp.new_folder(path[1:])
            else:
                print('ERROR: DPT-RP1 has already a folder {}'.format(path))

    def rm_dir(self, path):
        """Delete a (empty) directory on the DPT-RP1.

        """
        if path.endswith('/'):
            path = path[:-1]
        if (self.node_name_ok(path) and self.node_exists(path)):
            print('Deleting dir {}.'.format(path))
            self.dp.delete_directory(path[1:])

    def rm_file(self, path):
        """Delete a file on the DPT-RP1.

        """
        if (self.node_name_ok(path) and self.node_exists(path)):
            print('Deleting file {}.'.format(path))
            self.dp.delete_document(path[1:])

    def rm(self, path):
        """Delete a file or (empty) directory.

        """
        if (self.node_name_ok(path) and self.node_exists(path)):
            n = self.get_node(path)
            if n.isfile == True:
                self.rm_file(path)
            else:
                self.rm_dir(path)

    def rm_allfiles(self, path):
        """Delete all files in a directory on the DPT-RP1, but do not recurse
        into subdirectories.

        """
        if (self.node_name_ok(path) and self.node_exists(path)):
            files = self.get_folder_contents(path)
            for f in files:
                if f.isfile:
                    pathlist = f.metadata['entry_path']
                    remote_path = '/' + '/'.join(pathlist[:])
                    self.rm_file(remote_path)

    def rm_allfiles_recursively(self, path):
        """Delete all files and folders in a directory on the DPT-RP1. Do not
        delete the directory itself.

        """
        if (self.node_name_ok(path) and self.node_exists(path)):
            files = self.get_folder_contents(path)
            for f in files:
                if f.isfile:
                    pathlist = f.metadata['entry_path']
                    remote_path = '/' + '/'.join(pathlist[:])
                    self.rm_file(remote_path)
                else:
                    pathlist = f.metadata['entry_path']
                    new_path = '/' + '/'.join(pathlist[:])
                    self.rm_allfiles_recursively(new_path)
                    self.rm_dir(new_path)


class DPDataParser(object):
    """Parser for the data returned for each document.

    """
    def __init__(self):
        super(DPDataParser, self).__init__()

    def parsefile(self, data):
        """Parse the entry data for files.

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

    def parsefolder(self, data):
        """Parse the entry data for folders.

        Returns
        -------
        dict
            Parsed metadata dictionary. It has the following structure:
            'entry_id': string
            'entry_name': string (folder name)
            'entry_type': 'folder'
            'is_new': bool
            'parent_folder_id': string
            'entry_path': list of strings (full path)
            'created_date': datetime

        """
        res = {}
        # some keys are easy to parse
        res['entry_id'] = data['entry_id']
        res['entry_name'] = data['entry_name']
        res['entry_type'] = data['entry_type']
        res['is_new'] = bool(data['is_new'])
        res['parent_folder_id'] = data['parent_folder_id']
        res['entry_path'] = self._splitpath(data['entry_path'])
        res['created_date'] = self._string_to_datetime(data['created_date'])
        return res

    def _string_to_datetime(self, string):
        dt = datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ')
        return dt

    def _splitpath(self, string):
        path = osp.normpath(string)
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


class FileTransferHandler(object):
    """Base class for the Downloader and Uploader.

    Parameters
    ----------
    dp_mgr : DPManager

    """
    def __init__(self, dp_mgr):
        super(FileTransferHandler, self).__init__()
        self._dp_mgr = dp_mgr

    def _is_equal(self, local, remote):
        """Check if two files are equal.

        For now we just check for the size

        """
        remote_size = self._dp_mgr.get_node(remote).metadata['file_size']
        local_size = osp.getsize(local)
        if remote_size == local_size:
            return True
        else:
            return False

    def _check_datetime(self, local, remote):
        """Check if the local or remote file is newer.

        """
        remote_time = self._dp_mgr.get_node(remote).metadata['modified_date']
        local_time = datetime.datetime.fromtimestamp(osp.getmtime(local))
        print('{}: {}'.format(remote,remote_time))
        print('{}: {}'.format(local,local_time))
        if remote_time > local_time:
            return 'remote_newer'
        else:
            return 'local_newer'

    def _local_path_ok(self, path, printerr=True):
        if not osp.exists(path):
            if printerr:
                print('ERROR: Local file or folder {} does not exist.'.format(path))
            return False
        else:
            return True

    def _check_policy(self, policy):
        policies = ('remote_wins', 'local_wins', 'newer', 'skip')
        if not policy in policies:
            print('ERROR: Policy must be one of {}'.format(policies))
            return False
        else:
            return True


class Downloader(FileTransferHandler):
    """Manage downloading of files.

    """
    def __init__(self, dp_mgr):
        super(Downloader, self).__init__(dp_mgr)

    def download_file(self, source, dest, policy='skip'):
        """Download a file from the DPT-RP1.

        Parameter
        ---------
        source : string
            Full path to the file on the DPT-RP1
        dest : string
            Path to the destination including the file name
        policy : 'remote_wins', 'local_wins', 'newer', 'skip'
            Decide what to do if the file is already present.

        """
        dest = osp.expanduser(dest)
        if (self._check_policy(policy) and
                self._dp_mgr.node_name_ok(source) and
                self._dp_mgr.node_exists(source) and
                self._local_path_ok(osp.dirname(dest)) and
                self._dp_mgr.get_node(source).isfile):
            do_transfer = True
            if osp.exists(dest):
                if self._is_equal(dest, source):
                    do_transfer = False
                    print('EQUAL: Skipping download of {}'.format(osp.basename(source)))
                else:
                    if policy == 'local_wins':
                        do_transfer = False
                        print('LOCAL_WINS: Skipping download of {}'.format(osp.basename(source)))
                    elif policy == 'remote_wins':
                        do_transfer = True
                    elif policy == 'newer':
                        if self._check_datetime(dest, source) == 'remote_newer':
                            do_transfer = True
                        else:
                            do_transfer = False
                            print('NEWER: Skipping download of {}'.format(osp.basename(source)))
                    elif policy == 'skip':
                        do_transfer = False
                        print('SKIP: Skipping download of {}'.format(osp.basename(source)))
            if do_transfer:
                print('Downloading {}'.format(source))
                data = self._dp_mgr.dp.download(source[1:])
                with open(dest, 'wb') as f:
                    f.write(data)
        else:
            print('ERROR: Failed downloading {}. File not found.'.format(source))

    def download_folder_contents(self, source, dest, policy='skip'):
        """Download a full folder from the DPT-RP1.

        """
        dest = osp.expanduser(dest)
        if (self._check_policy(policy) and
                self._dp_mgr.node_name_ok(source) and
                self._dp_mgr.node_exists(source)):
            src_files = self._dp_mgr.get_folder_contents(source)
            if self._local_path_ok(dest):
                for f in src_files:
                    if f.isfile:
                        src_fp = osp.join(source, f.name)
                        self.download_file(src_fp, osp.join(dest, f.name), policy)

    def download_recursively(self, source, dest, policy='skip'):
        """Download recursively.

        """
        dest = osp.expanduser(dest)
        if not self._local_path_ok(dest):
            return None
        if (self._check_policy(policy) and
                self._dp_mgr.node_name_ok(source) and
                self._dp_mgr.node_exists(source)):
            src_nodes = self._dp_mgr.get_folder_contents(source)
            for f in src_nodes:
                if f.isfile:
                    src_fp = osp.join(source, f.name)
                    self.download_file(src_fp, osp.join(dest, f.name), policy)
                else:
                    new_local_path = osp.join(dest, f.name)
                    pathlist = f.metadata['entry_path']
                    new_remote_path = '/' + '/'.join(pathlist[:])
                    if not self._local_path_ok(new_local_path, printerr=False):
                        os.mkdir(new_local_path)
                    self.download_recursively(new_remote_path, new_local_path, policy)


class Uploader(FileTransferHandler):
    """Manage uploading of files.

    """
    def __init__(self, dp_mgr):
        super(Uploader, self).__init__(dp_mgr)

    def upload_file(self, source, dest, policy='skip'):
        """Upload a file to the DPT-RP1.

        Parameter
        ---------
        source : string
            Path to the source
        dest : string
            Full path to the file on the DPT-RP1 (incl. file name)
        policy : 'remote_wins', 'local_wins', 'newer', 'skip'
            Decide what to do if the file is already present.

        """
        source = osp.expanduser(source)
        if (self._check_policy(policy) and
                self._dp_mgr.node_name_ok(dest) and
                self._dp_mgr.node_exists(dest.rsplit('/', maxsplit=1)[0]) and
                self._local_path_ok(source) and
                self._dp_mgr.file_name_ok(dest)):
            do_transfer = True
            if self._dp_mgr.node_exists(dest, print_error=False):
                if self._is_equal(source, dest):
                    do_transfer = False
                    print('EQUAL: Skipping upload of {}'.format(osp.basename(source)))
                else:
                    if policy == 'local_wins':
                        # delete the old file
                        self._dp_mgr.rm_file(dest)
                        do_transfer = True
                    elif policy == 'remote_wins':
                        do_transfer = False
                        print('REMOTE_WINS: Skipping upload of {}'.format(osp.basename(source)))
                    elif policy == 'newer':
                        if self._check_datetime(source, dest) == 'local_newer':
                            # delete the old file
                            self._dp_mgr.rm_file(dest)
                            do_transfer = True
                        else:
                            do_transfer = False
                            print('NEWER: Skipping upload of {}'.format(osp.basename(source)))
                    elif policy == 'skip':
                        do_transfer = False
                        print('SKIP: Skipping upload of {}'.format(osp.basename(source)))
            if do_transfer:
                print('Adding file {}'.format(dest))
                with open(source, 'rb') as f:
                    self._dp_mgr.dp.upload(f, dest[1:])

    def upload_folder_contents(self, source, dest, policy='skip'):
        """Upload a full folder to the DPT-RP1.

        """
        source = osp.expanduser(source)
        if (self._check_policy(policy) and
                self._local_path_ok(source)):
            src_files = (osp.join(source, fn) for fn in os.listdir(source)
                    if osp.isfile(osp.join(source, fn)))
            if self._dp_mgr.node_name_ok(dest) and self._dp_mgr.node_exists(dest):
                for f in src_files:
                    dest_fn = dest + '/' + osp.basename(f)
                    self.upload_file(f, dest_fn, policy)

    def upload_recursively(self, source, dest, policy='skip'):
        """Upload recursively.

        """
        source = osp.expanduser(source)
        if (self._check_policy(policy) and
                self._local_path_ok(source)):
            if self._dp_mgr.node_name_ok(dest) and self._dp_mgr.node_exists(dest):
                src_files = (osp.join(source, fn) for fn in os.listdir(source)
                        if osp.isfile(osp.join(source, fn)))
                for f in src_files:
                    dest_fn = dest + '/' + osp.basename(f)
                    self.upload_file(f, dest_fn, policy)
                src_dirs = (osp.join(source, fn) for fn in os.listdir(source)
                        if osp.isdir(osp.join(source, fn)))
                for d in src_dirs:
                    new_remote_path = dest + '/' + osp.basename(d)
                    new_local_path = d
                    if not self._dp_mgr.node_exists(new_remote_path, print_error=False):
                        self._dp_mgr.mkdir(new_remote_path)
                        self._dp_mgr.rebuild_tree()
                    self.upload_recursively(new_local_path, new_remote_path, policy)


class Synchronizer(FileTransferHandler):
    """Syncronize the DPT-RP1 with a folder.

    """
    def __init__(self, dp_mgr):
        super(Synchronizer, self).__init__(dp_mgr)
        self._downloader = Downloader(dp_mgr)
        self._uploader = Uploader(dp_mgr)
        self._config = configparser.ConfigParser()
        self._checkconfigfile()

    def _checkconfigfile(self):
        """Check the config file.

        """
        if osp.exists(osp.join(CONFIGDIR, 'sync.conf')):
            self._config.read(osp.join(CONFIGDIR, 'sync.conf'))
        if self._config.sections() == []:
            self._config['pair1'] = {}
            self._config['pair1']['local_path'] = '<replace by local path>'
            self._config['pair1']['remote_path'] = '<replace by remote path>'
            self._config['pair1']['policy'] = '<one of: remote_wins, local_wins, newer, skip>'
        with open(osp.join(CONFIGDIR, 'sync.conf'), 'w') as f:
            self._config.write(f)

    def sync_folder(self, local, remote, policy='skip'):
        """Synchronize a local and remote folder recursively.

        Parameters
        ----------
        local : string
            Path to the source
        remote : string
            Full path to the folder on the DPT-RP1
        policy : 'remote_wins', 'local_wins', 'newer', 'skip'
            Decide what to do if the file is already present.

        """
        self._downloader.download_recursively(remote, local, policy)
        self._uploader.upload_recursively(local, remote, policy)

    def sync_pairs(self):
        """Sync the pairs defined in the config file.

        """
        for pair in self._config.sections():
            print('---Staring to sync pair {}---'.format(pair))
            lp = self._config[pair]['local_path']
            rp = self._config[pair]['remote_path']
            pol = self._config[pair]['policy']
            self.sync_folder(lp, rp, pol)


class DPConfig(object):
    """Represent the configuration of the DPT-RP1.

    Parameters
    ----------
    dp_mgr : DPManager

    """
    def __init__(self, dp_mgr):
        super(DPConfig, self).__init__()
        self._dp_mgr = dp_mgr

    @property
    def templates(self):
        """List of templates.

        """
        res = self._dp_mgr.dp.list_templates()
        tmp_list = []
        for template in res['template_list']:
            tmp_list.append(template['template_name'])
        return tmp_list

    def rename_template(self, old_name, new_name):
        self._dp_mgr.dp.rename_template(old_name, new_name)

    def delete_template(self, name):
        self._dp_mgr.dp.delete_template(name)

    def add_template(self, name, path):
        path = osp.expanduser(path)
        if osp.exists(path) and path.endswith('.pdf'):
            with open(path, 'rb') as f:
                self._dp_mgr.dp.add_template(name, f)
        else:
            print('Adding template failed. File {} not found or not a pdf file.'.format(path))

    @property
    def timeout(self):
        """Timeout to lock in minutes

        """
        timeout = self._dp_mgr.dp.get_timeout()
        return timeout

    @timeout.setter
    def timeout(self, val):
        self.dp._dp_mgr.set_timeout(value)

    @property
    def owner(self):
        """Owner of the device (for pdf comments)

        """
        owner = self._dp_mgr.dp.get_owner()
        return owner

    @owner.setter
    def owner(self, val):
        self._dp_mgr.dp.set_owner(value)

    @property
    def time_format(self):
        """The time format.

        """
        time_format = self._dp_mgr.dp.get_time_format()
        return time_format

    @time_format.setter
    def time_format(self, val):
        self._dp_mgr.dp.set_time_format(value)

    @property
    def date_format(self):
        """The date format

        """
        date_format = self._dp_mgr.dp.get_date_format()
        return date_format

    @date_format.setter
    def date_format(self, val):
        self._dp_mgr.dp.set_date_format(value)

    @property
    def timezone(self):
        """The timezone

        """
        timezone = self._dp_mgr.dp.get_timezone()
        return timezone

    @timezone.setter
    def timezone(self, val):
        self._dp_mgr.dp.set_timezone(value)

    @property
    def storage_free(self):
        """Free space on device in Byte

        """
        storage = self._dp_mgr.dp.get_storage()
        free = float(storage['available'])
        return free

    @property
    def storage_total(self):
        """Total storage capacity in Byte

        """
        storage = self._dp_mgr.dp.get_storage()
        total = float(storage['capacity'])
        return total

    @property
    def battery_level(self):
        """Battery level in percent.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery['level']

    @property
    def battery_pen(self):
        """Pen battery level in percent.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery['pen']

    @property
    def battery_health(self):
        """Battery health

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery['health']

    @property
    def battery_status(self):
        """Battery status (charging/discharging)

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery['status']

    @property
    def plugged(self):
        """Check if connected via usb for charging.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery['plugged']

    @property
    def model(self):
        """The model name

        """
        info = self._dp_mgr.dp.get_info()
        return info['model_name']

    @property
    def serial(self):
        """The seral number of the device

        """
        info = self._dp_mgr.dp.get_info()
        return info['serial_number']

    @property
    def firmware_version(self):
        """Get the firmware version

        """
        fw_version = self._dp_mgr.dp.get_firmware_version()
        return fw_version

    @property
    def mac_address(self):
        """The mac address

        """
        mac_address = self._dp_mgr.dp.get_mac_address()
        return mac_address

    def list_wifi(self):
        """List known wifis.

        """
        return self._dp_mgr.dp.wifi_list()

    def scan_wifi(self):
        """Scan wifis

        """
        return self._dp_mgr.dp.wifi_scan()

    def add_wifi(self, ssid, security='nonsec', passwd='', dhcp=True, static_address='', gateway='',
            network_mask='', dns1='', dns2='', proxy=False):
        """Add a wifi network.

        Parameters
        ----------
        ssid : string
            Wifi network name
        security : string ('nonsec', 'psk')
            Wifi security, default is 'nonsec'
        passwd : string
            Password, default is ''
        dhcp : bool (default True)
            Use dhcp for ip address management?
        static_address : string (default '')
            Static ip
        gateway : string (default '')
            Gateway ip
        network_mask : integer
            Integer determining the net mask (e.g. 24)
        dns1 : string (default '')
            DNS ip
        dns2 : string (default '')
            DNS ip
        proxy : bool (default False)
            Use a proxy?

        """
        self._dp_mgr.dp.configure_wifi(ssid, security, passwd, dhcp,
                static_address, gateway, network_mask, dns1, dns2, proxy)

    def delete_wifi(self, ssid, security='nonsec'):
        """Delete a known wifi

        Parameters
        ----------
        ssid : string
            Wifi network name
        security : string ('nonsec', 'psk')
            Wifi security, default is 'nonsec'

        """
        self._dp_mgr.dp.delete_wifi(ssid, security)

    @property
    def wifi_enabled(self):
        """Is wifi enabled?

        """
        val = self._dp_mgr.dp.wifi_enabled()['value']
        if val == 'on':
            return True
        else:
            return False

    def enable_wifi(self):
        self._dp_mgr.dp.enable_wifi()

    def disable_wifi(self):
        self._dp_mgr.dp.disable_wifi()


def main():
    dp_mgr = DPManager()
    config = DPConfig(dp_mgr)
    downloader = Downloader(dp_mgr)
    uploader = Uploader(dp_mgr)
    synchronizer = Synchronizer(dp_mgr)

    # synchronizer.sync_pairs()

    # print(config.wifi_enabled)

    # dp_mgr.print_full_tree()
    # dp_mgr.print_dir_tree()
    # dp_mgr.print_folder_contents('/Document/Reader/topics')

    # synchronizer.sync_folder(local='/home/cgross/Reader/projects', remote='/Document/Reader/projects', policy='remote_wins')

    # dp_mgr.rename_template('daily_planner', 'planner')
    # dp_mgr.delete_template('test')
    # dp_mgr.add_template('testA5', '/home/cgross/Downloads/test2.pdf')

    # downloader.download_recursively('/Document/Reader/projects', '/home/cgross/Downloads/test', 'remote_wins')
    # dp_mgr.rm_allfiles_recursively('/Document/Reader/projects')
    # uploader.upload_recursively('/home/cgross/Downloads/test', '/Document/Reader/projects', 'remote_wins')

    # downloader.download_folder_contents('/Document/Reader/topics/quantum_simulation', '/home/cgross/Downloads')
    # downloader.download_standalone_notes('/home/cgross/Downloads', policy='remote_wins')

    # dp_mgr.mkdir('/Document/testfolder')

    # uploader.upload_folder_contents('/home/cgross/Reader/projects/physikjournal', '/Document/Reader/projects/physikjournal', policy='remote_wins')
    # uploader.upload_folder_contents('/home/cgross/Downloads/test', '/Document/Reader/test', policy='remote_wins')



if __name__ == '__main__':
    main()
