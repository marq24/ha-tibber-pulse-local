# Home Assistant Integration for your Tibber Pulse (connected via Tibber Bridge) LOCAL-POLLING


## Installation

### Hacs

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

- Install [Home Assistant Community Store (HACS)](https://hacs.xyz/)
- Add custom repository https://github.com/marq24/ha-tibber-pulse-local to HACS
- Add integration repository (search for "Tibber Pulse Local" in "Explore & Download Repositories")
    - Select latest version or `master`
- Restart Home Assistant to install all dependencies

### Manual

- Copy all files from `custom_components/tibber/` to `custom_components/tibber/` inside your config Home Assistant
  directory.
- Restart Home Assistant to install all dependencies

### Adding or enabling integration

#### My Home Assistant (2021.3+)

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tibber)

#### Manual
