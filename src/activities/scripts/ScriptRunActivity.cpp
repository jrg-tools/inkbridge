#include "ScriptRunActivity.h"

#include <HalGPIO.h>
#include <WiFi.h>

#include "../../components/Icons.h"
#include "../../components/UiChrome.h"
#include "../../i18n/I18n.h"
#include "../ActivityManager.h"

void ScriptRunActivity::onEnter() {
  Activity::onEnter();
  connector.begin();
  state = connector.status() == WifiConnector::Status::NO_NETWORKS ? State::NO_WIFI
                                                                     : State::CONNECTING;
}

void ScriptRunActivity::onExit() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  Activity::onExit();
}

void ScriptRunActivity::loop() {
  if (gpio.wasLongPressed(HalGPIO::BTN_B)) {
    activityManager.popActivity();
    return;
  }

  if (state != State::CONNECTING) return;

  auto status = connector.update();

  if (status == WifiConnector::Status::CONNECTED) {
    Serial.printf("[ScriptRun] connected, running script.%s\n", script.id.c_str());
    haClient.begin(SETTINGS.haHost, SETTINGS.haPort, SETTINGS.haToken);
    bool ok = haClient.runScript(script.id);
    if (ok) {
      activityManager.popActivity();  // no separate "done" screen
    } else {
      state = State::FAILED;
      requestUpdate(HalDisplay::FULL_REFRESH);
    }
  } else if (status == WifiConnector::Status::FAILED) {
    Serial.println("[ScriptRun] all networks failed");
    state = State::FAILED;
    requestUpdate(HalDisplay::FULL_REFRESH);
  } else if (millis() - lastSpinnerTickMs > SPINNER_TICK_MS) {
    lastSpinnerTickMs = millis();
    spinnerFrame++;
    requestUpdate();
  }
}

void ScriptRunActivity::render() {
  auto& g = display.gfx();
  auto& t = display.text();
  g.fillScreen(GxEPD_WHITE);
  UiChrome::drawHeader(script.label.c_str());

  auto centered = [&](const char* text, int baseline) {
    int w = t.getUTF8Width(text);
    t.setCursor((g.width() - w) / 2, baseline);
    t.print(text);
  };

  t.setForegroundColor(GxEPD_BLACK);
  t.setFont(UITheme::FONT_BODY);

  switch (state) {
    case State::NO_WIFI:
      centered(TR(NO_WIFI_CONFIGURED), g.height() / 2);
      break;
    case State::CONNECTING:
      Icons::spinner(g, g.width() / 2, g.height() / 2, 36, spinnerFrame);
      break;
    case State::FAILED:
      centered(TR(SEND_FAILED), g.height() / 2);
      break;
  }
}
