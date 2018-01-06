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


from dptrp1.dptrp1 import DigitalPaper
import anytree
import configparser


class DPNode(anytry.NodeMixin):
    """Representation of a node in the file system of the DPT-RP1.

    Attributes
    ----------
    name : string
        The name of the node.
    isfile : bool
        Is the node representing a file?
    isdir : bool
        Is the node representing a directory?

    """
    def __init__(self, name):
        super(TreeNode, self).__init__()
        self.name = name


class DPManager(object):
    """Main class to manage the DPT-RP1.

    """
    def __init__(self):
        super(DPManager, self).__init__()


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

