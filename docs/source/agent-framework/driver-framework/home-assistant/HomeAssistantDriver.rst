.. _HomeAssistant-Driver:

Home Assistant Driver
=====================

The Home Assistant driver enables VOLTTRON to read any data point from any Home Assistant controlled device.
Currently control (write access) is supported for lights (state and brightness), thermostats (state and temperature), and fans (state and percentage speed), and switches (state).

The following diagram shows interaction between platform driver agent and home assistant driver.

.. mermaid::

   sequenceDiagram
       HomeAssistant Driver->>HomeAssistant: Retrieve Entity Data (REST API)
       HomeAssistant-->>HomeAssistant Driver: Entity Data (Status Code: 200)
       HomeAssistant Driver->>PlatformDriverAgent: Publish Entity Data
       PlatformDriverAgent->>Controller Agent: Publish Entity Data

       Controller Agent->>HomeAssistant Driver: Instruct to Turn Off Light
       HomeAssistant Driver->>HomeAssistant: Send Turn Off Light Command (REST API)
       HomeAssistant-->>HomeAssistant Driver: Command Acknowledgement (Status Code: 200)

Pre-requisites
--------------
Before proceeding, find your Home Assistant IP address and long-lived access token from `here <https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token>`_.

Clone the repository, start volttron, install the listener agent, and the platform driver agent.

- `Listener agent <https://volttron.readthedocs.io/en/main/introduction/platform-install.html#installing-and-running-agents>`_
- `Platform driver agent <https://volttron.readthedocs.io/en/main/agent-framework/core-service-agents/platform-driver/platform-driver-agent.html?highlight=platform%20driver%20isntall#configuring-the-platform-driver>`_

Configuration
--------------

After cloning, generate configuration files. Each device requires one device configuration file and one registry file.
Ensure your registry_config parameter in your device configuration file, links to correct registry config name in the
config store. For more details on how volttron platform driver agent works with volttron configuration store see,
`Platform driver configuration <https://volttron.readthedocs.io/en/main/agent-framework/driver-framework/platform-driver/platform-driver.html#configuration-and-installation>`_
Examples for lights and thermostats are provided below.

Device configuration
++++++++++++++++++++

Device configuration file contains the connection details to you home assistant instance and driver_type as "home_assistant"

.. code-block:: json

   {
       "driver_config": {
           "ip_address": "Your Home Assistant IP",
           "access_token": "Your Home Assistant Access Token",
           "port": "Your Port"
       },
       "driver_type": "home_assistant",
       "registry_config": "config://light.example.json",
       "interval": 30,
       "timezone": "UTC"
   }

Registry Configuration
+++++++++++++++++++++++

Registry file can contain one single device and its attributes or a logical group of devices and its
attributes. Each entry should include the full entity id of the device, including but not limited to home assistant provided prefix
such as "light.",  "climate.", and "fan.", and "switch." etc. The driver uses these prefixes to convert states into integers.
Like mentioned before, the driver can control lights, thermostats, fans, and switches, but can get data from all devices
controlled by Home Assistant.

Each entry in a registry file should also have a 'Entity Point' and a unique value for 'Volttron Point Name'. The 'Entity ID' maps to the device instance, the 'Entity Point' extracts the attribute or state, and 'Volttron Point Name' determines the name of that point as it appears in VOLTTRON.

Attributes can be located in the developer tools in the Home Assistant GUI.

.. image:: home-assistant.png


Below is an example file named light.example.json which has attributes of a single light instance with entity
id 'light.example':


.. code-block:: json

   [
       {
           "Entity ID": "light.example",
           "Entity Point": "state",
           "Volttron Point Name": "light_state",
           "Units": "On / Off",
           "Units Details": "on/off",
           "Writable": true,
           "Starting Value": true,
           "Type": "boolean",
           "Notes": "lights hallway"
       },
       {
           "Entity ID": "light.example",
           "Entity Point": "brightness",
           "Volttron Point Name": "light_brightness",
           "Units": "int",
           "Units Details": "light level",
           "Writable": true,
           "Starting Value": 0,
           "Type": "int",
           "Notes": "brightness control, 0 - 255"
       }
   ]


