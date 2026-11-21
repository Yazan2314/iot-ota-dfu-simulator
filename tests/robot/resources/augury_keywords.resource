*** Settings ***
Documentation    Shared keywords for the Augury IoT suites.
...              Tests only talk to AuguryAPI through these keywords.
Library          augury_iot.augury_api.AuguryAPI


*** Variables ***
# OTA poll/retry policy: up to 3 polls, 0.1s apart.
# A node needs 2 polls to install (POLLS_TO_INSTALL), so 3 leaves one spare.
${OTA_RETRIES}           3
${OTA_RETRY_INTERVAL}    0.1s


*** Keywords ***
# ---------- setup ----------

Reset System
    Api Reset

A Node At Version
    [Arguments]    ${uuid}    ${version}
    ${code}=    Api Init Node    ${uuid}    ${version}
    Should Be Equal As Integers    ${code}    200

An Endpoint Paired With Node
    [Arguments]    ${serial}    ${hardware_type}    ${uuid}    ${battery}    ${version}    ${backlog}=0
    ${code}=    Api Add Endpoint    ${serial}    ${hardware_type}    ${uuid}
    ...    ${{int($battery)}}    ${version}    ${{int($backlog)}}
    Should Be Equal As Integers    ${code}    200

# ---------- OTA ----------

OTA Channel Of Node
    [Arguments]    ${uuid}
    ${node}=    Api Get Node By Uuid    ${uuid}
    RETURN    ${node}[ota_channel]

Artifact Is Posted To Node
    [Arguments]    ${uuid}    ${artifact}
    ${channel}=    OTA Channel Of Node    ${uuid}
    ${code}=    Api Post Version To Ota Channel    ${channel}    ${artifact}
    Should Be Equal As Integers    ${code}    200

Artifact Is Cleared From Node
    [Arguments]    ${uuid}    ${artifact}
    ${channel}=    OTA Channel Of Node    ${uuid}
    ${code}=    Api Clear Ota Channel    ${channel}    ${artifact}
    Should Be Equal As Integers    ${code}    200

Posting Artifact To Node Should Be Rejected
    [Arguments]    ${uuid}    ${artifact}
    ${channel}=    OTA Channel Of Node    ${uuid}
    ${code}=    Api Post Version To Ota Channel    ${channel}    ${artifact}
    Should Be Equal As Integers    ${code}    400

Node Version Should Become
    [Documentation]    Poll/retry loop: keep polling until the version matches,
    ...                or fail when the retries run out.
    [Arguments]    ${uuid}    ${expected}
    Wait Until Keyword Succeeds    ${OTA_RETRIES}x    ${OTA_RETRY_INTERVAL}
    ...    Poll Node And Check Version    ${uuid}    ${expected}

Poll Node And Check Version
    [Arguments]    ${uuid}    ${expected}
    ${node}=    Api Poll Node    ${uuid}
    Should Be Equal As Integers    ${node}[version]    ${expected}

Node Should Stay At Version After All Retries
    [Documentation]    Use all the retries, then check nothing changed.
    [Arguments]    ${uuid}    ${expected}
    Repeat Keyword    ${OTA_RETRIES} times    Api Poll Node    ${uuid}
    Node Version Should Be    ${uuid}    ${expected}

Node Version Should Be
    [Arguments]    ${uuid}    ${expected}
    ${node}=    Api Get Node By Uuid    ${uuid}
    Should Be Equal As Integers    ${node}[version]    ${expected}

Node Should Report Error
    [Arguments]    ${uuid}    ${text}
    ${node}=    Api Get Node By Uuid    ${uuid}
    Should Contain    ${node}[last_error]    ${text}

Node Should Have No Error
    [Arguments]    ${uuid}
    ${node}=    Api Get Node By Uuid    ${uuid}
    Should Be Empty    ${node}[last_error]

# ---------- DFU ----------

DFU Should Be Blocked
    [Arguments]    ${serial}    ${new_version}
    ${code}=    Api Trigger Dfu    ${serial}    ${new_version}
    Should Be Equal As Integers    ${code}    400

DFU Should Succeed
    [Arguments]    ${serial}    ${new_version}
    ${code}=    Api Trigger Dfu    ${serial}    ${new_version}
    Should Be Equal As Integers    ${code}    200

Backlog Is Drained
    [Arguments]    ${serial}
    ${code}=    Api Drain Backlog    ${serial}
    Should Be Equal As Integers    ${code}    200

Endpoint Backlog Should Be
    [Arguments]    ${serial}    ${expected}
    ${ep}=    Api Get Endpoint By Serial    ${serial}
    Should Be Equal As Integers    ${ep}[backlog]    ${expected}

Endpoint Version Should Be
    [Arguments]    ${serial}    ${expected}
    ${ep}=    Api Get Endpoint By Serial    ${serial}
    Should Be Equal As Strings    ${ep}[version]    ${expected}

Endpoint Should Report Error
    [Arguments]    ${serial}    ${text}
    ${ep}=    Api Get Endpoint By Serial    ${serial}
    Should Contain    ${ep}[last_error]    ${text}

New Samples Arrive
    [Arguments]    ${serial}    ${count}
    ${code}=    Api Add Samples    ${serial}    ${{int($count)}}
    Should Be Equal As Integers    ${code}    200

Battery Is Set To
    [Arguments]    ${serial}    ${battery}
    ${code}=    Api Set Battery    ${serial}    ${{int($battery)}}
    Should Be Equal As Integers    ${code}    200

# ---------- input validation ----------

Adding Node Should Be Rejected
    [Arguments]    ${uuid}    ${version}=1
    ${code}=    Api Init Node    ${uuid}    ${version}
    Should Be Equal As Integers    ${code}    400

Adding Endpoint Should Be Rejected
    [Documentation]    Values are passed as given (no conversion), so bad types can be tested.
    [Arguments]    ${serial}    ${hardware_type}    ${uuid}    ${battery}    ${version}    ${backlog}=${0}
    ${code}=    Api Add Endpoint    ${serial}    ${hardware_type}    ${uuid}    ${battery}    ${version}    ${backlog}
    Should Be Equal As Integers    ${code}    400
