*** Settings ***
Documentation     Bad setup input is rejected with 400 instead of creating a broken device.
Resource          resources/augury_keywords.resource
Test Setup        Reset System


*** Variables ***
${UUID}    MOXA_TBCDB1045001


*** Test Cases ***
Invalid Node UUID Is Rejected
    Adding Node Should Be Rejected    MOXA_
    Adding Node Should Be Rejected    _123
    Adding Node Should Be Rejected    MOXA
    Adding Node Should Be Rejected    FOO_123

Duplicate Node UUID Is Rejected
    Given A Node At Version    ${UUID}    33
    Then Adding Node Should Be Rejected    ${UUID}    33

Endpoint With Invalid Values Is Rejected
    Given A Node At Version    ${UUID}    33
    Adding Endpoint Should Be Rejected    EP1-001    EP1         ${UUID}    ${-50}     1
    Adding Endpoint Should Be Rejected    EP1-001    EP1         ${UUID}    ${3000}    1    ${-1}
    Adding Endpoint Should Be Rejected    EP1-001    Unknown     ${UUID}    ${3000}    1
    Adding Endpoint Should Be Rejected    EP1-001    EP1         NO_SUCH    ${3000}    1

Node Gets Only One Endpoint Of Each Type
    Given A Node At Version    ${UUID}    33
    And An Endpoint Paired With Node    EP1-001    EP1    ${UUID}    battery=3000    version=1
    Then Adding Endpoint Should Be Rejected    EP1-002    EP1    ${UUID}    ${3000}    1

Duplicate Endpoint Serial Is Rejected
    Given A Node At Version    ${UUID}    33
    And A Node At Version    CASSIA_ABC123    33
    And An Endpoint Paired With Node    EP1-001    EP1    ${UUID}    battery=3000    version=1
    Then Adding Endpoint Should Be Rejected    EP1-001    EP1    CASSIA_ABC123    ${3000}    1
