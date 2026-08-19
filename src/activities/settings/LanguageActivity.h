#pragma once
#include "../UiListActivity.h"

// Language selection submenu.
//   A short: next   B short: apply language   B long: back
class LanguageActivity : public UiListActivity {
 public:
  LanguageActivity() : UiListActivity("Language") {}

 protected:
  int rowCount() const override;
  void drawRow(int index, int y, bool selected) override;
  void onSelectRow(int index) override;
  void onBack() override;
};
