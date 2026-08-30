# Tellstick (config flow)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=Integration&repository=hass_tellstick&owner=pallemannen)

A fork of Home Assistant core's built-in [`tellstick`](https://www.home-assistant.io/integrations/tellstick/) integration, replacing its YAML-only setup with a proper config flow -- including reconfigure and automatic import of existing `tellstick:` YAML config.

Reuses the same `tellstick` domain as core's integration on purpose: this is meant to *replace* it, not run alongside it. Home Assistant's own domain-uniqueness rules take care of that -- installing this via HACS overrides the core integration.

## Why fork instead of wait for upstream

Core's `tellstick` integration is `quality_scale: legacy` with no config flow, and has been for years. The actual device logic (`tellcore-py` talking to a local `telldusd`) works fine and isn't reimplemented here -- only the setup/config layer changed.

## What's different from core

- **Config flow** for initial setup (checks a `telldusd` is actually reachable before creating the entry, rather than accepting blind YAML).
- **Reconfigure flow** to change host/port and the signal-repetition count without deleting and re-adding the integration.
- **YAML import** -- existing `tellstick:` config is picked up automatically and converted to a config entry, with a repair issue prompting you to remove the YAML afterwards.
- **Local or network `telldusd`.** leave host and port blank to talk to a local `telldusd` directly through USB. Fill in both to reach a `telldusd` over the network (requires `telldusd` to be reachable over TCP). The HA add-on app is reached over the network, and should have been autodiscovered, so just use the suggested values."
- **Sensors are auto-discovered, with confirm/ignore.** Core's `tellstick` sensor platform required pre-declaring every sensor's ID/name via YAML (`only_named`) to limit the list. This fork instead listens live for new sensors and raises a repair issue per newly-heard one -- nothing gets added until you explicitly confirm it, since 433MHz reception is promiscuous and can pick up neighbouring equipment, not just your own.

## Requirements

A TellStick (or TellStick Duo/ZNet) reachable via `telldusd` -- e.g. the [Telldus add-on](https://github.com/michaelarnauts/home-assistant-tellstick-addon) if you're running Home Assistant OS/Supervised, a local USB Tellstick or a networked Tallstick where you setup your own TCP bridge.

## Installation

Via [HACS](https://hacs.xyz/), as a custom repository (category: Integration) pointing at this repo. Then **Settings → Devices & Services → Add Integration → Tellstick**.

## License

MIT - see [LICENSE](LICENSE).
