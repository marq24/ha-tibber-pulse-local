# Tibber Pulse IR LOCAL

If you like to access the data of your Tibber Pulse IR directly (instead via the detour through the cloud), then there is a simple approach to read the data directly from the Tibber Pulse Bridge. There are alternative solutions via an additional MQTT - but why should the data go through such a proxy, if it can be read directly.

This integration will work __only__ with the __IR__ Version of the Tibber Pulse. There are other versions: P1, HAN or KM (sold in countries like Sweden, Norway or Netherlands) that __are not compatible__ with this integration. If you are not sure, what Tibber Pulse version you have just check, if you have an additional 'Bridge' device - which is basically an additional thing, that you have to plug into a power outlet (see the picture below). 

__Please note__, _that this integration is not official and not supported by the tibber development team. I am not affiliated with tibber in any way._

[![hacs_badge][hacsbadge]][hacs] [![github][ghsbadge]][ghs] [![BuyMeCoffee][buymecoffeebadge]][buymecoffee] [![PayPal][paypalbadge]][paypal] [![hainstall][hainstallbadge]][hainstall]

---

## Tibber Invitation link

###### Advertisement / Werbung

If you want to join Tibber (become a customer), you might want to use my personal invitation link. When you use this link, Tibber will we grant you and me a bonus of 50,-€ for each of us. This bonus then can be used in the Tibber store (not for your power bill) - e.g. to buy a Tibber Bridge. I am fully aware, that when you are here in this repository the chances are very high, that you are already a Tibber customer and have already a Tibber Pulse. If you are already a Tibber customer and have not used an invitation link yet, you can also enter one afterward in the Tibber App (up to 14 days). [[see official Tibber support article](https://support.tibber.com/en/articles/4601431-tibber-referral-bonus#h_ae8df266c0)]

Please consider [using my personal Tibber invitation link to join Tibber today](https://invite.tibber.com/6o0kqvzf) or Enter the following code: 6o0kqvzf (six, oscar, zero, kilo, quebec, victor, zulu, foxtrot) afterward in the Tibber App - TIA!

---

## Know Issues

- The Tibber Pulse IR Bridge supporting different communication modes (when fetching data from electricity meter). Here I need your help! Obviously I have one electricity meter here at home. This meter is communicating via a protocol called SML 1.04 and this is currently the __only__ one that is supported/implemented.

  The Tibber Bridge supporting also the modes: AutoScanMode, IEC-62056.21, Logarex and Impressions (Blinks / kwh) using ambient or IR sensors. In order to support these other modes I would need sample data from you. If your Tibber Pulse IR using one of these communications protocols, please be so kind and create here an issue in github - TIA!

- Sometimes the Pulse deliver a data-package that does not contain valid data (looks like the build in webserver have a response buffer issue?). These invalid packages can't be read with the [python SML-Lib](https://github.com/spacemanspiff2007/SmlLib) and you will find then in the HA-log some `Bytes missing...` or `CRC while parse data...` messages. (when logging on INFO Level)

  If they happen the code will just try to load the data again for one time. Together with the message the actual payload (data that has been read from the Tibber Pulse Bridge) will also be logged. So you can verify that the data is indeed invalid.

- During the setup the integration check/verify that there is at least one data field available that can be read. If the bridge does not provide any data (OBIS codes) then the setup will fail (with the message, that the connection could not be established). You might like to check if `http://admin:[BRIDGE_PASSWORD]@[YOUR_IP]/data.json?node_id=1` will provide a data feed.

## Want to report an issue?

Please use the [GitHub Issues](https://github.com/marq24/ha-tibber-pulse-local/issues) for reporting any issues you encounter with this integration. Please be so kind before creating a new issues, check the closed ones, if your problem have been already reported (& solved). 

In order to speed up the support process you might like already prepare and provide DEBUG log output. In the case of a technical issue - like not-supported--yet-communication-mode - I would need this DEBUG log output to be able to help/fix the issue. There is a short [tutorial/guide 'How to provide DEBUG log' here](https://github.com/marq24/ha-senec-v3/blob/master/docs/HA_DEBUG.md) - please take the time to quickly go through it.

## Kudos

- [@spacemanspiff2007](https://github.com/spacemanspiff2007) for providing a Python SML lib that makes reading the data from the Pulse IR almost effortless for a python noob like me
- [@ProfDrYoMan](https://github.com/ProfDrYoMan) for providing the initial idea. I failed to setup the ESP32 stuff, so I took the approach writing this custom integration

## Preparation: Enabling the web frontend of the Tibber Pulse Bridge [*Required*]

To enable the web frontend permanently, one local variable needs to be set in the web frontend. But to get into the web frontend for the first time you need to start the Tibber Pulse Bridge in AccessPoint mode. This can be done by the following steps:

### 1. Start AP-Mode

* Unplug the Tibber bridge.
* After three seconds, plug the Tibber bridge.
* After three seconds, unplug the Tibber bridge.
* After three seconds, plug the Tibber bridge.

The LED on the Tibber bridge should now light up green and not light blue anymore.

If this is not the case, then try this alternative:

* Unplug the Tibber bridge.
* Plug the Tibber bridge
* When the bridge light in __yellow__ then unplug the bridge again
* Wait for a short while and plug in the bridge again after few seconds

NOW the LED on the Tibber bridge should now light up green and not light blue anymore.

### 2. Connect to the Pulse Bridge WiFi AccessPoint

Now use any device (laptop, tablet, phone) to connect to the `Tibber Bridge` WiFi network. The password for the WiFi is the nine characters printed on the Tibber bridge - it's important to include the dash. The password should have the pattern like this example one: `AD56-54BA`.

![img|160x90](images/bridge-pwd-location.png)

### 3. Set `webserver_force_enable` to `true` in the web frontend

After you are connected to the WiFi that have been created by the Pulse Bridge with your laptop/phone, use a web browser on that device to connect to <http://10.133.70.1/>. You will be prompted for a user and a password (BasicAuth).

The username is ```admin``` and the password is again the nine characters printed on the Tibber bridge.

When connected, select the param tab, there find and set the variable `webserver_force_enable` to `true`.

After setting and saving the value, remember to press *"Store params to flash"* on the bottom of the page.

__Please do not modify and other values in the params__

### 4. Bring your Pulse & Bridge back to normal operation

Unplug the Tibber bridge, wait __ten seconds__ and plug it back again. Now it should connect back to your previously configured WiFi and should work as before (submit the data to Tibber) - the LED should light up light blue again.

### 5. Final testing [do not continue if you did not completed this final step]

After you have successfully reset the Tibber bridge (AP mode is OFF and you are back in normal operation mode). Since you have set the `webserver_force_enable` to `true` the web frontend should now be still accessible via the following URL:
<http://tibber-host/> or <http://tibber-bridge/>.

If the hostname 'tibber-host' (or 'tibber-bridge') is not going to work for you in your LAN, you might like to check the IP-Address of your Tibber Pulse Bridge in your Router. __The IP *is not* the `10.133.70.1` any longer!__

Personally I have configured my router in a way, that the Pulse Bridge gets allways the same IP assigned. I just can recommend to do the same. Since accessing the device via IP (instead of the host name) will save you DNS-Lookups.

When you open the web frontend of the bridge, you have to provide the user `admin` and the password always.

![img|160x90](images/web-frontend.png)

Now (when the frontend works for you) all is prepared, so you can install and use this `Tibber Local Polling` integration

## Setup / Installation

### Installation using HACS

- Install [Home Assistant Community Store (HACS)](https://hacs.xyz/)
- Add integration repository (search for "Tibber Pulse Local" in "Explore & Download Repositories")
  - Select latest version or `main`
- Restart Home Assistant to install all dependencies

### Manual installation

- Copy all files from `custom_components/tibber_local/` to `custom_components/tibber_local/` inside your config Home Assistant directory.
- Restart Home Assistant to install all dependencies

### Adding or enabling integration

#### My Home Assistant (2021.3+)

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tibber_local)

#### Manual

Add custom integration using the web interface and follow instruction on screen.

- Go to `Configuration -> Integrations` and add "Tibber Pulse Local" integration
- Specify:
    - Provide display name for the device
    - Provide the address (hostname or IP) of the Pulse Bridge
    - Provide the password of the Pulse Bridge
    - Provide the update interval (can be 2 Seconds)
    - Provide area where the Tibber Pule Bridge is located

__IMPORTANT to know__: During the setup of this integration it will be checked, if there is at least one OBIS-Code (data field) available from the bridge. If there is no field/data available that can be read, the setup process will fail (with the message that no connection is possible).

## Additional entities to get status information about your Tibber Pulse IR itself

Beside the data that the Tibber Pulse IR is reading from your electricity meter, the device is also provide additional information about its own status. Since the assumption is that you want to read this additional status information with a much lower update-interval (less frequent) the usage of a REST-Entity template a (IMHO) simple way to archive your goal.

### REST-Template in your HA configuration.yaml

requesting `http://admin:[BRIDGE_PASSWORD]@[YOUR_IP]/metrics.json?node_id=1` will return a json like this one here

```json
{
  "$type": "node_status",
  "node_status": {
    "product_id": 49344,
    "bootloader_version": 17563650,
    "meter_mode": 3,
    "node_battery_voltage": 3.127,
    "node_temperature": 22.51,
    "node_avg_rssi": -72.746,
    "node_avg_lqi": 186.438,
    "radio_tx_power": 190,
    "node_uptime_ms": 167656940,
    "meter_msg_count_sent": 75,
    "meter_pkg_count_sent": 237,
    "time_in_em0_ms": 8405,
    "time_in_em1_ms": 30,
    "time_in_em2_ms": 291717,
    "acmp_rx_autolevel_300": 146,
    "acmp_rx_autolevel_9600": 164
  },
  "hub_attachments": {
    "meter_pkg_count_recv": 237,
    "meter_reading_count_recv": 75,
    "node_version": "1007-56bd9fb9"
  }
}
```

Check if you have already a `sensor` section in your `configuration.yaml` file - if there is none - create one on as top level entry like this (the line '  - platforms: ...' must (obviously) be replaced with the complete sections shown further below):

```yaml
sensor:
  - platform: ...
```

Add in the `sensor` section of your `configuration.yaml` file the following content: sections with `[ CHANGE_ME:xxx ]` have to be modified to your requirements. E.g. assuming your assuming password is __55AA-CC21__, then you have to replace `[ CHANGE_ME:YOUR_PASSWORD ]` with just `55AA-CC21`

```yaml
  - platform: rest
    name: [ CHANGE_ME:Tibber Prices ]
    unique_id: [ CHANGE_ME:tibber_prices ]
    resource: http://admin:[ CHANGE_ME:YOUR_PASSWORD ]@[ CHANGE_ME:YOUR_IP ]/metrics.json?node_id=1
    method: GET
    json_attributes_path: "node_status"
    json_attributes:
      - node_temperature
      - node_avg_rssi
      - radio_tx_power
      - [ CHANGE_ME: add/remove as many of the node_status attributes you want to meassure/do not need ]
    value_template: "{{ value_json.node_status.node_battery_voltage | float }}"
    # the scan_interval will be specified in seconds...
    # for update every 5min use 300 (60sec * 5min = 300sec)
    # for update every 15min use 900 (60sec * 15min = 900sec)
    # for update every 1h use 3600 (60sec * 60min = 3600sec)
    # for update every 24h use 86400 (60sec * 60min * 24h = 86400sec)
    scan_interval: 900
    headers:
      Content-Type: application/json
      User-Agent: REST
    unit_of_measurement: [ CHANGE_ME:A_UNIT_HERE ]
```

Here is a complete example assuming the password is __55AA-CC21__ the IP is __192.168.2.213__, and you want to capture the __node_battery_voltage__ as main entity information and all other children of the `node_status` as additional attributes of the entity that will be requested every 5 minutes:

```yaml
  - platform: rest
    name: Tibber Pulse Metrics
    unique_id: tibber_pulse_metrics
    resource: http://admin:55AA-CC21@192.168.2.213/metrics.json?node_id=1
    method: GET
    json_attributes_path: "node_status"
    json_attributes:
      - node_temperature
      - node_avg_rssi
      - node_avg_lqi
      - radio_tx_power
      - node_uptime_ms
      - meter_msg_count_sent
      - meter_pkg_count_sent
      - time_in_em0_ms
      - time_in_em1_ms
      - time_in_em2_ms
      - acmp_rx_autolevel_300
      - acmp_rx_autolevel_9600
    value_template: "{{ value_json.node_status.node_battery_voltage | float }}"
    scan_interval: 300
    headers:
      Content-Type: application/json
      User-Agent: REST
    unit_of_measurement: V
```

Here just another example with just a single value (without additional atributes) that will update every hour (just again have in mind, that this yaml section have to be under your `sensor` section of your `configuration.yaml` file):

```yaml
  - platform: rest
    name: Tibber Pulse Metrics
    unique_id: tibber_pulse_metrics
    resource: http://admin:55AA-CC21@192.168.2.213/metrics.json?node_id=1
    method: GET
    value_template: "{{ value_json.node_status.node_battery_voltage | float }}"
    scan_interval: 3600
    headers:
      Content-Type: application/json
      User-Agent: REST
    unit_of_measurement: V
```

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=ccc

[ghs]: https://github.com/sponsors/marq24
[ghsbadge]: https://img.shields.io/github/sponsors/marq24?style=for-the-badge&logo=github&logoColor=ccc&link=https%3A%2F%2Fgithub.com%2Fsponsors%2Fmarq24&label=Sponsors

[buymecoffee]: https://www.buymeacoffee.com/marquardt24
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a-coffee-blue.svg?style=for-the-badge&logo=buymeacoffee&logoColor=ccc

[paypal]: https://paypal.me/marq24
[paypalbadge]: https://img.shields.io/badge/paypal-me-blue.svg?style=for-the-badge&logo=paypal&logoColor=ccc

[hainstall]: https://my.home-assistant.io/redirect/config_flow_start/?domain=tibber_local
[hainstallbadge]: https://img.shields.io/badge/dynamic/json?style=for-the-badge&logo=home-assistant&logoColor=ccc&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.tibber_local.total