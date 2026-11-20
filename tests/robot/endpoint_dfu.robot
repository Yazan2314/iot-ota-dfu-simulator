*** Settings ***
Documentation     TC2 - Endpoint DFU gating: no DFU while backlog > 0 or battery
...               is below the threshold for the EP type.
Resource          resources/augury_keywords.resource
Test Setup        Setup Node With Endpoints


*** Variables ***
${UUID}    AHN2_GW0001


*** Test Cases ***
DFU Waits Until Backlog Drains
    Endpoint Backlog Should Be    EP1-001    5
    DFU Should Be Blocked    EP1-001    2
    Endpoint Version Should Be    EP1-001    1
    Endpoint Should Report Error    EP1-001    backlog pending
    When Backlog Is Drained    EP1-001
    Then DFU Should Succeed    EP1-001    2
    And Endpoint Version Should Be    EP1-001    2

DFU Is Deferred When Battery Is Low
    [Documentation]    Canary_A needs 3600; it has 3500.
    DFU Should Be Blocked    CAN-001    2
    Endpoint Version Should Be    CAN-001    1
    Endpoint Should Report Error    CAN-001    battery too low

DFU Is Allowed When Battery Equals Threshold
    [Documentation]    The rule is "below threshold", so exactly 2500 is allowed.
    DFU Should Succeed    EP2-001    2
    Endpoint Version Should Be    EP2-001    2

DFU Succeeds After Battery Charges
    Given DFU Should Be Blocked    CAN-001    2
    When Battery Is Set To    CAN-001    3600
    Then DFU Should Succeed    CAN-001    2
    And Endpoint Version Should Be    CAN-001    2

DFU Is Blocked Again When New Samples Arrive
    Given Backlog Is Drained    EP1-001
    When New Samples Arrive    EP1-001    3
    Then DFU Should Be Blocked    EP1-001    2
    And Endpoint Should Report Error    EP1-001    backlog pending

Same Or Older Endpoint Version Is Rejected
    [Documentation]    Same rule as OTA: a DFU must move to a newer version.
    DFU Should Be Blocked    EP2-001    1
    Endpoint Should Report Error    EP2-001    version not newer
    DFU Should Be Blocked    EP2-001    0
    Endpoint Version Should Be    EP2-001    1


*** Keywords ***
Setup Node With Endpoints
    [Documentation]    One node paired with one EP of each type.
    Reset System
    A Node At Version    ${UUID}    10
    An Endpoint Paired With Node    EP1-001    EP1         ${UUID}    battery=3000    version=1    backlog=5
    An Endpoint Paired With Node    EP2-001    EP2         ${UUID}    battery=2500    version=1
    An Endpoint Paired With Node    CAN-001    Canary_A    ${UUID}    battery=3500    version=1