.. note::
    
    When using a single registry file to represent a logical group of multiple physical entities, make sure the "Volttron Point Name" is unique within a single registry file.
    For example, if a registry file contains entities with
    id  'light.instance1' and 'light.instance2' the entry for the attribute brightness for these two light instances could
    have "Volttron Point Name" as 'light1/brightness' and 'light2/brightness' respectively. This would ensure that data
    is posted to unique topic names and brightness data from light1 is not overwritten by light2 or vice-versa.

Example Thermostat Registry
***************************

For thermostats, the state is converted into numbers as follows: "0: Off, 2: heat, 3: Cool, 4: Auto",

.. code-block:: json

   [
       {
           "Entity ID": "climate.my_thermostat",
           "Entity Point": "state",
           "Volttron Point Name": "thermostat_state",
           "Units": "Enumeration",
           "Units Details": "0: Off, 2: heat, 3: Cool, 4: Auto",
           "Writable": true,
           "Starting Value": 1,
           "Type": "int",
           "Notes": "Mode of the thermostat"
       },
       {
           "Entity ID": "climate.my_thermostat",
           "Entity Point": "current_temperature",
           "Volttron Point Name": "volttron_current_temperature",
           "Units": "F",
           "Units Details": "Current Ambient Temperature",
           "Writable": true,
           "Starting Value": 72,
           "Type": "float",
           "Notes": "Current temperature reading"
       },
       {
           "Entity ID": "climate.my_thermostat",
           "Entity Point": "temperature",
           "Volttron Point Name": "set_temperature",
           "Units": "F",
           "Units Details": "Desired Temperature",
           "Writable": true,
           "Starting Value": 75,
           "Type": "float",
           "Notes": "Target Temp"
       }
   ]

Transfer the registers files and the config files into the VOLTTRON config store using the commands below:

.. code-block:: bash

   vctl config store platform.driver light.example.json HomeAssistant_Driver/light.example.json
   vctl config store platform.driver devices/BUILDING/ROOM/light.example HomeAssistant_Driver/light.example.config

Upon completion, initiate the platform driver. Utilize the listener agent to verify the driver output:

.. code-block:: bash

   2023-09-12 11:37:00,226 (listeneragent-3.3 211531) __main__ INFO: Peer: pubsub, Sender: platform.driver:, Bus: , Topic: devices/BUILDING/ROOM/light.example/all, Headers: {'Date': '2023-09-12T18:37:00.224648+00:00', 'TimeStamp': '2023-09-12T18:37:00.224648+00:00', 'SynchronizedTimeStamp': '2023-09-12T18:37:00.000000+00:00', 'min_compatible_version': '3.0', 'max_compatible_version': ''}, Message:
   [{'light_brightness': 254, 'state': 'on'},
    {'light_brightness': {'type': 'integer', 'tz': 'UTC', 'units': 'int'},
     'state': {'type': 'integer', 'tz': 'UTC', 'units': 'On / Off'}}]


Comprehensive Fan Configuration Example
+++++++++++++++++++++++++++++++++++++++++

Fan Registry Configuration
*****************
Home Assistant fans are typically exposed under the `fan.` domain. The Home Assistant driver reads fan state and attributes and supports writing the on/off ``state`` and ``percentage`` speed. Fan ``state`` is converted to integers in VOLTTRON: ``on → 1``, ``off → 0``. ``percentage`` must be an integer between 0 and 100.

Below is an example file named ``fan.living_room_fan.json`` which includes common attributes for a single fan instance with entity id ``fan.living_room_fan``:

.. code-block:: json

   [
        {
            "Entity ID": "fan.living_room_fan",
            "Entity Point": "state",
            "Volttron Point Name": "fan_state",
            "Units": "On / Off",
            "Units Details": "off: 0, on: 1",
            "Writable": true,
            "Starting Value": 0,
            "Type": "int",
            "Notes": "Fan on/off control"
        },
        {
            "Entity ID": "fan.living_room_fan",
            "Entity Point": "percentage",
            "Volttron Point Name": "fan_speed",
            "Units": "Percent",
            "Units Details": "0-100",
            "Writable": true,
            "Starting Value": 0,
            "Type": "int",
            "Notes": "Fan speed percentage"
        }
   ]

