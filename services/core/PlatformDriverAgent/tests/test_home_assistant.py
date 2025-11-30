# -*- coding: utf-8 -*- {{{
# ===----------------------------------------------------------------------===
#
#                 Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
#
# Copyright 2023 Battelle Memorial Institute
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ===----------------------------------------------------------------------===
# }}}

import json
import logging
import os
import pytest
import gevent

from volttron.platform.agent.known_identities import (
    PLATFORM_DRIVER,
    CONFIGURATION_STORE,
)
from volttron.platform import get_services_core
from volttron.platform.agent import utils
from volttron.platform.keystore import KeyStore
from volttrontesting.utils.platformwrapper import PlatformWrapper

utils.setup_logging()
logger = logging.getLogger(__name__)

# To run these tests, create a helper toggle named volttrontest in your Home Assistant instance.
# This can be done by going to Settings > Devices & services > Helpers > Create Helper > Toggle
# For fan tests, you need a fan entity (e.g., from Demo integration or actual fan device)
import os

# Fan test configuration
HOMEASSISTANT_TEST_IP = os.environ.get("HOMEASSISTANT_TEST_FAN_IP", "")
ACCESS_TOKEN = os.environ.get("HOMEASSISTANT_FAN_ACCESS_TOKEN", "")
PORT = os.environ.get("HOMEASSISTANT_FAN_PORT", "8123")
HOMEASSISTANT_TEST_FAN_ENTITY = os.environ.get("HOMEASSISTANT_TEST_FAN_ENTITY", "")

# Cover test configuration
HOMEASSISTANT_TEST_IP = os.environ.get("HOMEASSISTANT_TEST_IP", "")
ACCESS_TOKEN = os.environ.get("HOMEASSISTANT_ACCESS_TOKEN", "")
PORT = os.environ.get("HOMEASSISTANT_PORT", "8123")
HOMEASSISTANT_TEST_COVER_ENTITY = os.environ.get("HOMEASSISTANT_TEST_COVER_ENTITY", "cover.hall_window")

skip_msg = "Some configuration variables are not set. Check HOMEASSISTANT_TEST_IP, ACCESS_TOKEN, and PORT"

# Skip tests if variables are not set
pytestmark = pytest.mark.skipif(
    not (HOMEASSISTANT_TEST_IP and ACCESS_TOKEN and PORT),
    reason=skip_msg
)

# Skip fan tests if fan entity is not configured
skip_fan_tests = pytest.mark.skipif(
    not HOMEASSISTANT_TEST_FAN_ENTITY,
    reason="Fan entity not configured. Set HOMEASSISTANT_TEST_FAN_ENTITY to run fan tests."
)

HOMEASSISTANT_DEVICE_TOPIC = "devices/home_assistant"
HOMEASSISTANT_FAN_DEVICE_TOPIC = "devices/home_assistant_fan"


# Get the point which will should be off
def test_get_point(volttron_instance, config_store):
    expected_values = 0
    agent = volttron_instance.dynamic_agent
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant', 'bool_state').get(timeout=20)
    assert result == expected_values, "The result does not match the expected result."


# The default value for this fake light is 3. If the test cannot reach out to home assistant,
# the value will default to 3 making the test fail.
def test_data_poll(volttron_instance: PlatformWrapper, config_store):
    expected_values = [{'bool_state': 0}, {'bool_state': 1}]
    agent = volttron_instance.dynamic_agent
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'scrape_all', 'home_assistant').get(timeout=20)
    bool_state_dict = {'bool_state': result.get('bool_state')}
    assert bool_state_dict in expected_values, "The result does not match the expected result."


# Turn on the light. Light is automatically turned off every 30 seconds to allow test to turn
# it on and receive the correct value.
def test_set_point(volttron_instance, config_store):
    expected_values = {'bool_state': 1}
    agent = volttron_instance.dynamic_agent
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant', 'bool_state', 1)
    gevent.sleep(10)
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'scrape_all', 'home_assistant').get(timeout=20)
    # Only check that bool_state is 1, ignore other fields
    assert result.get('bool_state') == 1, f"Expected bool_state to be 1, got {result.get('bool_state')}"


def test_get_cover_state(volttron_instance, config_store):
    """
    Integration test: Verify that the driver can read cover state from Home Assistant.
    Tests the get_point method for cover devices.
    """
    agent = volttron_instance.dynamic_agent
    # Read cover state
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant',
        'cover_state'
    ).get(timeout=20)
    # Cover state should be 0 (closed), 1 (open), 3 (opening), or 4 (closing)
    assert result in [0, 1, 3, 4], (
        f"Expected cover state to be 0, 1, 3, or 4 (closed/open/opening/closing), "
        f"but got {result}"
    )
    logger.info(f"Cover state successfully read: {result}")



