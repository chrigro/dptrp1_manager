#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from urllib.parse import quote_plus

from dptrp1.dptrp1 import DigitalPaper

class MyDigitalPaper(DigitalPaper):
    """My extension of the DigitalPaper class.

    """
    def __init__(self, addr = None):
        super().__init__(addr)

    # file management

    def download_byid(self, remote_id):
        url = "{base_url}/documents/{remote_id}/file".format(
                base_url = self.base_url,
                remote_id = remote_id)
        response = requests.get(url, verify=False, cookies=self.cookies)
        return response.content

    def delete_document_byid(self, remote_id):
        url = "/documents/{remote_id}".format(remote_id = remote_id)
        self._delete_endpoint(url)

    def delete_directory_byid(self, dir_id):
        data = self.get_directory_contents_byid(dir_id)
        if not "error_code" in data.keys():
            nnodes = data["count"]
            if nnodes == 0:
                self._delete_endpoint('/folders/{}'.format(dir_id))
            else:
                print('ERROR: Remote directory not empty. Cannot delete it.')

    def get_directory_contents_byid(self, dir_id):
        data = self._get_endpoint('/folders/{}/entries2'.format(dir_id)).json()
        return data

    def upload_byid(self, fh, directory_id, remote_filename):
        info = {
            "file_name": remote_filename,
            "parent_folder_id": directory_id,
            "document_source": ""
        }
        r = self._post_endpoint("/documents2", data=info)
        doc = r.json()
        doc_id = doc["document_id"]
        doc_url = "/documents/{doc_id}/file".format(doc_id = doc_id)

        files = {
            'file': (quote_plus(remote_filename), fh, 'rb')
        }
        self._put_endpoint(doc_url, files=files)

    def new_folder_byid(self, directory_id, remote_foldername):
        info = {
            "folder_name": remote_foldername,
            "parent_folder_id": directory_id
        }

        r = self._post_endpoint("/folders2", data=info)

    def list_all(self):
        allentries = []
        duplicatelist = self._list_all_worker('root', 'root', allentries)
        uniquelist = dict()
        for val in duplicatelist:
            if not val["entry_path"] in uniquelist.keys():
                uniquelist[val["entry_path"]] = val
        print(len(duplicatelist))
        print(len(list(uniquelist.values())))
        return uniquelist

        # for nn, dd in enumerate(data['entry_list']):
        #     print(f"{nn:3d}: Type: {dd['entry_type']}, Path: {dd['entry_path']}")
        # # data = self._get_endpoint('/documents2').json()
        # print(len(data['entry_list']))
        # print(type(data['entry_list']))

    def _list_all_worker(self, toplevel_folder_id, toplevel_folder_path, allentries):
        """recursive worker

        """
        print(f"current folder {toplevel_folder_path} with id {toplevel_folder_id}")

        limit = 200
        current_level = len(toplevel_folder_path.split("/"))

        data = self._get_endpoint(f"/documents2?entry_type=all&limit={limit}&order_type=entry_name_asc&origin_folder_id={toplevel_folder_id}").json()
        try:
            el = data['entry_list']
        except KeyError:
            print(data)
            raise
        # see if hit the limit
        if len(el) == limit:
            # print(f"Length of entrylist: {len(el)}")
            folds = self._get_folder_at_level(el, current_level + 1)
            for fold in folds:
                res = self._list_all_worker(fold["entry_id"], fold["entry_path"], allentries)
                # print(f"Appending {len(res)} entries")
                allentries = allentries + res
                # print(f"New length {len(allentries)} entries")
            return allentries
        else:
            print(f"found {len(el)} entries")
            return el

    def _get_folder_at_level(self, entrylist, n_level):
        """Return all folder at the given level below root (level 1)

        """
        res = []
        for entry in entrylist:
            if entry["entry_type"] == "folder":
                level = len(entry["entry_path"].split("/"))
                if level == n_level:
                    res.append(entry)
        return res


    ### Configuration

    def get_timeout(self):
        data = self._get_endpoint('/system/configs/timeout_to_standby').json()
        return(data['value'])

    def set_timeout(self, value):
        data = self._put_endpoint('/system/configs/timeout_to_standby', data={'value': value})

    def get_date_format(self):
        data = self._get_endpoint('/system/configs/date_format').json()
        return(data['value'])

    def set_date_format(self, value):
        data = self._put_endpoint('/system/configs/date_format', data={'value': value})

    def get_time_format(self):
        data = self._get_endpoint('/system/configs/time_format').json()
        return(data['value'])

    def set_time_format(self, value):
        data = self._put_endpoint('/system/configs/time_format', data={'value': value})

    def get_timezone(self):
        data = self._get_endpoint('/system/configs/timezone').json()
        return(data['value'])

    def set_timezone(self, value):
        data = self._put_endpoint('/system/configs/timezone', data={'value': value})

    def get_owner(self):
        data = self._get_endpoint('/system/configs/owner').json()
        return(data['value'])

    def set_owner(self, value):
        data = self._put_endpoint('/system/configs/owner', data={'value': value})

    ### System info

    def get_storage(self):
        data = self._get_endpoint('/system/status/storage').json()
        return(data)

    def get_firmware_version(self):
        data = self._get_endpoint('/system/status/firmware_version').json()
        return(data['value'])

    def get_mac_address(self):
        data = self._get_endpoint('/system/status/mac_address').json()
        return(data['value'])

    def get_battery(self):
        data = self._get_endpoint('/system/status/battery').json()
        return(data)

    def get_info(self):
        data = self._get_endpoint('/register/information').json()
        return(data)
