#pragma once
#include "../UiListActivity.h"

// Settings menu: Language and System submenus.
//   A short: next   B short: open   B long: back
class SettingsActivity : public UiListActivity {
 public:
  SettingsActivity() : UiListActivity("Settings") {}

 protected:
  int rowCount() const override;
  void drawRow(int index, int y, bool selected) override;
  void onSelectRow(int index) override;
  void onBack() override;
};
