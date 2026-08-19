#pragma once
#include <vector>

#include "../../homeassistant/HomeAssistantClient.h"
#include "../UiListActivity.h"

// Remote control screen: joins the saved WiFi and shows/toggles HA entities.
//   A short: next entity   A long: jump to top
//   B short: toggle        B long: back to menu
class RemoteActivity : public UiListActivity {
 public:
  RemoteActivity() : UiListActivity("Remote") {}

  void onEnter() override;
  void onExit() override;
  void loop() override;

 protected:
  int rowCount() const override { return entities.size(); }
  void drawRow(int index, int y, bool selected) override;
  void onSelectRow(int index) override;
  void onBack() override;
  const char* emptyText() const override;

 private:
  static constexpr uint32_t SYNC_INTERVAL_MS = 5000;

  void syncEntities();
  void maintainWifi();

  HomeAssistantClient haClient;
  std::vector<String> entityIds;
  std::vector<HomeAssistantClient::Entity> entities;
  uint32_t lastSyncMs = 0;
  uint32_t lastWifiAttemptMs = 0;
  uint32_t wifiBackoffMs = 5000;
};
