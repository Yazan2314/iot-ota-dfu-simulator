from augury_iot.node import Node
from augury_iot.endpoint import Endpoint

OK = 200
BAD_REQUEST = 400


# Fake Augury backend. Tests talk only to this class, never to Node/Endpoint
# directly, so the same tests could later run against a real API.
# It holds no domain rules itself: it finds the device, calls it, and turns
# the result into 200/400.
class AuguryAPI:
    def __init__(self):
        self._nodes = {}        # uuid -> Node
        self._endpoints = {}    # serial -> Endpoint

    def api_reset(self):
        # Clean state between tests.
        self._nodes = {}
        self._endpoints = {}

    # ---------- private helpers ----------

    # Asking for a device that doesn't exist is a test bug, so fail loudly.
    def _get_node(self, uuid):
        if uuid not in self._nodes:
            raise KeyError(f"Node with UUID {uuid} not found")
        return self._nodes[uuid]

    def _get_endpoint(self, serial):
        if serial not in self._endpoints:
            raise KeyError(f"Endpoint with serial {serial} not found")
        return self._endpoints[serial]

    def _find_node_by_channel(self, ota_channel):
        # Post/clear get a channel name ("OTA_<uuid>"), not a uuid.
        for node in self._nodes.values():
            if node.to_dict()["ota_channel"] == ota_channel:
                return node
        return None

    def _node_has_endpoint_type(self, node_uuid, hardware_type):
        for serial in self._nodes[node_uuid].to_dict()["endpoints"]:
            if self._endpoints[serial].hardware_type == hardware_type:
                return True
        return False

    # ---------- setup helpers ----------

    def api_add_node(self, uuid, version):
        # UUIDs are unique: a second add is rejected, not replaced.
        if uuid in self._nodes:
            return BAD_REQUEST
        try:
            node = Node(uuid, version)
        except ValueError:
            return BAD_REQUEST          # unknown hardware type in the UUID
        self._nodes[uuid] = node
        return OK

    def api_add_endpoint(self, serial, hardware_type, node_uuid, battery, version, backlog=0):
        # Serials are unique, and an endpoint must belong to an existing node.
        if serial in self._endpoints:
            return BAD_REQUEST
        if node_uuid not in self._nodes:
            return BAD_REQUEST
        try:
            endpoint = Endpoint(serial, hardware_type, node_uuid, battery, version, backlog)
        except ValueError:
            return BAD_REQUEST
        # A node is paired with one endpoint of each type.
        if self._node_has_endpoint_type(node_uuid, hardware_type):
            return BAD_REQUEST
        self._endpoints[serial] = endpoint
        self._nodes[node_uuid].add_endpoint(serial)   # keep the node's EP list in sync
        return OK

    # ---------- required by the assignment ----------

    def api_get_node_by_uuid(self, uuid):
        node = self._get_node(uuid)
        return node.to_dict()

    def api_get_endpoint_by_serial(self, serial):
        endpoint = self._get_endpoint(serial)
        return endpoint.to_dict()

    def api_post_version_to_ota_channel(self, ota_channel, version_artifact):
        # 400 = unknown channel or malformed name. A wrong-hardware artifact
        # still gets 200 here; the node rejects it when it installs.
        node = self._find_node_by_channel(ota_channel)
        if node is None:
            return BAD_REQUEST
        ok, message = node.receive_artifact(version_artifact)
        if not ok:
            return BAD_REQUEST
        return OK

    def api_clear_ota_channel(self, ota_channel, version_artifact):
        node = self._find_node_by_channel(ota_channel)
        if node is None:
            return BAD_REQUEST
        ok, message = node.clear_artifact(version_artifact)
        if not ok:
            return BAD_REQUEST
        return OK

    # ---------- test helpers ----------

    def api_poll_node(self, uuid):
        # One OTA poll. Tests call this in a retry loop until the version
        # changes or retries run out. Returns the node state after the poll.
        node = self._get_node(uuid)
        node.poll()
        return node.to_dict()

    def api_drain_backlog(self, serial):
        # Endpoint uploads all pending samples -> backlog 0.
        endpoint = self._get_endpoint(serial)
        endpoint.drain_backlog()
        return OK

    def api_add_samples(self, serial, count):
        # New measurements arrive -> backlog grows. 400 = invalid count.
        endpoint = self._get_endpoint(serial)
        try:
            endpoint.add_samples(count)
        except ValueError:
            return BAD_REQUEST
        return OK

    def api_set_battery(self, serial, battery):
        # Battery charges or drains. 400 = invalid value.
        endpoint = self._get_endpoint(serial)
        try:
            endpoint.set_battery(battery)
        except ValueError:
            return BAD_REQUEST
        return OK

    def api_trigger_dfu(self, serial, new_version):
        # Explicit DFU request. 400 = refused (backlog, low battery, version
        # not newer or invalid). The version stays the same and the reason is
        # in the endpoint's last_error.
        endpoint = self._get_endpoint(serial)
        try:
            ok, reason = endpoint.try_update(new_version)
        except ValueError:
            return BAD_REQUEST
        if not ok:
            return BAD_REQUEST
        return OK


