




# Enabling the web frontend of the Tibber Pulse Bridge [*Required*]

To enable the web frontend permanently, one local variable needs to be set in the web frontend. But to get into the web frontend for the first time, you need to start the Tibber Pulse Bridge in AccessPoint mode. This can be done by the following steps:

## 1. Start AP-Mode

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

## 2. Connect to the Pulse Bridge WiFi AccessPoint

Now use any device (laptop, tablet, phone) to connect to the `Tibber Bridge` WiFi network. The password for the WiFi is the nine characters printed on the Tibber bridge - it's important to include the dash. The password should have the pattern like this example one: `AD56-54BA`.

![img|160x90](https://github.com/marq24/ha-tibber-pulse-local/raw/main/images/bridge-pwd-location.png)

## 3. Set `webserver_force_enable` to `true` in the web frontend

After you are connected to the WiFi that have been created by the Pulse Bridge with your laptop/phone, use a web browser on that device to connect to <http://10.133.70.1/>. You will be prompted for a user and a password (BasicAuth).

The username is `admin` and the password is again the nine characters printed on the Tibber bridge.

Depending on the hardware revision and firmware, there are two alternatives to archive this goal. Please select the procedure that fits your situation.

### Via CONSOLE-Tab

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

### Via PARAMS-Tab [previously the default procedure]

1. Go to <http://10.133.70.1/params/>
2. Find the variable `webserver_force_enable` in the list
3. Set the value to `true` (lower case)
4. Press *"Store params to flash"* on the bottom of the page.

__Please do not modify any other values in the params list!__

## 4. Bring your Pulse & Bridge back to normal operation

Unplug the Tibber bridge, wait __ten seconds__ and plug it back again. Now it should connect back to your previously configured WiFi and should work as before (submit the data to Tibber) - the LED should light up light blue again.

## 5. Final testing [do not continue if you did not complete this final step]

### Part I: Access the web frontent

After you have successfully reset the Tibber bridge (AP mode is OFF and you are back in normal operation mode). Since you have set the `webserver_force_enable` to `true` the web frontend should now be still accessible via the following URL:
<http://tibber-host/> or <http://tibber-bridge/>.

If the hostname 'tibber-host' (or 'tibber-bridge') is not going to work for you in your LAN, you might like to check the IP-Address of your Tibber Pulse Bridge in your Router. __The IP *is not* the `10.133.70.1` any longer!__

Personally, I have configured my router in a way, that the Pulse Bridge gets always the same IP assigned. I just can recommend doing the same. Since accessing the device via IP (instead of the host name) will save you DNS-Lookups.

When you open the web frontend of the bridge, you always have to provide the user `admin` and the password.

![img|160x90](https://github.com/marq24/ha-tibber-pulse-local/raw/main/images/web-frontend.png)

Now (when the frontend works for you) almost everything is prepared... Just one more thing to check:

### Part II: Ensure that there is at least one node paired with the bridge

For whatever reasons, there are experts out there, trying to use this integration _without having paired_ the Tibber Pulse reading head (the part is mounted at your power meter) with the Tibber Pulse Bridge. For sure, this is not going to work! The pairing procedure is part of the regular Tibber Pulse setup process with your Tibber app - so probably you have done this already - but just in case:

Please double-check by opening the `http://[YOUR_IP]/nodes/` section (you can select from the menu the 'NODES' entry) and ensure, that there is at least one node listed - which means that the bridge is connected with the reading-head-unit.

Here you can also check, if the node is listed with the (expected) default NodeId value `1`. If you have a different NodeId, then you need to adjust the expert setting `Node Number (expert setting)` when configure this integration.

### Part III: Check 'Last seen' & 'Last data' [update frequency]

1. Go to `http://[YOUR-IP]/nodes/` (just like in part II)
2. Take a look at the value `Last data`

   This last data value is the last time (in seconds) the bridge has received a data update from the reading head. This value should not be higher than 2.5-5 seconds.

   If your `Last data` is frequently recently greater than this, then this integration can't work in a reliable way.

   __Rotate the reading head few degrees anti-clock wise in order to check, if the update frequency will be better (smaller).__

   ![img|20x20](https://github.com/marq24/ha-tibber-pulse-local/raw/main/images/rotate_head.png)

   Please also have a [look at the post from @ckarrie](https://github.com/marq24/ha-tibber-pulse-local/issues/6#issuecomment-1791117188) in order to learn a difference even a few degrees can make!


### Finally, you are done!

When part I, II & III are completed/confirmed, __then__ you can install and use this `Tibber Local Polling` integration.


[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-blue.svg?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=ccc

[hainstall]: https://my.home-assistant.io/redirect/config_flow_start/?domain=tibber_local
[hainstallbadge]: https://img.shields.io/badge/dynamic/json?style=for-the-badge&logo=home-assistant&logoColor=ccc&label=usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.tibber_local.total

[ghs]: https://github.com/sponsors/marq24
[ghsbadge]: https://img.shields.io/github/sponsors/marq24?style=for-the-badge&logo=github&logoColor=ccc&link=https%3A%2F%2Fgithub.com%2Fsponsors%2Fmarq24&label=Sponsors

[buymecoffee]: https://www.buymeacoffee.com/marquardt24
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a-coffee-blue.svg?style=for-the-badge&logo=buymeacoffee&logoColor=ccc&link=https%3A%2F%2Fwww.buymeacoffee.com%2Fmarquardt24

[buymecoffee2]: https://buymeacoffee.com/marquardt24/membership
[buymecoffeebadge2]: https://img.shields.io/badge/coffee-subs-blue.svg?style=for-the-badge&logo=buymeacoffee&logoColor=ccc&link=https%3A%2F%2Fbuymeacoffee.com%2Fmarquardt24%2Fmembership

[paypal]: https://paypal.me/marq24
[paypalbadge]: https://img.shields.io/badge/paypal-me-blue.svg?style=for-the-badge&logo=paypal&logoColor=ccc&link=https%3A%2F%2Fpaypal.me%2Fmarq24

[wero]: https://share.weropay.eu/p/1/c/6O371wjUW5
[werobadge]: https://img.shields.io/badge/_wero-me_-blue.svg?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZwogICByb2xlPSJpbWciCiAgIHZpZXdCb3g9IjAgMCA0Mi4wNDY1MDEgNDAuODg2NyIKICAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgo+CiAgPGcKICAgICBjbGlwLXBhdGg9InVybCgjY2xpcDApIgogICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKC01Ny4zODE4KSI+CiAgICA8cGF0aAogICAgICAgZD0ibSA3OC40MDUxLDMwLjM1NzQgYyAwLDAgLTAuMDE4NSwwIC0wLjAyNzgsMCAtNC4zMTg0LDAgLTcuMzQ2MiwtMi41NzY5IC04LjY0NjEsLTUuOTg4NyBIIDk5LjA2OTggQyA5OS4zMDU3LDIzLjA4NDkgOTkuNDI4MywyMS43NzExIDk5LjQyODMsMjAuNDQxIDk5LjQyODMsOS43NTY3MyA5MS43Mzc1LDAuMDEzODc4NyA3OC40MDUxLDAgdiAxMC41MjcgYyA0LjM0MzksMC4wMTE2IDcuMzQxNiwyLjU4MzcgOC42Mjc2LDUuOTg4NyBoIC0yOS4yOTcgYyAtMC4yMzM2LDEuMjgzNyAtMC4zNTM5LDIuNTk3NiAtMC4zNTM5LDMuOTI3NiAwLDEwLjY5MTMgNy43MDAyLDIwLjQ0MzQgMjAuOTk1NSwyMC40NDM0IDAuMDA5MywwIDAuMDE4NSwwIDAuMDI3OCwwIHYgLTEwLjUyNyB6IgogICAgICAgZmlsbD0iI0NDQ0NDQyIvPgogICAgPHBhdGgKICAgICAgIGQ9Im0gNzguMzc3NCw0MC44ODQ0IGMgMC40NTEsMCAwLjg5NTEsLTAuMDEzOSAxLjMzNDYsLTAuMDM0NyAyLjcwMTcsLTAuMTM2NSA1LjE1MzUsLTAuNjgwMSA3LjMzOTMsLTEuNTU2NyAyLjE4NTgsLTAuODc2NyA0LjEwNTcsLTIuMDgxOCA1LjczODcsLTMuNTM5MSAxLjYzMywtMS40NTczIDIuOTgxNSwtMy4xNjQzIDQuMDI3LC01LjA0NDkgMC45NTA2LC0xLjcwOTQgMS42NDQ1LC0zLjU1OTkgMi4wNzk0LC01LjQ5MTMgSCA4Ni42NzIgYyAtMC4yNDk4LDAuNTE1OCAtMC41NDEzLDEuMDA4NSAtMC44NzQ0LDEuNDY4OCAtMC40NTU2LDAuNjI5MSAtMC45ODk5LDEuMjAwNSAtMS41OTYsMS42OTMyIC0wLjYwNiwwLjQ5MjcgLTEuMjg2LDAuOTA5IC0yLjAzNTQsMS4yMzA2IC0wLjc0OTUsMC4zMjE1IC0xLjU2NiwwLjU0ODIgLTIuNDQ5NSwwLjY2MTUgLTAuNDMwMywwLjA1NTUgLTAuODc0NCwwLjA4NzkgLTEuMzM0NywwLjA4NzkgLTIuNzUwMiwwIC00Ljk3NzYsLTEuMDQ3OCAtNi41NjY3LC0yLjY4NzggbCAtNy45NDc2LDcuOTQ3OCBjIDMuNTM2NiwzLjIyOTIgOC40NDI2LDUuMjY0NyAxNC41MTY2LDUuMjY0NyB6IgogICAgICAgZmlsbD0idXJsKCNwYWludDApIgogICAgICAgc3R5bGU9ImZpbGw6dXJsKCNwYWludDApIiAvPgogICAgPHBhdGgKICAgICAgIGQ9Ik0gNzguMzc3NywwIEMgNjcuMTAxNiwwIDU5Ljg1MDIsNy4wMTMzNyA1Ny45MDcyLDE1LjY2OTEgSCA3MC4wOTcgYyAxLjQ1NzIsLTIuOTgxNyA0LjMyNzcsLTUuMTQyMSA4LjI4MDcsLTUuMTQyMSAzLjE1MDMsMCA1LjU5NTIsMS4zNDYyIDcuMTkzNSwzLjM4MTggTCA5My41OTA1LDUuODg5MiBDIDkwLjAwNzYsMi4zMDE1NSA4NC44NTY1LDAuMDAyMzEzMTIgNzguMzc1MywwLjAwMjMxMzEyIFoiCiAgICAgICBmaWxsPSJ1cmwoI3BhaW50MSkiCiAgICAgICBzdHlsZT0iZmlsbDp1cmwoI3BhaW50MSkiIC8+CiAgPC9nPgogIDxkZWZzPgogICAgPGxpbmVhckdyYWRpZW50CiAgICAgICBpZD0icGFpbnQwIgogICAgICAgeDE9IjkyLjc0MzY5OCIKICAgICAgIHkxPSIxOC4wMjYxOTkiCiAgICAgICB4Mj0iNzQuNzU0NTAxIgogICAgICAgeTI9IjQwLjMxMDIiCiAgICAgICBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC4wMiIKICAgICAgICAgc3RvcC1jb2xvcj0iI0NDQ0NDQyIKICAgICAgICAgc3RvcC1vcGFjaXR5PSIwIi8+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC4zOSIKICAgICAgICAgc3RvcC1jb2xvcj0iI0NDQ0NDQyIKICAgICAgICAgc3RvcC1vcGFjaXR5PSIwLjY2Ii8+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC42OCIKICAgICAgICAgc3RvcC1jb2xvcj0iI0NDQ0NDQyIvPgogICAgPC9saW5lYXJHcmFkaWVudD4KICAgIDxsaW5lYXJHcmFkaWVudAogICAgICAgaWQ9InBhaW50MSIKICAgICAgIHgxPSI2MS4yNzA0MDEiCiAgICAgICB5MT0iMjMuMDE3Nzk5IgogICAgICAgeDI9Ijc5Ljc1NDUwMSIKICAgICAgIHkyPSI0LjUzNDI5OTkiCiAgICAgICBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC4wMiIKICAgICAgICAgc3RvcC1jb2xvcj0iI0NDQ0NDQyIKICAgICAgICAgc3RvcC1vcGFjaXR5PSIwIi8+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC4zOSIKICAgICAgICAgc3RvcC1jb2xvcj0iI0NDQ0NDQyIKICAgICAgICAgc3RvcC1vcGFjaXR5PSIwLjY2Ii8+CiAgICAgIDxzdG9wCiAgICAgICAgIG9mZnNldD0iMC42OCIKICAgICAgICAgc3RvcC1jb2xvcj0iI0NDQ0NDQyIvPgogICAgPC9saW5lYXJHcmFkaWVudD4KICAgIDxjbGlwUGF0aAogICAgICAgaWQ9ImNsaXAwIj4KICAgICAgPHJlY3QKICAgICAgICAgd2lkdGg9IjE3Ny45MSIKICAgICAgICAgaGVpZ2h0PSI0MSIKICAgICAgICAgZmlsbD0iI2ZmZmZmZiIKICAgICAgICAgeD0iMCIKICAgICAgICAgeT0iMCIgLz4KICAgIDwvY2xpcFBhdGg+CiAgPC9kZWZzPgo8L3N2Zz4=

[revolut]: https://revolut.me/marq24
[revolutbadge]: https://img.shields.io/badge/_revolut-me_-blue.svg?style=for-the-badge&logo=revolut&logoColor=ccc&link=https%3A%2F%2Frevolut.me%2Fmarq24

[wise]: https://wise.com/pay/me/matthiasm1046
[wisebadge]: https://img.shields.io/badge/_wise-me_-blue.svg?style=for-the-badge&logo=wise&logoColor=ccc&link=https%3A%2F%2Fwise.com%2Fpay%2Fme%2Fmatthiasm1046