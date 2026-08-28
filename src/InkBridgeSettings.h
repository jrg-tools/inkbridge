#pragma once
#include <Arduino.h>

#include <vector>

// Persisted device settings, CrossPointSettings-style singleton.
// Backed by NVS (Preferences) until an SD card is wired up.
class InkBridgeSettings {
 public:
  static InkBridgeSettings& getInstance() {
    static InkBridgeSettings instance;
    return instance;
  }

  // A WiFi network to try. Tried in order (see wifis()) until one connects.
  struct WifiNetwork {
    String ssid;
    String password;
  };
  // JSON array of WifiNetwork, configured via the web UI's Wi-Fi section.
  String wifiNetworks = "[]";

  String haHost = "homeassistant.local";
  int haPort = 8123;
  String haToken;
  // Comma-separated entity ids (reserved for future device-side use).
  String haEntities = "light.kitchen,light.living_room,switch.fan";

  // A script quick-action button shown in the main menu's Scripts list.
  // `id` is the part after "script." — run via script.turn_on + entity_id.
  // `icon` selects a built-in device icon ("bulb"/"toggle"/"moon"/"bolt";
  // unknown/empty falls back to "bolt").
  struct ScriptButton {
    String label;
    String id;
    String icon;
  };
  // JSON array of ScriptButton, configured via the web UI (Scripts section).
  String haScripts = "[]";
  // UI language code ("en", "es"); applied to I18n on load.
  String language = "en";
  // Device font family: "notosans" (default) / "helvetica" / "lucida" /
  // "schoolbook"; applied via UITheme::applyFontFamily() on load.
  String fontFamily = "notosans";
  // Setup hotspot credentials. Password is generated once on first hotspot
  // start and persisted; both are editable via the web API (settings group).
  String apSsid = "inkbridge";
  String apPassword;

  void load();
  void save() const;

  bool hasWifi() const { return !wifis().empty(); }
  std::vector<String> entityIds() const;
  std::vector<ScriptButton> scripts() const;
  std::vector<WifiNetwork> wifis() const;

 private:
  InkBridgeSettings() = default;
};

#define SETTINGS InkBridgeSettings::getInstance()
