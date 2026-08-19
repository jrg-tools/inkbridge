#include "SystemActivity.h"

#include <HalBattery.h>
#include <HalGPIO.h>

#include "../../InkBridgeSettings.h"
#include "../../Version.h"
#include "../../components/UiChrome.h"
#include "../../i18n/I18n.h"
#include "../ActivityManager.h"

void SystemActivity::loop() {
  if (gpio.wasLongPressed(HalGPIO::BTN_B)) {
    activityManager.popActivity();
  }
}

void SystemActivity::render() {
  auto& g = display.gfx();
  auto& t = display.text();
  g.fillScreen(GxEPD_WHITE);
  UiChrome::drawHeader();

  int y = UITheme::CONTENT_Y + 16;
  auto row = [&](const char* label, const String& value) {
    t.setFont(UITheme::FONT_SMALL);
    t.setForegroundColor(GxEPD_BLACK);
    t.setCursor(6, y);
    t.print(label);
    y += 15;
    t.setFont(UITheme::FONT_BODY);
    t.setCursor(12, y);
    t.print(value);
    y += 24;
  };

  row(TR(VERSION), String("v") + INKBRIDGE_VERSION);
  row(TR(BATTERY), String(battery.percent()) + "%");
  row(TR(HOTSPOT), SETTINGS.apSsid);
  row(TR(PASSWORD), SETTINGS.apPassword.length() ? SETTINGS.apPassword : "-");
}
