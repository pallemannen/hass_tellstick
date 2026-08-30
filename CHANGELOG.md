# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2026-08-30

### Added
- Initial fork of Home Assistant core's YAML-only `tellstick` integration, adding a config flow. Reuses the `tellstick` domain intentionally (replacement, not coexistence with core's version).
- Config flow supports both local (`telldusd` on the same host) and network (host/port, e.g. a `telldusd` running in its own add-on/container) connections, as an optional pair matching the original YAML schema.
- Reconfigure flow, for changing host/port and signal-repetition count without removing and re-adding the integration.
- YAML import flow, automatically migrating existing `tellstick:` config into a config entry with a repair-issue prompt to remove the old YAML.
- Live sensor auto-discovery: new sensors are detected via `telldusd`'s real event stream and raised as a repair issue requiring explicit confirm-or-ignore, rather than silently added — 433 MHz reception is promiscuous and can pick up neighbouring equipment.
- Brand icons.

### Notes
- Switches/lights/covers are unchanged from core's behavior — they auto-discover from whatever the Tellstick add-on's own device configuration already defines; this fork doesn't touch that path.
- Untested against real hardware as of this release — built and self-verified against Home Assistant's actual current source, but discovery, network mode, and reconfigure all still need a real TellStick to confirm.
