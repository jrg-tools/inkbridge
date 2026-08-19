#include "TransferActivity.h"

#include "../ActivityManager.h"
#include "../network/SetupApActivity.h"
#include "../remote/RemoteActivity.h"

void TransferActivity::drawRow(int index, int y, bool rowSelected) {
  int x = 4, w = display.width() - 12, h = rowHeight() - 3;
  UiChrome::drawRowButton(x, y, w, h, rowSelected);
  UiChrome::drawButtonLabel(x, y, w, h,
                            index == 0 ? TR(SETUP_HOTSPOT) : TR(CONNECT_WIFI),
                            rowSelected);
}

void TransferActivity::onSelectRow(int index) {
  if (index == 0) {
    activityManager.pushActivity(std::make_unique<SetupApActivity>());
  } else {
    activityManager.pushActivity(std::make_unique<RemoteActivity>());
  }
}

void TransferActivity::onBack() { activityManager.popActivity(); }
