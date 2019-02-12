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
import configparser

from anytree import PreOrderIter
from dptrp1manager import remotetree, localtree
from dptrp1manager.dptfthandler import FileTransferHandler
from dptrp1manager.dptdownloader import Downloader
from dptrp1manager.dptuploader import Uploader


CONFIGDIR = osp.join(osp.expanduser("~"), ".dpmgr")


class Synchronizer(FileTransferHandler):
    """Syncronize the DPT-RP1 with a folder.

    """

    def __init__(self, dp_mgr):
        super(Synchronizer, self).__init__(dp_mgr)
        self._downloader = Downloader(dp_mgr)
        self._uploader = Uploader(dp_mgr)
        self._config = configparser.ConfigParser()
        self._checkconfigfile()
        # path to the root folders
        self._local_root = None
        self._remote_root = None

    def _checkconfigfile(self):
        """Check the config file.

        """
        if osp.exists(osp.join(CONFIGDIR, "sync.conf")):
            self._config.read(osp.join(CONFIGDIR, "sync.conf"))
        if self._config.sections() == []:
            self._config["pair1"] = {}
            self._config["pair1"]["local_path"] = "<replace by local path>"
            self._config["pair1"]["remote_path"] = "<replace by remote path>"
            self._config["pair1"][
                "policy"
            ] = "<one of: remote_wins, local_wins, newer, skip>"
        with open(osp.join(CONFIGDIR, "sync.conf"), "w") as f:
            self._config.write(f)

    def sync_pairs(self):
        """Sync the pairs defined in the config file.

        """
        for pair in self._config.sections():
            print("")
            print("---Staring to sync pair {}---".format(pair))
            lp = self._config[pair]["local_path"]
            rp = self._config[pair]["remote_path"]
            print("---Local root is  {}---".format(lp))
            print("---Remote root is {}---".format(rp))
            self.sync_folder(lp, rp)

    def sync_folder(self, local, remote):
        """Synchronize a local and remote folder recursively.

        Parameters
        ----------
        local : string
            Path to the source
        remote : string
            Full path to the folder on the DPT-RP1

        """
        self._local_root = osp.abspath(osp.expanduser(local))
        self._remote_root = remote
        # first compare the current state with the last known one
        print("Comparing remote state to old.")
        deletions_rem, tree_rem = self._cmp_remote2old(local, remote)
        print("Comparing local state to old.")
        deletions_loc, tree_loc = self._cmp_local2old(local)
        tree_rem, tree_loc = self._handle_deletions(
            deletions_loc, deletions_rem, tree_rem, tree_loc
        )
        # do the sync by comparing local and remote
        print("Comparing current local and remote states.")
        self._cmp_local2remote(tree_loc, tree_rem)
        # Save the new current state as old
        self._save_sync_state(local, remote)

    def _fix_path4local(self, path):
        """For performance reasons the remote tree is always the full one, not only 
        the synced subtree. We need to fix paths when finding nodes.

        """
        rp = osp.relpath(path, self._remote_root)
        if rp == ".":
            rp = osp.basename(self._local_root)
        else:
            rp = osp.join(osp.basename(self._local_root), rp)
        return rp

    def _fix_path4remote(self, path):
        """The opposite of fix_path4local

        """
        sppath = path.split("/", 1)
        if len(sppath) > 1:
            path = "{}/{}".format(self._remote_root, sppath[1])
        else:
            path = self._remote_root
        return path

    def _cmp_remote2old(self, local, remote):
        """Compare the current remote tree to the last seen one.

        """
        deleted_nodes = {"documents": [], "folders": []}

        oldtree = self._load_sync_state_remote(local)
        start_node = self._dp_mgr.get_node(remote)
        curtree = remotetree.RemoteTree(start_node)
        if oldtree is not None:
            # Iterate over all nodes in the old tree first
            for oldnode in PreOrderIter(oldtree.tree):
                node = curtree.get_node_by_path(oldnode.entry_path)
                if node is not None:
                    self._check_node(oldnode, node)
                    # print(f"Name: {node.entry_name}: {node.sync_state}")
                else:
                    # print("NOT FOUND")
                    if oldnode.entry_type == "document":
                        deleted_nodes["documents"].append(oldnode.entry_path)
                    else:
                        deleted_nodes["folders"].append(oldnode.entry_path)
            # Iterate over all nodes in the new tree now to find new items
            for node in PreOrderIter(curtree.tree):
                if node.sync_state is None:
                    # Node not yet checked means it was not present in the old tree.
                    node.sync_state = "new"
                    # print(f"Name: {node.entry_name}: {node.sync_state}")
        else:
            print("WARNING: No old remote state found. Maybe this is an initial sync?")
        print(deleted_nodes)
        return deleted_nodes, curtree

    # TODO: ISINSTANCE CHECKS NOT WORKING FOR TREES LOADED FROM FILE -> MAKE ALL NODES THE SAME TYPE (ANYTREE)

    def _cmp_local2old(self, local):
        """Compare the current local tree to the last seen one.

        """
        deleted_nodes = {"documents": [], "folders": []}

        oldtree = self._load_sync_state_local(local)
        curtree = localtree.LocalTree(local)
        curtree.rebuild_tree()
        if oldtree is not None:
            # Iterate over all nodes in the old tree first
            for oldnode in PreOrderIter(oldtree.tree):
                node = curtree.get_node_by_path(oldnode.relpath)
                if node is not None:
                    self._check_node(oldnode, node)
                    # print(f"Name: {node.name}: {node.sync_state}")
                else:
                    # print("NOT FOUND")
                    if oldnode.entry_type == "document":
                        deleted_nodes["documents"].append(oldnode.relpath)
                    else:
                        deleted_nodes["folders"].append(oldnode.relpath)
            # Iterate over all nodes in the new tree now to find new items
            for node in PreOrderIter(curtree.tree):
                if node.sync_state is None:
                    # Node not yet checked means it was not present in the old tree.
                    node.sync_state = "new"
                    # print(f"Name: {node.name}: {node.sync_state}")
        else:
            print("WARNING: No old remote state found. Maybe this is an initial sync?")
        print(deleted_nodes)
        return deleted_nodes, curtree

    def _handle_deletions(self, deletions_loc, deletions_rem, tree_rem, tree_loc):
        """Handle deletion, i.e. delete locally what was deleted remotely and
        the other way around.

        """
        for d in deletions_loc["documents"]:
            self._dp_mgr.rm_file(self._fix_path4remote(d))
            # delete the node from the tree
            tree_rem.remove_node(self._fix_path4remote(d))
        for d in deletions_loc["folders"]:
            self._dp_mgr.rm_dir(self._fix_path4remote(d))
            # delete the node from the tree
            tree_rem.remove_node(self._fix_path4remote(d))
        for d in deletions_rem["documents"]:
            fn = tree_loc.get_node_by_path(self._fix_path4local(d)).abspath
            print("Deleting local file {}".format(fn))
            if osp.exists(fn):
                os.remove(fn)
            else:
                print("ERROR: File {} not found".format(fn))
            # delete the node from the tree
            tree_loc.remove_node(self._fix_path4local(d))
        for d in deletions_rem["folders"]:
            fn = tree_loc.get_node_by_path(self._fix_path4local(d)).abspath
            print("Deleting local folder {}".format(fn))
            if osp.exists(fn):
                os.rmdir(fn)
            else:
                print("ERROR: File {} not found".format(fn))
            # delete the node from the tree
            tree_loc.remove_node(self._fix_path4local(d))
        return tree_rem, tree_loc

    def _cmp_local2remote(self, tree_loc, tree_rem):
        """Compare the changes in the local and remote trees.

        """
        # loop through all remote nodes
        for node_rem in PreOrderIter(tree_rem.tree):
            node_loc = tree_loc.get_node_by_path(
                self._fix_path4local(node_rem.entry_path)
            )
            if node_loc is not None:
                # Only relevant for documents
                if node_rem.entry_type == "document":
                    if not node_rem.file_size == node_loc.file_size:
                        # local and remote are different
                        self._handle_changes(node_loc, node_rem)
            else:
                # download
                targetpath = osp.join(
                    osp.dirname(self._local_root),
                    self._fix_path4local(node_rem.entry_path),
                )
                print(
                    "Local node not found. Attempting download of {}".format(targetpath)
                )
                if node_rem.entry_type == "folder":
                    os.mkdir(targetpath)
                    # TODO: must add the node in the tree!
                else:
                    self._downloader.download_file(
                        node_rem.entry_path, targetpath, "remote_wins"
                    )
        # loop through all local nodes, upload those not on the remote
        for node_loc in PreOrderIter(tree_loc.tree):
            node_rem = tree_rem.get_node_by_path(
                self._fix_path4remote(node_loc.relpath)
            )
            if node_rem is None:
                # upload
                targetpath = self._fix_path4remote(node_loc.relpath)
                print(
                    "Remote node not found. Attempting upload of {}".format(targetpath)
                )
                if node_loc.entry_type == "folder":
                    self._dp_mgr.mkdir(targetpath)
                    # TODO: must add the node in the tree!
                else:
                    self._uploader.upload_file(
                        node_loc.abspath, targetpath, "local_wins"
                    )

    def _handle_changes(self, node_loc, node_rem):
        """Handle a difference of the local and remote nodes.

        """
        if node_rem.sync_state is None or node_loc.sync_state is None:
            # download in remote wins mode
            print(
                "Attempting download of {} to {}".format(
                    node_rem.entry_path, node_loc.abspath
                )
            )
            self._downloader.download_file(
                node_rem.entry_path, node_loc.abspath, "remote_wins"
            )
        elif node_rem.sync_state == "equal" and node_loc.sync_state == "equal":
            # ask the user (should not happen)
            print(
                "Neither the local nor the remote node is modified, but the documents are different. WHAT!?"
            )
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "modified" and node_loc.sync_state == "modified":
            # ask the user
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "new" and node_loc.sync_state == "new":
            # ask the user
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "equal" and node_loc.sync_state == "modified":
            # upload
            print(
                "Attempting upload of {} to {}".format(
                    node_loc.abspath, node_rem.entry_path
                )
            )
            self._uploader.upload_file(
                node_loc.abspath, node_rem.entry_path, "local_wins"
            )
        elif node_rem.sync_state == "equal" and node_loc.sync_state == "new":
            # ask the user (should not happen)
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "modified" and node_loc.sync_state == "equal":
            # download
            print(
                "Attempting download of {} to {}".format(
                    node_rem.entry_path, node_loc.abspath
                )
            )
            self._downloader.download_file(
                node_rem.entry_path, node_loc.abspath, "remote_wins"
            )
        elif node_rem.sync_state == "new" and node_loc.sync_state == "equal":
            # ask the user (should not happen)
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "modified" and node_loc.sync_state == "new":
            # ask the user (should not happen)
            self._askuser(node_loc, node_rem)
        elif node_rem.sync_state == "new" and node_loc.sync_state == "modified":
            # ask the user (should not happen)
            self._askuser(node_loc, node_rem)

    def _askuser(self, node_loc, node_rem):
        """Ask the user what to do.

        """
        message = "Conflict for node {}, reason L:{} R:{}".format(
            node_loc.relpath, node_loc.sync_state, node_rem.sync_state
        )
        question = "Choose which version to keep [l]ocal, [r]emote, [s]kip: "
        print("")
        response = ""
        while response not in ["l", "r", "s"]:
            print(message)
            response = str(input(question))
        if response == "l":
            self._uploader.upload_file(
                node_loc.abspath, node_rem.entry_path, "local_wins"
            )
        elif response == "r":
            self._downloader.download_file(
                node_rem.entry_path, node_loc.abspath, "remote_wins"
            )

    def _check_node(self, old, new):
        """Check the status of the nodes.

        """
        if old.entry_type == "document":
            # first check the file sizes. We consider the nodes the same when the size matches
            if old.file_size == new.file_size:
                new.sync_state = "equal"
            else:
                new.sync_state = "modified"
        else:
            new.sync_state = "equal"

    def _save_sync_state(self, local, remote):
        # the remote tree
        self._dp_mgr.rebuild_tree()
        start_node = self._dp_mgr.get_node(remote)
        fn_loc, fn_rem = self._get_syncstate_paths(local)
        self._dp_mgr.remote_tree.save_to_file(fn_rem, start_node)
        # the local tree
        loctree = localtree.LocalTree(osp.expanduser(local))
        loctree.rebuild_tree()
        loctree.save_to_file(fn_loc)

    def _load_sync_state_remote(self, local):
        _, fn = self._get_syncstate_paths(local)
        if osp.exists(fn):
            oldtree = remotetree.load_from_file(fn)
        else:
            oldtree = None
        return oldtree

    def _load_sync_state_local(self, local):
        fn, _ = self._get_syncstate_paths(local)
        if osp.exists(fn):
            oldtree = localtree.load_from_file(fn)
        else:
            oldtree = None
        return oldtree

    def _get_syncstate_paths(self, local):
        rem = osp.join(osp.expanduser(local), ".dp_syncstate_remote")
        loc = osp.join(osp.expanduser(local), ".dp_syncstate_local")
        return loc, rem
