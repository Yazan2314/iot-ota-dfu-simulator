# IoT OTA/DFU Simulator

An in-memory simulation of IoT gateways (Nodes) and sensors (Endpoints) that implements the OTA and DFU update rules, exposed through a fake `AuguryAPI` and tested end to end with Robot Framework. No real hardware or cloud services are used.

## Setup

Requires Python 3.10 or newer (tested with 3.12).

```bash
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Running the tests

```bash
robot --pythonpath . --outputdir results tests/robot
```

The report is written to `results/report.html`.

## Project structure

```
augury_iot/
  node.py          Node model: OTA channel, polling, artifact validation
  endpoint.py      Endpoint model: battery, backlog, DFU gating
  augury_api.py    AuguryAPI: fake backend used by the tests
tests/robot/
  resources/augury_keywords.resource   shared keywords
  ota_happy_flow.robot                 TC1: OTA happy flow
  endpoint_dfu.robot                   TC2: Endpoint DFU with backlog and battery
  bad_firmware_ota.robot               TC3: Bad firmware OTA
  input_validation.robot               invalid or duplicate setup input
```

## Design

The system has three layers: **Robot suites → keyword resource → `AuguryAPI` → `Node` / `Endpoint`**.

- The tests interact only with the API, so the same suites could run against a real backend.
- The API holds no business logic. It looks up the device and translates the result into a dict or a 200/400 status.
- All domain rules live in `Node` and `Endpoint`. Their state is private and changes only through methods that enforce those rules.

## Domain rules

**OTA polling.** A posted artifact waits in the node's OTA channel and is installed on the node's second poll. The tests poll in a retry loop (3 retries, 0.1 s interval, using `Wait Until Keyword Succeeds`) and fail if the version does not update before the retries run out.

**Artifact validation.** A malformed artifact name is rejected at post time with 400. An artifact for a different hardware type is accepted at post time and rejected by the node at install time: the version stays unchanged and the error is reported in `last_error`, returned by `api_get_node_by_uuid`.

**DFU gating.** `api_trigger_dfu` returns 400 and leaves the version unchanged while the backlog is above 0, the battery is below the threshold for the endpoint type (EP1/EP2: 2500, Canary_A: 3600), or the requested version is not newer than the current one. The reason is reported in the endpoint's `last_error`. The backlog is drained with an explicit call to `api_drain_backlog`.

**Input validation.** Invalid UUIDs, unknown hardware types, negative or non-numeric battery and backlog values, duplicate UUIDs or serials, and a second endpoint of the same type on one node are all rejected with 400.

## API helpers

In addition to the four required functions, the following helpers are available to the tests:

| Helper | Description |
|---|---|
| `api_reset()` | Clears all state; runs before each test |
| `api_add_node(uuid, version)` | Creates a node |
| `api_add_endpoint(serial, type, node_uuid, battery, version, backlog)` | Creates an endpoint and pairs it with its node |
| `api_poll_node(uuid)` | Performs one OTA poll |
| `api_drain_backlog(serial)` | Sets the endpoint backlog to 0 |
| `api_add_samples(serial, count)` | Adds new samples to the endpoint backlog |
| `api_set_battery(serial, battery)` | Sets the endpoint battery level |
| `api_trigger_dfu(serial, version)` | Attempts a DFU (200 = updated, 400 = refused) |

## Assumptions

- A duplicate node UUID or endpoint serial is rejected with 400.
- Posting the same or an older version is treated as a failed OTA.
- DFU runs only when explicitly triggered, not automatically when the backlog reaches 0.
- A battery level exactly at the threshold allows DFU.
- A new artifact replaces one that is still pending in the channel.
- A DFU to the same or an older endpoint version is refused, the same as for OTA.
- Endpoint hardware types are case-sensitive (`EP1`, `EP2`, `Canary_A`); node types in UUIDs are not.
- Battery values may be fractional; backlog is a whole number of samples.
- Endpoint versions can be whole numbers or dotted (`2`, `1.0`, `2.1.4`) and are compared part by part as numbers, so `1.10` is newer than `1.9` and `1.0` equals `1`. Node versions stay whole numbers, matching the `<hardware_type>_<version>.swu` artifact format.
