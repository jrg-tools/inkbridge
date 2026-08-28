// inkbridge — Home Assistant e-ink remote (XIAO ESP32-S3 + Waveshare 2.13" V4)
//
// Architecture follows CrossPoint Reader: HAL singletons (display, gpio),
// Activity/ActivityManager screen stack, SETTINGS persistence singleton.
// Boot goes straight to the menu; no radio is started until the user asks.

#include <Arduino.h>
#include <HalDisplay.h>
#include <HalGPIO.h>

#include "InkBridgeSettings.h"
#include "Version.h"
#include "activities/ActivityManager.h"
#include "activities/menu/MainMenuActivity.h"
#include "components/UITheme.h"

HalDisplay display;
HalGPIO gpio;
ActivityManager activityManager;

namespace {
void drawSplash() {
  auto& g = display.gfx();
  auto& t = display.text();
  g.fillScreen(GxEPD_WHITE);
  t.setFont(UITheme::FONT_TITLE);
  t.setForegroundColor(GxEPD_BLACK);
  int w = t.getUTF8Width("inkbridge");
  t.setCursor((g.width() - w) / 2, 60);
  t.print("inkbridge");
  t.setFont(UITheme::FONT_SMALL);
  String version = String("v") + INKBRIDGE_VERSION;
  w = t.getUTF8Width(version.c_str());
  t.setCursor((g.width() - w) / 2, 78);
  t.print(version);
}
}  // namespace

void setup() {
  Serial.begin(115200);

  gpio.begin();
  display.begin();
  SETTINGS.load();
  UITheme::applyFontFamily(SETTINGS.fontFamily);

  display.refresh(drawSplash, HalDisplay::FULL_REFRESH);

  activityManager.replaceActivity(std::make_unique<MainMenuActivity>());
  Serial.println("[Main] inkbridge ready");
}

void loop() {
  gpio.update();
  activityManager.loop();
  delay(10);
}
