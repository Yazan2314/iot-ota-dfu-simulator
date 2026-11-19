*** Settings ***
Documentation     TC3 - Bad firmware OTA: a node rejects an artifact built for
...               different hardware. Version stays the same and an error is reported.
Resource          resources/augury_keywords.resource
Test Setup        Reset System


*** Variables ***
${CASSIA_UUID}    CASSIA_ABC123


*** Test Cases ***
Wrong Hardware Artifact Is Rejected
    Given A Node At Version    ${CASSIA_UUID}    33
    When Artifact Is Posted To Node    ${CASSIA_UUID}    moxa_34.swu
    Then Node Should Stay At Version After All Retries    ${CASSIA_UUID}    33
    And Node Should Report Error    ${CASSIA_UUID}    hardware mismatch

Malformed Artifact Name Is Rejected At Post
    Given A Node At Version    ${CASSIA_UUID}    33
    Then Posting Artifact To Node Should Be Rejected    ${CASSIA_UUID}    cassia34.swu
    And Node Version Should Be    ${CASSIA_UUID}    33

Older Version Is Rejected
    [Documentation]    Our assumption: same or older version is a failed OTA.
    Given A Node At Version    ${CASSIA_UUID}    33
    When Artifact Is Posted To Node    ${CASSIA_UUID}    cassia_32.swu
    Then Node Should Stay At Version After All Retries    ${CASSIA_UUID}    33
    And Node Should Report Error    ${CASSIA_UUID}    version not newer
