BATTERY_THRESHOLDS = {
    "EP1": 2500,
    "EP2": 2500,
    "Canary_A": 3600,
}


class Endpoint:
    def __init__(self, serial, hardware_type, node_uuid, battery, version, backlog=0):
        self._serial = serial
        self._hardware_type = hardware_type
        self._node_uuid = node_uuid
        self._battery = battery
        self._version = version
        self._backlog = backlog


    def drain_backlog(self):
        self._backlog = 0


    def why_blocked(self):
        if self._backlog > 0:
            return "backlog pending"
        threshold = BATTERY_THRESHOLDS[self._hardware_type]
        if self._battery < threshold:
            return "Battery too low"
        
        return None


    def try_update(self,new_version):
        reason = self.why_blocked()
        if reason is not None:
            return False, reason
        self._version = new_version
        return True, "Update successful"


    def to_dict(self):
        return {
            "serial_number": self._serial,
            "hardware_type": self._hardware_type,
            "node_uuid": self._node_uuid,
            "battery": self._battery,
            "version": self._version,
            "backlog": self._backlog
        }


    









if __name__ == "__main__":
    ep = Endpoint("EP1-001", "EP1", "MOXA_123", battery=3000, version="1", backlog=5)
    print(ep.try_update("2"))    # expect: False (backlog)
    print(ep.to_dict())          # version still "1"
    ep.drain_backlog()
    print(ep.try_update("2"))    # expect: True
    print(ep.to_dict())          # version now "2", backlog 0

    weak = Endpoint("CAN-001", "Canary_A", "MOXA_123", battery=3500, version="1")
    print(weak.try_update("2"))  # expect: False (battery)
    print(weak.to_dict())        # version still "1"