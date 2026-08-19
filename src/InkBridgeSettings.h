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

  String wifiSsid;
  String wifiPassword;
  String haHost = "homeassistant.local";
  int haPort = 8123;
  String haToken;
  // Comma-separated entity ids to show on the remote screen.
  String haEntities = "light.kitchen,light.living_room,switch.fan";
  // UI language code ("en", "es"); applied to I18n on load.
  String language = "en";
  // Setup hotspot credentials. Password is generated once on first hotspot
  // start and persisted; both are editable via the web API (settings group).
  String apSsid = "inkbridge";
  String apPassword;

  void load();
  void save() const;

  bool hasWifi() const { return wifiSsid.length() > 0; }
  std::vector<String> entityIds() const;

 private:
  InkBridgeSettings() = default;
};

#define SETTINGS InkBridgeSettings::getInstance()
