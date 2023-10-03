# Tibber Pulse LOCAL
If you like to access the data of your Tibber Pulse directly (instead vie the detour of the cloud), then there is quite
a simple approach to read the data directly from the Pulse Bridge.

## Know Inssues
- No Logo/Icons (Tibber) for the integration (yet)

## Preparation - enabling the web frontend of the Tibber Pulse Bridge

To enable the web frontend continuously, one variable needs to be set in the web frontend. But to get into the web
frontend for the first time you need to start the Tibber Pulse Bridge in AccessPoint mode. This can be done by the
following steps:

### Start AP-Mode
* Unplug the tibber bridge.
* After three seconds, plug the tibber bridge.
* After three seconds, unplug the tibber bridge.
* After three seconds, plug the tibber bridge.

The LED on the tibber bridge should now light up green and not light blue anymore.

If this is not the case, then try this alternative:
* Unplug the tibber bridge.
* Plug the tibber bridge
* When the bridge light in __yellow__ then unplug the bridge again
* Wait for a short while and plug in the bridge again after few seconds

NOW the LED on the tibber bridge should now light up green and not light blue anymore.

### Connect to the Pulse Bridge WiFi AccessPoint

Now use any device (laptop, pad, phone) to connect to the WiFi network `Tibber Bridge`.  The password for the WiFi
is the nine characters printed on the tibber bridge - it's important to inlclude the dash. The password should look
like this: `AD56-54BA`.

![img|160x90](images/bridge-pwd-location.png)

### Set `webserver_force_enable` to `true` in the web frontend

After you are connected to the WiFi that have been created by the Pulse Bridge with your laptop/phone, use a web browser
on that device to connect to <http://10.133.70.1/>. You will be prompted for a user and a password (BasicAuth).

The username is ```admin``` and the password is again the nine characters printed on the tibber bridge.

When connected, select the param tab, there find and set the variable `webserver_force_enable` to `true`.

After setting and saving the value, remember to press *"Store params to flash"* on the bottom of the page.

__Please do not modify and other values in the params__

### Bring your Pulse & Bridge back to normal operation 

Unplug the tibber bridge, wait __ten seconds__ and plug it back again. Now it should connect back to your previously
configured WiFi and should work as before (submit the data to tibber) - the LED should light up light blue again.

### Final testing

Since you have set the `webserver_force_enable` to `true` the web frontend should now be accessible via
<http://tibber_bridge/>. If this is not going to work for you, you might like to check the IP-Address of your Tibber
Pulse Bridge in your Router. Personally I have configured my router in a way, that the Pulse Bridge gets allways the
same IP assigned. I just can recommend to do the same.

When you open the web frontend of the bridge, you have to provide always the user `admin` and the password.

Now all is setup, that you can install and use this `Tibber Local Polling` integration

## Installation

### Hacs

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

- Install [Home Assistant Community Store (HACS)](https://hacs.xyz/)
- Add custom repository https://github.com/marq24/ha-tibber-pulse-local to HACS
- Add integration repository (search for "Tibber Pulse Local" in "Explore & Download Repositories")
    - Select latest version or `master`
- Restart Home Assistant to install all dependencies

### Manual

- Copy all files from `custom_components/tibber_local/` to `custom_components/tibber_local/` inside your config Home Assistant
  directory.
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
  - Provide the update intervall (can be 2 Seconds)
  - Provide area where the battery is located