def test_set_cover_open(volttron_instance, config_store):
    """
    Integration test: Verify that the driver can send open command to a cover.
    Tests the set_point method with value=1 (open) for cover devices.
    """
    agent = volttron_instance.dynamic_agent
    # Send open command (value = 1)
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant',
        'cover_state',
        1  # 1 = open
    )
    # Wait for Home Assistant to process the command
    gevent.sleep(5)
     # Verify the cover is open or opening
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant',
        'cover_state'
    ).get(timeout=20)
    # Should be 1 (open) or 3 (opening)
    assert result in [1, 3], (
        f"Expected cover to be open (1) or opening (3), but got {result}"
    )
    logger.info(f"Cover successfully opened, state: {result}")

def test_set_cover_close(volttron_instance, config_store):
    """
    Integration test: Verify that the driver can send close command to a cover.
    Tests the set_point method with value=0 (close) for cover devices.
    """
    agent = volttron_instance.dynamic_agent
    
    # First, ensure cover is open
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant', 'cover_state', 1)
    gevent.sleep(5)
    # Send close command (value = 0)
    agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'set_point',
        'home_assistant',
        'cover_state',
        0  # 0 = close
    )
    # Wait for Home Assistant to process the command
    gevent.sleep(5)
    # Verify the cover is closed or closing
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'get_point',
        'home_assistant',
        'cover_state'
    ).get(timeout=20)
    # Should be 0 (closed) or 4 (closing)
    assert result in [0, 4], (
        f"Expected cover to be closed (0) or closing (4), but got {result}"
    )
    logger.info(f"Cover successfully closed, state: {result}")


# def test_set_cover_position(volttron_instance, config_store):
#     """
#     Integration test: Verify that the driver can set cover position.
#     Tests the set_point method for cover position (0-100).
#     """
#     agent = volttron_instance.dynamic_agent 
#     # Set cover to 50% open
#     target_position = 50
#     agent.vip.rpc.call(
#         PLATFORM_DRIVER,
#         'set_point',
#         'home_assistant',
#         'cover_position',
#         target_position
#     )
#     # Wait for Home Assistant to process the command
#     gevent.sleep(12)
#     # Read the current position
#     result = agent.vip.rpc.call(
#         PLATFORM_DRIVER,
#         'get_point',
#         'home_assistant',
#         'cover_position'
#     ).get(timeout=20)
#     # Allow ±5 tolerance due to timing and device precision
#     assert abs(result - target_position) <= 5, (
#         f"Expected cover position to be around {target_position}, but got {result}"
#     )
#     logger.info(f"Cover position successfully set to {result}")

def test_scrape_all_includes_covers(volttron_instance, config_store):
    """
    Integration test: Verify that scrape_all includes cover devices.
    Tests that the scrape_all method returns all configured points including covers.
    """
    agent = volttron_instance.dynamic_agent
    # Scrape all points
    result = agent.vip.rpc.call(
        PLATFORM_DRIVER,
        'scrape_all',
        'home_assistant'
    ).get(timeout=20)
    # Verify result is a dictionary
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    # Verify all required points are present
    required_points = ['bool_state', 'cover_state']
    for point in required_points:
        assert point in result, f"Missing required point: {point}"
    # Verify cover state is valid
    assert result['cover_state'] in [0, 1, 3, 4], (
        f"Invalid cover state: {result['cover_state']}"
    )
    logger.info(f"Scrape all successful. Points: {list(result.keys())}")
    logger.info(f"Cover values - state: {result['cover_state']}")