if __name__ == "__main__":
    api = AuguryAPI()
    print(api.api_add_node("MOXA_TBCDB1045001", 33))     # 200
    print(api.api_add_node("MOXA_TBCDB1045001", 33))     # 400 duplicate
    print(api.api_add_node("FOO_123", 1))                # 400 bad type

    print(api.api_add_endpoint("EP1-001", "EP1", "MOXA_TBCDB1045001", 3000, 1, backlog=5))  # 200
    print(api.api_add_endpoint("EP1-001", "EP1", "MOXA_TBCDB1045001", 3000, 1))             # 400 duplicate
    print(api.api_add_endpoint("EP2-001", "EP2", "NO_SUCH_NODE", 3000, 1))                  # 400 no node

    print("--- find by channel ---")
    print(api._find_node_by_channel("OTA_MOXA_TBCDB1045001").to_dict()["uuid"])   # MOXA_TBCDB1045001
    print(api._find_node_by_channel("OTA_NOPE"))                                  # None

    print("--- post / clear ---")
    channel = "OTA_MOXA_TBCDB1045001"
    print(api.api_post_version_to_ota_channel(channel, "moxa_34.swu"))      # 200
    print(api.api_post_version_to_ota_channel("OTA_NOPE", "moxa_34.swu"))   # 400 no channel
    print(api.api_post_version_to_ota_channel(channel, "moxa34.swu"))       # 400 bad name
    print(api.api_clear_ota_channel(channel, "moxa_99.swu"))                # 400 not in channel
    print(api.api_clear_ota_channel(channel, "moxa_34.swu"))                # 200

    print("--- poll (OTA happy flow) ---")
    api.api_post_version_to_ota_channel(channel, "moxa_34.swu")
    print(api.api_poll_node("MOXA_TBCDB1045001")["version"])   # 33 (downloading)
    print(api.api_poll_node("MOXA_TBCDB1045001")["version"])   # 34

    print("--- DFU ---")
    print(api.api_trigger_dfu("EP1-001", 2))                      # 400 (backlog 5)
    print(api.api_get_endpoint_by_serial("EP1-001")["version"])   # 1, unchanged
    print(api.api_drain_backlog("EP1-001"))                       # 200
    print(api.api_trigger_dfu("EP1-001", 2))                      # 200
    print(api.api_get_endpoint_by_serial("EP1-001")["version"])   # 2

    print("--- low battery ---")
    api.api_add_endpoint("CAN-001", "Canary_A", "MOXA_TBCDB1045001", 3500, 1)
    print(api.api_trigger_dfu("CAN-001", 2))                      # 400 (3500 < 3600)
    print(api.api_get_endpoint_by_serial("CAN-001")["version"])   # 1, unchanged
