#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

import anytree


class DPNode(anytree.NodeMixin):
    """Representation of a general node in the file system of the DPT-RP1.

    Attributes
    ----------
    entry_name : string
        The name of the node.
    entry_type : string
        type of the entry
    entry_id : string
        The unique id of the node. This is used to modify content on the dptrp1.
    created_date : datetime.datetime
        Date the entry was created
    entry_path : string
        Path to the entry
    is_new : bool
        Is the entry new?

    """
    def __init__(self, parent, entry_name, entry_type, entry_id, created_date, entry_path, is_new):
        super().__init__(parent=parent)
        self.entry_name = entry_name
        self.entry_type = entry_type
        self.entry_id = entry_id
        self.created_date = self._todatetime(created_date)
        self.entry_path = entry_path
        self.is_new = bool(is_new)

    def _todatetime(self, datestring):
        res = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%SZ")
        return res


class DPFolderNode(DPNode):
    """Representation of a folder node.

    Attributes
    ----------
    document_source : string
        Not sure what this is.
    parent_folder_id : string
        Id of the parent folder.

    """
    def __init__(self, parent, entry_name, entry_type, entry_id, created_date, entry_path, is_new, document_source, parent_folder_id):
        super().__init__(parent, entry_name, entry_type, entry_id, created_date, entry_path, is_new)
        self.document_source = document_source
        self.parent_folder_id = parent_folder_id


class DPDocumentNode(DPNode):
    """Representation of a document node.

    Attributes
    ----------
    author : string
        Document author.
    current_page : int
        Current page number
    document_type : string
        Type of the document
    file_revision : string
        String identifying the document revision.
    file_size : int
        File size in bytes
    mime_type : string
        Type
    modified_date : datetime
        Last modified date
    title : string
        Title of the document
    total_page : int
        Total page count

    """
    def __init__(self, parent, entry_name, entry_type, entry_id, created_date, entry_path, is_new, author, current_page, document_type, file_revision, file_size, mime_type, modified_date, title, total_page):
        super().__init__(parent, entry_name, entry_type, entry_id, created_date, entry_path, is_new)
        self.author = author
        self.current_page = int(current_page)
        self.document_type = document_type
        self.file_revision = file_revision
        self.file_size = int(file_size)
        self.mime_type = mime_type
        self.modified_date = self._todatetime(modified_date)
        self.title = title
        self.total_page = int(total_page)

class RemoteTree(object):
    """Representation of the files and folders on the dpt-rp1.

    """
    def __init__(self):
        self._tree = None

    def rebuild_tree(self, jsondata):
        self._tree = self._create_tree_root()
        for data in jsondata:
            self._create_path(data['entry_path'])
            self._fill_node_data(data)

    def _create_tree_root(self):
        """Add the root tree node.

        """
        rootnode = DPNode(parent=None, entry_name="Document", entry_type="folder", entry_id="root", created_date = "2017-12-12T13:53:50Z", entry_path="Document", is_new=False)
        return rootnode

    def _create_path(self, path):
        """Create the path to the node if not yet there.

        We just create empty nodes, the data will be added in _fill_node_data.

        """
        pathcmp = path.split("/")
        pass

    def _get_node_by_path(self, path):
        """Get a tree node by its path.

        """
        return anytree.search.find_by_attr(self._tree.root, "entry_path", path)




## A file
#{'author': 'lsr',
# 'created_date': '2017-12-14T13:55:00Z',
# 'current_page': '1',
# 'document_type': 'normal',
# 'entry_id': 'f1d09cac-1832-48b7-b060-4d39cbc0e582',
# 'entry_name': 'book-majlis-2000-majlis2000-the_quant_theor_of_magne.pdf',
# 'entry_path': 'Document/Reader/books/solid_state/book-majlis-2000-majlis2000-the_quant_theor_of_magne.pdf',
# 'entry_type': 'document',
# 'file_revision': '05873ef2024a.1.0',
# 'file_size': '19093553',
# 'is_new': 'true',
# 'mime_type': 'application/pdf',
# 'modified_date': '2017-12-14T13:55:00Z',
# 'parent_folder_id': 'c9f9cde4-f12f-4285-a42c-7b38206581ca',
# 'title': 'Print The Quantum Theory of Magnetism.tif (150 '
#          'pages)',
# 'total_page': '436'},
#
#
## A Folder
#{'created_date': '2018-10-06T07:38:12Z',
# 'document_source': '2ae5e78c-8766-416b-baf6-ba3e1be3ab02',
# 'entry_id': '6dd5f5a9-4136-4591-960a-c7f04d129f45',
# 'entry_name': 'paper',
# 'entry_path': 'Document/Reader/projects/macrodimers/paper',
# 'entry_type': 'folder',
# 'is_new': 'false',
# 'parent_folder_id': '9d9eced8-18be-4b82-b9d3-5a9ebddfe8dc'},
#
#
## Root (Document)
#{'created_date': '2017-12-12T13:53:50Z',
# 'entry_id': 'root',
# 'entry_name': 'Document',
# 'entry_path': 'Document',
# 'entry_type': 'folder',
# 'is_new': 'false'}

