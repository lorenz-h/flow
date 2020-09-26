# flow
A webservice that optimizes the use of photovoltaic power to charge of electric cars. This repo was developed for a setup with a Tesla Powerwall, a Keba P30 C-series Wallbox,
a BMW i3 and an Audi E-Tron. While the service would require some tweaking to work with other setups, some of the individual modules may be helpful.

<img src="/screenshot.png" width="70%" style="display: block; margin-left: auto; margin-right: auto;">

## Modules
The API is structured in different object-oriented Modules, some of which run their own background tasks in seperate threads.
### Connected Drive Cache
This module acts as a simple caching layer for BMW's Connected Drive API. Moreover, it translates the users generic flow vehicle API calls into BMW's specific API.
The Connected Drive API is accessed through the [bimmer_connected](https://github.com/bimmerconnected/bimmer_connected) package.

### Keba Rest
This module communicates with a Keba P30 C-series Wallbox via UDP and offers access to some of the wallbox functions as a REST API. Among other things it can query the power consumption
of the wallbox, as well as set the desired charging current.

### Billing
The billing module constantly queries the Keba Rest module for charging sessions and stores them on disk. If requested it can create itemized power bills filtered by RFID tag and date.

### Manager
The manager module integrates the information obtained by the other modules. It calculates charging currents based on the current photovoltaic yield, the level of the Tesla Powerwall and the SOC of the connected vehicle.

### Audi Cache
The audi cache module should work very similar to the connected drive module. However, Audi is currently changing their API quite frequently which makes it difficult to provide reliable service.

