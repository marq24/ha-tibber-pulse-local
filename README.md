# Tibber Pulse IR LOCAL

If you like to access the data of your Tibber Pulse IR directly (instead of the detour through the cloud), then there is a simple approach to read the data directly from the Tibber Pulse Bridge. There are alternative solutions via an additional MQTT - but why should the data go through such a proxy if it can be read directly.

This integration will work __only__ with the __IR__ Version of the Tibber Pulse. There are other versions: P1, HAN or KM (sold in countries like Sweden, Norway or the Netherlands) that __are not compatible__ with this integration. If you are not sure, what Tibber Pulse version you have just check, if you have an additional 'Bridge' device - which is basically an additional thing, that you have to plug into a power outlet (see the picture below). 

__Please note__, _that this integration is not official and not supported by the tibber development team. I am not affiliated with tibber in any way._

[![hacs_badge][hacsbadge]][hacs] [![github][ghsbadge]][ghs] [![Wero][werobadge]][wero] [![BuyMeCoffee][buymecoffeebadge]][buymecoffee] [![PayPal][paypalbadge]][paypal] [![hainstall][hainstallbadge]][hainstall]

---

## Tibber Invitation link

###### Advertisement / Werbung

If you want to join Tibber (become a customer), you might want to use my personal invitation link. When you use this link, Tibber will grant you and me a bonus of 50,-€ for each of us. This bonus then can be used in the Tibber store (not for your power bill) - e.g. to buy a Tibber Bridge. I am fully aware, that when you are here in this repository the chances are very high, that you are already a Tibber customer and have already a Tibber Pulse. If you are already a Tibber customer and have not used an invitation link yet, you can also enter one afterward in the Tibber App (up to 14 days). [[see official Tibber support article](https://support.tibber.com/en/articles/4601431-tibber-referral-bonus#h_ae8df266c0)]

Please consider [using my personal Tibber invitation link to join Tibber today](https://invite.tibber.com/6o0kqvzf) or Enter the following code: 6o0kqvzf (six, oscar, zero, kilo, quebec, victor, zulu, foxtrot) afterward in the Tibber App - TIA!

---

## Know Issues

- The Tibber Pulse IR Bridge supports different communication modes (when fetching data from electricity meter). Here I need your help! Obviously, I have only one electricity meter here at home. This meter is communicating via a protocol called SML 1.04.

    Over the time with the help of the community, the following modes are currently supported:

  - SML 1.04
  - Plaintext
  - IEC-62056.21
  - Impressions (Blinks / kwh) using ambient

  The Tibber Bridge additionally offers the modes: _AutoScanMode, IEC-62056.21, Logarex and Impressions (Blinks / kwh) using IR sensors_. To support these other modes, I would need sample data from you. If your Tibber Pulse IR using one of these communications protocols, please be so kind and create here an issue in github - TIA!

- Sometimes the Pulse deliver a data-package that does not contain valid data (looks like the build in webserver have a response buffer issue?). These invalid packages can't be read with the [python SML-Lib](https://github.com/spacemanspiff2007/SmlLib) and you will find then in the HA-log some `Bytes missing...` or `CRC while parse data...` messages. (when logging on INFO Level)

  If they happen the code will just try to load the data again for one time. Together with the message the actual payload (data that has been read from the Tibber Pulse Bridge) will also be logged. So you can verify that the data is indeed invalid.

- During the setup the integration check/verify that there is at least one data field available that can be read. If the bridge does not provide any data (OBIS codes) then the setup will fail (with the message, that the connection could not be established). You might like to check if `http://admin:[BRIDGE_PASSWORD]@[YOUR_IP]/data.json?node_id=1` will provide a data feed.

## Want to report an issue?

Please use the [GitHub Issues](https://github.com/marq24/ha-tibber-pulse-local/issues) for reporting any issues you encounter with this integration. Please be so kind before creating a new issues, check the closed ones, if your problem have been already reported (& solved). 

In order to speed up the support process, you might like to already prepare and provide DEBUG log output. In the case of a technical issue - like not-supported--yet-communication-mode - I would need this DEBUG log output to be able to help/fix the issue. There is a short [tutorial/guide 'How to provide DEBUG log' here](https://github.com/marq24/ha-senec-v3/blob/main/docs/HA_DEBUG.md) - please take the time to quickly go through it.

## Kudos

- [@spacemanspiff2007](https://github.com/spacemanspiff2007) for providing a Python SML lib that makes reading the data from the Pulse IR almost effortless for a python noob like me
- [@ProfDrYoMan](https://github.com/ProfDrYoMan) for providing the initial idea. I failed to setup the ESP32 stuff, so I took the approach writing this custom integration

## Preparation: Enabling the web frontend of the Tibber Pulse Bridge [*Required*]

To enable the web frontend permanently, one local variable needs to be set in the web frontend. But to get into the web frontend for the first time, you need to start the Tibber Pulse Bridge in AccessPoint mode. This can be done by the following steps:

### 1. Start AP-Mode

> [!TIP]
> While you have unplugged the bridge you might like to use the opportunity to get the password from the bottom of the plug - e.g. by taking a photo (see also step 2: 'Connect to the Pulse Bridge WiFi AccessPoint').   

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

![img|160x90](https://github.com/marq24/ha-tibber-pulse-local/raw/main/images/bridge-pwd-location.png)

### 3. Set `webserver_force_enable` to `true` in the web frontend

After you are connected to the WiFi that have been created by the Pulse Bridge with your laptop/phone, use a web browser on that device to connect to <http://10.133.70.1/>. You will be prompted for a user and a password (BasicAuth).

The username is `admin` and the password is again the nine characters printed on the Tibber bridge.

Depending on the hardware revision and firmware, there are two alternatives to archive this goal. Please select the procedure that fits your situation.

#### Via CONSOLE-Tab

With a recent firmware release the `webserver_force_enable` flag (39) does __not appear__ any longer in the param list. So the console tab is the way to go!

1. Go to <http://10.133.70.1/console/>
2. type `param_get 39` (just to ensure, that the system still know the `webserver_force_enable` parameter) - you can also try to type `param_get webserver_force_enable` [and press the `send` button afterwards] - this should give you some output like this:
   ```
   tibber-bridge> param_get 39
   esp32> param_get 39
   webserver_force_enable (39):
   false
   Command 'param_get 39' executed successfully
   ```
3. So if `39` (= `webserver_force_enable`) is still present, then and __only then__ you can continue!

4. type `param_set 39 TRUE` (the upper case of TRUE is important here) [and press the `send` button afterward]
5. type `param_store` [and press the `send` button afterward]
6. for confirmation, you can type again `param_get 39` [and press the `send` button afterward]

#### Via PARAMS-Tab [previously the default procedure]

1. Go to <http://10.133.70.1/params/>
2. Find the variable `webserver_force_enable` in the list
3. Set the value to `true` (lower case)
4. Press *"Store params to flash"* on the bottom of the page.

__Please do not modify any other values in the params list!__

### 4. Bring your Pulse & Bridge back to normal operation

Unplug the Tibber bridge, wait __ten seconds__ and plug it back again. Now it should connect back to your previously configured WiFi and should work as before (submit the data to Tibber) - the LED should light up light blue again.

### 5. Final testing [do not continue if you did not complete this final step]

#### Part I: Access the web frontent

After you have successfully reset the Tibber bridge (AP mode is OFF and you are back in normal operation mode). Since you have set the `webserver_force_enable` to `true` the web frontend should now be still accessible via the following URL:
<http://tibber-host/> or <http://tibber-bridge/>.

If the hostname 'tibber-host' (or 'tibber-bridge') is not going to work for you in your LAN, you might like to check the IP-Address of your Tibber Pulse Bridge in your Router. __The IP *is not* the `10.133.70.1` any longer!__

Personally, I have configured my router in a way, that the Pulse Bridge gets always the same IP assigned. I just can recommend doing the same. Since accessing the device via IP (instead of the host name) will save you DNS-Lookups.

When you open the web frontend of the bridge, you always have to provide the user `admin` and the password.

![img|160x90](https://github.com/marq24/ha-tibber-pulse-local/raw/main/images/web-frontend.png)

Now (when the frontend works for you) almost everything is prepared... Just one more thing to check:

#### Part II: Ensure that there is at least one node paired with the bridge

For whatever reasons, there are experts out there, trying to use this integration _without having paired_ the Tibber Pulse reading head (the part is mounted at your power meter) with the Tibber Pulse Bridge. For sure, this is not going to work! The pairing procedure is part of the regular Tibber Pulse setup process with your Tibber app - so probably you have done this already - but just in case:

Please double-check by opening the `http://[YOUR_IP]/nodes/` section (you can select from the menu the 'NODES' entry) and ensure, that there is at least one node listed - which means that the bridge is connected with the reading-head-unit.

Here you can also check, if the node is listed with the (expected) default NodeId value `1`. If you have a different NodeId, then you need to adjust the expert setting `Node Number (expert setting)` when configure this integration.

#### Part III: Check 'Last seen' & 'Last data' [update frequency]

1. Go to `http://[YOUR-IP]/nodes/` (just like in part II)
2. Take a look at the value `Last data`
   
   This last data value is the last time (in seconds) the bridge has received a data update from the reading head. This value should not be higher than 2.5-5 seconds.
  
   If your `Last data` is frequently recently greater than this, then this integration can't work in a reliable way.
   
   __Rotate the reading head few degrees anti-clock wise in order to check, if the update frequency will be better (smaller).__ 
   
   ![img|20x20](https://github.com/marq24/ha-tibber-pulse-local/raw/main/images/rotate_head.png)
   
   Please also have a [look at the post from @ckarrie](https://github.com/marq24/ha-tibber-pulse-local/issues/6#issuecomment-1791117188) in order to learn a difference even a few degrees can make!


#### Finally, you are done!

When part I, II & III are completed/confirmed, __then__ you can install and use this `Tibber Local Polling` integration.

## Setup / Installation

### Step I: Install the integration

#### Option 1: via HACS
 
- Install [Home Assistant Community Store (HACS)](https://hacs.xyz/)
- Add integration repository (search for "Tibber Pulse Local" in "Explore & Download Repositories")
- Use the 3-dots at the right of the list entry (not at the top bar!) to download/install the custom integration - the latest release version is automatically selected. Only select a different version if you have specific reasons.
- After you have pressed download and the process has completed, you must __Restart Home Assistant__ to install all dependencies
- Setup the custom integration as described below (see _Step II: Adding or enabling the integration_)

#### Option 2: manual steps

- Copy all files from `custom_components/tibber_local/` to `custom_components/tibber_local/` inside your config Home Assistant directory.
- Restart Home Assistant to install all dependencies

### Step II: Adding or enabling the integration

__You must have installed the integration (manually or via HACS before)!__

#### Option 1: My Home Assistant (2021.3+)

Just click the following Button to start the configuration automatically (for the rest see _Option 2: Manually steps by step_):

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tibber_local)

#### Option 2: Manually steps by step

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

[buymecoffee2]: https://buymeacoffee.com/marquardt24/membership
[buymecoffeebadge2]: https://img.shields.io/badge/coffee-subs-blue.svg?style=for-the-badge&logo=buymeacoffee&logoColor=ccc

[paypal]: https://paypal.me/marq24
[paypalbadge]: https://img.shields.io/badge/paypal-me-blue.svg?style=for-the-badge&logo=paypal&logoColor=ccc

[wero]: https://share.weropay.eu/p/1/r/2FVLe2F3tBoefQee8YGY4o
[werobadge]: https://img.shields.io/badge/_wero-me_-blue.svg?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZwogICByb2xlPSJpbWciCiAgIHZpZXdCb3g9IjAgMCA0Mi4wNDY1MDEgNDAuODg2NyIKICAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgo+CiAgPGcKICAgICBjbGlwLXBhdGg9InVybCgjY2xpcDApIgogICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKC01Ny4zODE4KSI+CiAgICA8cGF0aAogICAgICAgZD0ibSA3OC40MDUxLDMwLjM1NzQgYyAwLDAgLTAuMDE4NSwwIC0wLjAyNzgsMCAtNC4zMTg0LDAgLTcuMzQ2MiwtMi41NzY5IC04LjY0NjEsLTUuOTg4NyBIIDk5LjA2OTggQyA5OS4zMDU3LDIzLjA4NDkgOTkuNDI4MywyMS43NzExIDk5LjQyODMsMjAuNDQxIDk5LjQyODMsOS43NTY3MyA5MS43Mzc1LDAuMDEzODc4NyA3OC40MDUxLDAgdiAxMC41MjcgYyA0LjM0MzksMC4wMTE2IDcuMzQxNiwyLjU4MzcgOC42Mjc2LDUuOTg4NyBoIC0yOS4yOTcgYyAtMC4yMzM2LDEuMjgzNyAtMC4zNTM5LDIuNTk3NiAtMC4zNTM5LDMuOTI3NiAwLDEwLjY5MTMgNy43MDAyLDIwLjQ0MzQgMjAuOTk1NSwyMC40NDM0IDAuMDA5MywwIDAuMDE4NSwwIDAuMDI3OCwwIHYgLTEwLjUyNyB6IgogICAgICAgZmlsbD0iI2UyZTNlMyIvPgogICAgPHBhdGgKICAgICAgIGQ9Im0gNzguMzc3NCw0MC44ODQ0IGMgMC40NTEsMCAwLjg5NTEsLTAuMDEzOSAxLjMzNDYsLTAuMDM0NyAyLjcwMTcsLTAuMTM2NSA1LjE1MzUsLTAuNjgwMSA3LjMzOTMsLTEuNTU2NyAyLjE4NTgsLTAuODc2NyA0LjEwNTcsLTIuMDgxOCA1LjczODcsLTMuNTM5MSAxLjYzMywtMS40NTczIDIuOTgxNSwtMy4xNjQzIDQuMDI3LC01LjA0NDkgMC45NTA2LC0xLjcwOTQgMS42NDQ1LC0zLjU1OTkgMi4wNzk0LC01LjQ5MTMgSCA4Ni42NzIgYyAtMC4yNDk4LDAuNTE1OCAtMC41NDEzLDEuMDA4NSAtMC44NzQ0LDEuNDY4OCAtMC40NTU2LDAuNjI5MSAtMC45ODk5LDEuMjAwNSAtMS41OTYsMS42OTMyIC0wLjYwNiwwLjQ5MjcgLTEuMjg2LDAuOTA5IC0yLjAzNTQsMS4yMzA2IC0wLjc0OTUsMC4zMjE1IC0xLjU2NiwwLjU0ODIgLTIuNDQ5NSwwLjY2MTUgLTAuNDMwMywwLjA1NTUgLTAuODc0NCwwLjA4NzkgLTEuMzM0NywwLjA4NzkgLTIuNzUwMiwwIC00Ljk3NzYsLTEuMDQ3OCAtNi41NjY3LC0yLjY4NzggbCAtNy45NDc2LDcuOTQ3OCBjIDMuNTM2NiwzLjIyOTIgOC40NDI2LDUuMjY0NyAxNC41MTY2LDUuMjY0NyB6IgogICAgICAgZmlsbD0idXJsKCNwYWludDApIgogICAgICAgc3R5bGU9ImZpbGw6dXJsKCNwYWludDApIiAvPgogICAgPHBhdGgKICAgICAgIGQ9Ik0gNzguMzc3NywwIEMgNjcuMTAxNiwwIDU5Ljg1MDIsNy4wMTMzNyA1Ny45MDcyLDE1LjY2OTEgSCA3MC4wOTcgYyAxLjQ1NzIsLTIuOTgxNyA0LjMyNzcsLTUuMTQyMSA4LjI4MDcsLTUuMTQyMSAzLjE1MDMsMCA1LjU5NTIsMS4zNDYyIDcuMTkzNSwzLjM4MTggTCA5My41OTA1LDUuODg5MiBDIDkwLjAwNzYsMi4zMDE1NSA4NC44NTY1LDAuMDAyMzEzMTIgNzguMzc1MywwLjAwMjMxMzEyIFoiCiAgICAgICBmaWxsPSJ1cmwoI3BhaW50MSkiCiAgICAgICBzdHlsZT0iZmlsbDp1cmwoI3BhaW50MSkiIC8+CiAgPC9nPgogIDxkZWZzPgogICAgPGxpbmVhckdyYWRpZW50CiAgICAgICBpZD0icGFpbnQwIgogICAgICAgeDE9IjkyLjc0MzY5OCIKICAgICAgIHkxPSIxOC4wMjYxOTkiCiAgICAgICB4Mj0iNzQuNzU0NTAxIgogICAgICAgeTI9IjQwLjMxMDIiCiAgICAgICBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC4wMiIKICAgICAgICAgc3RvcC1jb2xvcj0iI0UyRTNFMyIKICAgICAgICAgc3RvcC1vcGFjaXR5PSIwIi8+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC4zOSIKICAgICAgICAgc3RvcC1jb2xvcj0iI0UyRTNFMyIKICAgICAgICAgc3RvcC1vcGFjaXR5PSIwLjY2Ii8+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC42OCIKICAgICAgICAgc3RvcC1jb2xvcj0iI0UyRTNFMyIvPgogICAgPC9saW5lYXJHcmFkaWVudD4KICAgIDxsaW5lYXJHcmFkaWVudAogICAgICAgaWQ9InBhaW50MSIKICAgICAgIHgxPSI2MS4yNzA0MDEiCiAgICAgICB5MT0iMjMuMDE3Nzk5IgogICAgICAgeDI9Ijc5Ljc1NDUwMSIKICAgICAgIHkyPSI0LjUzNDI5OTkiCiAgICAgICBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC4wMiIKICAgICAgICAgc3RvcC1jb2xvcj0iI0UyRTNFMyIKICAgICAgICAgc3RvcC1vcGFjaXR5PSIwIi8+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC4zOSIKICAgICAgICAgc3RvcC1jb2xvcj0iI0UyRTNFMyIKICAgICAgICAgc3RvcC1vcGFjaXR5PSIwLjY2Ii8+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC42OCIKICAgICAgICAgc3RvcC1jb2xvcj0iI0UyRTNFMyIvPgogICAgPC9saW5lYXJHcmFkaWVudD4KICAgIDxjbGlwUGF0aAogICAgICAgaWQ9ImNsaXAwIj4KICAgICAgPHJlY3QKICAgICAgICAgd2lkdGg9IjE3Ny45MSIKICAgICAgICAgaGVpZ2h0PSI0MSIKICAgICAgICAgZmlsbD0iI2ZmZmZmZiIKICAgICAgICAgeD0iMCIKICAgICAgICAgeT0iMCIgLz4KICAgIDwvY2xpcFBhdGg+CiAgPC9kZWZzPgo8L3N2Zz4=

[hainstall]: https://my.home-assistant.io/redirect/config_flow_start/?domain=tibber_local
[hainstallbadge]: https://img.shields.io/badge/dynamic/json?style=for-the-badge&logo=home-assistant&logoColor=ccc&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.tibber_local.total