.. note::

    Available attributes vary by fan integration. To discover attributes for your specific fan entity, use Home Assistant Developer Tools and inspect the ``fan.living_room_fan`` entity to list its state and attributes. 
    Map each desired attribute to an ``Entity Point`` and assign a unique ``Volttron Point Name`` within the registry file.

    The fan's on/off value comes from the entity's primary state (shown as the "State" field in Developer Tools) and does not appear inside the attributes list. 
    Use ``state`` as the ``Entity Point`` to capture this and it will be converted to 1 (on) or 0 (off) by the driver.
    Names like ``fan_state`` and ``fan_speed`` are user-defined ``Volttron Point Name`` values and need not match Home Assistant attribute keys; they are labels for VOLTTRON topics.

Fan Device Configuration
****************************
Below is an example device configuration file for the above fan registry:

.. code-block:: json
    
   {
       "driver_config": {
           "ip_address": "Your Home Assistant IP",
           "access_token": "Your Home Assistant Access Token",
           "port": "Your Port"
       },
       "driver_type": "home_assistant",
       "registry_config": "config://fan.living_room_fan.json",
       "interval": 30,
       "timezone": "UTC"
   }

Transfer the registers files and the config files into the VOLTTRON config store using the commands below:

.. code-block:: bash
    
   vctl config store platform.driver fan.living_room_fan.json HomeAssistant_Driver/fan.living_room_fan.json
   vctl config store platform.driver devices/home/living_room/fan.living_room_fan config/fan.living_room_fan.config

Upon completion, initiate the platform driver. Utilize the listener agent to verify the driver output:

.. code-block:: bash

    vctl status
    vctl start <UUID-of-platform-driver-agent>  
    vctl start <UUID-of-listener-agent>

View the logs in volttron.log which is located in the root level of your repo. You should see data being displayed from the Listener Agent, which is listening to all data being sent to the Message Bus. Example log output:

.. code-block:: bash

    2025-12-01 21:28:00,051 (platform_driveragent-4.0 16005 [223]) platform_driver.driver DEBUG: home/living_room/fan.living_room_fan next scrape scheduled: 2025-12-02 05:28:30.050000+00:00
    2025-12-01 21:28:00,052 (platform_driveragent-4.0 16005 [227]) platform_driver.driver DEBUG: scraping device: home/living_room/fan.living_room_fan
    2025-12-01 21:28:00,086 (platform_driveragent-4.0 16005 [288]) platform_driver.driver DEBUG: publishing: devices/home/living_room/fan.living_room_fan/all
    2025-12-01 21:28:00,089 (listeneragent-3.3 16061 [99]) __main__ INFO: Peer: pubsub, Sender: platform.driver:, Bus: , Topic: devices/home/living_room/fan.living_room_fan/all, Headers: {'Date': '2025-12-02T05:28:00.086514+00:00', 'TimeStamp': '2025-12-02T05:28:00.086514+00:00', 'SynchronizedTimeStamp': '2025-12-02T05:28:00.000000+00:00', 'min_compatible_version': '3.0', 'max_compatible_version': ''}, Message: 
    [{'fan_speed': 0, 'fan_state': 0},
    {'fan_speed': {'type': 'integer', 'tz': 'UTC', 'units': 'Percent'},
    'fan_state': {'type': 'integer', 'tz': 'UTC', 'units': 'On / Off'}}]
    2025-12-01 21:28:00,089 (platform_driveragent-4.0 16005 [294]) platform_driver.driver DEBUG: finish publishing: devices/home/living_room/fan.living_room_fan/all

Comprehensive Switch Configuration Example
+++++++++++++++++++++++++++++++++++++++++

Switch Registry Configuration
*****************
Home Assistant switches are typically exposed under the ``switch.`` domain. The Home Assistant driver reads switch state and supports writing the on/off ``state``. Switch ``state`` is converted to integers in VOLTTRON: ``on → 1``, ``off → 0``.

Below is an example file named ``switch.bedroom_outlet.json`` which includes attributes for a single switch instance with entity id ``switch.bedroom_outlet``:

