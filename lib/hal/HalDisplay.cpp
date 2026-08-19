#include "HalDisplay.h"

HalDisplay::HalDisplay() : epd(GxEPD2_213_B74(PIN_CS, PIN_DC, PIN_RST, PIN_BUSY)) {}

void HalDisplay::begin() {
  epd.init(115200);
  epd.setRotation(0);  // portrait (122x250)
  u8f.begin(epd);
  u8f.setFontMode(1);       // transparent background
  u8f.setFontDirection(0);  // left to right
  u8f.setForegroundColor(GxEPD_BLACK);
  u8f.setBackgroundColor(GxEPD_WHITE);  // safety net if solid mode sneaks in
}

void HalDisplay::refresh(const std::function<void()>& drawFrame, RefreshMode mode) {
  if (mode == FAST_REFRESH && ++fastRefreshCount >= FULL_REFRESH_INTERVAL) {
    mode = FULL_REFRESH;
  }
  if (mode == FULL_REFRESH) {
    fastRefreshCount = 0;
    epd.setFullWindow();
  } else {
    epd.setPartialWindow(0, 0, epd.width(), epd.height());
  }
  epd.firstPage();
  do {
    drawFrame();
  } while (epd.nextPage());
}

void HalDisplay::refreshRegion(int x, int y, int w, int h,
                               const std::function<void()>& drawFrame) {
  epd.setPartialWindow(x, y, w, h);
  epd.firstPage();
  do {
    drawFrame();
  } while (epd.nextPage());
}
