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


import os.path as osp
import datetime


class FileTransferHandler(object):
    """Base class for the Downloader and Uploader.

    Parameters
    ----------
    dp_mgr : DPManager

    """

    def __init__(self, dp_mgr):
        super(FileTransferHandler, self).__init__()
        self._dp_mgr = dp_mgr

    # FIXME: Updade this method to use the modification date as in sync
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
