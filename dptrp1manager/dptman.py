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
import configparser
import subprocess
import re
import socket
import psutil
import time
import requests

import serial
import anytree
from dptrp1manager import tools, remotetree, mydptrp1


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
        print("Reading contents of the device")
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

    def _wait_until_connected(self, interfaces):
        """Get interfaces to try and return the one connected.

        """
        res = None
        for iface in interfaces:
            retry = 0
            print(f"Connecting to {iface}", end="", flush=True)
            while (not self._interface_up(iface)) and retry < 50:
                time.sleep(0.3)
                retry += 1
                print(".", end="", flush=True)
            if self._interface_up(iface):
                res = iface
                break
            print("\n", end="", flush=True)
        if not res:
            print("\n")
            print("Could not connect to the DPT-RP1 via USB, exiting.")
            sys.exit(1)
        else:
            print("\n")
            return res

    def _get_ip(self, ip):
        # prefer usb
        if self._is_usb_conneted():
            self._set_up_eth_usb()
            ip_bare = self._config["USB"]["ipv6"]
            ifaces = self._config["USB"]["interfaces"]
            iface = self._wait_until_connected(ifaces.split(","))
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
            if "Sony Corp. DPT-RP1" in dev["tag"]:
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
        send_val = b"\x01\x00\x00\x01\x00\x00\x00\x01\x00\x04"

        # use CDC/ECM mode
        # send_val = b"\x01\x00\x00\x01\x00\x00\x00\x01\x01\x04"
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

    def print_full_tree(self, path):
        path = self.fix_path(path)
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
        # skip dot folders
        # skip anything below a dot folder
        isdotpath = False
        for comp in path.split("/"):
            if comp.startswith("."):
                isdotpath = True
        if not isdotpath:
            path = self.fix_path(path)
            parent_folder, new_folder = path.rsplit("/", maxsplit=1)
            if self.node_exists(parent_folder):
                if not self.node_exists(path, print_error=False):
                    print("Creating folder {}".format(path))
                    parent_folder_id = self.get_node(parent_folder).entry_id
                    self.dp.new_folder_byid(parent_folder_id, new_folder)
                else:
                    print("ERROR: DPT-RP1 has already a folder {}".format(path))
        else:
            print("Skipping 'dot' folder {}".format(path))

    def rm_dir(self, path):
        """Delete a (empty) directory on the DPT-RP1.

        """
        path = self.fix_path(path)
        if self.node_exists(path):
            print("Deleting dir {}.".format(path))
            dir_id = self.get_node(path).entry_id
            self._rm_dir(dir_id)
        else:
            print("ERROR: Directory {} not found".format(path))

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
        else:
            print("ERROR: File {} not found".format(path))

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

    def rm_all_recursively(self, path):
        """Delete all files and folders in a directory on the DPT-RP1 including
        the directory itself.

        """
        self.rm_allfiles_recursively(path)
        self.rm_dir(path)


def main():
    dp_mgr = DPManager()


if __name__ == "__main__":
    main()
