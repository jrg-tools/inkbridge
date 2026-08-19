#pragma once
#include "../UiListActivity.h"

// Root menu: Transfer (WiFi/HA connectivity) and Settings (device options).
class MainMenuActivity : public UiListActivity {
 public:
  MainMenuActivity() : UiListActivity("MainMenu") {}

 protected:
  int rowCount() const override { return 2; }
  void drawRow(int index, int y, bool selected) override;
  void onSelectRow(int index) override;
  // Root screen — nothing to go back to.
  void onBack() override {}
};
