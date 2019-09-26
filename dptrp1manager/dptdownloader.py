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


import os
import os.path as osp

from dptrp1manager.dptfthandler import FileTransferHandler


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
                # if self._is_equal(dest, source):
                #     do_transfer = False  # FIXME: to modified date checking here.
                # else:
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
