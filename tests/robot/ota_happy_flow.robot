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
