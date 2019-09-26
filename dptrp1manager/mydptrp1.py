#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from urllib.parse import quote_plus

from dptrp1.dptrp1 import DigitalPaper


class MyDigitalPaper(DigitalPaper):
    """My extension of the DigitalPaper class.

    """

    def __init__(self, addr=None):
        super().__init__(addr)
        # set the time of the dpt-rp1
        self.set_datetime()

    # file management

    def download_byid(self, remote_id):
        url = "{base_url}/documents/{remote_id}/file".format(
            base_url=self.base_url, remote_id=remote_id
        )
        response = self.session.get(url)
        return response.content

    def delete_document_byid(self, remote_id):
        url = "/documents/{remote_id}".format(remote_id=remote_id)
        self._delete_endpoint(url)

    def delete_directory_byid(self, dir_id):
        data = self.get_directory_contents_byid(dir_id)
        if not "error_code" in data.keys():
            nnodes = data["count"]
            if nnodes == 0:
                self._delete_endpoint("/folders/{}".format(dir_id))
            else:
                print("ERROR: Remote directory not empty. Cannot delete it.")

    def get_directory_contents_byid(self, dir_id):
        data = self._get_endpoint("/folders/{}/entries2".format(dir_id)).json()
        return data

    def upload_byid(self, fh, directory_id, remote_filename):
        info = {
            "file_name": remote_filename,
            "parent_folder_id": directory_id,
            "document_source": "",
        }
        r = self._post_endpoint("/documents2", data=info)
        doc = r.json()
        doc_id = doc["document_id"]
        doc_url = "/documents/{doc_id}/file".format(doc_id=doc_id)

        files = {"file": (quote_plus(remote_filename), fh, "rb")}
        self._put_endpoint(doc_url, files=files)

    def new_folder_byid(self, directory_id, remote_foldername):
        info = {"folder_name": remote_foldername, "parent_folder_id": directory_id}

        r = self._post_endpoint("/folders2", data=info)

    def _get_highest_level_folder(self, folderdict):
        res = []
        for fpath, fentry in folderdict.items():
            level = len(fpath.split("/"))
            res.append([level, fentry])
        return sorted(res, key=lambda xx: xx[0])[0][1]

    def list_all(self):
        # TODO: This is not yet perfect. If folders are to large, entries might be missed.
        limit = 1000

        # use a dict with paths as keys
        entrydict = self._get_contents("root", limit)

        if len(entrydict.keys()) >= limit:
            folders = self._get_folders(entrydict)
            while folders != {}:
                cur_folder = self._get_highest_level_folder(folders)
                # print(cur_folder["entry_path"])
                # get new folders and append
                new_entries = self._get_contents(cur_folder["entry_id"], limit)
                entrydict.update(new_entries)
                new_folders = self._get_folders(new_entries)
                # remove folders if new entrydict length below limit, else add
                # print(len(new_entries.keys()))
                if len(new_entries.keys()) < limit:
                    folders.pop(cur_folder["entry_path"])
                    for ff in new_folders.keys():
                        folders.pop(ff, None)
                else:
                    folders.update(new_folders)
                    folders.pop(cur_folder["entry_path"])
        return list(entrydict.values())

    def _get_contents(self, toplevel_folder_id, limit):
        data = self._get_endpoint(
            f"/documents2?entry_type=all&limit={limit}&order_type=created_date_asc&origin_folder_id={toplevel_folder_id}"
        ).json()
        try:
            el = data["entry_list"]
        except KeyError:
            print(data)
            raise
        res = dict()
        for entry in el:
            res[entry["entry_path"]] = entry
        return res

    def _get_folders(self, entrydict):
        res = {}
        for entry in entrydict.values():
            if entry["entry_type"] == "folder":
                res[entry["entry_path"]] = entry
        return res

    ### Configuration

    def get_timeout(self):
        data = self._get_endpoint("/system/configs/timeout_to_standby").json()
        return data["value"]

    def set_timeout(self, value):
        data = self._put_endpoint(
            "/system/configs/timeout_to_standby", data={"value": value}
        )

    def get_date_format(self):
        data = self._get_endpoint("/system/configs/date_format").json()
        return data["value"]

    def set_date_format(self, value):
        data = self._put_endpoint("/system/configs/date_format", data={"value": value})

    def get_time_format(self):
        data = self._get_endpoint("/system/configs/time_format").json()
        return data["value"]

    def set_time_format(self, value):
        data = self._put_endpoint("/system/configs/time_format", data={"value": value})

    def get_timezone(self):
        data = self._get_endpoint("/system/configs/timezone").json()
        return data["value"]

    def set_timezone(self, value):
        data = self._put_endpoint("/system/configs/timezone", data={"value": value})

    def get_owner(self):
        data = self._get_endpoint("/system/configs/owner").json()
        return data["value"]

    def set_owner(self, value):
        data = self._put_endpoint("/system/configs/owner", data={"value": value})

    ### System info

    def get_storage(self):
        data = self._get_endpoint("/system/status/storage").json()
        return data

    def get_firmware_version(self):
        data = self._get_endpoint("/system/status/firmware_version").json()
        return data["value"]

    def get_mac_address(self):
        data = self._get_endpoint("/system/status/mac_address").json()
        return data["value"]

    def get_battery(self):
        data = self._get_endpoint("/system/status/battery").json()
        return data

    def get_info(self):
        data = self._get_endpoint("/register/information").json()
        return data
