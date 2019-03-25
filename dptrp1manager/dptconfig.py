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


class DPConfig(object):
    """Represent the configuration of the DPT-RP1.

    Parameters
    ----------
    dp_mgr : DPManager

    """

    def __init__(self, dp_mgr):
        super(DPConfig, self).__init__()
        self._dp_mgr = dp_mgr

    @property
    def templates(self):
        """List of templates.

        """
        res = self._dp_mgr.dp.list_templates()
        tmp_list = []
        for template in res["template_list"]:
            tmp_list.append(template["template_name"])
        return tmp_list

    def rename_template(self, old_name, new_name):
        self._dp_mgr.dp.rename_template(old_name, new_name)

    def delete_template(self, name):
        self._dp_mgr.dp.delete_template(name)

    def add_template(self, name, path):
        path = osp.expanduser(path)
        if osp.exists(path) and path.endswith(".pdf"):
            with open(path, "rb") as f:
                self._dp_mgr.dp.add_template(name, f)
        else:
            print(
                "Adding template failed. File {} not found or not a pdf file.".format(
                    path
                )
            )

    @property
    def timeout(self):
        """Timeout to lock in minutes

        """
        timeout = self._dp_mgr.dp.get_timeout()
        return timeout

    @timeout.setter
    def timeout(self, val):
        self.dp._dp_mgr.set_timeout(val)

    @property
    def owner(self):
        """Owner of the device (for pdf comments)

        """
        owner = self._dp_mgr.dp.get_owner()
        return owner

    @owner.setter
    def owner(self, val):
        self._dp_mgr.dp.set_owner(val)

    @property
    def time_format(self):
        """The time format.

        """
        time_format = self._dp_mgr.dp.get_time_format()
        return time_format

    @time_format.setter
    def time_format(self, val):
        self._dp_mgr.dp.set_time_format(val)

    @property
    def date_format(self):
        """The date format

        """
        date_format = self._dp_mgr.dp.get_date_format()
        return date_format

    @date_format.setter
    def date_format(self, val):
        self._dp_mgr.dp.set_date_format(val)

    @property
    def timezone(self):
        """The timezone

        """
        timezone = self._dp_mgr.dp.get_timezone()
        return timezone

    @timezone.setter
    def timezone(self, val):
        self._dp_mgr.dp.set_timezone(val)

    @property
    def storage_free(self):
        """Free space on device in Byte

        """
        storage = self._dp_mgr.dp.get_storage()
        free = float(storage["available"])
        return free

    @property
    def storage_total(self):
        """Total storage capacity in Byte

        """
        storage = self._dp_mgr.dp.get_storage()
        total = float(storage["capacity"])
        return total

    @property
    def battery_level(self):
        """Battery level in percent.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["level"]

    @property
    def battery_pen(self):
        """Pen battery level in percent.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["pen"]

    @property
    def battery_health(self):
        """Battery health

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["health"]

    @property
    def battery_status(self):
        """Battery status (charging/discharging)

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["status"]

    @property
    def plugged(self):
        """Check if connected via usb for charging.

        """
        battery = self._dp_mgr.dp.get_battery()
        return battery["plugged"]

    @property
    def model(self):
        """The model name

        """
        info = self._dp_mgr.dp.get_info()
        return info["model_name"]

    @property
    def serial(self):
        """The seral number of the device

        """
        info = self._dp_mgr.dp.get_info()
        return info["serial_number"]

    @property
    def firmware_version(self):
        """Get the firmware version

        """
        fw_version = self._dp_mgr.dp.get_firmware_version()
        return fw_version

    @property
    def mac_address(self):
        """The mac address

        """
        mac_address = self._dp_mgr.dp.get_mac_address()
        return mac_address

    def list_wifi(self):
        """List known wifis.

        """
        return self._dp_mgr.dp.wifi_list()

    def scan_wifi(self):
        """Scan wifis

        """
        return self._dp_mgr.dp.wifi_scan()

    def add_wifi(
        self,
        ssid,
        security="nonsec",
        passwd="",
        dhcp=True,
        static_address="",
        gateway="",
        network_mask="",
        dns1="",
        dns2="",
        proxy=False,
    ):
        """Add a wifi network.

        Parameters
        ----------
        ssid : string
            Wifi network name
        security : string ('nonsec', 'psk')
            Wifi security, default is 'nonsec'
        passwd : string
            Password, default is ''
        dhcp : bool (default True)
            Use dhcp for ip address management?
        static_address : string (default '')
            Static ip
        gateway : string (default '')
            Gateway ip
        network_mask : integer
            Integer determining the net mask (e.g. 24)
        dns1 : string (default '')
            DNS ip
        dns2 : string (default '')
            DNS ip
        proxy : bool (default False)
            Use a proxy?

        """
        self._dp_mgr.dp.configure_wifi(
            ssid,
            security,
            passwd,
            dhcp,
            static_address,
            gateway,
            network_mask,
            dns1,
            dns2,
            proxy,
        )

    def delete_wifi(self, ssid, security="nonsec"):
        """Delete a known wifi

        Parameters
        ----------
        ssid : string
            Wifi network name
        security : string ('nonsec', 'psk')
            Wifi security, default is 'nonsec'

        """
        self._dp_mgr.dp.delete_wifi(ssid, security)

    @property
    def wifi_enabled(self):
        """Is wifi enabled?

        """
        val = self._dp_mgr.dp.wifi_enabled()["value"]
        if val == "on":
            return True
        else:
            return False

    def enable_wifi(self):
        self._dp_mgr.dp.enable_wifi()

    def disable_wifi(self):
        self._dp_mgr.dp.disable_wifi()
