"""
The MIT License (MIT)

Copyright (c) 2017 Markus Peter mpeter at emdev dot de

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


Support for Medisana BS440 and compatible bathroom scales
With thanks to https://github.com/keptenkurk

"""

import struct
from datetime import datetime, timedelta
from ..lib.connection import BTLEConnection
import logging

_LOGGER = logging.getLogger(__name__)

PROP_PERSON_HANDLE = 0x25
PROP_WEIGHT_HANDLE = 0x1b
PROP_BODY_HANDLE = 0x1e

PROP_GENDER_MALE = "male"
PROP_GENDER_FEMALE = "female"

PROP_ACTIVITY_HIGH = "high"
PROP_ACTIVITY_NORMAL = "normal"

PROP_WRITE_HANDLE = 0x23


class MedisanaBS440Person:
    """Representation of a person record."""
    
    def __init__(self, _handle, _data):
        """
        Originally by https://github.com/keptenkurk
        decodePerson
        handle: 0x25
        values[0] = 0x84
        Properties:
            valid (True, False)
            person (1..9)
            gender (male|female)
            age (0..255 years)
            size (0..255 cm)
            activity (normal|high)
        """
        data = unpack('BxBxBBBxB', bytes(_data[0:9]))
        self.valid = (handle == 0x25 and data[0] == 0x84)
        self.person = data[1]
        if data[2] == 1:
            self.gender = PROP_GENDER_MALE
        else:
            self.gender = PROP_GENDER_FEMALE
        self.age = data[3]
        self.size = data[4]
        if data[5] == 3:
            self.activity = PROP_ACTIVITY_HIGH
        else:
            self.activity = PROP_ACTIVITY_NORMAL
        
        self.weight = []
        self.body = []

 
 class MedisanaBS440Weight:
    """Representation of a weight record."""
    
    def __init__(self, _handle, _data):
        """
        Originally by https://github.com/keptenkurk
        decodeWeight
        Handle: 0x1b
        Byte[0] = 0x1d
        Properties:
            valid (True, False)
            weight (5,0 .. 180,0 kg)
            timestamp (unix timestamp date and time of measurement)
            person (1..9)
        """
        data = unpack('<BHxxIxxxxB', bytes(_data[0:14]))
        self.valid = (handle == 0x1b and data[0] == 0x1d)
        self.weight = data[1]/100.0
        if data[2] < sys.maxint:
            self.timestamp = data[2]
        else:
            self.timestamp = 0
        self.person = data[3]


 class MedisanaBS440Body:
    """Representation of a body record."""
    
    def __init__(self, _handle, _data):
        """
        Originally by https://github.com/keptenkurk
        decodeBody
        Handle: 0x1e
        Byte[0] = 0x6f
        Properties:
            valid (True, False)
            timestamp (unix timestamp date and time of measurement)
            person (1..9)
            kcal = (0..65025 Kcal)
            fat = (0..100,0 %)  percentage of body fat
            tbw = (0..100,0 %) percentage of water
            muscle = (0..100,0 %) percentage of muscle
            bone = (0..100,0) bone weight
        """
        data = unpack('<BIBHHHHH', bytes(_data[0:16]))
        self.valid = (handle == 0x1e and data[0] == 0x6f)
        if data[1] < sys.maxint:
            self.timestamp = data[1]
        else:
            self.timestamp = 0
        self.person = data[2]
        self.kcal = data[3]
        self.fat = (0x0fff & data[4])/10.0
        self.tbw = (0x0fff & data[5])/10.0
        self.muscle = (0x0fff & data[6])/10.0
        self.bone = (0x0fff & data[7])/10.0



# pylint: disable=too-many-instance-attributes
class MedisanaBS440:
    """Representation of a Medisana BS440 or compatible bathroom scale."""

    def __init__(self, _mac):
        """Initialize the object."""
        
        self._person = {}
        self._conn = BTLEConnection(_mac)
        self._conn.set_callback(PROP_PERSON_HANDLE, self.handle_person_notification)
        self._conn.set_callback(PROP_WEIGHT_HANDLE, self.handle_weight_notification)
        self._conn.set_callback(PROP_BODY_HANDLE, self.handle_body_notification)


    def handle_person_notification(self, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        _LOGGER.debug("Received person notification from the device..")
        result = MedisanaBS440Person(PROP_PERSON_HANDLE, data)
        self._person[result.person] = result

    def handle_weight_notification(self, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        _LOGGER.debug("Received person notification from the device..")
        result = MedisanaBS440Weight(PROP_WEIGHT_HANDLE, data)
        self._person[result.person].weight.append(result)

    def handle_body_notification(self, data):
        """Handle Callback from a Bluetooth (GATT) request."""
        _LOGGER.debug("Received person notification from the device..")
        result = MedisanaBS440Body(PROP_BODY_HANDLE, data)
        self._person[result.person].body.append(result)

    def update(self):
        """Update the data from the thermostat. Always sets the current time."""
        _LOGGER.debug("Querying the device..")
        timestamp = bytearray(pack('<I', int(time.time())))
        timestamp.insert(0, 2)
        self._conn.write_request_raw(PROP_WRITE_HANDLE, timestamp, 30)

