#pragma once
#include <vector>

#include "../../InkBridgeSettings.h"
#include "../../homeassistant/HomeAssistantClient.h"
#include "../../network/WifiConnector.h"
#include "../UiListActivity.h"

// Mirrors an HA `todo` list locally and lets you check/uncheck items with
// only two buttons — no on-device add/remove/rename (there's no on-device
// text entry anywhere in this codebase; item existence is always HA's call).
//
// Sync runs once per onEnter(): fetch the HA list, reconcile it against the
// local list (see reconcile() — a locally-dirty item always wins and gets
// pushed, since HA exposes no per-item timestamp to compare against any
// other way), push what needs pushing, then persist. If WiFi/HA is
// unreachable, or no entity is configured, the local cached list is still
// shown/toggleable — this screen's job is the list, not the network call.
//
//   A short: next row   A long: previous row
//   B short: toggle checked (once synced)   B long: back (any time)
class ShoppingListActivity : public UiListActivity {
 public:
  ShoppingListActivity() : UiListActivity("ShoppingList") {}

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render() override;

 protected:
  int rowCount() const override { return (int)items.size(); }
  void drawRow(int index, int y, bool selected) override;
  void onSelectRow(int index) override;
  void onBack() override;
  void drawHeader() override { UiChrome::drawHeader(TR(SHOPPING_LIST)); }
  const char* footerLabel() const override { return syncOk ? nullptr : TR(SYNC_FAILED_HINT); }

 private:
  enum class SyncState { CONNECTING, PUSHING, DONE };

  static constexpr uint32_t SPINNER_TICK_MS = 400;

  void reconcile(const std::vector<HomeAssistantClient::TodoItem>& remote);
  void finishSync();
  String truncateToWidth(const String& text, int maxWidth) const;

  HomeAssistantClient haClient;
  WifiConnector connector;
  std::vector<InkBridgeSettings::ShoppingItem> items;
  std::vector<String> pushQueue;  // uids still needing todo.update_item
  size_t pushIndex = 0;
  SyncState state = SyncState::DONE;
  bool syncOk = false;
  uint32_t lastSpinnerTickMs = 0;
  int spinnerFrame = 0;
};
