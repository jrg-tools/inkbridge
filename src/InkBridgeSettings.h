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
  // Gates the main menu's Shopping List button — off by default until the
  // user opts in via the web UI (which also picks haShoppingListEntity from
  // a fetched list of the HA instance's actual `todo` entities).
  bool shoppingListEnabled = false;
  // Full entity_id of the HA `todo` list to sync (e.g. "todo.shopping_list").
  String haShoppingListEntity = "todo.shopping_list";

  // A script quick-action button shown in the main menu's Scripts list.
  // `id` is the part after "script." — run via script.turn_on + entity_id.
  // `icon` selects a built-in device icon (see Icons::byKey for the full
  // key list); unknown/empty falls back to the generic bolt.
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

  // One HA todo-list item, mirrored locally. `dirty` means the checked state
  // was toggled on-device since the last successful push to HA — it's local
  // runtime state, never sent to/read from the web config API. This is also
  // the whole conflict policy: reconcile() pushes whenever `dirty` is true
  // and pulls HA's value otherwise, so a dirty item always wins regardless
  // of what else changed remotely (HA gives no per-item timestamp to compare
  // against, so "local touched it since last sync" is the only signal used).
  struct ShoppingItem {
    String uid;
    String text;
    bool checked = false;
    bool dirty = false;
  };
  // JSON array of ShoppingItem, mutated by ShoppingListActivity via
  // setShoppingList() + saveShoppingList() — not part of the web config API's
  // settings payload (see ConfigWebServer).
  String shoppingItems = "[]";

  void load();
  void save() const;
  // Narrow NVS write: touches only the shopping-list key, so a checkbox tap
  // never rewrites haToken/wifiNetworks/etc. like save() would.
  void saveShoppingList() const;

  std::vector<ScriptButton> scripts() const;
  std::vector<WifiNetwork> wifis() const;
  std::vector<ShoppingItem> shoppingList() const;
  void setShoppingList(const std::vector<ShoppingItem>& items);

 private:
  InkBridgeSettings() = default;
};

#define SETTINGS InkBridgeSettings::getInstance()
