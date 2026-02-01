# Setting Up the Tibber Bridge for Non-Tibber Customers

If you have a Tibber Bridge (and IR sensor) and are not a Tibber customer anymore, you can still use the Tibber Bridge to get the grid meter readings into you HA.

## MQTT Settings

It's crucial that you have a valid mqtt configuration.
The Tibber Bridge must be able to send mqtt data somewhere.
Otherwise it believes something is wrong and does not stay in your Wifi after you have performed the normal setup.
Instead, it reverts to creating a Wifi access point.
Normally, it sends the data to some mqtt server of Tibber.
If you are not a customer of Tibber anymore, maybe you don't want that.
For this, you can set up a new or use your own existing mqtt server ( e.g. a [mosquitto](https://mosquitto.org) in your local network).

Here is an example mqtt section of the params:

```
mqtt_param:
   5  ca_cert                       : '-----BEGIN CERTIFICATE-----\r\nMIIDQTCCAimgAwIBAgITB' concatenated 1208 bytes.
   6  certificate                   : '-----BEGIN CERTIFICATE-----\r\nMIIDWTCCAkGgAwIBAgIUd' concatenated 1238 bytes.
   7  private_key                   : '' 0 bytes.
   8  mqtt_url                      : '<some ip>' 14 bytes.
   9  mqtt_topic                    : 'tibber-bridge/data/publish' 26 bytes.
   10 mqtt_topic_sub                : 'tibber-bridge/data/receive' 26 bytes.
   11 mqtt_port                     : '1883' 4 bytes.
   12 mqtt_valid                    : true
   23 mqtt_pause                    : false
   42 mqtt_client_id                : '<some id>' 13 bytes.
```

You don't need to use the information that are supplied via mqtt, it's all just to make the Tibber Bridge happy.

## Step-by-Step

1. Reset your Tibber Bridge by plugging/unplugging it 10 times.
LED is green now.

1. Sometimes, now the params tab is empty and no file upload works.
With [this cool method](https://www.photovoltaikforum.com/thread/197149-tibber-pulse-einrichtung-installation-geht-nicht/?postID=4199269#post4199269) you can get back to a functioning Tibber bridge.
Only do this is your params tab is empty.

1. Check the params.
If there is data in the params `ca_crt` and `certificate` you are good.
They are a root certificate and an IoT certificate.
If these fields are empty, you must create new values for them.
You can [use](https://docs.aws.amazon.com/iot/latest/developerguide/device-certs-create.html) e.g. the IoT Console of an AWS Free Tier account for this.
This should be free (no guarantee though!).
There is no need to activate them or attach policies - they are never really used.
Paste the content of the generated `*-certificate.pem.crt` file to the `certificate` field and the content of the `AmazonRootCA1.pem` file to the `ca_cert` field.

1. Put address and port of your mqtt server into `mqtt_url` resp. `mqtt_port`.

1. Set `mqtt_topic` and `mqtt_topic_sub` to values of your choice. I used `tibber-bridge/data/publish` resp. `tibber-bridge/data/receive`.

1. Make sure your Wifi data in `ssid` and `psk` is correct and that `webserver_force_enable` is `true`.

1. Don't forget to hit `save` for each modified parameter and hit `Save and update params` at the bottom after all this.

1. Go to the console and execute `param set mqtt_valid true`, `param_set wifimode 1` and `param_store`.

1. Execute `reboot` in the console or unplug/plug your Tibber bridge once.

1. Now the Tibber Bridge shows in your Wifi and and stays there.
You can do things like pairing a IR sensor now and wiggling the IR sensor until you have good readings and so on.
