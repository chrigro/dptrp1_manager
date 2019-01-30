#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import os.path as osp
from datetime import datetime

import anytree

import time


class LocalNode(anytree.NodeMixin):
    """Representation of a general node in the local file system.

    Attributes
    ----------
    parent : LocalNode
        Parent node.
    relpath : string
        Path to the node relative to the tree root.
    name : string
        The name of the node.
    abspath : string
        Absolute path on the file system

    """

    def __init__(self, parent, relpath, name, abspath):
        super().__init__()
        self.parent = parent
        self.relpath = relpath
        self.name = name
        self.abspath = abspath


class LocalFolderNode(LocalNode):
    """Representation of a local folder node.

    """

    def __init__(self, parent, relpath, name, abspath):
        super().__init__(parent, relpath, name, abspath)


class LocalDocumentNode(LocalNode):
    """Representation of a document node.

    Attributes
    ----------
    file_size : int
        File size in bytes
    modified_date : datetime
        Last modified date

    """

    def __init__(self, parent, relpath, name, abspath, file_size, modified_date):
        super().__init__(parent, relpath, name, abspath)
        self.file_size = file_size
        self.modified_date = modified_date


class LocalTree(object):
    """Representation of the local files and folders.

    """

    def __init__(self, rootpath):
        if osp.basename(rootpath) == "":
            rootpath = osp.dirname(rootpath)
        self._rootpath = osp.abspath(osp.expanduser(rootpath))
        self._tree = None
        self._resolver = None

    def rebuild_tree(self):
        self._resolver = anytree.resolver.Resolver("name")
        self._tree = self._create_tree_root()
        self._create_tree()

    def _create_tree_root(self):
        """Add the root tree node.

        """
        bn = osp.basename(self._rootpath)
        rootnode = LocalNode(parent=None, name=bn, relpath=bn, abspath=self._rootpath)
        return rootnode

    def _create_tree(self):
        """Create the tree by wlking through the file system.

        """
        for path, dirs, files in os.walk(self._rootpath):
            if not path == self._rootpath:
                parentpath = osp.relpath(osp.dirname(path), osp.dirname(self._rootpath))
                parentnode = self.get_node_by_path(parentpath)
                name = osp.basename(path)
                relpath = osp.relpath(path, osp.dirname(self._rootpath))
                LocalFolderNode(
                    parent=parentnode, name=name, relpath=relpath, abspath=path
                )
                for name in files:
                    if osp.splitext(name)[1].lower() == ".pdf":
                        parentpath = osp.relpath(path, osp.dirname(self._rootpath))
                        parentnode = self.get_node_by_path(parentpath)
                        relpath = osp.join(parentpath, name)
                        abspath = osp.join(path, name)
                        modtime = datetime.fromtimestamp(int(osp.getmtime(abspath)))
                        fsize = osp.getsize(abspath)
                        LocalDocumentNode(
                            parent=parentnode,
                            name=name,
                            relpath=relpath,
                            abspath=abspath,
                            file_size=fsize,
                            modified_date=modtime,
                        )

    def printtree(self, foldersonly):
        for pre, _, node in anytree.render.RenderTree(self._tree):
            if not foldersonly:
                print("{}{}".format(pre, node.name))
            else:
                if not isinstance(node, LocalDocumentNode):
                    print("{}{}".format(pre, node.name))

    def print_folder_contents(self, path):
        foldernode = self.get_node_by_path(path)
        if foldernode is not None:
            for pre, _, node in anytree.render.RenderTree(foldernode):
                if isinstance(node, LocalDocumentNode):
                    print(
                        "{0}[{1: <7}][{2:}] {3}".format(
                            pre, self._sizeof_fmt(node.file_size), node.modified_date, node.name
                        )
                    )
                else:
                    print("{}{}".format(pre, node.name))

    def _sizeof_fmt(self, num, suffix="B"):
        for unit in ["", "k", "M", "G", "T", "P", "E", "Z"]:
            if abs(num) < 1024.0:
                return "{:3.1f}{}{}".format(num, unit, suffix)
            num /= 1024.0
        return "{:.1f}{}{}".format(num, "Y", suffix)

    def get_node_by_path(self, path):
        """Get a tree node by its path.

        """
        try:
            searchpath = "/{}".format(path)
            res = self._resolver.get(self._tree.root, searchpath)
        except anytree.resolver.ChildResolverError:
            res = None
        return res


if __name__ == "__main__":
    lt = LocalTree("~/work/reader")
    lt.rebuild_tree()
    lt.printtree(False)
    lt.print_folder_contents("reader/unpublished")