@pytest.fixture(scope="module")
def config_store(volttron_instance, platform_driver):

    capabilities = [{"edit_config_store": {"identity": PLATFORM_DRIVER}}]
    volttron_instance.add_capabilities(volttron_instance.dynamic_agent.core.publickey, capabilities)

    registry_config = "homeassistant_test.json"
    registry_obj = [{
        "Entity ID": "input_boolean.volttrontest",
        "Entity Point": "state",
        "Volttron Point Name": "bool_state",
        "Units": "On / Off",
        "Units Details": "off: 0, on: 1",
        "Writable": True,
        "Starting Value": 3,
        "Type": "int",
        "Notes": "lights hallway"
        },
        # NEW: Add cover state point
        {
            "Entity ID": "cover.hall_window",
            "Entity Point": "state",
            "Volttron Point Name": "cover_state",
            "Units": "",
            "Units Details": "closed: 0, open: 1, opening: 3, closing: 4",
            "Writable": True,
            "Starting Value": 0,
            "Type": "int",
            "Notes": "Test cover device for integration testing"
        }
        # ,
        # NEW: Add cover position point
        # {
        #     "Entity ID": "cover.hall_window",
        #     "Entity Point": "current_position",
        #     "Volttron Point Name": "cover_position",
        #     "Units": "%",
        #     "Units Details": "0-100 percentage",
        #     "Writable": True,
        #     "Starting Value": 0,
        #     "Type": "int",
        #     "Notes": "Test cover position"
        # }
        ]

    volttron_instance.dynamic_agent.vip.rpc.call(CONFIGURATION_STORE,
                                                 "manage_store",
                                                 PLATFORM_DRIVER,
                                                 registry_config,
                                                 json.dumps(registry_obj),
                                                 config_type="json")
    gevent.sleep(2)
    # driver config
    driver_config = {
        "driver_config": {"ip_address": HOMEASSISTANT_TEST_IP, "access_token": ACCESS_TOKEN, "port": PORT},
        "driver_type": "home_assistant",
        "registry_config": f"config://{registry_config}",
        "timezone": "US/Pacific",
        "interval": 30,
    }

    volttron_instance.dynamic_agent.vip.rpc.call(CONFIGURATION_STORE,
                                                 "manage_store",
                                                 PLATFORM_DRIVER,
                                                 HOMEASSISTANT_DEVICE_TOPIC,
                                                 json.dumps(driver_config),
                                                 config_type="json"
                                                 )
    gevent.sleep(2)

    yield platform_driver

    print("Wiping out store.")
    volttron_instance.dynamic_agent.vip.rpc.call(CONFIGURATION_STORE, "manage_delete_store", PLATFORM_DRIVER)
    gevent.sleep(0.1)


@pytest.fixture(scope="module")
def platform_driver(volttron_instance):
    # Start the platform driver agent which would in turn start the bacnet driver
    platform_uuid = volttron_instance.install_agent(
        agent_dir=get_services_core("PlatformDriverAgent"),
        config_file={
            "publish_breadth_first_all": False,
            "publish_depth_first": False,
            "publish_breadth_first": False,
        },
        start=True,
    )
    gevent.sleep(2)  # wait for the agent to start and start the devices
    assert volttron_instance.is_agent_running(platform_uuid)
    yield platform_uuid

    volttron_instance.stop_agent(platform_uuid)
    if not volttron_instance.debug_mode:
        volttron_instance.remove_agent(platform_uuid)


# ==================== FAN TESTS ====================

@skip_fan_tests
def test_get_fan_state(volttron_instance, fan_config_store):
    """Test getting fan state - should return 0 (off) or 1 (on)"""
    agent = volttron_instance.dynamic_agent
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_fan', 'fan_state').get(timeout=20)
    assert result in [0, 1, "off", "on"], f"Fan state should be 0/1 or on/off, got {result}"


@skip_fan_tests
def test_fan_scrape_all(volttron_instance, fan_config_store):
    """Test scraping all fan data points"""
    agent = volttron_instance.dynamic_agent
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'scrape_all', 'home_assistant_fan').get(timeout=20)
    assert 'fan_state' in result, "Result should contain fan_state"
    # Check if fan supports speed/percentage
    if 'fan_speed' in result:
        assert isinstance(result['fan_speed'], (int, str)), "Fan speed should be int or string"


@skip_fan_tests
def test_set_fan_on(volttron_instance, fan_config_store):
    """Test turning fan on"""
    agent = volttron_instance.dynamic_agent
    # Turn fan off first
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_fan', 'fan_state', 0)
    gevent.sleep(3)
    
    # Turn fan on
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_fan', 'fan_state', 1)
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_fan', 'fan_state').get(timeout=20)
    assert result in [1, "on"], f"Fan should be on, got {result}"


@skip_fan_tests
def test_set_fan_off(volttron_instance, fan_config_store):
    """Test turning fan off"""
    agent = volttron_instance.dynamic_agent
    # Turn fan on first
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_fan', 'fan_state', 1)
    gevent.sleep(3)
    
    # Turn fan off
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_fan', 'fan_state', 0)
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_fan', 'fan_state').get(timeout=20)
    assert result in [0, "off"], f"Fan should be off, got {result}"


