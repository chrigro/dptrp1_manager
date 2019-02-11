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
import subprocess
import re
import socket
import psutil
import time
import requests

import serial
import anytree
from anytree import PreOrderIter
from dptrp1manager import tools, remotetree, mydptrp1, localtree

from pprint import pprint

CONFIGDIR = osp.join(osp.expanduser("~"), ".dpmgr")

# on usb
# dptrp1  --addr "[fe80::b47f:46ff:fe5d:7741%enp0s20f0u2]" list-documents


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

    def __init__(self, ip="", register=False):
        super(DPManager, self).__init__()
        self._config = configparser.ConfigParser()
        self._checkconfigfile()
        addr = self._get_ip(ip)
        print("Attempting connection to ip {}".format(addr))
        self.dp = mydptrp1.MyDigitalPaper(addr)
        if self.dp is None:
            sys.exit(1)
        self._key_file = osp.join(CONFIGDIR, "dptrp1_key")
        self._clientid_file = osp.join(CONFIGDIR, "dptrp1_id")
        self._resolver = anytree.resolver.Resolver("name")
        self._remote_tree = None

        self._check_registered(register)
        self._authenticate()
        self._build_tree()

    def _checkconfigfile(self):
        """Check the config file.

        """
        if osp.exists(osp.join(CONFIGDIR, "dpmgr.conf")):
            self._config.read(osp.join(CONFIGDIR, "dpmgr.conf"))
        if not self._config.has_section("IP"):
            self._config["IP"] = {}
            self._config["IP"]["default"] = "digitalpaper.local"
        with open(osp.join(CONFIGDIR, "dpmgr.conf"), "w") as f:
            self._config.write(f)

    def _interface_up(self, interface):
        """Check if the net interface is up.

        """
        interface_addrs = psutil.net_if_addrs().get(interface) or []
        return socket.AF_INET in [snicaddr.family for snicaddr in interface_addrs]

    def _wait_until_connected(self, interface):
        retry = 0
        print("Connecting ", end="", flush=True)
        while (not self._interface_up(interface)) and retry < 50:
            time.sleep(0.3)
            retry += 1
            print(".", end="", flush=True)
        if not self._interface_up(interface):
            print("Could not connect to the DPT-RP1 via USB, exiting.")
            sys.exit(1)
        print("\n", end="", flush=True)

    def _get_ip(self, ip):
        # prefer usb
        if self._is_usb_conneted():
            self._set_up_eth_usb()
            ip_bare = self._config["USB"]["ipv6"]
            iface = self._config["USB"]["interface"]
            self._wait_until_connected(iface)
            ip = "[{}%{}]".format(ip_bare, iface)
            print("Using ethernet over USB with ip {} to connect.".format(ip))
        elif ip == "":
            ip = self._config["IP"]["default"]
            ssids = tools.get_ssids()
            print("Network info: {}".format(ssids))
            if ssids is not None:
                # we are on linux, try to find configured ip
                for ssid in ssids.values():
                    if not ssid == "":
                        if self._config.has_option("IP", ssid):
                            ip = self._config["IP"][ssid]
                        else:
                            print("No custom IP defined for network {}".format(ssid))
        return ip

    def _is_usb_conneted(self):
        """use lsusb. **this is linux specific!**

        """
        res = False
        device_re = re.compile(
            "Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$",
            re.I,
        )
        df = str(subprocess.check_output("lsusb"), encoding="UTF8")
        devices = []
        for i in df.split("\n"):
            if i:
                info = device_re.match(i)
                if info:
                    dinfo = info.groupdict()
                    dinfo["device"] = "/dev/bus/usb/%s/%s" % (
                        dinfo.pop("bus"),
                        dinfo.pop("device"),
                    )
                    devices.append(dinfo)
        for dev in devices:
            if dev["tag"] == "Sony Corp. ":
                res = True
        return res

    def _set_up_eth_usb(self):
        """Set up ethernet usb functionality in linux.

        See https://github.com/janten/dpt-rp1-py/blob/master/docs/linux-ethernet-over-usb.md

        Notes
        -----
        The user must be in the group that own /dev/ttyACM0

        """
        # use RNDIS mode
        # send_val = b"\x01\x00\x00\x01\x00\x00\x00\x01\x00\x04"

        # use CDC/ECM mode
        send_val = b"\x01\x00\x00\x01\x00\x00\x00\x01\x01\x04"
        try:
            ser = serial.Serial(
                "/dev/ttyACM0",
                9600,
                serial.EIGHTBITS,
                serial.PARITY_NONE,
                serial.STOPBITS_ONE,
            )
            ser.write(send_val)
        except serial.serialutil.SerialException:
            try:
                ser = serial.Serial(
                    "/dev/ttyACM1",
                    9600,
                    serial.EIGHTBITS,
                    serial.PARITY_NONE,
                    serial.STOPBITS_ONE,
                )
                ser.write(send_val)
            except:
                pass

    def _authenticate(self):
        with open(self._clientid_file, "r") as f:
            client_id = f.readline().strip()
        with open(self._key_file, "rb") as f:
            key = f.read()
        try:
            res = self.dp.authenticate(client_id, key)
        except requests.exceptions.ConnectionError:
            print("\nERROR: Cannot connect to the device. USB connected? Wifi on?")
            sys.exit(1)
        if res is False:
            print(
                "\nERROR: Cannot authenticate with the device. Is the client ID and key correct?"
            )
            sys.exit(1)

    def _check_configpath(self):
        if not osp.exists(CONFIGDIR):
            os.mkdir(CONFIGDIR)

    def _check_registered(self, register):
        self._check_configpath()
        if not register:
            if not osp.exists(self._clientid_file) or not osp.exists(self._key_file):
                self._register()
        else:
            self._register()

    def _register(self):
        res = self.dp.register()
        if res is not None:
            key = res[1]
            device_id = res[2]
            with open(self._key_file, "w") as f:
                f.write(key)
            with open(self._clientid_file, "w") as f:
                f.write(device_id)
        else:
            sys.exit(1)

    def _get_all_contents(self):
        data = self.dp.list_all()
        return data

    def _build_tree(self):
        data = self._get_all_contents()
        self._remote_tree = remotetree.RemoteTree()
        self._remote_tree.rebuild_tree(data)

    def rebuild_tree(self):
        """Rebuild the local tree.

        """
        self._remote_tree = None
        self._build_tree()

    @property
    def remote_tree(self):
        return self._remote_tree

    def print_full_tree(self):
        self._remote_tree.printtree(path, foldersonly=False)

    def print_dir_tree(self, path):
        path = self.fix_path(path)
        self._remote_tree.printtree(path, foldersonly=True)

    def print_folder_contents(self, path):
        path = self.fix_path(path)
        self._remote_tree.print_folder_contents(path)

    def get_folder_contents(self, folder):
        folder = self.get_node(folder)
        return folder.children

    def get_node(self, path):
        path = self.fix_path(path)
        res = self._remote_tree.get_node_by_path(path)
        return res

    def node_exists(self, path, print_error=True):
        """Check if a node exists on the DPT-RP1.

        """
        path = self.fix_path(path)
        if self.get_node(path) is None:
            return False
        else:
            return True

    def fix_path(self, path):
        """Append Document/ to path and remove trailing / if necessary.

        """
        if path.endswith("/"):
            path = path[:-1]
        if not path.startswith("Document"):
            return "Document/{}".format(path)
        else:
            return path

    def file_name_ok(self, name):
        splitname = name.rsplit(".", maxsplit=1)
        if len(splitname) == 2 and splitname[1] == "pdf":
            return True
        else:
            print('ERROR: DPT-RP1 file name must end with ".pdf"')
            return False

    def mkdir(self, path):
        """Create a new directory on the DPT-RP1.

        """
        path = self.fix_path(path)
        parent_folder, new_folder = path.rsplit("/", maxsplit=1)
        if self.node_exists(parent_folder):
            if not self.node_exists(path, print_error=False):
                print("Creating folder {}".format(path))
                parent_folder_id = self.get_node(parent_folder).entry_id
                self.dp.new_folder_byid(parent_folder_id, new_folder)
            else:
                print("ERROR: DPT-RP1 has already a folder {}".format(path))

    def rm_dir(self, path):
        """Delete a (empty) directory on the DPT-RP1.

        """
        path = self.fix_path(path)
        if self.node_exists(path):
            print("Deleting dir {}.".format(path))
            dir_id = self.get_node(path).entry_id
            self._rm_dir(dir_id)

    def _rm_dir(self, dir_id):
        self.dp.delete_directory_byid(dir_id)

    def rm_file(self, path):
        """Delete a file on the DPT-RP1.

        """
        path = self.fix_path(path)
        if self.node_exists(path):
            print("Deleting file {}.".format(path))
            file_id = self.get_node(path).entry_id
            self._rm_file(file_id)

    def _rm_file(self, file_id):
        self.dp.delete_document_byid(file_id)

    def rm(self, path):
        """Delete a file or (empty) directory.

        """
        path = self.fix_path(path)
        if self.node_exists(path):
            n = self.get_node(path)
            if n.entry_type == "document":
                self.rm_file(path)
            else:
                self.rm_dir(path)

    def rm_allfiles(self, path):
        """Delete all files in a directory on the DPT-RP1, but do not recurse
        into subdirectories.

        """
        path = self.fix_path(path)
        if self.node_exists(path):
            files = self.get_folder_contents(path)
            for f in files:
                if f.entry_type == "document":
                    self.rm_file(f.entry_path)

    def rm_allfiles_recursively(self, path):
        """Delete all files and folders in a directory on the DPT-RP1. Do not
        delete the directory itself.

        """
        path = self.fix_path(path)
        if self.node_exists(path):
            files = self.get_folder_contents(path)
            for f in files:
                if f.entry_type == "document":
                    self.rm_file(f.entry_path)
                else:
                    self.rm_allfiles_recursively(f.entry_path)
                    self.rm_dir(f.entry_path)


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
        remote_size = self._dp_mgr.get_node(remote).file_size
        local_size = osp.getsize(local)
        if remote_size == local_size:
            return True
        else:
            return False

    def _check_datetime(self, local, remote):
        """Check if the local or remote file is newer.

        """
        remote_time = self._dp_mgr.get_node(remote).modified_date
        local_time = datetime.datetime.fromtimestamp(osp.getmtime(local))
        print("{}: {}".format(remote, remote_time))
        print("{}: {}".format(local, local_time))
        if remote_time > local_time:
            return "remote_newer"
        else:
            return "local_newer"

    def _local_path_ok(self, path, printerr=True):
        if not osp.exists(path):
            if printerr:
                print("ERROR: Local file or folder {} does not exist.".format(path))
            return False
        else:
            return True

    def _check_policy(self, policy):
        policies = ("remote_wins", "local_wins", "newer", "skip")
        if policy not in policies:
            print("ERROR: Policy must be one of {}".format(policies))
            return False
        else:
            return True


