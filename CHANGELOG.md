# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.2.0] - 2026-08-30

### Added
- The setup form now suggests a host automatically when a TellStick-like add-on is installed under Supervisor (matched by slug suffix `_tellstick`, converted to its network hostname) — one less thing to look up manually for the common case of connecting to the Telldus add-on's own network-bridged `telldusd`. Only a suggestion, not forced; still leave host/port blank for local mode. Has no effect on non-Supervisor installs (HA Container/Core).

## [0.1.1] - 2026-08-30

### Fixed
- The network-mode connection form crashed on open with "Config flow could not be loaded: 500 Internal Server Error" — the `port` field's schema (`vol.All(cv.ensure_list, [cv.port], vol.Length(min=2, max=2))`, ported directly from the original YAML schema) isn't something Home Assistant's frontend can serialize into a form field, only something plain YAML validation can use. Split into two separate scalar fields (client port, events port) in the interactive form; internally still combined into the same `[client, events]` list this integration always used, so entry storage and the YAML import path are unaffected.

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
