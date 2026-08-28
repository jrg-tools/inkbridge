#include "ShoppingListActivity.h"

#include <HalGPIO.h>
#include <WiFi.h>

#include <algorithm>

#include "../../components/Icons.h"
#include "../../components/UiChrome.h"
#include "../../components/UITheme.h"
#include "../../i18n/I18n.h"
#include "../ActivityManager.h"

void ShoppingListActivity::onEnter() {
  Activity::onEnter();
  items = SETTINGS.shoppingList();
  sortItems();
  pushQueue.clear();
  pushIndex = 0;
  syncOk = false;
  selected = 0;
  scrollOffset = 0;

  if (!SETTINGS.haShoppingListEntity.length()) {
    state = SyncState::DONE;
    return;
  }

  connector.begin();
  state = connector.status() == WifiConnector::Status::NO_NETWORKS ? SyncState::DONE
                                                                    : SyncState::CONNECTING;
}

void ShoppingListActivity::onExit() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  Activity::onExit();
}

void ShoppingListActivity::onBack() { activityManager.popActivity(); }

void ShoppingListActivity::loop() {
  if (gpio.wasLongPressed(HalGPIO::BTN_B)) {
    onBack();
    return;
  }

  if (state == SyncState::DONE) {
    UiListActivity::loop();
    return;
  }

  if (state == SyncState::CONNECTING) {
    auto status = connector.update();
    if (status == WifiConnector::Status::CONNECTED) {
      haClient.begin(SETTINGS.haHost, SETTINGS.haPort, SETTINGS.haToken);
      std::vector<HomeAssistantClient::TodoItem> remote;
      if (haClient.getTodoItems(SETTINGS.haShoppingListEntity, remote)) {
        reconcile(remote);
        sortItems();
        if (pushQueue.empty()) {
          finishSync();
          syncOk = true;
          state = SyncState::DONE;
        } else {
          state = SyncState::PUSHING;
        }
      } else {
        syncOk = false;
        state = SyncState::DONE;
      }
      requestUpdate(HalDisplay::FULL_REFRESH);
    } else if (status == WifiConnector::Status::FAILED) {
      syncOk = false;
      state = SyncState::DONE;
      requestUpdate(HalDisplay::FULL_REFRESH);
    } else if (millis() - lastSpinnerTickMs > SPINNER_TICK_MS) {
      lastSpinnerTickMs = millis();
      spinnerFrame++;
      requestUpdate();
    }
    return;
  }

  // PUSHING: one todo.update_item per loop() tick, so the back button stays
  // responsive and the spinner keeps animating across a batch of pushes
  // instead of one long blocking burst.
  const String& uid = pushQueue[pushIndex];
  bool checked = false;
  for (auto& item : items) {
    if (item.uid == uid) {
      checked = item.checked;
      break;
    }
  }
  if (haClient.updateTodoItem(SETTINGS.haShoppingListEntity, uid, checked)) {
    for (auto& item : items) {
      if (item.uid == uid) {
        item.dirty = false;
        break;
      }
    }
  }
  // On failure item.dirty stays true — reconcile() will detect it as still
  // dirty next sync and re-queue it, no separate retry bookkeeping needed.

  pushIndex++;
  if (pushIndex >= pushQueue.size()) {
    finishSync();
    syncOk = true;
    state = SyncState::DONE;
    requestUpdate(HalDisplay::FULL_REFRESH);
  } else {
    if (millis() - lastSpinnerTickMs > SPINNER_TICK_MS) {
      lastSpinnerTickMs = millis();
      spinnerFrame++;
    }
    requestUpdate();
  }
}

void ShoppingListActivity::reconcile(const std::vector<HomeAssistantClient::TodoItem>& remote) {
  std::vector<InkBridgeSettings::ShoppingItem> local = items;

  auto findByUid = [&local](const String& uid) -> InkBridgeSettings::ShoppingItem* {
    for (auto& item : local) {
      if (item.uid == uid) return &item;
    }
    return nullptr;
  };

  std::vector<InkBridgeSettings::ShoppingItem> reconciled;
  pushQueue.clear();

  // `remote` defines which uids exist at all — item existence is always
  // HA's call, so a uid present only in `local` (deleted on HA's side)
  // simply isn't iterated and drops out here.
  for (const auto& r : remote) {
    InkBridgeSettings::ShoppingItem* l = findByUid(r.uid);

    InkBridgeSettings::ShoppingItem item;
    item.uid = r.uid;
    item.text = r.text;

    // Conflict policy: a locally-dirty item always wins and gets pushed,
    // regardless of what HA's copy says — HA exposes no per-item timestamp
    // to weigh "who changed it more recently" any other way. Otherwise
    // (not dirty), HA's value is authoritative and gets pulled in.
    if (l && l->dirty) {
      item.checked = l->checked;
      item.dirty = true;
      pushQueue.push_back(r.uid);
    } else {
      item.checked = r.checked;
      item.dirty = false;
    }
    reconciled.push_back(item);
  }

  items = reconciled;
}

