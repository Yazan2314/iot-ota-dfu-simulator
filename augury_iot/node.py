# Which cloud server talks to each node hardware type.
API_HOSTS = {
    "ahn2": "buildroot_api.azure",
    "cassia": "buildroot_api.azure",
    "moxa": "moxa_api.azure",
}

# A node doesn't install an artifact instantly: it installs on its Nth poll
# of the OTA channel (simulates download + install time).
POLLS_TO_INSTALL = 2


def hardware_type_from_uuid(uuid: str) -> str:
    # "MOXA_TBCDB1045001" -> "moxa". Raises ValueError if the UUID is invalid.
    # Split only at the first "_", so the string part may contain "_" too.
    if not isinstance(uuid, str):
        raise ValueError("UUID must be a string")

    parts = uuid.split("_", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid UUID: {uuid}")

    hardware_type = parts[0].lower()
    if hardware_type not in API_HOSTS:
        raise ValueError(f"Unknown hardware type in UUID: {uuid}")
    return hardware_type


def parse_artifact(artifact: str) -> tuple[str, int] | None:
    # "moxa_34.swu" -> ("moxa", 34)
    # None if the name doesn't follow <hardware_type>_<version>.swu
    if not artifact.endswith(".swu"):
        return None
    new_artifact = artifact.removesuffix(".swu")
    parts = new_artifact.split("_")
    if len(parts) != 2:
        return None
    hw_type = parts[0]
    version = parts[1]
    if not version.isdigit():
        return None
    # Version as a number so 10 > 9 compares correctly.
    return hw_type.lower(), int(version)


class Node:
    def __init__(self, uuid: str, version: int | str) -> None:
        hardware_type = hardware_type_from_uuid(uuid)
        self._uuid = uuid
        self._version = int(version)
        self._hardware_type = hardware_type
        self._ota_channel = f"OTA_{uuid}"
        self._api_host = API_HOSTS[hardware_type]
        self._endpoints = []             # serials of paired endpoints
        self._pending_artifact = None    # what's waiting in the OTA channel
        self._polls_waited = 0           # polls since the artifact arrived
        self._last_error = ""            # reason of the last failed OTA

    def add_endpoint(self, serial: str) -> None:
        if serial not in self._endpoints:
            self._endpoints.append(serial)

    def receive_artifact(self, artifact: str) -> tuple[bool, str]:
        # Cloud posted an artifact to this node's channel.
        # Only the name format is checked here; the hardware type is checked
        # by the node itself at install time (see poll), like a real device.
        if parse_artifact(artifact) is None:
            return False, f"invalid artifact name: {artifact}"
        # A newer post replaces whatever was waiting, and the download restarts.
        self._pending_artifact = artifact
        self._polls_waited = 0
        self._last_error = ""            # a new artifact clears the old error
        return True, "artifact queued"

    def clear_artifact(self, artifact: str) -> tuple[bool, str]:
        if parse_artifact(artifact) is None:
            return False, f"invalid artifact name: {artifact}"
        if self._pending_artifact != artifact:
            return False, f"artifact not in channel: {artifact}"
        self._pending_artifact = None
        self._polls_waited = 0
        return True, "artifact cleared"

    def poll(self) -> tuple[bool, str]:
        # One check of the OTA channel. The test calls this in its retry loop.
        if self._pending_artifact is None:
            return False, "no artifact pending"

        # Not instant: still "downloading" until enough polls have passed.
        self._polls_waited += 1
        if self._polls_waited < POLLS_TO_INSTALL:
            return False, "downloading"

        # Install attempt. The artifact leaves the channel even if it fails,
        # otherwise a bad artifact would fail again on every poll.
        artifact = self._pending_artifact
        self._pending_artifact = None
        self._polls_waited = 0

        # Only accept artifacts built for this node's hardware.
        hw_type, version = parse_artifact(artifact)
        if hw_type != self._hardware_type:
            self._last_error = f"hardware mismatch: {artifact} is for {hw_type}, node is {self._hardware_type}"
            return False, self._last_error

        # Our assumption: same or older version counts as a failed OTA.
        if version <= self._version:
            self._last_error = f"version not newer: {artifact} vs current {self._version}"
            return False, self._last_error

        self._version = version
        self._last_error = ""            # a successful OTA clears the old error
        return True, f"updated to {version}"

    def to_dict(self) -> dict:
        # Matches the API shape in the assignment, plus a few extra fields.
        return {
            "uuid": self._uuid,
            "hardware_type": self._hardware_type,
            "api_host": self._api_host,
            "ota_channel": self._ota_channel,
            "version": self._version,
            "endpoints": list(self._endpoints),   # copy, so callers can't edit the node
            "pending_artifact": self._pending_artifact,
            "last_error": self._last_error,
        }


if __name__ == "__main__":
    print("--- TC1: happy flow ---")
    node = Node("MOXA_TBCDB1045001", 33)
    node.receive_artifact("moxa_34.swu")
    print(node.poll())                 # (False, 'downloading')
    print(node.poll())                 # (True, 'updated to 34')
    print(node._version)               # 34

    print("--- TC3: bad firmware ---")
    cassia = Node("CASSIA_ABC123", 33)
    cassia.receive_artifact("moxa_34.swu")
    print(cassia.poll())               # (False, 'downloading')
    print(cassia.poll())               # (False, 'hardware mismatch: ...')
    print(cassia._version)             # 33, unchanged
    print(cassia._last_error)

    print("--- to_dict ---")
    cassia.add_endpoint("EP1-001")
    print(cassia.to_dict())