@skip_fan_tests
def test_set_fan_speed(volttron_instance, fan_config_store):
    """Test setting fan speed"""
    agent = volttron_instance.dynamic_agent
    # Turn fan on first
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_fan', 'fan_state', 1)
    gevent.sleep(3)
    
    # Set speed (using percentage 0-100 or speed level depending on your fan)
    test_speed = 75
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_fan', 'fan_speed', test_speed)
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_fan', 'fan_speed').get(timeout=20)
    # Some fans may return approximate values
    assert result is not None, "Fan speed should return a value"


@pytest.fixture(scope="module")
def fan_config_store(volttron_instance, platform_driver):
    """Fixture for configuring fan tests"""
    capabilities = [{"edit_config_store": {"identity": PLATFORM_DRIVER}}]
    volttron_instance.add_capabilities(volttron_instance.dynamic_agent.core.publickey, capabilities)

    registry_config = "homeassistant_fan_test.json"
    registry_obj = [
        {
            "Entity ID": HOMEASSISTANT_TEST_FAN_ENTITY,
            "Entity Point": "state",
            "Volttron Point Name": "fan_state",
            "Units": "On / Off",
            "Units Details": "off: 0, on: 1",
            "Writable": True,
            "Type": "int",
            "Notes": "Fan state control"
        },
        {
            "Entity ID": HOMEASSISTANT_TEST_FAN_ENTITY,
            "Entity Point": "percentage",
            "Volttron Point Name": "fan_speed",
            "Units": "Percent",
            "Units Details": "0-100",
            "Writable": True,
            "Type": "int",
            "Notes": "Fan speed percentage"
        }
    ]

    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        registry_config,
        json.dumps(registry_obj),
        config_type="json"
    )
    gevent.sleep(2)

    driver_config = {
        "driver_config": {
            "ip_address": HOMEASSISTANT_TEST_IP,
            "access_token": ACCESS_TOKEN,
            "port": PORT
        },
        "driver_type": "home_assistant",
        "registry_config": f"config://{registry_config}",
        "timezone": "US/Pacific",
        "interval": 30,
    }

    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        HOMEASSISTANT_FAN_DEVICE_TOPIC,
        json.dumps(driver_config),
        config_type="json"
    )
    gevent.sleep(5)  # Give more time for driver to initialize

    yield platform_driver

    # Cleanup
    print("Cleaning up fan test configuration.")
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_delete_config",
        PLATFORM_DRIVER,
        HOMEASSISTANT_FAN_DEVICE_TOPIC
    )
    gevent.sleep(0.1)

# ==================== SWITCH TESTS ====================

# Switch test configuration
HOMEASSISTANT_TEST_IP = os.environ.get("HOMEASSISTANT_TEST_SWITCH_IP", "")
ACCESS_TOKEN = os.environ.get("HOMEASSISTANT_SWITCH_ACCESS_TOKEN", "")
PORT = os.environ.get("HOMEASSISTANT_SWITCH_PORT", "8123")
HOMEASSISTANT_TEST_SWITCH_ENTITY = os.environ.get("HOMEASSISTANT_TEST_SWITCH_ENTITY", "")

skip_switch_tests = pytest.mark.skipif(
    not HOMEASSISTANT_TEST_SWITCH_ENTITY,
    reason="Switch entity not configured. Set HOMEASSISTANT_TEST_SWITCH_ENTITY to run switch tests."
)

HOMEASSISTANT_SWITCH_DEVICE_TOPIC = "devices/home_assistant_switch"


@skip_switch_tests
def test_get_switch_state(volttron_instance, switch_config_store):
    """Test getting switch state - should return 0 (off) or 1 (on)"""
    agent = volttron_instance.dynamic_agent
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_switch', 'switch_state').get(timeout=20)
    assert result in [0, 1, "off", "on"], f"Switch state should be 0/1 or on/off, got {result}"


@skip_switch_tests
def test_switch_scrape_all(volttron_instance, switch_config_store):
    """Test scraping all switch data points"""
    agent = volttron_instance.dynamic_agent
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'scrape_all', 'home_assistant_switch').get(timeout=20)
    assert 'switch_state' in result, "Result should contain switch_state"
    assert result['switch_state'] in [0, 1, "on", "off"], f"Switch state should be valid, got {result['switch_state']}"


