# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.3.0] - 2026-08-30

### Added
- Each sensor device now has a diagnostic "Last seen" timestamp entity, the newest timestamp across every datatype that sensor reports -- useful for spotting a dead/silent sensor (e.g. a flat battery), since the value entities themselves just keep showing their last known reading forever.
- Each sensor device's protocol/model/id are now also set as its manufacturer/model/serial_number, so that identity stays visible on the device page even after renaming the device to something meaningful (e.g. "Guest room") -- previously it only existed in the auto-generated device name, which renaming would overwrite.

## [0.2.2] - 2026-08-30

### Fixed
- Declared `hassio` in `after_dependencies` -- the add-on-detection code (see 0.2.0/0.2.1) imports from `homeassistant.components.hassio`, which hassfest correctly flags as an undeclared dependency if missing. `after_dependencies` (not `dependencies`) since this integration still needs to work fine on non-Supervisor installs where `hassio` isn't available at all.

## [0.2.1] - 2026-08-30

### Added
- The setup form now suggests the two connection ports (50800/50801) unconditionally in network mode, not just when a TellStick-like add-on is detected -- they're the michaelarnauts add-on's fixed, non-configurable socat-bridge ports, a reasonable default for network mode generally, and this way the ports still show something sensible even if the add-on-detection lookup (see 0.2.0, for the host suggestion) doesn't find a match. Still just a suggestion, not forced.

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
- Live sensor auto-discovery: New sensors are detected via `telldusd`'s real event stream and raised as a repair issue requiring explicit confirm-or-ignore, rather than silently added — 433 MHz reception is promiscuous and can pick up neighbouring equipment.
- Brand icons.

### Notes
- Switches/lights/covers are unchanged from core's behavior — they auto-discover from whatever the Tellstick add-on's own device configuration already defines; this fork doesn't touch that path.
- Untested against real hardware as of this release — built and self-verified against Home Assistant's actual current source, but discovery, network mode, and reconfigure all still need a real TellStick to confirm.
