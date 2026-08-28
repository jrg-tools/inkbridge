// inkbridge — Home Assistant e-ink remote (XIAO ESP32-S3 + Waveshare 2.13" V4)
//
// Architecture follows CrossPoint Reader: HAL singletons (display, gpio),
// Activity/ActivityManager screen stack, SETTINGS persistence singleton.
// Boot goes straight to the menu; no radio is started until the user asks.

#include <Arduino.h>
#include <HalDisplay.h>
#include <HalGPIO.h>
#include <esp_sleep.h>
#include <string.h>

#include "IdleSleep.h"
#include "InkBridgeSettings.h"
#include "Version.h"
#include "activities/ActivityManager.h"
#include "activities/menu/MainMenuActivity.h"
#include "components/UITheme.h"

HalDisplay display;
HalGPIO gpio;
ActivityManager activityManager;

namespace {
// Only sleeps while idle on the root menu — WiFi is always off there, and it
// avoids cutting off an in-progress WiFi connect/config flow on another
// screen. Neither button GPIO is RTC-capable, so true deep sleep (ext0/ext1
// wakeup) isn't available on this wiring; light sleep's GPIO wakeup works on
// any digital pin and still preserves all state, so waking just resumes
// loop() normally.

// The header's status icons (moon/lightning bolt) only reflect current
// state when something else triggers a redraw — a button press, or a
// screen change. Left alone, an icon would go stale the moment the USB
// cable is (un)plugged in the background, or once the idle timer crosses
// into its pre-sleep warning window with nothing pressed in the meantime.
// Poll both for a change and, if seen, refresh just that corner — cheap to
// check every loop(), and only touches the display on an actual transition.
bool lastUsbPlugged = false;
bool lastNearSleep = false;

void enterLightSleep() {
  Serial.println("[Main] idle — light sleep until a button is pressed");
  Serial.flush();
  gpio.prepareForSleep();
  esp_light_sleep_start();
  gpio.begin();  // sleep's GPIO wakeup config overwrote the FALLING-edge ISR setup
  Serial.println("[Main] woke up");
}

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
  IdleSleep::noteActivity();
  lastUsbPlugged = Serial.isPlugged();
  Serial.println("[Main] inkbridge ready");
}

void loop() {
  gpio.update();
  if (gpio.anyEventThisFrame()) IdleSleep::noteActivity();
  activityManager.loop();

  Activity* current = activityManager.getCurrentActivity();
  bool onRootMenu = current && strcmp(current->getName(), "MainMenu") == 0;

  // The moon hint only ever applies on the root menu (the only screen the
  // idle-sleep timer runs on), so a stale flag elsewhere is harmless — it's
  // never read outside that screen's own render().
  bool usbPlugged = Serial.isPlugged();
  bool nearSleep = onRootMenu && IdleSleep::nearTimeout();
  if (current && (usbPlugged != lastUsbPlugged || nearSleep != lastNearSleep)) {
    lastUsbPlugged = usbPlugged;
    lastNearSleep = nearSleep;
    display.refreshRegion(display.width() - 20, 0, 20, UITheme::HEADER_H,
                           [current] { current->render(); });
  }

  if (onRootMenu && IdleSleep::timedOut()) {
    enterLightSleep();
    IdleSleep::noteActivity();
  }

  delay(10);
}
