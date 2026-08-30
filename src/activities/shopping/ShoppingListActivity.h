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
// Sync runs once per onEnter(), in the background: fetch the HA list,
// reconcile it against the local list (see reconcile() — a locally-dirty
// item always wins and gets pushed, since HA exposes no per-item timestamp
// to compare against any other way), push what needs pushing, then persist.
// The list stays visible and fully interactive the whole time — nav and
// toggling never block on the network — with a small blinking dot in the
// header (see UiChrome::drawHeader's `syncFrame`) as the only cue a sync is
// still running. A toggle made mid-sync is folded into whatever's still in
// flight: before the HA fetch lands it's just picked up by reconcile() like
// any other locally-dirty item; once pushing has started, onSelectRow()
// queues it itself if it isn't already queued (see loop()'s PUSHING branch).
// If WiFi/HA is unreachable, or no entity is configured, the local cached
// list is still shown/toggleable — this screen's job is the list, not the
// network call. Rows are ordered alphabetically with checked ("already
// bought") items sunk to the bottom (see sortItems()), so the top of the
// list is always what's still left to buy. That ordering is a pure function
// of each item's (checked, text) — not of arrival order — so it comes out
// identical no matter what order onEnter()'s load, a background reconcile(),
// or a toggle produced `items` in; the only thing that ever visibly moves a
// row mid-session is its own checked state crossing the top/bottom split.
//
//   A short: next row   A long: previous row
//   B short: toggle checked (anytime, even mid-sync)   B long: back (any time)
class ShoppingListActivity : public UiListActivity {
 public:
  ShoppingListActivity() : UiListActivity("ShoppingList") {}

  void onEnter() override;
  void onExit() override;
  void loop() override;

 protected:
  int rowCount() const override { return (int)items.size(); }
  void drawRow(int index, int y, bool selected) override;
  // Two lines tall (see drawRow()) — an item name that doesn't fit on one
  // line wraps onto a second instead of getting truncated, since this
  // screen's rows are just item names with no secondary detail line to give
  // up. rowHeight() is uniform across all rows (UiListActivity's scroll math
  // assumes it), so every row gets the two-line box even when an item's
  // name is short enough to fit on one.
  int rowHeight() const override;
  void onSelectRow(int index) override;
  void onBack() override;
  void drawHeader() override {
    UiChrome::drawHeader(TR(SHOPPING_LIST), state == SyncState::DONE ? -1 : spinnerFrame);
  }
  // Only a truly-finished (state == DONE), non-ok sync counts as "failed" —
  // while CONNECTING/PUSHING, syncOk is still false but nothing has failed
  // yet, so the hint would otherwise flash incorrectly during every sync.
  const char* footerLabel() const override {
    return (state == SyncState::DONE && !syncOk) ? TR(SYNC_FAILED_HINT) : nullptr;
  }

 private:
  enum class SyncState { CONNECTING, PUSHING, DONE };

  static constexpr uint32_t SPINNER_TICK_MS = 400;

  void reconcile(const std::vector<HomeAssistantClient::TodoItem>& remote);
  void finishSync();
  // Sorts `items` by (checked, case-insensitive text) — checked items sink
  // to the bottom, and each group is alphabetical. A pure function of the
  // items themselves, not their prior order, so re-running it (as every
  // load, reconcile, and toggle does) never reshuffles anything beyond
  // whatever just changed checked state.
  void sortItems();
  String truncateToWidth(const String& text, int maxWidth) const;
  // Finds the byte offset (always a whole UTF-8 codepoint boundary) where
  // `text` should break so its first line fits within maxWidth — prefers
  // the last space before the break (whole-word wrap), falling back to a
  // straight cut only when there's no space to break at (e.g. one long
  // word/URL).
  int wrapPoint(const String& text, int maxWidth) const;

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
