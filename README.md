[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
# hass-smartbroker
A custom component to integrate your [Smartbroker](https://smartbroker.de/) securities account into Home Assistant.

The component scrapes the Smartbroker website and adds all clearing and securities accounts as sensors.

# Installation
Can be installed through [HACS](https://hacs.xyz) or by copying all files from `custom_components/smartbroker/` to `<config directory>/custom_components/smartbroker`.

# Configuration
* Go to integrations and search for "Smartbroker"
* Enter your credentials
* All your accounts should now be added as sensor entities with names `sensor.smartbroker_<account number>`
