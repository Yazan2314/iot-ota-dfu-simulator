from augury_iot.node import Node
from augury_iot.endpoint import Endpoint

OK = 200
BAD_REQUEST = 400

class AuguryAPI:
    def __init__(self):
        self._nodes = {}
        self._endpoints = {}


    def api_reset(self):
        self._nodes = {}
        self._endpoints = {}


    def _get_node(self, uuid):
        if uuid not in self._nodes:
            raise KeyError(f"Node with UUID {uuid} not found")
        return self._nodes[uuid]


    def _get_endpoint(self, serial):
        if serial not in self._endpoints:
            raise KeyError(f"Endpoint with serial {serial} not found")
        return self._endpoints[serial]


    def _find_node_by_channel(self, ota_channel):
        for node in self._nodes.values():
            if node.to_dict()["ota_channel"] == ota_channel:
                return node
        return None    

        
    def api_add_node(self, uuid, version):
        if uuid in self._nodes:
            return BAD_REQUEST

        try:
            node = Node(uuid, version)
        except ValueError:
            return BAD_REQUEST
        self._nodes[uuid] = node
        return OK


    def api_get_node_by_uuid(self, uuid):
        node = self._get_node(uuid)
        return node.to_dict()


    def api_add_endpoint(self,serial, hardware_type, node_uuid, battery, version, backlog=0):
        if serial in self._endpoints:
            return BAD_REQUEST
        if node_uuid not in self._nodes:
            return BAD_REQUEST
        try:
            endpoint = Endpoint(serial, hardware_type, node_uuid, battery, version, backlog)
        except ValueError:
            return BAD_REQUEST
        self._endpoints[serial] = endpoint
        self._nodes[node_uuid].add_endpoint(serial)
        return OK


    def api_get_endpoint_by_serial(self, serial):
        endpoint = self._get_endpoint(serial)
        return endpoint.to_dict()


    def api_post_version_to_ota_channel(self, ota_channel, version_artifact):
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


    def api_poll_node(self, uuid):
        node = self._get_node(uuid)
        node.poll()
        return node.to_dict()


    def api_drain_backlog(self, serial):
        endpoint = self._get_endpoint(serial)
        endpoint.drain_backlog()
        return OK


    def api_trigger_dfu(self, serial, new_version):
        endpoint = self._get_endpoint(serial)
        ok, reason = endpoint.try_update(new_version)
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
    print(api.api_add_endpoint("EP2-001", "EP2", "NO_SUCH_NODE", 3000, 1))    
    print(api._find_node_by_channel("OTA_MOXA_TBCDB1045001").to_dict()["uuid"])   # MOXA_TBCDB1045001
    print(api._find_node_by_channel("OTA_NOPE"))                                  # None              # 400 no node
    print("--- post / clear ---")
    channel = "OTA_MOXA_TBCDB1045001"
    print(api.api_post_version_to_ota_channel(channel, "moxa_34.swu"))      # 200
    print(api.api_post_version_to_ota_channel("OTA_NOPE", "moxa_34.swu"))   # 400 no channel
    print(api.api_post_version_to_ota_channel(channel, "moxa34.swu"))       # 400 bad name
    print(api.api_clear_ota_channel(channel, "moxa_99.swu"))                # 400 not in mailbox
    print(api.api_clear_ota_channel(channel, "moxa_34.swu"))                # 200
    print("--- poll (OTA happy flow) ---")
    api.api_post_version_to_ota_channel(channel, "moxa_34.swu")
    print(api.api_poll_node("MOXA_TBCDB1045001")["version"])   # 33 (downloading)
    print(api.api_poll_node("MOXA_TBCDB1045001")["version"])   # 34 ✅
    print("--- DFU (TC2) ---")
    print(api.api_trigger_dfu("EP1-001", 2))                      # 400 (backlog 5)
    print(api.api_get_endpoint_by_serial("EP1-001")["version"])   # 1  ← unchanged
    print(api.api_drain_backlog("EP1-001"))                       # 200
    print(api.api_trigger_dfu("EP1-001", 2))                      # 200
    print(api.api_get_endpoint_by_serial("EP1-001")["version"])   # 2  ✅

    print("--- low battery ---")
    api.api_add_endpoint("CAN-001", "Canary_A", "MOXA_TBCDB1045001", 3500, 1)
    print(api.api_trigger_dfu("CAN-001", 2))                      # 400 (3500 < 3600)
    print(api.api_get_endpoint_by_serial("CAN-001")["version"])   # 1  ← unchanged