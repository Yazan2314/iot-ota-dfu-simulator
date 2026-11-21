import re

# Minimum battery needed before an endpoint is allowed to run a DFU.
BATTERY_THRESHOLDS = {
    "EP1": 2500,
    "EP2": 2500,
    "Canary_A": 3600,
}


def _is_number(value: object) -> bool:
    # bool is a subclass of int in Python, so exclude it explicitly.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


VERSION_PATTERN = re.compile(r"\d+(\.\d+)*")


def parse_version(value: int | str) -> tuple[str, tuple[int, ...]]:
    # Endpoint versions: 3, "3", "1.0", "2.1.4".
    # Returns (text, key): text is what the API shows, key is used to compare.
    if _is_count(value) and value >= 0:
        text = str(value)
    elif isinstance(value, str) and VERSION_PATTERN.fullmatch(value):
        text = value
    else:
        raise ValueError(f"Invalid version: {value}")
    # Compare part by part as numbers, so "1.10" > "1.9".
    # Trailing zeros don't count, so "1.0" == "1".
    key = [int(part) for part in text.split(".")]
    while len(key) > 1 and key[-1] == 0:
        key.pop()
    return text, tuple(key)


class Endpoint:
    def __init__(
        self,
        serial: str,
        hardware_type: str,
        node_uuid: str,
        battery: float,
        version: int | str,
        backlog: int = 0,
    ) -> None:
        # Fail early on bad input instead of letting it slip into the DFU rules later.
        # Type checks come before comparisons, so bad types raise ValueError
        # (which the API turns into 400) instead of a TypeError.
        if hardware_type not in BATTERY_THRESHOLDS:
            raise ValueError(f"Unknown endpoint hardware type: {hardware_type}")
        self._check_battery(battery)
        self._check_backlog(backlog)

        self._serial = serial
        self._hardware_type = hardware_type
        self._node_uuid = node_uuid          # the node this endpoint is paired with
        self._battery = battery              # can be fractional, e.g. 3000.5
        self._version, self._version_key = parse_version(version)
        self._backlog = backlog              # samples not uploaded yet (whole number)
        self._last_error = ""                # why the last DFU was refused

    @staticmethod
    def _check_battery(battery: float) -> None:
        if not _is_number(battery) or battery < 0:
            raise ValueError(f"Invalid battery level: {battery}")

    @staticmethod
    def _check_backlog(backlog: int) -> None:
        if not _is_count(backlog) or backlog < 0:
            raise ValueError(f"Invalid backlog: {backlog}")

    @property
    def hardware_type(self) -> str:
        return self._hardware_type

    def drain_backlog(self) -> None:
        # Simulates the endpoint uploading all pending samples.
        self._backlog = 0

    def add_samples(self, count: int) -> None:
        # New measurements waiting to be uploaded.
        self._check_backlog(count)
        self._backlog += count

    def set_battery(self, battery: float) -> None:
        # Simulates the battery charging or draining.
        self._check_battery(battery)
        self._battery = battery

    def why_blocked(self) -> str | None:
        # All DFU gating rules live here. Returns the reason DFU can't run, or None.
        # Pending samples would be lost if the endpoint restarts for an update.
        if self._backlog > 0:
            return "backlog pending"
        # Low battery could kill the endpoint mid-update.
        threshold = BATTERY_THRESHOLDS[self._hardware_type]
        if self._battery < threshold:
            return "battery too low"
        return None

    def try_update(self, new_version: int | str) -> tuple[bool, str]:
        # The only way to change the version: refused -> nothing changes,
        # and the reason is kept in last_error.
        new_text, new_key = parse_version(new_version)
        # Same rule as the Node: only move to a newer version.
        if new_key <= self._version_key:
            reason = f"version not newer: {new_text} vs current {self._version}"
        else:
            reason = self.why_blocked()
        if reason is not None:
            self._last_error = reason
            return False, reason
        self._version, self._version_key = new_text, new_key
        self._last_error = ""
        return True, f"updated to {new_text}"

    def to_dict(self) -> dict:
        # Same field names as the API shape in the assignment, plus last_error.
        return {
            "serial_number": self._serial,
            "hardware_type": self._hardware_type,
            "uuid": self._node_uuid,
            "battery": self._battery,
            "version": self._version,
            "backlog": self._backlog,
            "last_error": self._last_error,
        }


if __name__ == "__main__":
    ep = Endpoint("EP1-001", "EP1", "MOXA_123", battery=3000, version=1, backlog=5)
    print(ep.try_update(2))      # False: backlog pending
    ep.drain_backlog()
    print(ep.try_update(2))      # True
    print(ep.try_update(2))      # False: version not newer
    print(ep.to_dict())

    weak = Endpoint("CAN-001", "Canary_A", "MOXA_123", battery=3500, version=1)
    print(weak.try_update(2))    # False: battery too low (3500 < 3600)
    weak.set_battery(3600)
    print(weak.try_update(2))    # True after charging

    dotted = Endpoint("EP2-001", "EP2", "MOXA_123", battery=3000, version="1.9")
    print(dotted.try_update("1.10"))     # True: 1.10 is newer than 1.9
    print(dotted.try_update("1.10.0"))   # False: same version
