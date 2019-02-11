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
