#include "SettingsActivity.h"

#include "../ActivityManager.h"
#include "LanguageActivity.h"
#include "SystemActivity.h"

int SettingsActivity::rowCount() const { return 2; }

void SettingsActivity::drawRow(int index, int y, bool rowSelected) {
  int x = 4, w = display.width() - 12, h = rowHeight() - 3;
  UiChrome::drawRowButton(x, y, w, h, rowSelected);
  UiChrome::drawButtonLabel(x, y, w, h,
                            index == 0 ? TR(LANGUAGE) : TR(SYSTEM),
                            rowSelected);
}

void SettingsActivity::onSelectRow(int index) {
  if (index == 0) {
    activityManager.pushActivity(std::make_unique<LanguageActivity>());
  } else {
    activityManager.pushActivity(std::make_unique<SystemActivity>());
  }
}

void SettingsActivity::onBack() { activityManager.popActivity(); }
