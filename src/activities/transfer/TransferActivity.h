#pragma once
#include "../UiListActivity.h"

// Transfer menu: WiFi/HA connectivity actions.
//   A short: next   B short: open   B long: back
class TransferActivity : public UiListActivity {
 public:
  TransferActivity() : UiListActivity("Transfer") {}

 protected:
  int rowCount() const override { return 2; }
  void drawRow(int index, int y, bool selected) override;
  void onSelectRow(int index) override;
  void onBack() override;
};
