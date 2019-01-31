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


from subprocess import check_output
import sys
from datetime import datetime

def check_link(devs):
    if sys.platform == 'linux' or sys.platform == 'linux2':
        for dev, val in devs.items():
            scanoutput = check_output(['iw', 'dev', dev, 'link']).decode()
            lines = scanoutput.split('\n')
            for nn, line in enumerate(lines):
                line = line.strip()
                if line.startswith('SSID'):
                    devs[dev] = line.split()[1]

def get_ssids():
    """Find connected wireless networks.

    Returns
    -------
    dictionary
        keys are the device names of the wireless adapters, values the ssid if
        connected, an empty string otherwise. If not on linux return None.

    """
    if sys.platform == 'linux' or sys.platform == 'linux2':
        scanoutput = check_output(['iw', 'dev']).decode()
        lines = scanoutput.split('\n')
        devs = {}
        lastdev = ''
        for nn, line in enumerate(lines):
            line = line.strip()
            if line.startswith('Interface'):
                lastdev = line.split()[1]
                devs[lastdev] = ''
            if line.startswith('ssid'):
                devs[lastdev] = line.split()[1]
        conn = False
        for val in devs.values():
            if not val == '':
                conn = True
        if not conn:
            # we need to check again for the ssid using iw dev <name> link for each dev
            check_link(devs)
        return devs
    else:
        print('Can check for wireless devices only on linux.')
        return None


def default(obj):
    """For json serialization of a datetime object.

    Use as json.dumps(default=default)

    """
    if isinstance(obj, datetime):
        return { '_isoformat': obj.isoformat() }
    return super().default(obj)

def object_hook(obj):
    """For json deserialization of a datetime object.

    Use as json.loads(object_hook=object_hook)

    """
    _isoformat = obj.get('_isoformat')
    if _isoformat is not None:
        return datetime.fromisoformat(_isoformat)
    return obj


if __name__ == '__main__':
    devs = get_ssids()
    print(devs)