@skip_switch_tests
def test_set_switch_on(volttron_instance, switch_config_store):
    """Test turning switch on"""
    agent = volttron_instance.dynamic_agent
    # Turn switch off first
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_switch', 'switch_state', 0)
    gevent.sleep(3)
    
    # Turn switch on
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_switch', 'switch_state', 1)
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_switch', 'switch_state').get(timeout=20)
    assert result in [1, "on"], f"Switch should be on, got {result}"


@skip_switch_tests
def test_set_switch_off(volttron_instance, switch_config_store):
    """Test turning switch off"""
    agent = volttron_instance.dynamic_agent
    # Turn switch on first
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_switch', 'switch_state', 1)
    gevent.sleep(3)
    
    # Turn switch off
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_switch', 'switch_state', 0)
    gevent.sleep(5)
    
    result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_switch', 'switch_state').get(timeout=20)
    assert result in [0, "off"], f"Switch should be off, got {result}"


@skip_switch_tests
def test_switch_toggle(volttron_instance, switch_config_store):
    """Test toggling switch multiple times"""
    agent = volttron_instance.dynamic_agent
    
    # Turn on
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_switch', 'switch_state', 1)
    gevent.sleep(3)
    result1 = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_switch', 'switch_state').get(timeout=20)
    assert result1 in [1, "on"], f"Switch should be on after first toggle, got {result1}"
    
    # Turn off
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_switch', 'switch_state', 0)
    gevent.sleep(3)
    result2 = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_switch', 'switch_state').get(timeout=20)
    assert result2 in [0, "off"], f"Switch should be off after second toggle, got {result2}"
    
    # Turn on again
    agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_switch', 'switch_state', 1)
    gevent.sleep(3)
    result3 = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_switch', 'switch_state').get(timeout=20)
    assert result3 in [1, "on"], f"Switch should be on after third toggle, got {result3}"


@skip_switch_tests
def test_invalid_switch_value(volttron_instance, switch_config_store):
    """Test that invalid switch values are handled correctly"""
    agent = volttron_instance.dynamic_agent
    
    # Try to set invalid value (should fail gracefully or be rejected)
    try:
        agent.vip.rpc.call(PLATFORM_DRIVER, 'set_point', 'home_assistant_switch', 'switch_state', 2)
        gevent.sleep(2)
        # If it doesn't raise an error, verify the state didn't change to an invalid value
        result = agent.vip.rpc.call(PLATFORM_DRIVER, 'get_point', 'home_assistant_switch', 'switch_state').get(timeout=20)
        assert result in [0, 1, "on", "off"], f"Switch state should remain valid even after invalid input, got {result}"
    except Exception as e:
        # Expected to raise an error for invalid value
        assert "should be an integer value of 1 or 0" in str(e) or "ValueError" in str(type(e).__name__), \
            f"Expected ValueError for invalid switch value, got {type(e).__name__}: {e}"


@pytest.fixture(scope="module")
def switch_config_store(volttron_instance, platform_driver):
    """Fixture for configuring switch tests"""
    capabilities = [{"edit_config_store": {"identity": PLATFORM_DRIVER}}]
    volttron_instance.add_capabilities(volttron_instance.dynamic_agent.core.publickey, capabilities)

    registry_config = "homeassistant_switch_test.json"
    registry_obj = [
        {
            "Entity ID": HOMEASSISTANT_TEST_SWITCH_ENTITY,
            "Entity Point": "state",
            "Volttron Point Name": "switch_state",
            "Units": "On / Off",
            "Units Details": "off: 0, on: 1",
            "Writable": True,
            "Type": "int",
            "Notes": "Switch state control"
        }
    ]

    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        registry_config,
        json.dumps(registry_obj),
        config_type="json"
    )
    gevent.sleep(2)

    driver_config = {
        "driver_config": {
            "ip_address": HOMEASSISTANT_TEST_IP,
            "access_token": ACCESS_TOKEN,
            "port": PORT
        },
        "driver_type": "home_assistant",
        "registry_config": f"config://{registry_config}",
        "timezone": "US/Pacific",
        "interval": 30,
    }

    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_store",
        PLATFORM_DRIVER,
        HOMEASSISTANT_SWITCH_DEVICE_TOPIC,
        json.dumps(driver_config),
        config_type="json"
    )
    gevent.sleep(5)  # Give more time for driver to initialize

    yield platform_driver

    # Cleanup
    print("Cleaning up switch test configuration.")
    volttron_instance.dynamic_agent.vip.rpc.call(
        CONFIGURATION_STORE,
        "manage_delete_config",
        PLATFORM_DRIVER,
        HOMEASSISTANT_SWITCH_DEVICE_TOPIC
    )
    gevent.sleep(0.1)