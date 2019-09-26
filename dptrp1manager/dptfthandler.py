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
from datetime import datetime


class FileTransferHandler(object):
    """Base class for the Downloader and Uploader.

    Parameters
    ----------
    dp_mgr : DPManager

    """

    def __init__(self, dp_mgr):
        super(FileTransferHandler, self).__init__()
        self._dp_mgr = dp_mgr

    def _check_newer(self, local, remote):
        """Check if the local or remote file is newer.

        """
        remote_time = self._dp_mgr.get_node(remote).modified_date
        local_time = datetime.utcfromtimestamp(osp.getmtime(local))
        # print("{}: {}".format(remote, remote_time))
        # print("{}: {}".format(local, local_time))
        dt = (remote_time -  local_time).total_seconds()
        if dt == 0:
            # print("equal")
            return 0
        elif dt < 0:
            # print("local_newer")
            return 1
        elif dt > 0:
            # print("remote_newer")
            return 2

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
