# Minimum battery needed before an endpoint is allowed to run a DFU.
BATTERY_THRESHOLDS = {
    "EP1": 2500,
    "EP2": 2500,
    "Canary_A": 3600,
}


class Endpoint:
    def __init__(self, serial, hardware_type, node_uuid, battery, version, backlog=0):
        # Fail early on bad input instead of letting it slip into the DFU rules later.
        if hardware_type not in BATTERY_THRESHOLDS:
            raise ValueError(f"Unknown endpoint hardware type: {hardware_type}")
        if backlog < 0:
            raise ValueError("backlog cannot be negative")
        self._serial = serial
        self._hardware_type = hardware_type
        self._node_uuid = node_uuid        # the node this endpoint is paired with
        self._battery = battery
        self._version = version
        self._backlog = backlog            # samples not uploaded yet

    def drain_backlog(self):
        # Simulates the endpoint uploading all pending samples.
        self._backlog = 0

    def why_blocked(self):
        # All DFU gating rules live here. Returns the reason DFU can't run, or None.
        # Pending samples would be lost if the endpoint restarts for an update.
        if self._backlog > 0:
            return "backlog pending"
        # Low battery could kill the endpoint mid-update.
        threshold = BATTERY_THRESHOLDS[self._hardware_type]
        if self._battery < threshold:
            return "battery too low"
        return None

    def try_update(self, new_version):
        # The only way to change the version: blocked -> nothing changes.
        reason = self.why_blocked()
        if reason is not None:
            return False, reason
        self._version = new_version
        return True, "Update successful"

    def to_dict(self):
        # Same field names as the API shape in the assignment.
        return {
            "serial_number": self._serial,
            "hardware_type": self._hardware_type,
            "uuid": self._node_uuid,
            "battery": self._battery,
            "version": self._version,
            "backlog": self._backlog,
        }


if __name__ == "__main__":
    ep = Endpoint("EP1-001", "EP1", "MOXA_123", battery=3000, version="1", backlog=5)
    print(ep.try_update("2"))    # False: backlog
    print(ep.to_dict())          # version still "1"
    ep.drain_backlog()
    print(ep.try_update("2"))    # True
    print(ep.to_dict())          # version "2", backlog 0

    weak = Endpoint("CAN-001", "Canary_A", "MOXA_123", battery=3500, version="1")
    print(weak.try_update("2"))  # False: battery (3500 < 3600)
    print(weak.to_dict())        # version still "1"
