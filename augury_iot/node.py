# Which cloud server talks to each node hardware type.
API_HOSTS = {
    "ahn2": "buildroot_api.azure",
    "cassia": "buildroot_api.azure",
    "moxa": "moxa_api.azure",
}

# A node does not install an artifact instantly. It installs it on its
# Nth poll of the OTA channel (simulates download + install time).
POLLS_TO_INSTALL = 2


def hardware_type_from_uuid(uuid):
    parts = uuid.split("_")
    hardware_type = parts[0].lower()
    return hardware_type


def parse_artifact(artifact):
    # "moxa_34.swu" -> ("moxa", 34)
    # Returns None if the name does not follow <hardware_type>_<version>.swu
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

    return hw_type.lower(), int(version)


class Node:
    def __init__(self, uuid, version):
        hardware_type = hardware_type_from_uuid(uuid)
        if hardware_type not in API_HOSTS:
            raise ValueError(f"Unknown node hardware type in UUID: {uuid}")
        self._uuid = uuid
        self._version = int(version)
        self._hardware_type = hardware_type
        self._ota_channel = f"OTA_{uuid}"
        self._api_host = API_HOSTS[hardware_type]
        self._endpoints = []
        self._pending_artifact = None
        self._polls_waited = 0
        self._last_error = ""

    def add_endpoint(self, serial):
        if serial not in self._endpoints:
            self._endpoints.append(serial)
           

    def receive_artifact(self, artifact):
        if parse_artifact(artifact) is None:
            return False, f"invalid artifact name: {artifact}"

        self._pending_artifact = artifact
        self._polls_waited = 0
        return True, "artifact queued"
        

    def clear_artifact(self, artifact):
        if parse_artifact(artifact) is None:
            return False, f"invalid artifact name: {artifact}"
        if self._pending_artifact != artifact:
            return False, f"artifact not in channel: {artifact}"
        self._pending_artifact = None
        self._polls_waited = 0
        return True, "artifact cleared"


    def poll(self):
        if self._pending_artifact is None:
            return False, "no artifact pending"

        self._polls_waited += 1
        if self._polls_waited < POLLS_TO_INSTALL:
            return False, "downloading"
           
        artifact = self._pending_artifact
        self._pending_artifact = None
        self._polls_waited = 0

        hw_type, version = parse_artifact(artifact)
        if hw_type != self._hardware_type:
            self._last_error = f"hardware mismatch: {artifact} is for {hw_type}, node is {self._hardware_type}"
            return False, self._last_error

        if version <= self._version:
            self._last_error = f"version not newer: {artifact} vs current {self._version}"
            return False, self._last_error

        self._version = version
        self._last_error = ""
        return True, f"updated to {version}"

    def to_dict(self):
        return {
            "uuid": self._uuid,
            "hardware_type": self._hardware_type,
            "api_host": self._api_host,
            "ota_channel": self._ota_channel,
            "version": self._version,
            "endpoints": list(self._endpoints),   # a copy, not the real list
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
    print(cassia._version)             # 33  ← unchanged
    print(cassia._last_error)          # hardware mismatch: ...

    print("--- to_dict ---")
    cassia.add_endpoint("EP1-001")
    print(cassia.to_dict())