# Stecagrid
Home Assistant custom integration for reading information from Steca StecaGrid inverters with proprietary RS485 protocol (like ex. the StecaGrid 8000+ 3ph)

[![BuyMeCoffee][buymecoffeebadge]][michaeloe-buymecoffee]

## Target
The project is meant to get current power production from a StecaGrid 8000+ 3ph solar inverter

## Method
I used a cheap LAN-to-RS485 converter to connect to the inverter - https://raspberrypi.dk/produkt/rs485-til-ethernet-converter-til-eu/

## Sensors
Several sensors from the inverter is exposed, including:
- Current ouptut power to grid
- Current panel power
- Current panel voltage
- Current panel current
- Todays total output
- Lifetime total AC energy (kWh), read directly from inverter (service `0x64`, topic `0xF1`). Exposed with `total_increasing` statistics for the Home Assistant Energy dashboard. If the inverter does not support this query or communication fails, this sensor is unavailable instead of reporting a false zero.

![billede](https://github.com/user-attachments/assets/9cd77002-f1f3-4711-b854-1526972bef73)

## Credits
The physical connection I got information from here: https://svgroeneveld.blogspot.com/2015/08/communication-with-inverter.html

I got inspiration from this Arduino project: https://github.com/tsybolek/Aquarea_Stecagrid_Modbus_NodeMCU/blob/master/aquarea_steca_modbus_public.ino

[buymecoffeebadge]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
[michaeloe-buymecoffee]: https://buymeacoffee.com/michaeloe

## Installation with HACS

Add `michlimek/homeassistant-stecagrid` as a **custom integration repository** in HACS, download the latest version, and restart Home Assistant. The repository includes a root `hacs.json` for branch/commit downloads. HACS releases are optional; when no release is published, HACS tracks the default branch commit. Current integration version: **1.0.5**.

### Serial/TCP diagnostics

Each inverter measurement is polled independently with a 2.5-second timeout. Failed individual readings become unavailable without replacing other sensors with zero. The integration logs changed failure details at warning level (enable debug logging for individual query durations). Steca frames are reassembled using their declared length, avoiding incomplete TCP reads. Some earlier decoder branches still need verification against real inverter replies; in particular the lifetime counter support must be confirmed on StecaGrid 8000+.

### Nighttime when the inverter powers down

When the inverter no longer answers and Home Assistant's `sun.sun` is `below_horizon`, instantaneous AC/DC power and panel current report `0` rather than keeping the last positive sample. During the day, or if `sun.sun` is not available, missing measurements are `unavailable` so a network fault is not mistaken for zero generation. Fresh readings are always preferred. Daily and lifetime energy counters, inverter timestamp and voltage are never synthesized; unavailable readings stay unavailable. The Sun integration must be configured in HA for this fallback.
