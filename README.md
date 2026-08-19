# inkbridge

A minimal, always-on **Home Assistant remote control** on an e-ink display. Two mechanical buttons, sub-second feedback, runs for ages on almost no power.

```
┌──────────────────────────────┐
│ Remote              (wifi)HA │
│ ──────────────────────────── │
│ (o) Kitchen              on  │
│ ( ) Living room         off  │
│ [=] Fan                  on  │
│ ──────────────────────────── │
│ [A] next   [B] toggle        │
└──────────────────────────────┘
    ▲ A            ▲ B
```

- Show live entity state from Home Assistant, toggle lights/switches with a button press
- Configure everything (WiFi, HA host/token, entities) from a web UI served by the device itself
- Keeps working when WiFi or HA drop — reconnects with backoff, status shown in the header

Architecture follows [CrossPoint Reader](https://github.com/crosspoint-reader/crosspoint-reader): HAL singletons, an Android-style Activity stack for screens, a persisted settings singleton, and an API-first web server.

## Hardware

| Part | Details |
|---|---|
| MCU | Seeed Studio XIAO ESP32-S3 |
| Display | Waveshare 2.13" e-Paper HAT V4 (250x122, SPI) |
| Input | 2x Cherry MX switches (A/B) |
| Power | USB-C |

### Wiring

| HAT pin | XIAO pin | GPIO | Purpose |
|---|---|---:|---|
| VCC | 3V3 | — | Power |
| GND | GND | — | Ground |
| DIN | D10 | 9 | SPI MOSI |
| CLK | D8 | 7 | SPI clock |
| CS | D1 | 2 | Chip select |
| DC | D2 | 3 | Data/Command |
| RST | D3 | 4 | Reset |
| BUSY | D4 | 5 | Busy status |
| Button A | D6 | 43 | to GND (internal pull-up) |
| Button B | D7 | 44 | to GND (internal pull-up) |

## Using the device

Boot shows the home screen (no radio is started until you pick an option):

- **Generate setup hotspot** — opens the access point `inkbridge-setup`. Join it and open `http://inkbridge.local` (or `http://192.168.4.1`) to configure WiFi, Home Assistant host/port/token, and the entity list. Saving restarts the device. Hold **B** to go back.
- **Connect to saved WiFi** — joins your network and shows the configured entities (the remote).

Button language (everywhere):

| Gesture | Action |
|---|---|
| A short | next / scroll (wraps) |
| A long | jump to top |
| B short | select / toggle |
| B long | back |

## Repository layout

```
lib/hal/                  Hardware abstraction (reusable, app-agnostic)
  HalDisplay              GxEPD2 wrapper; FULL/FAST refresh modes, ghosting cadence
  HalGPIO                 Debounced buttons, short/long-press events
src/
  main.cpp                Globals + setup()/loop()
  InkBridgeSettings       Persisted settings singleton (NVS), SETTINGS macro
  activities/             One screen = one Activity
    Activity, ActivityManager    Lifecycle + deferred screen stack
    UiListActivity               Reusable scrolling-list base
    settings/ network/ remote/     The screens
  components/             UITheme (fonts/metrics), Icons, UiChrome (header/footer/rows)
  homeassistant/          HA REST client (fetch states, toggle services)
  network/                ConfigWebServer (JSON API + static SvelteKit UI)
web/                      SvelteKit config UI (TypeScript, pnpm, adapter-static)
nix/                      Dev environment (flake)
data/                     Staged web build, flashed to LittleFS (generated)
```

## Development

### Environment

Everything is provided by the Nix dev shell (PlatformIO, Node 24, pnpm, clang-format):

```sh
nix develop ./nix
```

First entry bootstraps a `.venv` with PlatformIO Core automatically. Works on Linux (FHS env) and macOS. Without Nix you need: PlatformIO Core, Node.js >= 24, pnpm.

### Quick commands (inside the shell)

| Command | What it does |
|---|---|
| `build-ui` | Build the SvelteKit UI and stage it into `data/` |
| `flash-ui` | `build-ui` + flash the LittleFS partition |
| `flash` | Flash the firmware |
| `flash-monitor` | Flash the firmware + attach the serial monitor |
| `flash-all` | UI + filesystem + firmware + monitor (full deploy) |

First flash on a new board: `flash-all`. Day-to-day firmware work: `flash-monitor`. UI-only change: `flash-ui`.

### Working on the web UI

```sh
cd web
pnpm dev
```

`/api/*` calls are proxied to a real device — defaults to `inkbridge.local`, override with `INKBRIDGE_HOST=192.168.4.1 pnpm dev`. Put the device in Setup mode (or on your LAN) so the API is reachable.

### Web API

The device is API-first; the UI is a static SvelteKit build served from LittleFS. CORS is enabled.

| Endpoint | Method | Description |
|---|---|---|
| `/api/status` | GET | `{version, ip, mode, rssi, freeHeap, uptime}` |
| `/api/settings` | GET | Current settings (secrets omitted) |
| `/api/settings` | POST | JSON body; applies + persists. Secrets only overwritten when present |
| `/api/restart` | POST | Reboot the device |

### Conventions

- C++20, no exceptions in app code, 2-space indent, 120 columns
- `PascalCase` classes (one per file), `camelCase` methods/members, `UPPER_SNAKE_CASE` constants
- `lib/` is hardware-agnostic/reusable; `src/` is app logic
- Screens are Activities: implement `onEnter/onExit/loop/render`, request repaints with `requestUpdate()`; never transition mid-`loop()` — ask `activityManager`
- e-ink discipline: FAST (partial) refresh by default, full refresh every 15 frames to clear ghosting; use `refreshRegion()` when only a row changed

## Roadmap

- [x] M0 — display, buttons, menu
- [x] M1 — WiFi + HA entity state
- [x] M2 — remote control + web config
- [ ] M3 — shopping list (microSD)
- [ ] M4 — OTA updates
