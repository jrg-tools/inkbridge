#include "ConnectWifiActivity.h"

#include <ESPmDNS.h>
#include <HalGPIO.h>
#include <WiFi.h>

#include "../../components/QrCode.h"
#include "../../components/UiChrome.h"
#include "../../i18n/I18n.h"
#include "../ActivityManager.h"

void ConnectWifiActivity::onEnter() {
  Activity::onEnter();
  connector.begin();
  state = connector.status() == WifiConnector::Status::NO_NETWORKS ? State::NO_WIFI
                                                                     : State::CONNECTING;
}

void ConnectWifiActivity::onExit() {
  webServer.stop();
  MDNS.end();
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  Activity::onExit();
}

void ConnectWifiActivity::loop() {
  if (gpio.wasLongPressed(HalGPIO::BTN_B)) {
    activityManager.popActivity();
    return;
  }

  if (state == State::CONNECTED) {
    webServer.loop();
    return;
  }

  if (state != State::CONNECTING) return;

  String prevSsid = connector.ssid();
  auto status = connector.update();

  if (status == WifiConnector::Status::CONNECTED) {
    ip = WiFi.localIP().toString();
    Serial.printf("[ConnectWifi] connected, IP %s\n", ip.c_str());
    MDNS.begin("inkbridge");
    webServer.begin(/*apMode=*/false);
    state = State::CONNECTED;
    requestUpdate(HalDisplay::FULL_REFRESH);
  } else if (status == WifiConnector::Status::FAILED) {
    Serial.println("[ConnectWifi] all networks failed");
    state = State::FAILED;
    requestUpdate(HalDisplay::FULL_REFRESH);
  } else if (connector.ssid() != prevSsid) {
    requestUpdate();  // moved on to the next network — refresh the SSID text
  }
}

void ConnectWifiActivity::render() {
  auto& g = display.gfx();
  auto& t = display.text();
  g.fillScreen(GxEPD_WHITE);
  UiChrome::drawHeader(TR(CONNECT_WIFI));

  auto centered = [&](const char* text, int baseline) {
    int w = t.getUTF8Width(text);
    t.setCursor((g.width() - w) / 2, baseline);
    t.print(text);
  };

  t.setForegroundColor(GxEPD_BLACK);

  switch (state) {
    case State::NO_WIFI: {
      t.setFont(UITheme::FONT_BODY);
      centered(TR(NO_WIFI_CONFIGURED), g.height() / 2);
      break;
    }
    case State::CONNECTING: {
      t.setFont(UITheme::FONT_BODY);
      centered(TR(CONNECTING), g.height() / 2 - 10);
      t.setFont(UITheme::FONT_SMALL);
      centered(connector.ssid().c_str(), g.height() / 2 + 12);
      break;
    }
    case State::FAILED: {
      t.setFont(UITheme::FONT_BODY);
      centered(TR(WIFI_FAILED), g.height() / 2);
      break;
    }
    case State::CONNECTED: {
      // Scan-to-open QR right under the header (server URL by IP — most
      // reliable to resolve; the mDNS name is shown alongside for manual use).
      int qrTop = UITheme::CONTENT_Y + 2;
      String url = String("http://") + ip + "/";
      int qrSize = drawQrCode(g, url.c_str(), qrTop, GxEPD_BLACK);

      int y = qrTop + qrSize + 16;
      t.setFont(UITheme::FONT_SMALL);
      centered("inkbridge.local", y);
      y += 13;
      centered(ip.c_str(), y);
      break;
    }
  }
}