.. code-block:: json

   [
        {
            "Entity ID": "switch.bedroom_outlet",
            "Entity Point": "state",
            "Volttron Point Name": "switch_state",
            "Units": "On / Off",
            "Units Details": "off: 0, on: 1",
            "Writable": true,
            "Starting Value": 0,
            "Type": "int",
            "Notes": "Switch on/off control"
        }
   ]

.. note::

    Switch devices provide binary on/off functionality. To inspect the current state of your switch entity, navigate to Home Assistant Developer Tools and examine the entity (e.g., ``switch.bedroom_outlet``) to view its status.
    
    The Switch on/off status is retrieved from the entity's primary state field (displayed as "State" in Developer Tools) rather than from the attributes dictionary.
    Configure ``state`` as the ``Entity Point`` to access this value, which the driver automatically converts to 1 (on) or 0 (off).
    Note that ``switch_state`` represents a user-defined ``Volttron Point Name`` and serves as a label for VOLTTRON topics—it does not need to correspond to any Home Assistant attribute key.

Switch Device Configuration
****************************
Below is an example device configuration file for the above switch registry:

.. code-block:: json
    
   {
       "driver_config": {
           "ip_address": "Your Home Assistant IP",
           "access_token": "Your Home Assistant Access Token",
           "port": "Your Port"
       },
       "driver_type": "home_assistant",
       "registry_config": "config://switch.bedroom_outlet.json",
       "interval": 30,
       "timezone": "UTC"
   }

Transfer the registers files and the config files into the VOLTTRON config store using the commands below:

.. code-block:: bash
    
   vctl config store platform.driver switch.bedroom_outlet.json HomeAssistant_Driver/switch.bedroom_outlet.json
   vctl config store platform.driver devices/home/bedroom/switch.bedroom_outlet config/switch.bedroom_outlet.config

Upon completion, initiate the platform driver. Utilize the listener agent to verify the driver output:

.. code-block:: bash

    vctl status
    vctl start <UUID-of-platform-driver-agent>  
    vctl start <UUID-of-listener-agent>

View the logs in volttron.log which is located in the root level of your repo. You should see data being displayed from the Listener Agent, which is listening to all data being sent to the Message Bus. Here is an example log output:

.. code-block:: bash

    2025-12-02 15:18:00,067 (platform_driveragent-4.0 12458 [445]) platform_driver.driver DEBUG: home/bedroom/switch.bedroom_outlet next scrape scheduled: 2025-12-02 15:18:30.067000+00:00
    2025-12-02 15:18:00,068 (platform_driveragent-4.0 12458 [449]) platform_driver.driver DEBUG: scraping device: home/bedroom/switch.bedroom_outlet
    2025-12-02 15:18:00,095 (platform_driveragent-4.0 12458 [512]) platform_driver.driver DEBUG: publishing: devices/home/bedroom/switch.bedroom_outlet/all
    2025-12-02 15:18:00,097 (listeneragent-3.3 12514 [156]) __main__ INFO: Peer: pubsub, Sender: platform.driver:, Bus: , Topic: devices/home/bedroom/switch.bedroom_outlet/all, Headers: {'Date': '2025-12-02T23:18:00.095362+00:00', 'TimeStamp': '2025-12-02T23:18:00.095362+00:00', 'SynchronizedTimeStamp': '2025-12-02T23:18:00.000000+00:00', 'min_compatible_version': '3.0', 'max_compatible_version': ''}, Message: 
    [{'switch_state': 0},
    {'switch_state': {'type': 'integer', 'tz': 'UTC', 'units': 'On / Off'}}]
    2025-12-02 15:18:00,098 (platform_driveragent-4.0 12458 [518]) platform_driver.driver DEBUG: finish publishing: devices/home/bedroom/switch.bedroom_outlet/all

Running Tests
+++++++++++++++++++++++
To run tests on the VOLTTRON home assistant driver you need to create a helper in your home assistant instance. This can be done by going to **Settings > Devices & services > Helpers > Create Helper > Toggle**. Name this new toggle **volttrontest**. After that run the pytest from the root of your VOLTTRON file.

.. code-block:: bash

    pytest volttron/services/core/PlatformDriverAgent/tests/test_home_assistant.py

If everything works, you will see 6 passed tests.
