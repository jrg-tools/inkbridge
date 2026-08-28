#include "InkBridgeSettings.h"

#include <ArduinoJson.h>
#include <Preferences.h>

#include "i18n/I18n.h"

namespace {
constexpr const char* NVS_NAMESPACE = "inkbridge";
}  // namespace

void InkBridgeSettings::load() {
  Preferences prefs;
  prefs.begin(NVS_NAMESPACE, /*readOnly=*/true);
  wifiNetworks = prefs.getString("wifiNetworks", wifiNetworks);
  haHost = prefs.getString("haHost", haHost);
  haPort = prefs.getInt("haPort", haPort);
  haToken = prefs.getString("haToken", "");
  haEntities = prefs.getString("haEntities", haEntities);
  haScripts = prefs.getString("haScripts", haScripts);
  language = prefs.getString("language", language);
  fontFamily = prefs.getString("fontFamily", fontFamily);
  apSsid = prefs.getString("apSsid", apSsid);
  apPassword = prefs.getString("apPassword", "");
  prefs.end();
  I18n::getInstance().setLanguage(language == "es" ? Lang::ES : Lang::EN);
}

void InkBridgeSettings::save() const {
  Preferences prefs;
  prefs.begin(NVS_NAMESPACE, /*readOnly=*/false);
  prefs.putString("wifiNetworks", wifiNetworks);
  prefs.putString("haHost", haHost);
  prefs.putInt("haPort", haPort);
  prefs.putString("haToken", haToken);
  prefs.putString("haEntities", haEntities);
  prefs.putString("haScripts", haScripts);
  prefs.putString("language", language);
  prefs.putString("fontFamily", fontFamily);
  prefs.putString("apSsid", apSsid);
  prefs.putString("apPassword", apPassword);
  prefs.end();
  Serial.println("[Settings] saved");
}

std::vector<String> InkBridgeSettings::entityIds() const {
  std::vector<String> ids;
  int start = 0;
  while (start < (int)haEntities.length()) {
    int comma = haEntities.indexOf(',', start);
    if (comma < 0) comma = haEntities.length();
    String id = haEntities.substring(start, comma);
    id.trim();
    if (id.length()) ids.push_back(id);
    start = comma + 1;
  }
  return ids;
}

std::vector<InkBridgeSettings::ScriptButton> InkBridgeSettings::scripts() const {
  std::vector<ScriptButton> out;
  JsonDocument doc;
  if (deserializeJson(doc, haScripts) != DeserializationError::Ok) return out;

  for (JsonObjectConst entry : doc.as<JsonArrayConst>()) {
    ScriptButton s;
    s.label = entry["label"] | "";
    s.id = entry["id"] | "";
    s.icon = entry["icon"] | "";
    if (s.label.length() && s.id.length()) out.push_back(s);
  }
  return out;
}

std::vector<InkBridgeSettings::WifiNetwork> InkBridgeSettings::wifis() const {
  std::vector<WifiNetwork> out;
  JsonDocument doc;
  if (deserializeJson(doc, wifiNetworks) != DeserializationError::Ok) return out;

  for (JsonObjectConst entry : doc.as<JsonArrayConst>()) {
    WifiNetwork n;
    n.ssid = entry["ssid"] | "";
    n.password = entry["password"] | "";
    if (n.ssid.length()) out.push_back(n);
  }
  return out;
}
