#include "InkBridgeSettings.h"

#include <ArduinoJson.h>
#include <Preferences.h>

#include <memory>

#include "i18n/I18n.h"

namespace {
constexpr const char* NVS_NAMESPACE = "inkbridge";
}  // namespace

namespace {
// shoppingItems can approach the ~4000 byte ceiling nvs_set_str enforces, so
// it's stored via putBytes/getBytes (blob API, chunked across pages up to
// ~508000 bytes) instead of putString/getString. The JSON text itself is
// unchanged — just a different NVS read/write path.
String getBytesAsString(Preferences& prefs, const char* key, const String& fallback) {
  size_t len = prefs.getBytesLength(key);
  if (!len) return fallback;
  std::unique_ptr<char[]> buf(new char[len]);
  prefs.getBytes(key, buf.get(), len);
  return String(buf.get(), len);
}
}  // namespace

void InkBridgeSettings::load() {
  Preferences prefs;
  prefs.begin(NVS_NAMESPACE, /*readOnly=*/true);
  wifiNetworks = prefs.getString("wifiNetworks", wifiNetworks);
  haHost = prefs.getString("haHost", haHost);
  haPort = prefs.getInt("haPort", haPort);
  haToken = prefs.getString("haToken", "");
  haScripts = prefs.getString("haScripts", haScripts);
  shoppingListEnabled = prefs.getBool("shopEnabled", shoppingListEnabled);
  haShoppingListEntity = prefs.getString("haShopEntity", haShoppingListEntity);
  language = prefs.getString("language", language);
  fontFamily = prefs.getString("fontFamily", fontFamily);
  apSsid = prefs.getString("apSsid", apSsid);
  apPassword = prefs.getString("apPassword", "");
  shoppingItems = getBytesAsString(prefs, "shopItems", shoppingItems);
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
  prefs.putString("haScripts", haScripts);
  prefs.putBool("shopEnabled", shoppingListEnabled);
  prefs.putString("haShopEntity", haShoppingListEntity);
  prefs.putString("language", language);
  prefs.putString("fontFamily", fontFamily);
  prefs.putString("apSsid", apSsid);
  prefs.putString("apPassword", apPassword);
  prefs.end();
  Serial.println("[Settings] saved");
}

void InkBridgeSettings::saveShoppingList() const {
  Preferences prefs;
  prefs.begin(NVS_NAMESPACE, /*readOnly=*/false);
  prefs.putBytes("shopItems", shoppingItems.c_str(), shoppingItems.length());
  prefs.end();
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

std::vector<InkBridgeSettings::ShoppingItem> InkBridgeSettings::shoppingList() const {
  std::vector<ShoppingItem> out;
  JsonDocument doc;
  if (deserializeJson(doc, shoppingItems) != DeserializationError::Ok) return out;

  for (JsonObjectConst entry : doc.as<JsonArrayConst>()) {
    ShoppingItem item;
    item.uid = entry["uid"] | "";
    item.text = entry["text"] | "";
    item.checked = entry["checked"] | false;
    item.dirty = entry["dirty"] | false;
    if (item.uid.length()) out.push_back(item);
  }
  return out;
}

void InkBridgeSettings::setShoppingList(const std::vector<ShoppingItem>& items) {
  JsonDocument doc;
  JsonArray arr = doc.to<JsonArray>();
  for (const auto& item : items) {
    JsonObject o = arr.add<JsonObject>();
    o["uid"] = item.uid;
    o["text"] = item.text;
    o["checked"] = item.checked;
    o["dirty"] = item.dirty;
  }
  String out;
  serializeJson(arr, out);
  shoppingItems = out;
}
