#include "InkBridgeSettings.h"

#include <Preferences.h>

#include "i18n/I18n.h"

namespace {
constexpr const char* NVS_NAMESPACE = "inkbridge";
}  // namespace

void InkBridgeSettings::load() {
  Preferences prefs;
  prefs.begin(NVS_NAMESPACE, /*readOnly=*/true);
  wifiSsid = prefs.getString("ssid", "");
  wifiPassword = prefs.getString("password", "");
  haHost = prefs.getString("haHost", haHost);
  haPort = prefs.getInt("haPort", haPort);
  haToken = prefs.getString("haToken", "");
  haEntities = prefs.getString("haEntities", haEntities);
  language = prefs.getString("language", language);
  apSsid = prefs.getString("apSsid", apSsid);
  apPassword = prefs.getString("apPassword", "");
  prefs.end();
  I18n::getInstance().setLanguage(language == "es" ? Lang::ES : Lang::EN);
}

void InkBridgeSettings::save() const {
  Preferences prefs;
  prefs.begin(NVS_NAMESPACE, /*readOnly=*/false);
  prefs.putString("ssid", wifiSsid);
  prefs.putString("password", wifiPassword);
  prefs.putString("haHost", haHost);
  prefs.putInt("haPort", haPort);
  prefs.putString("haToken", haToken);
  prefs.putString("haEntities", haEntities);
  prefs.putString("language", language);
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
