# inkbridge

A minimal, always-on **Home Assistant script launcher** on an e-ink display. Two mechanical buttons, sub-second feedback, runs for ages on almost no power.

```
┌──────────────────────────────┐
│                           (》)│
│                                │
│   ┌────────┐    ┌────────┐   │
│   │  bulb  │    │  wifi  │   │
│   │ Sleep  │    │Transfer│   │
│   └────────┘    └────────┘   │
│                                │
│ ──────────────────────────── │
│  A                      ▲ ▼  │
│                    "Sleep"    │
└──────────────────────────────┘
```

- A 2-column grid of icon-only buttons — each one a script configured in Home Assistant (lights, scenes, "goodnight" routines, whatever you script). Press it, it runs, done.
- Configure everything — WiFi networks (with automatic fallback), Home Assistant host/token, the script buttons and their icons, hotspot credentials, language, even the device's font — from a web UI the device serves itself.
- Multiple saved WiFi networks: tried in priority order until one connects, so it isn't stuck if you move it between locations.
- Idle **light sleep** after 5 minutes on any screen except while the config web UI is being used, waking instantly on either button. The header shows a small status icon (moon = about to nap, lightning = USB connected) that stays in sync even without touching a button.

Architecture follows [CrossPoint Reader](https://github.com/crosspoint-reader/crosspoint-reader): HAL singletons, an Android-style Activity stack for screens, a persisted settings singleton, an API-first web server, and — for the icon set — the same idea of rasterizing stock [Lucide](https://lucide.dev) icons to 1-bit bitmaps rather than hand-drawing vector shapes.

## Hardware

| Part | Details |
|---|---|
| MCU | Seeed Studio XIAO ESP32-S3 |
| Display | Waveshare 2.13" e-Paper HAT V4 (250x122, SPI) |
| Input | 2x Cherry MX switches (A/B) |
| Power | USB-C, EEMB 603449 LiPo (3.7V, 1100mAh) |

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

### Power

- **Idle light sleep**: after 5 minutes untouched, the device drops into light sleep (`esp_light_sleep_start`) and wakes instantly on either button press. Skipped while the config web server is running (AP setup or a connected WiFi session), so it never naps mid-configuration.
- **No deep sleep**: true deep sleep wakeup (`ext0`/`ext1`) needs RTC-capable GPIOs (0–21 on the S3); the buttons are wired to GPIO43/44 (the UART pins), which aren't RTC pins. Light sleep's GPIO wakeup works on any digital pin instead, and has the added benefit of preserving all RAM state across the nap.
- **Rough battery life**: active draw is tens of mA; light sleep drops that to roughly 0.25–1 mA. At typical "check it a dozen-ish times a day" usage, that's on the order of 2–3 weeks per charge; left almost untouched, more like a month or two. Frequent short interactions cost more than you'd expect, since each one keeps it awake for the full 5-minute idle window afterward, not just the interaction itself.
- **Charging**: the XIAO's onboard charge management fast-charges at a fixed 100mA regardless of what the USB-C source can supply. For the 1100mAh cell here, that's roughly **11–14 hours** empty to full.
- No software-readable charging-status or battery-voltage pin exists on stock XIAO ESP32-S3 wiring — the header's lightning-bolt icon reflects "USB host connected" (native-USB frame detection), not literal charge state, and won't fire for a dumb USB-C power brick with no data lines.

## Using the device

Boot goes straight to the main menu — no radio starts until you pick something:

- **Script buttons**: each one configured in the web UI (label, HA script ID, icon) shows up as an icon-only square. Pressing it joins WiFi (trying each saved network in order), calls `script.turn_on` for that script's entity, and returns to the menu — a spinner is the only feedback while it works, and the footer shows its name while it's selected.
- **Transfer**: opens WiFi/hotspot connectivity —
  - *Setup hotspot* opens the access point `inkbridge-setup`. Join it, then open `http://inkbridge.local` (or `http://192.168.4.1`) to configure WiFi networks, Home Assistant host/token, scripts, hotspot, language, and font. Saving restarts the device.
  - *Connect WiFi* joins a saved network (again trying each until one connects) and starts the same config web server on your LAN — the screen then shows a QR code plus the mDNS name and IP to reach it from a browser. It does nothing else; no on-device entity control.

Button language (everywhere):

| Gesture | Action |
|---|---|
| A short | next row (wraps) |
| A long | previous row (wraps) |
| B short | select / run |
| B long | back |

The footer always shows a bold **A** (bottom-left, the action button) and up/down chevrons (bottom-right, the move button); on the main menu it also centers the currently selected item's name.

## Repository layout

```
lib/hal/                    Hardware abstraction (reusable, app-agnostic)
  HalDisplay                  GxEPD2 wrapper; FULL/FAST/region refresh, ghosting cadence
  HalGPIO                      Debounced buttons, short/long-press events, sleep-wakeup arming
scripts/
  gen_icons.py                 Rasterizes stock Lucide SVGs into 1-bit icon bitmaps
src/
  main.cpp                     Globals + setup()/loop(); idle-sleep + header status-icon polling
  InkBridgeSettings             Persisted settings singleton (NVS), SETTINGS macro
  Version.h                     Firmware version string
  IdleSleep.h                   Shared idle-timeout/warning-window constants and clock
  activities/                   One screen = one Activity
    Activity, ActivityManager     Lifecycle + deferred screen stack
    UiListActivity                 Reusable scrolling-list base
    menu/                           MainMenuActivity — the 2-column script/Transfer grid
    transfer/ network/ scripts/     Transfer menu, WiFi/hotspot screens, script-run screen
  components/                   UITheme (fonts/metrics), Icons + icons/IconBitmaps.h,
                                  UiChrome (header/footer/rows), QrCode (QR rendering)
  homeassistant/                 HA REST client — runs a script via script.turn_on
  network/                       ConfigWebServer (JSON API + static SvelteKit UI),
                                  WifiConnector (multi-network fallback)
  i18n/                          I18n singleton + EN/ES string table
web/                          SvelteKit config UI (TypeScript, pnpm, adapter-static, @lucide/svelte icon picker)
nix/                          Dev environment (flake)
data/                         Staged web build, flashed to LittleFS (generated)
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

`pnpm check` type-checks the app; `pnpm build` produces the static site; `pnpm deploy` does both and stages the result into `../data` (equivalent to the `build-ui` shell command above).

### Regenerating icons

Device icons are real [Lucide](https://lucide.dev) glyphs rasterized to 1-bit bitmaps (`src/components/icons/IconBitmaps.h`) — no hand-drawn vector shapes, no SVG rendering on-device. To add or change one, edit the `ICONS` list in `scripts/gen_icons.py` (path/circle/rect data, easiest lifted from `@lucide/svelte`'s source under `web/node_modules`) and rerun:

```sh
python3 scripts/gen_icons.py
```

Requires ImageMagick (`magick`) on `PATH` for SVG rasterization. Writes straight back into `src/components/icons/IconBitmaps.h` — don't hand-edit that file. If the icon is meant to be selectable from a script button, also add it to `ICON_OPTIONS` in `web/src/routes/+page.svelte` and to `Icons::byKey()` in `src/components/Icons.h`.

### Web API

The device is API-first; the UI is a static SvelteKit build served from LittleFS. CORS is enabled.

| Endpoint | Method | Description |
|---|---|---|
| `/api/status` | GET | `{version, ip, mode, rssi, freeHeap, uptime}` |
| `/api/settings` | GET | Current settings (secrets omitted; WiFi networks return SSID only) |
| `/api/settings` | POST | JSON body; applies + persists. Secrets/passwords only overwritten when present — matched by SSID for WiFi networks, so leaving a password blank keeps the stored one |
| `/api/restart` | POST | Reboot the device |

Settings are grouped as `transfer` (`wifiNetworks: [{ssid, password}]`, `haHost`, `haPort`, `haToken`, `haScripts: [{label, id, icon}]`) and `settings` (`language`, `fontFamily`, `apSsid`, `apPassword`).

### Conventions

- C++20, no exceptions in app code, 2-space indent, 120 columns
- `PascalCase` classes (one per file), `camelCase` methods/members, `UPPER_SNAKE_CASE` constants
- `lib/` is hardware-agnostic/reusable; `src/` is app logic
- Screens are Activities: implement `onEnter/onExit/loop/render`, request repaints with `requestUpdate()`; never transition mid-`loop()` — ask `activityManager`
- e-ink discipline: FAST (partial) refresh by default, full refresh every 15 frames to clear ghosting; use `refreshRegion()` when only a small area changed

## Roadmap

- [x] M0 — display, buttons, menu
- [x] M1 — WiFi (multi-network fallback) + Home Assistant
- [x] M2 — script launcher + web config + idle sleep
- [ ] M3 — shopping list (microSD)
- [ ] M4 — OTA updates
