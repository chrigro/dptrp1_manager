#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
    def __init__(self):
        super().__init__()


class DPFolderNode(DPNode):
    def __init__(self):
        super().__init__()


class DPFileNode(DPNode):
    def __init__(self):
        super().__init__()



class RemoteTree(object):
    """Representation of the files and folders on the dpt-rp1.

    """
    def update_tree(self, jsondata):


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

