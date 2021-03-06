#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import os.path as osp
import time

import anytree
from anytree.exporter import JsonExporter
from anytree.importer import JsonImporter, DictImporter

from dptrp1manager import tools


class DPNode(anytree.NodeMixin):
    """Representation of a general node in the file system of the DPT-RP1.

    Attributes
    ----------
    parent : DPNode
        Parent node.
    entry_path : string
        Path to the entry
    entry_name : string
        The name of the node.
    entry_type : string
        type of the entry, `document` of `folder`
    entry_id : string
        The unique id of the node. This is used to modify content on the dptrp1.
    created_date : datetime.datetime
        Date the entry was created
    is_new : bool
        Is the entry new?
    document_source : string (default None)
        Not sure what this is.
    parent_folder_id : string (default None)
        Id of the parent folder.
    author : string (default None)
        Document author.
    current_page : int (default None)
        Current page number
    document_type : string (default None)
        Type of the document
    file_revision : string (default None)
        String identifying the document revision.
    file_size : int (default None)
        File size in bytes
    mime_type : string (default None)
        Type
    modified_date : datetime (default None)
        Last modified date
    title : string (default None)
        Title of the document
    total_page : int (default None)
        Total page count

    sync_state : string
        Used for syncing different trees.

    """

    def __init__(
        self,
        parent,
        entry_path,
        entry_name,
        entry_type,
        entry_id,
        created_date,
        is_new,
        document_source=None,
        parent_folder_id=None,
        author=None,
        current_page=None,
        document_type=None,
        file_revision=None,
        file_size=None,
        mime_type=None,
        modified_date=None,
        title=None,
        total_page=None,
        sync_state=None,
    ):
        super().__init__()
        self.parent = parent
        self.entry_path = entry_path
        self.entry_name = entry_name
        self.entry_type = entry_type
        self.entry_id = entry_id
        self.created_date = self.todatetime(created_date)
        if is_new is not None:
            self.is_new = bool(is_new)
        else:
            self.is_new = None
        self.document_source = document_source
        self.parent_folder_id = parent_folder_id
        self.author = author
        self.document_type = document_type
        self.file_revision = file_revision
        self.mime_type = mime_type
        self.modified_date = self.todatetime(modified_date)
        self.title = title
        if current_page is not None:
            self.current_page = int(current_page)
        else:
            self.current_page = None
        if file_size is not None:
            self.file_size = int(file_size)
        else:
            self.file_size = None
        if total_page is not None:
            self.total_page = int(total_page)
        else:
            self.total_page = None

        self.sync_state = sync_state

    def todatetime(self, datestring):
        if datestring is not None:
            if isinstance(datestring, datetime):
                res = datestring
            else:
                res = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%SZ")
        else:
            res = None
        return res


