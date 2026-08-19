#include "MainMenuActivity.h"

#include "../ActivityManager.h"
#include "../settings/SettingsActivity.h"
#include "../transfer/TransferActivity.h"

void MainMenuActivity::drawRow(int index, int y, bool rowSelected) {
  int x = 4, w = display.width() - 12, h = rowHeight() - 3;
  UiChrome::drawRowButton(x, y, w, h, rowSelected);
  UiChrome::drawButtonLabel(x, y, w, h,
                            index == 0 ? TR(TRANSFER) : TR(SETTINGS_MENU),
                            rowSelected);
}

void MainMenuActivity::onSelectRow(int index) {
  if (index == 0) {
    activityManager.pushActivity(std::make_unique<TransferActivity>());
  } else {
    activityManager.pushActivity(std::make_unique<SettingsActivity>());
  }
}