class Downloader(FileTransferHandler):
    """Manage downloading of files.

    """

    def __init__(self, dp_mgr):
        super(Downloader, self).__init__(dp_mgr)

    def download_file(self, source, dest, policy="skip"):
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
        if osp.isdir(dest):
            # take the filename from remote
            dest = osp.join(dest, source.rsplit("/")[-1])
        source = self._dp_mgr.fix_path(source)
        source_node = self._dp_mgr.get_node(source)
        if (
            self._check_policy(policy)
            and self._dp_mgr.node_exists(source)
            and self._local_path_ok(osp.dirname(dest))
            and source_node.entry_type == "document"
        ):
            do_transfer = True
            if osp.exists(dest):
                if self._is_equal(dest, source):
                    do_transfer = False
                    # print("EQUAL: Skipping download of {}".format(osp.basename(source)))
                else:
                    if policy == "local_wins":
                        do_transfer = False
                        print(
                            "LOCAL_WINS: Skipping download of {}".format(
                                osp.basename(source)
                            )
                        )
                    elif policy == "remote_wins":
                        do_transfer = True
                    elif policy == "newer":
                        if self._check_datetime(dest, source) == "remote_newer":
                            do_transfer = True
                        else:
                            do_transfer = False
                            print(
                                "NEWER: Skipping download of {}".format(
                                    osp.basename(source)
                                )
                            )
                    elif policy == "skip":
                        do_transfer = False
                        print(
                            "SKIP: Skipping download of {}".format(osp.basename(source))
                        )
            if do_transfer:
                print("Downloading {}".format(source))
                data = self._dp_mgr.dp.download_byid(source_node.entry_id)
                with open(dest, "wb") as f:
                    f.write(data)
        else:
            print("ERROR: Failed downloading {}. File not found.".format(source))

    def download_folder_contents(self, source, dest, policy="skip"):
        """Download a full folder from the DPT-RP1.

        """
        dest = osp.expanduser(dest)
        source = self._dp_mgr.fix_path(source)
        if self._check_policy(policy) and self._dp_mgr.node_exists(source):
            src_files = self._dp_mgr.get_folder_contents(source)
            if self._local_path_ok(dest):
                for f in src_files:
                    if f.entry_type == "document":
                        self.download_file(
                            f.entry_path, osp.join(dest, f.entry_name), policy
                        )

    def download_recursively(self, source, dest, policy="skip"):
        """Download recursively.

        """
        dest = osp.expanduser(dest)
        source = self._dp_mgr.fix_path(source)
        if not self._local_path_ok(dest):
            return None
        if self._check_policy(policy) and self._dp_mgr.node_exists(source):
            src_nodes = self._dp_mgr.get_folder_contents(source)
            for f in src_nodes:
                if f.entry_type == "document":
                    self.download_file(
                        f.entry_path, osp.join(dest, f.entry_name), policy
                    )
                else:
                    new_local_path = osp.join(dest, f.entry_name)
                    if not self._local_path_ok(new_local_path, printerr=False):
                        os.mkdir(new_local_path)
                    self.download_recursively(f.entry_path, new_local_path, policy)


