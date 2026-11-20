*** Settings ***
Documentation     TC1 - OTA happy flow: a node updates from 33 to 34 after polling.
Resource          resources/augury_keywords.resource
Test Setup        Reset System


*** Variables ***
${UUID}    MOXA_TBCDB1045001


*** Test Cases ***
OTA Happy Flow
    Given A Node At Version    ${UUID}    33
    When Artifact Is Posted To Node    ${UUID}    moxa_34.swu
    Then Node Version Should Become    ${UUID}    34
    And Node Should Have No Error    ${UUID}

OTA Matching Is Case Insensitive
    [Documentation]    MOXA in the UUID matches moxa in the artifact name.
    Given A Node At Version    ${UUID}    33
    When Artifact Is Posted To Node    ${UUID}    MOXA_34.swu
    Then Node Version Should Become    ${UUID}    34

Newer Post Replaces Pending Artifact
    [Documentation]    Our assumption: the channel holds one artifact; the latest post wins.
    Given A Node At Version    ${UUID}    33
    When Artifact Is Posted To Node    ${UUID}    moxa_34.swu
    And Artifact Is Posted To Node    ${UUID}    moxa_35.swu
    Then Node Version Should Become    ${UUID}    35

Cleared Artifact Is Not Installed
    Given A Node At Version    ${UUID}    33
    When Artifact Is Posted To Node    ${UUID}    moxa_34.swu
    And Artifact Is Cleared From Node    ${UUID}    moxa_34.swu
    Then Node Should Stay At Version After All Retries    ${UUID}    33