void ShoppingListActivity::finishSync() {
  SETTINGS.setShoppingList(items);
  SETTINGS.saveShoppingList();
}

void ShoppingListActivity::sortItems() {
  std::stable_sort(items.begin(), items.end(),
                    [](const InkBridgeSettings::ShoppingItem& a,
                       const InkBridgeSettings::ShoppingItem& b) { return a.checked < b.checked; });
}

void ShoppingListActivity::onSelectRow(int index) {
  if (index < 0 || index >= (int)items.size()) return;
  String uid = items[index].uid;
  items[index].checked = !items[index].checked;
  items[index].dirty = true;
  sortItems();
  // Follow the toggled item to its new row, since it just moved (checked
  // items sink to the bottom) — otherwise `selected` would silently land on
  // whatever item happens to now occupy the old row index.
  for (int i = 0; i < (int)items.size(); i++) {
    if (items[i].uid == uid) {
      selected = i;
      break;
    }
  }
  clampScroll();
  SETTINGS.setShoppingList(items);
  SETTINGS.saveShoppingList();  // NVS only — no network call, pushed on next sync
  requestUpdate();
}

void ShoppingListActivity::render() {
  if (state == SyncState::DONE) {
    UiListActivity::render();
    return;
  }
  auto& g = display.gfx();
  g.fillScreen(GxEPD_WHITE);
  UiChrome::drawHeader(TR(SHOPPING_LIST));
  Icons::spinner(g, g.width() / 2, g.height() / 2, 36, spinnerFrame);
}

void ShoppingListActivity::drawRow(int index, int y, bool rowSelected) {
  auto& g = display.gfx();
  auto& t = display.text();
  const auto& item = items[index];
  int h = rowHeight();

  // No bordered/filled pill here (explicitly no row borders) — the
  // currently-selected row gets a small leading caret instead, since 2-button
  // nav still needs some focus indicator.
  if (rowSelected) {
    int cy = y + h / 2;
    g.fillTriangle(2, cy - 4, 2, cy + 4, 7, cy, GxEPD_BLACK);
  }

  int boxSize = 14;
  int boxX = 10;
  int boxY = y + (h - boxSize) / 2;
  if (item.checked) {
    g.fillRect(boxX, boxY, boxSize, boxSize, GxEPD_BLACK);
  } else {
    g.drawRect(boxX, boxY, boxSize, boxSize, GxEPD_BLACK);
  }

  int textX = boxX + boxSize + 6;
  int maxW = g.width() - textX - 8;  // leave room for the scrollbar gutter
  String label = truncateToWidth(item.text, maxW);

  t.setFont(UITheme::FONT_BODY);
  t.setForegroundColor(GxEPD_BLACK);
  int baseline = y + (h + t.getFontAscent()) / 2;
  t.setCursor(textX, baseline);
  t.print(label);

  if (item.checked) {
    int textW = t.getUTF8Width(label.c_str());
    g.drawFastHLine(textX, y + h / 2, textW, GxEPD_BLACK);
  }
}

String ShoppingListActivity::truncateToWidth(const String& text, int maxWidth) const {
  auto& t = display.text();
  t.setFont(UITheme::FONT_BODY);
  if (t.getUTF8Width(text.c_str()) <= maxWidth) return text;

  const char* ELLIPSIS = "\xE2\x80\xA6";  // UTF-8 "…"
  String candidate = text;
  while (candidate.length() > 0) {
    // Drop one whole UTF-8 codepoint (continuation bytes are 10xxxxxx) —
    // this app's fonts carry Latin-1 accents, so a byte-wise cut could split
    // one and corrupt the glyph stream.
    int cut = candidate.length() - 1;
    while (cut > 0 && (candidate[cut] & 0xC0) == 0x80) cut--;
    candidate = candidate.substring(0, cut);
    String withEllipsis = candidate + ELLIPSIS;
    if (t.getUTF8Width(withEllipsis.c_str()) <= maxWidth) return withEllipsis;
  }
  return ELLIPSIS;
}