class Uploader(FileTransferHandler):
    """Manage uploading of files.

    """

    def __init__(self, dp_mgr):
        super(Uploader, self).__init__(dp_mgr)

    def upload_file(self, source, dest, policy="skip"):
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
        dest = self._dp_mgr.fix_path(dest)
        if not dest.endswith(".pdf"):
            if dest.endswith("/"):
                dest_dir = dest[:-1]
            dest = "{}/{}".format(dest, osp.basename(source))
        dest_dir, dest_fn = dest.rsplit("/", maxsplit=1)
        if (
            self._check_policy(policy)
            and self._dp_mgr.node_exists(dest_dir)
            and self._local_path_ok(source)
            and self._dp_mgr.file_name_ok(dest)
        ):
            do_transfer = True
            if self._dp_mgr.node_exists(dest, print_error=False):
                if self._is_equal(source, dest):
                    do_transfer = False
                    # print("EQUAL: Skipping upload of {}".format(osp.basename(source)))
                else:
                    if policy == "local_wins":
                        # delete the old file
                        self._dp_mgr.rm_file(dest)
                        do_transfer = True
                    elif policy == "remote_wins":
                        do_transfer = False
                        print(
                            "REMOTE_WINS: Skipping upload of {}".format(
                                osp.basename(source)
                            )
                        )
                    elif policy == "newer":
                        if self._check_datetime(source, dest) == "local_newer":
                            # delete the old file
                            self._dp_mgr.rm_file(dest)
                            do_transfer = True
                        else:
                            do_transfer = False
                            print(
                                "NEWER: Skipping upload of {}".format(
                                    osp.basename(source)
                                )
                            )
                    elif policy == "skip":
                        do_transfer = False
                        print(
                            "SKIP: Skipping upload of {}".format(osp.basename(source))
                        )
            if do_transfer:
                print("Adding file {}".format(dest))
                with open(source, "rb") as f:
                    dest_dir_node = self._dp_mgr.get_node(dest_dir)
                    self._dp_mgr.dp.upload_byid(f, dest_dir_node.entry_id, dest_fn)

    def upload_folder_contents(self, source, dest, policy="skip"):
        """Upload a full folder to the DPT-RP1.

        """
        source = osp.expanduser(source)
        dest = self._dp_mgr.fix_path(dest)
        if self._check_policy(policy) and self._local_path_ok(source):
            src_files = (
                osp.join(source, fn)
                for fn in os.listdir(source)
                if osp.isfile(osp.join(source, fn))
            )
            if self._dp_mgr.node_exists(dest):
                for f in src_files:
                    dest_fn = dest + "/" + osp.basename(f)
                    self.upload_file(f, dest_fn, policy)

    def upload_recursively(self, source, dest, policy="skip"):
        """Upload recursively.

        """
        source = osp.expanduser(source)
        dest = self._dp_mgr.fix_path(dest)
        if self._check_policy(policy) and self._local_path_ok(source):
            if self._dp_mgr.node_exists(dest):
                src_files = (
                    osp.join(source, fn)
                    for fn in os.listdir(source)
                    if osp.isfile(osp.join(source, fn))
                )
                for f in src_files:
                    dest_fn = dest + "/" + osp.basename(f)
                    self.upload_file(f, dest_fn, policy)
                src_dirs = (
                    osp.join(source, fn)
                    for fn in os.listdir(source)
                    if osp.isdir(osp.join(source, fn))
                )
                for d in src_dirs:
                    if (
                        not d.startswith(".") and "/." not in d
                    ):  # no hidden directories.
                        new_remote_path = dest + "/" + osp.basename(d)
                        new_local_path = d
                        if not self._dp_mgr.node_exists(
                            new_remote_path, print_error=False
                        ):
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
        # path to the root folders
        self._local_root = None
        self._remote_root = None

    def _checkconfigfile(self):
        """Check the config file.

        """
        if osp.exists(osp.join(CONFIGDIR, "sync.conf")):
            self._config.read(osp.join(CONFIGDIR, "sync.conf"))
        if self._config.sections() == []:
            self._config["pair1"] = {}
            self._config["pair1"]["local_path"] = "<replace by local path>"
            self._config["pair1"]["remote_path"] = "<replace by remote path>"
            self._config["pair1"][
                "policy"
            ] = "<one of: remote_wins, local_wins, newer, skip>"
        with open(osp.join(CONFIGDIR, "sync.conf"), "w") as f:
            self._config.write(f)

    def sync_pairs(self):
        """Sync the pairs defined in the config file.

        """
        for pair in self._config.sections():
            print("")
            print("---Staring to sync pair {}---".format(pair))
            lp = self._config[pair]["local_path"]
            rp = self._config[pair]["remote_path"]
            print("---Local root is  {}---".format(lp))
            print("---Remote root is {}---".format(rp))
            self.sync_folder(lp, rp)

    def sync_folder(self, local, remote):
        """Synchronize a local and remote folder recursively.

        Parameters
        ----------
        local : string
            Path to the source
        remote : string
            Full path to the folder on the DPT-RP1

        """
        self._local_root = osp.abspath(osp.expanduser(local))
        self._remote_root = remote
        # first compare the current state with the last known one
        print("Comparing remote state to old.")
        deletions_rem, tree_rem = self._cmp_remote2old(local, remote)
        print("Comparing local state to old.")
        deletions_loc, tree_loc = self._cmp_local2old(local)
        print("Comparing current local and remote states.")
        self._handle_deletions(deletions_loc, deletions_rem)
        # do the sync by comparing local and remote
        self._cmp_local2remote(tree_loc, tree_rem)
        # Save the new current state as old
        self._save_sync_state(local, remote)

    def _fix_path4local(self, path):
        """For performance reasons the remote tree is always the full one, not only 
        the synced subtree. We need to fix paths when finding nodes.

        """
        rp = osp.relpath(path, self._remote_root)
        if rp == ".":
            rp = osp.basename(self._local_root)
        else:
            rp = osp.join(osp.basename(self._local_root), rp)
        return rp

    def _fix_path4remote(self, path):
        """The opposite of fix_path4local

        """
        sppath = path.split("/", 1)
        if len(sppath) > 1:
            path = "{}/{}".format(self._remote_root, sppath[1])
        else:
            path = self._remote_root
        return path

    def _cmp_remote2old(self, local, remote):
        """Compare the current remote tree to the last seen one.

        """
        deleted_nodes = {"documents": [], "folders": []}

        oldtree = self._load_sync_state_remote(local)
        start_node = self._dp_mgr.get_node(remote)
        curtree = remotetree.RemoteTree(start_node)
        if oldtree is not None:
            # Iterate over all nodes in the old tree first
            for oldnode in PreOrderIter(oldtree.tree):
                node = curtree.get_node_by_path(oldnode.entry_path)
                if node is not None:
                    self._check_node(oldnode, node)
                    # print(f"Name: {node.entry_name}: {node.sync_state}")
                else:
                    # print("NOT FOUND")
                    if oldnode.entry_type == "document":
                        deleted_nodes["documents"].append(oldnode.entry_path)
                    else:
                        deleted_nodes["folders"].append(oldnode.entry_path)
            # Iterate over all nodes in the new tree now to find new items
            for node in PreOrderIter(curtree.tree):
                if node.sync_state is None:
                    # Node not yet checked means it was not present in the old tree.
                    node.sync_state = "new"
                    # print(f"Name: {node.entry_name}: {node.sync_state}")
        else:
            print("WARNING: No old remote state found. Maybe this is an initial sync?")
        print(deleted_nodes)
        return deleted_nodes, curtree

    # TODO: ISINSTANCE CHECKS NOT WORKING FOR TREES LOADED FROM FILE -> MAKE ALL NODES THE SAME TYPE (ANYTREE)

    def _cmp_local2old(self, local):
        """Compare the current local tree to the last seen one.

        """
        deleted_nodes = {"documents": [], "folders": []}

        oldtree = self._load_sync_state_local(local)
        curtree = localtree.LocalTree(local)
        curtree.rebuild_tree()
        if oldtree is not None:
            # Iterate over all nodes in the old tree first
            for oldnode in PreOrderIter(oldtree.tree):
                node = curtree.get_node_by_path(oldnode.relpath)
                if node is not None:
                    self._check_node(oldnode, node)
                    # print(f"Name: {node.name}: {node.sync_state}")
                else:
                    # print("NOT FOUND")
                    if oldnode.entry_type == "document":
                        deleted_nodes["documents"].append(oldnode.abspath)
                    else:
                        deleted_nodes["folders"].append(oldnode.abspath)
            # Iterate over all nodes in the new tree now to find new items
            for node in PreOrderIter(curtree.tree):
                if node.sync_state is None:
                    # Node not yet checked means it was not present in the old tree.
                    node.sync_state = "new"
                    # print(f"Name: {node.name}: {node.sync_state}")
        else:
            print("WARNING: No old remote state found. Maybe this is an initial sync?")
        return deleted_nodes, curtree

    def _handle_deletions(self, deletions_loc, deletions_rem):
        """Handle deletion, i.e. delete locally what was deleted remotely and
        the other way around.

        """
        for d in deletions_loc["documents"]:
            self._dp_mgr.rm_file(d)
        for d in deletions_loc["folders"]:
            self._dp_mgr.rm_dir(d)
        for d in deletions_rem["documents"]:
            print("Deleting local file {}".format(d))
            if osp.exists(d):
                os.remove(d)
        for d in deletions_rem["folders"]:
            print("Deleting local folder {}".format(d))
            if osp.exists(d):
                os.rmdir(d)

    def _cmp_local2remote(self, tree_loc, tree_rem):
        """Compare the changes in the local and remote trees.

        """
        # loop through all remote nodes
        for node_rem in PreOrderIter(tree_rem.tree):
            node_loc = tree_loc.get_node_by_path(
                self._fix_path4local(node_rem.entry_path)
            )
            if node_loc is not None:
                # Only relevant for documents
                if node_rem.entry_type == "document":
                    if not node_rem.file_size == node_loc.file_size:
                        # local and remote are different
                        self._handle_changes(node_loc, node_rem)
            else:
                # download
                targetpath = osp.join(
                    osp.dirname(self._local_root),
                    self._fix_path4local(node_rem.entry_path),
                )
                print(
                    "Local node not found. Attempting download of {}".format(targetpath)
                )
                if node_rem.entry_type == "folder":
                    os.mkdir(targetpath)
                else:
                    self._downloader.download_file(
                        node_rem.entry_path, targetpath, "remote_wins"
                    )
        # loop through all local nodes, upload those not on the remote
        for node_loc in PreOrderIter(tree_loc.tree):
            node_rem = tree_rem.get_node_by_path(
                self._fix_path4remote(node_loc.relpath)
            )
            if node_rem is None:
                # upload
                targetpath = self._fix_path4remote(node_loc.relpath)
                print(
                    "Remote node not found. Attempting upload of {}".format(targetpath)
                )
                if node_loc.entry_type == "folder":
                    self._dp_mgr.mkdir(targetpath)
                else:
                    self._uploader.upload_file(
                        node_loc.abspath, targetpath, "local_wins"
                    )

    def _handle_changes(self, node_loc, node_rem):
        """Handle a difference of the local and remote nodes.

        """
        if node_rem.sync_state is None or node_loc.sync_state is None:
            # download in remote wins mode
            print(
                "Attempting download of {} to {}".format(
                    node_rem.entry_path, node_loc.abspath
                )
            )
            self._downloader.download_file(
                node_rem.entry_path, node_loc.abspath, "remote_wins"
            )
        elif node_rem.sync_state == "equal" and node_loc.sync_state == "equal":
            # ask the user (should not happen)
            print(
                "Neither the local nor the remote node is modified, but the documents are different. WHAT!?"
            )
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "modified" and node_loc.sync_state == "modified":
            # ask the user
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "new" and node_loc.sync_state == "new":
            # ask the user
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "equal" and node_loc.sync_state == "modified":
            # upload
            print(
                "Attempting upload of {} to {}".format(
                    node_loc.abspath, node_rem.entry_path
                )
            )
            self._uploader.upload_file(
                node_loc.abspath, node_rem.entry_path, "local_wins"
            )
        elif node_rem.sync_state == "equal" and node_loc.sync_state == "new":
            # ask the user (should not happen)
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "modified" and node_loc.sync_state == "equal":
            # download
            print(
                "Attempting download of {} to {}".format(
                    node_rem.entry_path, node_loc.abspath
                )
            )
            self._downloader.download_file(
                node_rem.entry_path, node_loc.abspath, "remote_wins"
            )
        elif node_rem.sync_state == "new" and node_loc.sync_state == "equal":
            # ask the user (should not happen)
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "modified" and node_loc.sync_state == "new":
            # ask the user (should not happen)
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "new" and node_loc.sync_state == "modified":
            # ask the user (should not happen)
            self._askuser(node_loc, node_rem)

    def _askuser(self, node_loc, node_rem):
        """Ask the user what to do.

        """
        message = "Conflict for node {}, reason L:{} R:{}".format(
            node_loc.relpath, node_loc.sync_state, node_rem.sync_state
        )
        question = "Choose which version to keep [l]ocal, [r]emote, [s]kip: "
        print("")
        response = ""
        while response not in ["l", "r", "s"]:
            print(message)
            response = str(input(question))
        if response == "l":
            self._uploader.upload_file(
                node_loc.abspath, node_rem.entry_path, "local_wins"
            )
        elif response == "r":
            self._downloader.download_file(
                node_rem.entry_path, node_loc.abspath, "remote_wins"
            )

    def _check_node(self, old, new):
        """Check the status of the nodes.

        """
        if old.entry_type == "document":
            # first check the file sizes. We consider the nodes the same when the size matches
            if old.file_size == new.file_size:
                new.sync_state = "equal"
            else:
                new.sync_state = "modified"
        else:
            new.sync_state = "equal"

    def _save_sync_state(self, local, remote):
        # the remote tree
        self._dp_mgr.rebuild_tree()
        start_node = self._dp_mgr.get_node(remote)
        fn_loc, fn_rem = self._get_syncstate_paths(local)
        self._dp_mgr.remote_tree.save_to_file(fn_rem, start_node)
        # the local tree
        loctree = localtree.LocalTree(osp.expanduser(local))
        loctree.rebuild_tree()
        loctree.save_to_file(fn_loc)

    def _load_sync_state_remote(self, local):
        _, fn = self._get_syncstate_paths(local)
        if osp.exists(fn):
            oldtree = remotetree.load_from_file(fn)
        else:
            oldtree = None
        return oldtree

    def _load_sync_state_local(self, local):
        fn, _ = self._get_syncstate_paths(local)
        if osp.exists(fn):
            oldtree = localtree.load_from_file(fn)
        else:
            oldtree = None
        return oldtree

    def _get_syncstate_paths(self, local):
        rem = osp.join(osp.expanduser(local), ".dp_syncstate_remote")
        loc = osp.join(osp.expanduser(local), ".dp_syncstate_local")
        return loc, rem


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
        for template in res["template_list"]:
            tmp_list.append(template["template_name"])
        return tmp_list

    def rename_template(self, old_name, new_name):
        self._dp_mgr.dp.rename_template(old_name, new_name)

    def delete_template(self, name):
        self._dp_mgr.dp.delete_template(name)

    def add_template(self, name, path):
        path = osp.expanduser(path)
        if osp.exists(path) and path.endswith(".pdf"):
            with open(path, "rb") as f:
                self._dp_mgr.dp.add_template(name, f)
        else:
            print(
                "Adding template failed. File {} not found or not a pdf file.".format(
                    path
                )
            )

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
        free = float(storage["available"])
        return free

    @property
    def storage_total(self):
        """Total storage capacity in Byte

        """
        storage = self._dp_mgr.dp.get_storage()
        total = float(storage["capacity"])
        return total

    @property
    def battery_level(self):
        """Battery level in percent.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["level"]

    @property
    def battery_pen(self):
        """Pen battery level in percent.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["pen"]

    @property
    def battery_health(self):
        """Battery health

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["health"]

    @property
    def battery_status(self):
        """Battery status (charging/discharging)

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["status"]

    @property
    def plugged(self):
        """Check if connected via usb for charging.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["plugged"]

    @property
    def model(self):
        """The model name

        """
        info = self._dp_mgr.dp.get_info()
        return info["model_name"]

    @property
    def serial(self):
        """The seral number of the device

        """
        info = self._dp_mgr.dp.get_info()
        return info["serial_number"]

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

    def add_wifi(
        self,
        ssid,
        security="nonsec",
        passwd="",
        dhcp=True,
        static_address="",
        gateway="",
        network_mask="",
        dns1="",
        dns2="",
        proxy=False,
    ):
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
        self._dp_mgr.dp.configure_wifi(
            ssid,
            security,
            passwd,
            dhcp,
            static_address,
            gateway,
            network_mask,
            dns1,
            dns2,
            proxy,
        )

    def delete_wifi(self, ssid, security="nonsec"):
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
        val = self._dp_mgr.dp.wifi_enabled()["value"]
        if val == "on":
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
    # dp_mgr.print_folder_contents('Document/Reader/projects')

    # synchronizer.sync_folder(local='~/Reader/projects', remote='Document/Reader/projects', policy='remote_wins')

    # dp_mgr.rename_template('daily_planner', 'planner')
    # dp_mgr.delete_template('test')
    # dp_mgr.add_template('testA5', 'home/cgross/Downloads/test2.pdf')

    # downloader.download_recursively('Document/Reader/projects', '~/Downloads/test', 'remote_wins')
    # dp_mgr.rm_allfiles_recursively('Document/Reader/projects')
    # uploader.upload_recursively('~/Downloads/test', 'Document/Reader/projects', 'remote_wins')

    # downloader.download_folder_contents('Document/Reader/topics/quantum_simulation', '~/Downloads')
    # downloader.download_standalone_notes('~/Downloads', policy='remote_wins')

    # dp_mgr.mkdir('Document/testfolder')

    # uploader.upload_folder_contents('~/Reader/projects/physikjournal', 'Document/Reader/projects/physikjournal', policy='remote_wins')
    # uploader.upload_folder_contents('~/Downloads/test', 'Document/Reader/test', policy='remote_wins')

    synchronizer._cmp_remote2old("~/work/reader/projects", "Reader/projects")
    synchronizer._cmp_local2old("~/work/reader/projects")


if __name__ == "__main__":
    main()
