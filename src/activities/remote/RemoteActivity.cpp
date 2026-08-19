#include "RemoteActivity.h"

#include <ESPmDNS.h>
#include <WiFi.h>

#include "../../InkBridgeSettings.h"
#include "../../components/Icons.h"
#include "../../i18n/I18n.h"
#include "../ActivityManager.h"

void RemoteActivity::onEnter() {
  Activity::onEnter();
  entityIds = SETTINGS.entityIds();

  if (!SETTINGS.hasWifi()) {
    Serial.println("[Remote] no WiFi configured — run setup first");
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(SETTINGS.wifiSsid.c_str(), SETTINGS.wifiPassword.c_str());
  Serial.printf("[Remote] connecting to %s\n", SETTINGS.wifiSsid.c_str());

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) delay(250);

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[Remote] connected, IP %s\n", WiFi.localIP().toString().c_str());
    MDNS.begin("inkbridge");
  } else {
    Serial.println("[Remote] WiFi connect failed, will retry in loop");
  }

  haClient.begin(SETTINGS.haHost, SETTINGS.haPort, SETTINGS.haToken);
  syncEntities();
}

void RemoteActivity::onExit() {
  MDNS.end();
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  Activity::onExit();
}

void RemoteActivity::maintainWifi() {
  if (!SETTINGS.hasWifi()) return;
  if (WiFi.status() == WL_CONNECTED) {
    wifiBackoffMs = 5000;
    return;
  }
  if (millis() - lastWifiAttemptMs < wifiBackoffMs) return;
  lastWifiAttemptMs = millis();
  wifiBackoffMs = min<uint32_t>(wifiBackoffMs * 2, 60000);  // exponential backoff
  Serial.println("[Remote] WiFi reconnecting...");
  WiFi.disconnect();
  WiFi.begin(SETTINGS.wifiSsid.c_str(), SETTINGS.wifiPassword.c_str());
}

void RemoteActivity::syncEntities() {
  if (WiFi.status() != WL_CONNECTED) return;
  std::vector<HomeAssistantClient::Entity> fresh;
  bool ok = haClient.fetch(entityIds, fresh);

  bool changed = fresh.size() != entities.size();
  for (size_t i = 0; !changed && i < fresh.size(); i++) {
    changed = fresh[i].state != entities[i].state;
  }
  entities = std::move(fresh);
  if (changed || !ok) requestUpdate();
}

void RemoteActivity::loop() {
  maintainWifi();
  if (millis() - lastSyncMs > SYNC_INTERVAL_MS) {
    lastSyncMs = millis();
    syncEntities();
  }
  UiListActivity::loop();  // A/B navigation
}

void RemoteActivity::onSelectRow(int index) {
  auto& entity = entities[index];
  if (!haClient.toggle(entity)) return;

  // Optimistic update for instant feedback; next sync corrects if needed.
  entity.state = (entity.state == "on") ? "off" : "on";
  lastSyncMs = millis();

  // Only the toggled row changed — refresh just its region (~150ms).
  display.refreshRegion(0, rowY(index), display.width(), UITheme::ROW_H,
                        [this] { render(); });
}

void RemoteActivity::onBack() { activityManager.popActivity(); }

void RemoteActivity::drawRow(int index, int y, bool rowSelected) {
  auto& g = display.gfx();
  const auto& e = entities[index];
  bool on = e.state == "on";
  uint16_t fg = rowSelected ? GxEPD_WHITE : GxEPD_BLACK;

  int x = 4, w = g.width() - 12, h = UITheme::ROW_H - 3;
  UiChrome::drawRowButton(x, y, w, h, rowSelected);

  // Domain icon at the left edge; on/off state is conveyed by the icon.
  int iconCx = x + 13, iconCy = y + h / 2;
  if (e.id.startsWith("light.")) {
    Icons::bulb(g, iconCx, iconCy, 6, fg, on);
  } else if (e.id.startsWith("switch.")) {
    Icons::toggle(g, iconCx, iconCy, 6, fg, on);
  }

  // Name centered in the remaining space (portrait is narrow — keep short).
  char nameBuf[12];
  snprintf(nameBuf, sizeof(nameBuf), "%.11s", e.name.c_str());
  int labelX = x + 24;
  UiChrome::drawButtonLabel(labelX, y, w - 24 - 4, h, nameBuf, rowSelected);
}

const char* RemoteActivity::emptyText() const {
  if (!SETTINGS.hasWifi()) return TR(NO_WIFI_CONFIGURED);
  return WiFi.status() == WL_CONNECTED ? TR(SYNCING_HA) : TR(WIFI_SEARCHING);
}