class RemoteTree(object):
    """Representation of the files and folders on the dpt-rp1.

    """

    def __init__(self, tree=None):
        self._tree = tree
        self._resolver = anytree.resolver.Resolver("entry_name")

    def rebuild_tree(self, jsondata):
        self._tree = self._create_tree_root()
        for data in jsondata:
            self._create_path(data["entry_path"])
            self._create_update_node(data)
        # self.save_to_file("~/.dpmgr/contents.json")
        self._save_content_list("~/.dpmgr/contents")

    @property
    def tree(self):
        return self._tree

    def save_to_file(self, path, start_node=None):
        path = osp.expanduser(path)
        if osp.exists(osp.dirname(path)):
            exp = JsonExporter(indent=2, sort_keys=True, default=tools.default)
            with open(path, "w") as f:
                if start_node is None:
                    exp.write(self._tree, f)
                else:
                    exp.write(start_node, f)
        else:
            print(
                "Error saving to disk. Dir {} not existing.".format(osp.dirname(path))
            )

    def _save_dir_list(self, path):
        path = osp.expanduser(path)
        if osp.exists(osp.dirname(path)):
            with open(path, "w") as f:
                for _, _, node in anytree.render.RenderTree(self._tree):
                    if node.entry_type == "folder":
                        f.write("{}\n".format(node.entry_path.split("/", 1)[1]))

    def _save_content_list(self, path):
        path = osp.expanduser(path)
        if osp.exists(osp.dirname(path)):
            with open(path, "w") as f:
                for _, _, node in anytree.render.RenderTree(self._tree):
                    if node.is_leaf:
                        f.write("{}\n".format(node.entry_path.split("/", 1)[1]))

    def _create_tree_root(self):
        """Add the root tree node.

        """
        rootnode = DPNode(
            parent=None,
            entry_name="Document",
            entry_type="folder",
            entry_id="root",
            created_date="2017-12-12T13:53:50Z",
            entry_path="Document",
            is_new=False,
        )
        return rootnode

    def remove_node(self, path):
        node = self.get_node_by_path(path)
        childs = []
        if node is not None:
            for n in node.parent.children:
                if n.entry_path == node.entry_path:
                    pass
                else:
                    childs.append(n)
            node.parent.children = childs

    def _create_path(self, path):
        """Create the path to the node if not yet there.

        We just create empty nodes, the data will be added in _create_update_node.

        """
        splpath = path.split("/")
        lastpath = "{}".format(splpath[0])
        for d in splpath[1:-1]:
            curpath = "{}/{}".format(lastpath, d)
            if self.get_node_by_path(curpath) is None:
                parent = self.get_node_by_path(lastpath)
                DPNode(
                    parent=parent,
                    entry_path=curpath,
                    entry_name=d,
                    entry_type=None,
                    entry_id=None,
                    created_date=None,
                    is_new=None,
                    document_source=None,
                    parent_folder_id=None,
                )
            lastpath = curpath

    def _create_update_node(self, data):
        """Create or update the node given in data.

        """
        parentpath = data["entry_path"].rsplit("/", 1)[0]
        parent = self.get_node_by_path(parentpath)
        if data["entry_type"] == "folder":
            node = self.get_node_by_path(data["entry_path"])
            if node is None:
                DPNode(
                    parent=parent,
                    entry_path=data["entry_path"],
                    entry_name=data["entry_name"],
                    entry_type=data["entry_type"],
                    entry_id=data["entry_id"],
                    created_date=data["created_date"],
                    is_new=data["is_new"],
                    document_source=data.get("document_source", None),
                    parent_folder_id=data["parent_folder_id"],
                )
            else:
                # add node data
                node.entry_type = data["entry_type"]
                node.entry_id = data["entry_id"]
                node.created_date = node.todatetime(data["created_date"])
                node.is_new = bool(data["is_new"])
                node.document_source = data.get("document_source", None)
                node.parent_folder_id = data["parent_folder_id"]
        elif data["entry_type"] == "document":
            DPNode(
                parent=parent,
                entry_path=data["entry_path"],
                entry_name=data["entry_name"],
                entry_type=data["entry_type"],
                entry_id=data["entry_id"],
                created_date=data["created_date"],
                is_new=data["is_new"],
                author=data.get("author", None),
                current_page=data["current_page"],
                document_type=data["document_type"],
                file_revision=data["file_revision"],
                file_size=data["file_size"],
                mime_type=data["mime_type"],
                modified_date=data["modified_date"],
                title=data.get("title", None),
                total_page=data["total_page"],
            )

    def printtree(self, path, foldersonly):
        foldernode = self.get_node_by_path(path)
        if foldernode is not None:
            for pre, _, node in anytree.render.RenderTree(foldernode):
                if not foldersonly:
                    print("{}{}".format(pre, node.entry_name))
                else:
                    if node.entry_type == "folder":
                        print("{}{}".format(pre, node.entry_name))
        else:
            print("ERROR: Folder {} not found.".format(path))

    def print_folder_contents(self, path):
        foldernode = self.get_node_by_path(path)
        if foldernode is not None:
            for pre, _, node in anytree.render.RenderTree(foldernode):
                if node.entry_type == "document":
                    print(
                        "{0}[{1: <7}][{2:}] {3}".format(
                            pre,
                            self._sizeof_fmt(node.file_size),
                            node.modified_date,
                            node.entry_name,
                        )
                    )
                else:
                    print("{}{}".format(pre, node.entry_name))
        else:
            print("ERROR: Folder {} not found.".format(path))

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
        except (anytree.resolver.ChildResolverError, anytree.resolver.ResolverError):
            res = None
        return res

    def insert_folder_node(self, data):
        """Insert a folder into the tree.

        """
        parentpath = data["entry_path"].rsplit("/", 1)[0]
        parent = self.get_node_by_path(parentpath)
        DPNode(
            parent=parent,
            entry_path=data["entry_path"],
            entry_name=data["entry_name"],
            entry_type="folder",
            entry_id=data["entry_id"],
            created_date=data["created_date"],
            is_new=data["is_new"],
            document_source=data.get("document_source", None),
            parent_folder_id=data["parent_folder_id"],
        )


def load_from_file(path):
    path = osp.expanduser(path)
    if osp.exists(osp.dirname(path)):
        dict_imp = DictImporter(nodecls=DPNode)
        imp = JsonImporter(dictimporter=dict_imp, object_hook=tools.object_hook)
        with open(path, "r") as f:
            res = imp.read(f)
        return RemoteTree(res)
    else:
        print("Error saving to disk. Dir {} not existing.".format(osp.dirname(path)))
